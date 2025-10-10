"""iRODS tasks for Taskflow"""

import codecs
import logging
import math
import os
import random
import re
import string
import time

from datetime import datetime
from typing import Any, Optional, Union

from irods import keywords as kw
from irods.access import iRODSAccess
from irods.data_object import iRODSDataObject, iRODSReplica
from irods.exception import (
    GroupDoesNotExist,
    NetworkException,
    UserDoesNotExist,
    CAT_SUCCESS_BUT_WITH_NO_INFO,
)
from irods.models import Collection
from irods.path import iRODSPath

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.email import send_generic_mail
from projectroles.plugins import PluginAPI

# Landingzones dependency
from landingzones.utils import cleanup_file_prohibit

from taskflowbackend.constants import (
    IRODS_HASH_SCHEME_SHA256,
    IRODS_META_EMPTY_VALUE,
)
from taskflowbackend.tasks.base_task import BaseTask


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
plugin_api = PluginAPI()
User = get_user_model()


# Local constants
APP_NAME = 'taskflow'
APP_NAME_LZ = 'landingzones'
INHERIT_STRINGS = {True: 'inherit', False: 'noinherit'}
CHECKSUM_FILE_RE = re.compile(r'([^\w.])')
CHECKSUM_RETRY = 5
NO_FILE_CHECKSUM_LABEL = 'None'
VERIFY_ERR_MSG = 'iRODS sample data verification failed'

EMAIL_MSG_VERIFY_FAILED = r'''
Verifying file integrity in sample data for the project
"{project_title}"
has failed. Please contact an administrator or the site
contact address for assistance.

Assay: {assay_name}

Reported errors:
{ex_msg}

See the project files in the following URL:
{url}

'''.lstrip()


# Mixins -----------------------------------------------------------------------


class IrodsAccessMixin:
    """Mixin for iRODS access helpers"""

    def execute_set_access(
        self,
        access_name: str,
        path: str,
        user_name: str,
        obj_target: bool,
        recursive: bool,
    ):
        """
        Set access for user in a single data object or collection.

        :param access_name: Access level to set (string)
        :param path: Full iRODS path to collection or data object (string)
        :param user_name: Name of user or group (string)
        :param obj_target: Whether target is a data object (boolean)
        :param recursive: Set collection access recursively if True (boolean)
        """
        if not self.execute_data.get('access_names'):
            self.execute_data['access_names'] = {}
        if obj_target:
            target = self.irods.data_objects.get(path)
            recursive = False
        else:
            target = self.irods.collections.get(path)
            recursive = recursive
        target_access = self.irods.acls.get(target=target)

        user_access = next(
            (x for x in target_access if x.user_name == user_name), None
        )
        modifying_data = False
        if user_access and user_access.access_name != access_name:
            self.execute_data['access_names'][path] = user_access.access_name
            modifying_data = True
        elif not user_access:
            self.execute_data['access_names'][path] = 'null'
            modifying_data = True

        if modifying_data:
            acl = iRODSAccess(
                access_name=access_name,
                path=path,
                user_name=user_name,
                user_zone=self.irods.zone,
            )
            self.irods.acls.set(acl, recursive=recursive)
            self.data_modified = True  # Access was modified

    def revert_set_access(
        self,
        path: str,
        user_name: str,
        obj_target: bool,
        recursive: bool,
    ):
        """
        Revert setting access for user in a single collection or data object.

        :param path: Full iRODS path to collection or data object (string)
        :param user_name: Name of user or group (string)
        :param obj_target: Whether target is a data object (boolean)
        :param recursive: Set collection access recursively if True (boolean)
        """
        if self.data_modified:
            acl = iRODSAccess(
                access_name=self.execute_data['access_names'][path],
                path=path,
                user_name=user_name,
                user_zone=self.irods.zone,
            )
            recursive = False if obj_target else recursive
            self.irods.acls.set(acl, recursive=recursive)


class ProgressCounterMixin:
    """Mixin for file operation progress counter helpers"""

    @classmethod
    def update_zone_progress(
        cls,
        zone: Any,
        status_base: str,
        current: int,
        previous: int,
        total: int,
        time_start: datetime,
    ) -> tuple[int, datetime]:
        """
        Update landing zone status for progress counter.

        :param zone: LandingZone object
        :param status_base: Base status message (string)
        :param current: Current file index (int)
        :param previous: Previous logged file index (int)
        :param total: Total file count (int)
        :param time_start: Time of operation start (datetime)
        :return: Tuple of int, datetime
        """
        interval = settings.TASKFLOW_ZONE_PROGRESS_INTERVAL
        if time.time() - time_start > interval and previous != current:
            pct = math.floor(current / total * 100) if total > 0 else '?'
            zone.set_status(
                zone.status, f'{status_base} ({current}/{total}: {pct}%)'
            )
            return current, time.time()
        return previous, time_start  # If not updated, return previous values

    @classmethod
    def set_zone_final_status(cls, zone: Any, status_base: str, total: int):
        """
        Set final progress status for landing zone.

        :param zone: LandingZone object
        :param status_base: Base status message (string)
        :param total: Total file count (int)
        """
        zone.set_status(zone.status, f'{status_base} ({total}/{total}: 100%)')


# Base Task --------------------------------------------------------------------


class IrodsBaseTask(BaseTask):
    """Base iRODS task"""

    def __init__(self, name, force_fail=False, inject=None, *args, **kwargs):
        super().__init__(
            name, force_fail=force_fail, inject=inject, *args, **kwargs
        )
        self.name = f'<iRODS> {name} ({self.__class__.__name__})'
        self.irods = kwargs['irods']

    def raise_irods_exception(self, ex: Exception, info: Optional[str] = None):
        """
        Raise an exception when taskflow doesn't catch a proper exception from
        the iRODS client.
        """
        desc = '{} failed: {}'.format(
            self.__class__.__name__,
            (ex if str(ex) not in ['', 'None'] else ex.__class__.__name__),
        )
        if info:
            desc += f'\n{info}'
        logger.error(desc)
        raise Exception(desc)


# Tasks ------------------------------------------------------------------------


class CreateCollectionTask(IrodsBaseTask):
    """
    Create collection and its parent collections if they doesn't exist (imkdir)
    """

    def execute(self, path: str, *args, **kwargs):
        # Create parent collections if they don't exist
        self.execute_data['created_colls'] = []
        for i in range(2, len(path.split('/')) + 1):
            sub_path = '/'.join(path.split('/')[:i])
            if not self.irods.collections.exists(sub_path):
                self.irods.collections.create(sub_path)
                self.execute_data['created_colls'].append(sub_path)
                self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, path: str, *args, **kwargs):
        if self.data_modified:
            for coll_path in reversed(self.execute_data['created_colls']):
                if self.irods.collections.exists(coll_path):
                    self.irods.collections.remove(coll_path, recurse=True)


# TODO: Refactor this as follows: Before removing, set a random metadata value
# TODO:     for the collection. If reverting, search for the version of the
# TODO:     deleted collection with the tag, recover that and remove the tag.
class RemoveCollectionTask(IrodsBaseTask):
    """Remove a collection if it exists (irm)"""

    # NOTE: Instead of using irm, move manually to trash with a specific name
    #       So we can be sure to recover the correct structure on revert
    #       (if collections with the same path are removed, they are collected
    #       in trash versioned with a timestamp, which we can't know for sure)
    def execute(self, path: str, *args, **kwargs):
        random_str = ''.join(
            random.SystemRandom().choice(string.ascii_lowercase + string.digits)
            for _ in range(16)
        )
        trash_path = iRODSPath(self.irods.zone, 'trash', random_str)

        if self.irods.collections.exists(path):
            self.irods.collections.create(trash_path)  # Must create this 1st

            try:
                self.irods.collections.move(src_path=path, dest_path=trash_path)
            # NOTE: iRODS/client doesn't like to return a proper exception here
            except Exception:
                pass
            # ..so let's test success manually just to be sure
            new_path = iRODSPath(trash_path, path.split('/')[-1])

            if self.irods.collections.exists(new_path):
                self.data_modified = True
                self.execute_data['trash_path'] = trash_path
            else:
                raise Exception('Failed to remove collection')
        super().execute(*args, **kwargs)

    def revert(self, path: str, *args, **kwargs):
        if self.data_modified:
            src_path = iRODSPath(
                self.execute_data['trash_path'], path.split('/')[-1]
            )
            dest_path = iRODSPath(*path.split('/')[:-1])
            self.irods.collections.move(src_path=src_path, dest_path=dest_path)
            # Delete temp trash collection
            self.irods.collections.remove(self.execute_data['trash_path'])


# TODO: Also refactor using the metadata trick, once time allows
class RemoveDataObjectTask(IrodsBaseTask):
    """Remove a data object if it exists (irm)"""

    def execute(self, path: str, *args, **kwargs):
        random_str = ''.join(
            random.SystemRandom().choice(string.ascii_lowercase + string.digits)
            for _ in range(16)
        )
        trash_path = iRODSPath(self.irods.zone, 'trash', random_str)

        if self.irods.data_objects.exists(path):
            self.irods.collections.create(trash_path)  # Must create this 1st
            try:
                self.irods.data_objects.move(
                    src_path=path, dest_path=trash_path
                )
            # NOTE: iRODS/client doesn't like to return a proper exception here
            except Exception:
                pass
            # ..so let's test success manually just to be sure
            new_path = iRODSPath(trash_path, path.split('/')[-1])

            if self.irods.data_objects.exists(new_path):
                self.data_modified = True
                self.execute_data['trash_path'] = trash_path
            else:
                raise Exception('Failed to remove data object')
        super().execute(*args, **kwargs)

    def revert(self, path: str, *args, **kwargs):
        if self.data_modified:
            src_path = iRODSPath(
                self.execute_data['trash_path'], path.split('/')[-1]
            )
            self.irods.data_objects.move(src_path=src_path, dest_path=path)
            # Delete temp trash collection
            self.irods.collections.remove(self.execute_data['trash_path'])


# TODO: Do we need to add several metadata items until the same key? If so,
# TODO: A separate task should be created
class SetCollectionMetadataTask(IrodsBaseTask):
    """
    Set new value to existing metadata item (imeta set). NOTE: will replace
    existing value with the same name.
    """

    def execute(
        self,
        path: str,
        name: str,
        value: Optional[str],
        units: Optional[str] = None,
        *args,
        **kwargs,
    ):
        coll = None
        try:
            coll = self.irods.collections.get(path)
        except Exception as ex:
            self.raise_irods_exception(ex)
        meta_item = None
        try:
            meta_item = coll.metadata.get_one(name)
        except Exception:
            pass

        if not value:  # HACK: Can not set empty value in imeta
            value = IRODS_META_EMPTY_VALUE
        if meta_item and value != meta_item.value:
            self.execute_data['value'] = str(meta_item.value)
            self.execute_data['units'] = (
                str(meta_item.units) if meta_item.units else None
            )
            meta_item.value = str(value)
            meta_item.units = str(units)
            self.irods.metadata.set(
                model_cls=Collection, path=path, meta=meta_item
            )
            self.data_modified = True
        elif not meta_item:
            coll.metadata.add(str(name), str(value), str(units))
            self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(
        self,
        path: str,
        name: str,
        value: Optional[str],
        units: Optional[str] = None,
        *args,
        **kwargs,
    ):
        if not self.data_modified:
            return
        coll = self.irods.collections.get(path)
        if self.execute_data:
            meta_item = coll.metadata.get_one(name)
            meta_item.value = str(self.execute_data['value'])
            meta_item.units = str(self.execute_data['units'])

            self.irods.metadata.set(
                model_cls=Collection, path=path, meta=meta_item
            )
        else:
            try:
                coll.metadata.remove(name, str(value), units)
            except CAT_SUCCESS_BUT_WITH_NO_INFO:
                pass


class CreateUserGroupTask(IrodsBaseTask):
    """Create user group if it doesn't exist (iadmin mkgroup)"""

    def execute(self, name: str, *args, **kwargs):
        try:
            self.irods.user_groups.get(name)
        except GroupDoesNotExist:
            self.irods.user_groups.create(name=name, user_zone=self.irods.zone)
            self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, name: str, *args, **kwargs):
        if self.data_modified:
            # NOTE: Not group_name
            self.irods.users.remove(user_name=name)


# TODO: Improve this once inherit is properly implemented in python client
# TODO: Tests
# See: https://github.com/irods/python-irodsclient/issues/85
class SetInheritanceTask(IrodsBaseTask):
    """Set collection inheritance (ichmod inherit)"""

    def execute(self, path: str, inherit: bool = True, *args, **kwargs):
        acl = iRODSAccess(
            access_name=INHERIT_STRINGS[inherit],
            path=path,
            user_name='',
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=True)

    def revert(self, path: str, inherit: bool = True, *args, **kwargs):
        # TODO: Add checks for inheritance status prior to execute
        pass
        '''
        acl = iRODSAccess(
            access_name=INHERIT_STRINGS[!inherit],
            path=path,
            user_name='',
            user_zone=self.irods.zone)
        self.irods.acls.set(acl, recursive=True)
        '''


class SetAccessTask(IrodsAccessMixin, IrodsBaseTask):
    """
    Set user/group access to target (ichmod). If the target is a data object
    (obj_target=True), the recursive argument will be ignored.
    """

    def execute(
        self,
        access_name: str,
        path: str,
        user_name: str,
        irods_backend: Any,
        obj_target: bool = False,
        recursive: bool = True,
        *args,
        **kwargs,
    ):
        try:
            self.execute_set_access(
                access_name,
                path,
                user_name,
                obj_target,
                recursive,
            )
        except Exception as ex:
            self.raise_irods_exception(ex, user_name)
        super().execute(*args, **kwargs)

    def revert(
        self,
        access_name: str,
        path: str,
        user_name: str,
        irods_backend: Any,
        obj_target: bool = False,
        recursive: bool = True,
        *args,
        **kwargs,
    ):
        try:
            self.revert_set_access(path, user_name, obj_target, recursive)
        except Exception:
            pass  # TODO: Log revert() exceptions?


class IssueTicketTask(IrodsBaseTask):
    """Create access ticket to a collection if not yet available"""

    def execute(
        self,
        access_name: str,
        path: str,
        ticket_str: str,
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        if not irods_backend.get_ticket(self.irods, ticket_str):
            try:
                irods_backend.issue_ticket(
                    self.irods, access_name, path, ticket_str
                )
                self.data_modified = True
            except Exception as ex:
                self.raise_irods_exception(ex)
        super().execute(*args, **kwargs)

    def revert(
        self,
        access_name: str,
        path: str,
        ticket_str: str,
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        if self.data_modified:
            irods_backend.delete_ticket(self.irods, ticket_str)


class DeleteTicketTask(IrodsBaseTask):
    """Delete access ticket if it exists"""

    def execute(
        self,
        access_name: str,
        path: str,
        ticket_str: str,
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        ticket = irods_backend.get_ticket(self.irods, ticket_str)
        if ticket:
            try:
                irods_backend.delete_ticket(self.irods, ticket_str)
                self.data_modified = True
            except Exception as ex:
                self.raise_irods_exception(ex)
        super().execute(*args, **kwargs)

    def revert(
        self,
        access_name: str,
        path: str,
        ticket_str: str,
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        if self.data_modified:
            irods_backend.issue_ticket(
                self.irods, access_name, path, ticket_str
            )


class CreateUserTask(IrodsBaseTask):
    """Create user if it does not exist (iadmin mkuser)"""

    # NOTE: Password not needed as users log in via LDAP

    def execute(self, user_name: str, user_type: str, *args, **kwargs):
        try:
            self.irods.users.get(user_name)
        except UserDoesNotExist:
            self.irods.users.create(
                user_name=user_name,
                user_type=user_type,
                user_zone=self.irods.zone,
            )
            self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, user_name: str, user_type: str, *args, **kwargs):
        # Remove user only if it was added in this run
        if self.data_modified:
            self.irods.users.remove(user_name)


class AddUserToGroupTask(IrodsBaseTask):
    """Add user to group if not yet added (iadmin atg)"""

    def execute(self, group_name: str, user_name: str, *args, **kwargs):
        try:
            group = self.irods.user_groups.get(group_name)
        except Exception as ex:
            self.raise_irods_exception(
                ex, info=f'Failed to retrieve group "{group_name}"'
            )
        if not group.hasmember(user_name):
            try:
                group.addmember(user_name=user_name, user_zone=self.irods.zone)
                self.data_modified = True
            except Exception as ex:
                self.raise_irods_exception(
                    ex,
                    info=f'Failed to add user "{user_name}" '
                    f'into group "{group_name}"',
                )
        super().execute(*args, **kwargs)

    def revert(self, group_name: str, user_name: str, *args, **kwargs):
        if self.data_modified:
            group = self.irods.user_groups.get(group_name)
            group.removemember(user_name=user_name, user_zone=self.irods.zone)


class RemoveUserFromGroupTask(IrodsBaseTask):
    """Remove user from group (iadmin rfg)"""

    def execute(self, group_name: str, user_name: str, *args, **kwargs):
        try:
            group = self.irods.user_groups.get(group_name)
        except GroupDoesNotExist:
            # This is ok, user isn't in a group that doesn't exist :)
            group = None
        if group:
            try:
                if group.hasmember(user_name):
                    group.removemember(
                        user_name=user_name, user_zone=self.irods.zone
                    )
                    self.data_modified = True
            except Exception as ex:
                self.raise_irods_exception(ex)
        super().execute(*args, **kwargs)

    def revert(self, group_name: str, user_name: str, *args, **kwargs):
        if self.data_modified:
            group = self.irods.user_groups.get(group_name)
            group.addmember(user_name=user_name, user_zone=self.irods.zone)


# TODO: Improve this to accept both obj/collection for dest_path in revert
class MoveDataObjectTask(IrodsBaseTask):
    """Move file to destination collection (imv)"""

    def execute(self, src_path: str, dest_path: str, *args, **kwargs):
        try:
            self.irods.data_objects.move(src_path=src_path, dest_path=dest_path)
            self.data_modified = True
        except Exception as ex:
            self.raise_irods_exception(ex)
        super().execute(*args, **kwargs)

    def revert(self, src_path: str, dest_path: str, *args, **kwargs):
        if self.data_modified:
            # TODO: First check if final item in path is obj or coll
            new_src = iRODSPath(dest_path, src_path.split('/')[-1])
            new_dest = iRODSPath(*src_path.split('/')[:-1])
            self.irods.data_objects.move(src_path=new_src, dest_path=new_dest)


# Batch Tasks ------------------------------------------------------------------


class BatchSetAccessTask(IrodsAccessMixin, IrodsBaseTask):
    """
    Set user/group access to multiple targets (ichmod). If a target is a data
    object (obj_target=True), the recursive argument will be ignored.
    """

    def execute(
        self,
        access_name: str,
        paths: str,
        user_name: str,
        irods_backend: Any,
        obj_target: bool = False,
        recursive: bool = True,
        *args,
        **kwargs,
    ):
        # NOTE: Exception handling is done within execute_set_access()
        for path in paths:
            self.execute_set_access(
                access_name,
                path,
                user_name,
                obj_target,
                recursive,
            )
        super().execute(*args, **kwargs)

    def revert(
        self,
        access_name: str,
        paths: str,
        user_name: str,
        irods_backend: Any,
        obj_target: bool = False,
        recursive: bool = True,
        *args,
        **kwargs,
    ):
        for path in paths:
            self.revert_set_access(path, user_name, obj_target, recursive)


class BatchCheckFileSuffixTask(IrodsBaseTask):
    """Batch check for prohibited file name suffixes"""

    def execute(
        self,
        file_paths: list[str],
        suffixes: list[str],
        zone_path: str,
        *args,
        **kwargs,
    ):
        suffixes = cleanup_file_prohibit(suffixes)
        if not suffixes:
            super().execute(*args, **kwargs)
            return
        err_paths = []
        for p in file_paths:
            if any(p.lower().endswith('.' + s) for s in suffixes):
                err_paths.append(p)
        err_len = len(err_paths)
        if err_len > 0:
            msg = '{} file{} found with prohibited file type ({}):\n{}'.format(
                err_len,
                's' if err_len != 1 else '',
                ', '.join(suffixes),
                '\n'.join([p.replace(zone_path + '/', '') for p in err_paths]),
            )
            logger.error(msg)
            self.raise_irods_exception(Exception(), msg)
        super().execute(*args, **kwargs)

    def revert(
        self,
        file_paths: list[str],
        suffixes: list[str],
        zone_path: str,
        *args,
        **kwargs,
    ):
        pass  # Nothing to revert


class BatchCheckFileExistTask(IrodsBaseTask):
    """
    Batch check for existence of files and corresponding checksum files
    """

    def execute(
        self,
        file_paths: list[str],
        chk_paths: list[str],
        zone_path: str,
        chk_suffix: str,
        *args,
        **kwargs,
    ):
        err_paths = []
        for p in file_paths:
            p_chk = p + chk_suffix
            if p_chk not in chk_paths:
                err_paths.append(p_chk)
        for p in chk_paths:
            p_file = p[: p.rfind('.')]
            if p_file not in file_paths:
                err_paths.append(p_file)
        err_len = len(err_paths)
        if err_len > 0:
            msg = '{} expected file{} missing:\n{}'.format(
                err_len,
                's' if err_len != 1 else '',
                '\n'.join([p.replace(zone_path + '/', '') for p in err_paths]),
            )
            logger.error(msg)
            self.raise_irods_exception(Exception(), msg)
        super().execute(*args, **kwargs)

    def revert(
        self,
        file_paths: list[str],
        chk_paths: list[str],
        zone_path: str,
        chk_suffix: str,
        *args,
        **kwargs,
    ):
        pass  # Nothing is modified so no need for revert


class BatchValidateChecksumsBase(IrodsBaseTask):
    """Base class for batch checksum validation"""

    def read_checksum(
        self, chk_path: str, zone_path_len: int, read_errors: list
    ) -> Union[str, bool]:
        """
        Read checksum file. Appends error and returns False if error is
        reached.
        """
        try:
            with self.irods.data_objects.open(chk_path, mode='r') as f:
                dec = 'utf-8'
                chk_content = f.read()
                # Support for BOM header forced by PowerShell (see #1818)
                if chk_content[:3] == codecs.BOM_UTF8:
                    dec += '-sig'
                return re.split(CHECKSUM_FILE_RE, chk_content.decode(dec))[0]
        except Exception as ex:
            ex_msg = 'File: {}\nException: {}'.format(
                '/'.join(chk_path.split('/')[zone_path_len:]), ex
            )
            read_errors.append(ex_msg)
            return False

    @classmethod
    def compare_checksums(
        cls,
        data_obj: iRODSDataObject,
        checksum: str,
        root_path_len: int,
        hash_scheme: str,
        irods_backend: Any,
    ):
        """
        Compare object replicate checksums to expected sum. Raises exception if
        checksums do not match.

        :param data_obj: Data object
        :param checksum: Expected checksum (string)
        :param root_path_len: File list root path collection depth (int)
        :param hash_scheme: Checksum hashing scheme (string)
        :param irods_backend: IrodsAPI object
        :raises: Exception if checksums do not match
        """
        for replica in data_obj.replicas:
            repl_checksum = replica.checksum
            if hash_scheme == IRODS_HASH_SCHEME_SHA256:
                # Convert SHA256 from base64
                repl_checksum = irods_backend.get_sha256_hex(repl_checksum)
            if (
                not checksum
                or not repl_checksum
                or checksum.lower() != repl_checksum.lower()
            ):
                log_msg = (
                    f'Checksums do not match for '
                    f'"{os.path.basename(data_obj.path)}" in resource '
                    f'"{replica.resource_name}" '
                    f'(File: {checksum or NO_FILE_CHECKSUM_LABEL}; '
                    f'iRODS: {repl_checksum})'
                )
                logger.error(log_msg)
                ex_path = '/'.join(data_obj.path.split('/')[root_path_len:])
                ex_msg = (
                    f'Path: {ex_path}\n'
                    f'Resource: {replica.resource_name}\n'
                    f'File: {checksum or NO_FILE_CHECKSUM_LABEL}\n'
                    f'iRODS: {repl_checksum}'
                )
                raise Exception(ex_msg)

    @classmethod
    def get_error_msg(
        cls, read_errors: list[str], cmp_errors: list[str]
    ) -> str:
        """
        Return output message in case of validation errors.

        :param read_errors: Errors in reading checksum files (list of strings)
        :param cmp_errors: Errors in comparing checksums (list of strings)
        :return: string
        """
        ret = ''
        if read_errors:
            err_len = len(read_errors)
            ret += 'Unable to read {} checksum file{}:\n'.format(
                err_len, 's' if err_len != 1 else ''
            )
            ret += '\n'.join(read_errors)
        if cmp_errors:
            err_len = len(cmp_errors)
            ret += '{}Checksums do not match for {} file{}:\n'.format(
                '\n' if read_errors else '',
                err_len,
                's' if err_len != 1 else '',
            )
            ret += '\n'.join(cmp_errors)
        return ret


class BatchValidateZoneChecksumsTask(
    ProgressCounterMixin, BatchValidateChecksumsBase
):
    """
    Batch validate checksums of a given list of landing zone data object paths.
    """

    def execute(
        self,
        landing_zone: Any,
        file_paths: list[str],
        zone_path: str,
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        zone_path_len = len(zone_path.split('/'))
        hash_scheme = settings.IRODS_HASH_SCHEME
        chk_suffix = irods_backend.get_checksum_file_suffix()
        file_count = len(file_paths)
        status_base = landing_zone.status_info
        i = 0
        i_prev = 0
        read_errors = []
        cmp_errors = []
        time_start = time.time()

        for f_path in file_paths:
            chk_path = f_path + chk_suffix
            file_sum = self.read_checksum(chk_path, zone_path_len, read_errors)
            if file_sum is not False:
                try:
                    self.compare_checksums(
                        self.irods.data_objects.get(f_path),
                        file_sum,
                        zone_path_len,
                        hash_scheme,
                        irods_backend,
                    )
                except Exception as ex:
                    cmp_errors.append(str(ex))

            i_prev, time_start = self.update_zone_progress(
                landing_zone, status_base, i, i_prev, file_count, time_start
            )
            i += 1
        self.set_zone_final_status(landing_zone, status_base, file_count)

        if read_errors or cmp_errors:
            ex_msg = self.get_error_msg(read_errors, cmp_errors)
            self.raise_irods_exception(Exception(), ex_msg)
        super().execute(*args, **kwargs)


class BatchVerifySampleChecksumsTask(
    ProgressCounterMixin, BatchValidateChecksumsBase
):
    """
    Batch verify checksums of a given list of sample data repository data
    object paths.
    """

    @classmethod
    def _add_alert(cls, assay: Any, user: User, ex_msg: str):
        """
        Add app alert for user if AppAlerts app is enabled and the user has
        landing zone alerts enabled.

        :param assay: Assay object
        :param user: User object
        :param ex_msg: String
        """
        app_alerts = plugin_api.get_backend_api('appalerts_backend')
        if not app_alerts or not app_settings.get(
            APP_NAME_LZ, 'notify_alert_zone_status', user=user
        ):
            logger.debug(f'{cls.__name__}: Alert not created, alerts disabled')
            return
        project = assay.get_project()
        alert_msg = (
            VERIFY_ERR_MSG + f':\nAssay: {assay.get_display_name()}\n' + ex_msg
        )
        app_alerts.add_alert(
            app_name=APP_NAME,
            alert_name='sample_data_verify',
            user=user,
            message=alert_msg,
            level='DANGER',
            url=reverse(
                'samplesheets:project_sheets',
                kwargs={'project': project.sodar_uuid},
            ),
            project=project,
        )
        logger.info(f'{cls.__name__}: Alert sent to {user.username}')

    @classmethod
    def _send_email(cls, assay: Any, user: User, ex_msg: str):
        """
        Send email to user if email sending is enabled and the user has email
        alerting enabled.

        :param assay: Assay object
        :param user: User object
        :param ex_msg: String
        """
        if not settings.PROJECTROLES_SEND_EMAIL or not app_settings.get(
            APP_NAME_LZ, 'notify_email_zone_status', user=user
        ):
            logger.debug(f'{cls.__name__}: Email not sent, email disabled')
            return
        project = assay.get_project()
        subject = VERIFY_ERR_MSG
        body = EMAIL_MSG_VERIFY_FAILED.format(
            project_title=project.title,
            assay_name=assay.get_display_name(),
            ex_msg=ex_msg,
            url=settings.SODAR_API_DEFAULT_HOST.geturl()
            + reverse(
                'samplesheets:project_sheets',
                kwargs={'project': project.sodar_uuid},
            ),
        )
        mail_sent = send_generic_mail(subject, body, [user])
        if mail_sent > 0:
            logger.info(f'{cls.__name__}: Email sent to {user.username}')

    def execute(
        self,
        file_paths: list[str],
        assay: Any,
        user: Optional[User],
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        root_path = irods_backend.get_path(assay)
        root_path_len = len(root_path.split('/'))
        hash_scheme = settings.IRODS_HASH_SCHEME
        chk_suffix = irods_backend.get_checksum_file_suffix()
        read_errors = []
        cmp_errors = []

        for f_path in file_paths:
            chk_path = f_path + chk_suffix
            file_sum = self.read_checksum(chk_path, root_path_len, read_errors)
            if file_sum is not False:
                try:
                    self.compare_checksums(
                        self.irods.data_objects.get(f_path),
                        file_sum,
                        root_path_len,
                        hash_scheme,
                        irods_backend,
                    )
                except Exception as ex:
                    cmp_errors.append(str(ex))

        if read_errors or cmp_errors:
            ex_msg = self.get_error_msg(read_errors, cmp_errors)
            if user:  # Add alert and send email for user
                self._add_alert(assay, user, ex_msg)
                self._send_email(assay, user, ex_msg)
            # NOTE: Timeline event gets updated on exception
            self.raise_irods_exception(Exception(), ex_msg)
        super().execute(*args, **kwargs)


class BatchCreateCollectionsTask(IrodsBaseTask):
    """Batch create collections from a list (imkdir)"""

    def execute(self, coll_paths: list[str], *args, **kwargs):
        # Create parent collections if they don't exist
        self.execute_data['created_colls'] = []
        for path in coll_paths:
            for i in range(2, len(path.split('/')) + 1):
                sub_path = '/'.join(path.split('/')[:i])
                try:
                    if not self.irods.collections.exists(sub_path):
                        self.irods.collections.create(sub_path)
                        self.execute_data['created_colls'].append(sub_path)
                        self.data_modified = True
                except Exception as ex:
                    self.raise_irods_exception(
                        ex,
                        f'Failed to create collection: {sub_path}',
                    )
        super().execute(*args, **kwargs)

    def revert(self, coll_paths: list[str], *args, **kwargs):
        if self.data_modified:
            for coll_path in reversed(self.execute_data['created_colls']):
                if self.irods.collections.exists(coll_path):
                    self.irods.collections.remove(coll_path, recurse=True)


class BatchMoveDataObjectsTask(ProgressCounterMixin, IrodsBaseTask):
    """Batch move files (imv) and set access to user group (ichmod)"""

    @staticmethod
    def get_dest_coll_path(src_path: str, src_root: str, dest_root: str) -> str:
        src_depth = len(src_root.split('/'))
        return iRODSPath(dest_root, *src_path.split('/')[src_depth:-1])

    @staticmethod
    def get_dest_obj_path(src_path: str, dest_path: str) -> str:
        return (
            dest_path
            + ('/' if dest_path[-1] != '/' else '')
            + src_path.split('/')[-1]
        )

    def execute(
        self,
        landing_zone: Any,
        src_root: str,
        dest_root: str,
        src_paths: list[str],
        access_name: str,
        user_name: str,
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        self.execute_data['moved_objects'] = []
        # Disregard checksum files in file count
        chk_suffix = irods_backend.get_checksum_file_suffix()
        file_count = len([p for p in src_paths if not p.endswith(chk_suffix)])
        status_base = landing_zone.status_info
        i = 0
        i_prev = 0
        time_start = time.time()

        for src_path in src_paths:
            dest_coll_path = self.get_dest_coll_path(
                src_path, src_root, dest_root
            )
            dest_obj_path = self.get_dest_obj_path(src_path, dest_coll_path)

            try:
                self.irods.data_objects.move(
                    src_path=src_path, dest_path=dest_obj_path
                )
            except Exception as ex:
                if ex.__class__.__name__ == 'CAT_NAME_EXISTS_AS_DATAOBJ':
                    msg = f'Target file already exists: {dest_obj_path}'
                else:
                    msg = (
                        f'Error moving move data object "{src_path}" to '
                        f'"{dest_obj_path}"'
                    )
                self.raise_irods_exception(ex, msg)
            try:
                target = self.irods.data_objects.get(dest_obj_path)
            except Exception as ex:
                self.raise_irods_exception(
                    ex,
                    f'Error retrieving destination object "{dest_obj_path}"',
                )
            try:
                target_access = self.irods.acls.get(target=target)
            except Exception as ex:
                self.raise_irods_exception(
                    ex,
                    f'Error getting permissions of target "{target}"',
                )

            # TODO: Remove repetition, use IrodsAccessMixin
            user_access = next(
                (x for x in target_access if x.user_name == user_name), None
            )
            prev_access = None
            if user_access and user_access.access_name != access_name:
                prev_access = user_access.access_name
                modifying_access = True
            elif not user_access:
                prev_access = 'null'
                modifying_access = True
            else:
                modifying_access = False
            self.execute_data['moved_objects'].append((src_path, prev_access))

            if modifying_access:
                acl = iRODSAccess(
                    access_name=access_name,
                    path=dest_obj_path,
                    user_name=user_name,
                    user_zone=self.irods.zone,
                )
                try:
                    self.irods.acls.set(acl, recursive=False)
                except Exception as ex:
                    self.raise_irods_exception(
                        ex,
                        f'Error setting permission for "{dest_coll_path}"',
                    )

            i_prev, time_start = self.update_zone_progress(
                landing_zone, status_base, i, i_prev, file_count, time_start
            )
            if not src_path.endswith(chk_suffix):
                i += 1  # Only increment progress counter with data files

        self.set_zone_final_status(landing_zone, status_base, file_count)
        super().execute(*args, **kwargs)

    def revert(
        self,
        landing_zone: Any,
        src_root: str,
        dest_root: str,
        src_paths: list[str],
        access_name: str,
        user_name: str,
        irods_backend: Any,
        *args,
        **kwargs,
    ):
        for moved_object in self.execute_data['moved_objects']:
            src_path = moved_object[0]
            prev_access = moved_object[1]
            dest_path = self.get_dest_coll_path(src_path, src_root, dest_root)
            new_src = (
                dest_path
                + ('/' if dest_path[-1] != '/' else '')
                + src_path.split('/')[-1]
            )
            new_dest = '/'.join(src_path.split('/')[:-1])
            new_dest_obj = iRODSPath(new_dest, src_path.split('/')[-1])
            self.irods.data_objects.move(src_path=new_src, dest_path=new_dest)

            acl = iRODSAccess(
                access_name=prev_access,
                path=new_dest_obj,
                user_name=user_name,
                user_zone=self.irods.zone,
            )
            self.irods.acls.set(acl, recursive=False)


class BatchCalculateChecksumTask(ProgressCounterMixin, IrodsBaseTask):
    """Batch calculate checksum for data objects (ichksum)"""

    def _raise_checksum_exception(
        self,
        ex: Exception,
        data_obj: iRODSDataObject,
        replica: iRODSReplica,
        info: Optional[str] = None,
    ):
        info_str = (': ' + info) if info else ''
        self.raise_irods_exception(
            ex,
            f'Failed to calculate checksum{info_str}\nReplica: '
            f'{replica.resc_hier}\nFile: {data_obj.path}',
        )

    def _compute_checksum(
        self, data_obj: iRODSDataObject, replica: iRODSReplica, force: bool
    ):
        if replica.checksum and not force:
            return
        for j in range(CHECKSUM_RETRY):
            if j > 0:  # Retry if iRODS times out (see #1941)
                logger.info(f'Retrying ({j + 1})..')
            try:
                c_kw = {kw.RESC_HIER_STR_KW: replica.resc_hier}
                if force:
                    c_kw[kw.FORCE_CHKSUM_KW] = ''
                data_obj.chksum(**c_kw)
                return
            # Retry for network exceptions
            except NetworkException as ex:
                logger.error(
                    f'NetworkException in BatchCalculateChecksumTask for path '
                    f'"{data_obj.path}" in replica "{replica.resc_hier}" '
                    f'(attempt {j + 1}/{CHECKSUM_RETRY}): {ex}'
                )
                # Raise if we reached maximum retry count
                if j == CHECKSUM_RETRY - 1:
                    info = 'maximum network timeout retry attempts reached'
                    self._raise_checksum_exception(ex, data_obj, replica, info)
            # Raise other exceptions normally
            except Exception as ex:
                self._raise_checksum_exception(ex, data_obj, replica)

    def execute(
        self,
        landing_zone: Any,
        file_paths: list[str],
        force: bool,
        *args,
        **kwargs,
    ):
        file_count = len(file_paths)
        if file_count == 0:  # Nothing to do
            super().execute(*args, **kwargs)
            return
        status_base = landing_zone.status_info if landing_zone else None
        i = 0
        i_prev = 0
        if landing_zone:
            landing_zone.set_status(
                landing_zone.status, f'{status_base} (0/{file_count}: 0%)'
            )  # Set initial status in case first file is a time consuming one
        time_start = time.time()
        for path in file_paths:
            if not self.irods.data_objects.exists(path):
                continue
            data_obj = self.irods.data_objects.get(path)
            for replica in data_obj.replicas:
                self._compute_checksum(data_obj, replica, force)
            if landing_zone:
                i_prev, time_start = self.update_zone_progress(
                    landing_zone, status_base, i, i_prev, file_count, time_start
                )
                i += 1
        if landing_zone:
            self.set_zone_final_status(landing_zone, status_base, file_count)
        super().execute(*args, **kwargs)
        # NOTE: We don't need revert for this
