"""iRODS tasks for Taskflow"""

import codecs
import logging
import math
import os
import random
import re
import string
import time

from irods import keywords as kw
from irods.access import iRODSAccess
from irods.exception import (
    GroupDoesNotExist,
    NetworkException,
    UserDoesNotExist,
    CAT_SUCCESS_BUT_WITH_NO_INFO,
)
from irods.models import Collection

from django.conf import settings

# Landingzones dependency
from landingzones.utils import cleanup_file_prohibit

from taskflowbackend.tasks.base_task import BaseTask


logger = logging.getLogger(__name__)


# Local constants
# NOTE: This is only compabitle with iRODS 4.3.
# Backwards compatibility with 4.2 has been removed in SODAR v1.0.
ACCESS_LOOKUP = {
    'read': 'read_object',
    'read_object': 'read',
    'write': 'modify_object',
    'modify_object': 'write',
    'null': 'null',
    'own': 'own',
}
INHERIT_STRINGS = {True: 'inherit', False: 'noinherit'}
META_EMPTY_VALUE = 'N/A'
CHECKSUM_FILE_RE = re.compile(r'([^\w.])')
CHECKSUM_RETRY = 5
NO_FILE_CHECKSUM_LABEL = 'None'
HASH_SCHEME_SHA256 = 'SHA256'


# Mixins -----------------------------------------------------------------------


class IrodsAccessMixin:
    """Mixin for iRODS access helpers"""

    def execute_set_access(
        self,
        access_name,
        path,
        user_name,
        obj_target,
        recursive,
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
        if (
            user_access
            and user_access.access_name != ACCESS_LOOKUP[access_name]
        ):
            self.execute_data['access_names'][path] = ACCESS_LOOKUP[
                user_access.access_name
            ]
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
        path,
        user_name,
        obj_target,
        recursive,
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
        cls, zone, status_base, current, previous, total, time_start
    ):
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
    def set_zone_final_status(cls, zone, status_base, total):
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
        self.name = '<iRODS> {} ({})'.format(name, self.__class__.__name__)
        self.irods = kwargs['irods']

    def raise_irods_exception(self, ex, info=None):
        """
        Raise an exception when taskflow doesn't catch a proper exception from
        the iRODS client.
        """
        desc = '{} failed: {}'.format(
            self.__class__.__name__,
            (str(ex) if str(ex) not in ['', 'None'] else ex.__class__.__name__),
        )
        if info:
            desc += '\n{}'.format(info)
        logger.error(desc)
        raise Exception(desc)


# Tasks ------------------------------------------------------------------------


class CreateCollectionTask(IrodsBaseTask):
    """
    Create collection and its parent collections if they doesn't exist (imkdir)
    """

    def execute(self, path, *args, **kwargs):
        # Create parent collections if they don't exist
        self.execute_data['created_colls'] = []
        for i in range(2, len(path.split('/')) + 1):
            sub_path = '/'.join(path.split('/')[:i])
            if not self.irods.collections.exists(sub_path):
                self.irods.collections.create(sub_path)
                self.execute_data['created_colls'].append(sub_path)
                self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, path, *args, **kwargs):
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
    def execute(self, path, *args, **kwargs):
        trash_path = (
            '/'
            + path.split('/')[1]
            + '/trash/'
            + ''.join(
                random.SystemRandom().choice(
                    string.ascii_lowercase + string.digits
                )
                for _ in range(16)
            )
        )

        if self.irods.collections.exists(path):
            self.irods.collections.create(trash_path)  # Must create this 1st

            try:
                self.irods.collections.move(src_path=path, dest_path=trash_path)
            # NOTE: iRODS/client doesn't like to return a proper exception here
            except Exception:
                pass
            # ..so let's test success manually just to be sure
            new_path = trash_path + '/' + path.split('/')[-1]

            if self.irods.collections.exists(new_path):
                self.data_modified = True
                self.execute_data['trash_path'] = trash_path
            else:
                raise Exception('Failed to remove collection')
        super().execute(*args, **kwargs)

    def revert(self, path, *args, **kwargs):
        if self.data_modified:
            src_path = (
                self.execute_data['trash_path'] + '/' + path.split('/')[-1]
            )
            dest_path = '/'.join(path.split('/')[:-1])
            self.irods.collections.move(src_path=src_path, dest_path=dest_path)
            # Delete temp trash collection
            self.irods.collections.remove(self.execute_data['trash_path'])


# TODO: Also refactor using the metadata trick, once time allows
class RemoveDataObjectTask(IrodsBaseTask):
    """Remove a data object if it exists (irm)"""

    def execute(self, path, *args, **kwargs):
        trash_path = (
            '/'
            + path.split('/')[1]
            + '/trash/'
            + ''.join(
                random.SystemRandom().choice(
                    string.ascii_lowercase + string.digits
                )
                for _ in range(16)
            )
        )

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
            new_path = trash_path + '/' + path.split('/')[-1]

            if self.irods.data_objects.exists(new_path):
                self.data_modified = True
                self.execute_data['trash_path'] = trash_path
            else:
                raise Exception('Failed to remove data object')
        super().execute(*args, **kwargs)

    def revert(self, path, *args, **kwargs):
        if self.data_modified:
            src_path = (
                self.execute_data['trash_path'] + '/' + path.split('/')[-1]
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

    def execute(self, path, name, value, units=None, *args, **kwargs):
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
            value = META_EMPTY_VALUE
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

    def revert(self, path, name, value, units=None, *args, **kwargs):
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

    def execute(self, name, *args, **kwargs):
        try:
            self.irods.user_groups.get(name)
        except GroupDoesNotExist:
            self.irods.user_groups.create(name=name, user_zone=self.irods.zone)
            self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, name, *args, **kwargs):
        if self.data_modified:
            # NOTE: Not group_name
            self.irods.users.remove(user_name=name)


# TODO: Improve this once inherit is properly implemented in python client
# TODO: Tests
# See: https://github.com/irods/python-irodsclient/issues/85
class SetInheritanceTask(IrodsBaseTask):
    """Set collection inheritance (ichmod inherit)"""

    def execute(self, path, inherit=True, *args, **kwargs):
        acl = iRODSAccess(
            access_name=INHERIT_STRINGS[inherit],
            path=path,
            user_name='',
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=True)

    def revert(self, path, inherit=True, *args, **kwargs):
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
        access_name,
        path,
        user_name,
        irods_backend,
        obj_target=False,
        recursive=True,
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
        access_name,
        path,
        user_name,
        irods_backend,
        obj_target=False,
        recursive=True,
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
        self, access_name, path, ticket_str, irods_backend, *args, **kwargs
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
        self, access_name, path, ticket_str, irods_backend, *args, **kwargs
    ):
        if self.data_modified:
            irods_backend.delete_ticket(self.irods, ticket_str)


class DeleteTicketTask(IrodsBaseTask):
    """Delete access ticket if it exists"""

    def execute(
        self, access_name, path, ticket_str, irods_backend, *args, **kwargs
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
        self, access_name, path, ticket_str, irods_backend, *args, **kwargs
    ):
        if self.data_modified:
            irods_backend.issue_ticket(
                self.irods, access_name, path, ticket_str
            )


class CreateUserTask(IrodsBaseTask):
    """Create user if it does not exist (iadmin mkuser)"""

    # NOTE: Password not needed as users log in via LDAP

    def execute(self, user_name, user_type, *args, **kwargs):
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

    def revert(self, user_name, user_type, *args, **kwargs):
        # Remove user only if it was added in this run
        if self.data_modified:
            self.irods.users.remove(user_name)


class AddUserToGroupTask(IrodsBaseTask):
    """Add user to group if not yet added (iadmin atg)"""

    def execute(self, group_name, user_name, *args, **kwargs):
        try:
            group = self.irods.user_groups.get(group_name)
        except Exception as ex:
            self.raise_irods_exception(
                ex, info='Failed to retrieve group "{}"'.format(group_name)
            )
        if not group.hasmember(user_name):
            try:
                group.addmember(user_name=user_name, user_zone=self.irods.zone)
                self.data_modified = True
            except Exception as ex:
                self.raise_irods_exception(
                    ex,
                    info='Failed to add user "{}" into group "{}"'.format(
                        user_name, group_name
                    ),
                )
        super().execute(*args, **kwargs)

    def revert(self, group_name, user_name, *args, **kwargs):
        if self.data_modified:
            group = self.irods.user_groups.get(group_name)
            group.removemember(user_name=user_name, user_zone=self.irods.zone)


class RemoveUserFromGroupTask(IrodsBaseTask):
    """Remove user from group (iadmin rfg)"""

    def execute(self, group_name, user_name, *args, **kwargs):
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

    def revert(self, group_name, user_name, *args, **kwargs):
        if self.data_modified:
            group = self.irods.user_groups.get(group_name)
            group.addmember(user_name=user_name, user_zone=self.irods.zone)


# TODO: Improve this to accept both obj/collection for dest_path in revert
class MoveDataObjectTask(IrodsBaseTask):
    """Move file to destination collection (imv)"""

    def execute(self, src_path, dest_path, *args, **kwargs):
        try:
            self.irods.data_objects.move(src_path=src_path, dest_path=dest_path)
            self.data_modified = True
        except Exception as ex:
            self.raise_irods_exception(ex)
        super().execute(*args, **kwargs)

    def revert(self, src_path, dest_path, *args, **kwargs):
        if self.data_modified:
            # TODO: First check if final item in path is obj or coll
            new_src = dest_path + '/' + src_path.split('/')[-1]
            new_dest = '/'.join(src_path.split('/')[:-1])
            self.irods.data_objects.move(src_path=new_src, dest_path=new_dest)


# Batch Tasks ------------------------------------------------------------------


class BatchSetAccessTask(IrodsAccessMixin, IrodsBaseTask):
    """
    Set user/group access to multiple targets (ichmod). If a target is a data
    object (obj_target=True), the recursive argument will be ignored.
    """

    def execute(
        self,
        access_name,
        paths,
        user_name,
        irods_backend,
        obj_target=False,
        recursive=True,
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
        access_name,
        paths,
        user_name,
        irods_backend,
        obj_target=False,
        recursive=True,
        *args,
        **kwargs,
    ):
        for path in paths:
            self.revert_set_access(path, user_name, obj_target, recursive)


class BatchCheckFileSuffixTask(IrodsBaseTask):
    """Batch check for prohibited file name suffixes"""

    def execute(self, file_paths, suffixes, zone_path, *args, **kwargs):
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

    def revert(self, file_paths, suffixes, zone_path, *args, **kwargs):
        pass  # Nothing to revert


class BatchCheckFileExistTask(IrodsBaseTask):
    """
    Batch check for existence of files and corresponding checksum files
    """

    def execute(
        self, file_paths, chk_paths, zone_path, chk_suffix, *args, **kwargs
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
        self, file_paths, chk_paths, zone_path, chk_suffix, *args, **kwargs
    ):
        pass  # Nothing is modified so no need for revert


class BatchValidateChecksumsTask(ProgressCounterMixin, IrodsBaseTask):
    """Batch validate checksums of a given list of data object paths"""

    def _read_checksum(self, chk_path, zone_path_len, read_errors):
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
    def _compare_checksums(
        cls, data_obj, checksum, zone_path_len, hash_scheme, irods_backend
    ):
        """
        Compare object replicate checksums to expected sum. Raises exception if
        checksums do not match.

        :param data_obj: Data object
        :param checksum: Expected checksum (string)
        :param zone_path_len: Landing zone iRODS path length (int)
        :param hash_scheme: Checksum hashing scheme (string)
        :param irods_backend: IrodsAPI object
        :raises: Exception if checksums do not match
        """
        for replica in data_obj.replicas:
            repl_checksum = replica.checksum
            if hash_scheme == HASH_SCHEME_SHA256:
                # Convert SHA256 from base64
                repl_checksum = irods_backend.get_sha256_hex(repl_checksum)
            if (
                not checksum
                or not repl_checksum
                or checksum.lower() != repl_checksum.lower()
            ):
                log_msg = (
                    'Checksums do not match for "{}" in resource "{}" '
                    '(File: {}; iRODS: {})'.format(
                        os.path.basename(data_obj.path),
                        replica.resource_name,
                        checksum or NO_FILE_CHECKSUM_LABEL,
                        repl_checksum,
                    )
                )
                logger.error(log_msg)
                ex_path = '/'.join(data_obj.path.split('/')[zone_path_len:])
                ex_msg = 'Path: {}\nResource: {}\nFile: {}\niRODS: {}'.format(
                    ex_path,
                    replica.resource_name,
                    checksum or NO_FILE_CHECKSUM_LABEL,
                    repl_checksum,
                )
                raise Exception(ex_msg)

    def execute(
        self,
        landing_zone,
        file_paths,
        zone_path,
        irods_backend,
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
            file_sum = self._read_checksum(chk_path, zone_path_len, read_errors)
            if file_sum is not False:
                try:
                    self._compare_checksums(
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
            ex_msg = ''
            if read_errors:
                err_len = len(read_errors)
                ex_msg += 'Unable to read {} checksum file{}:\n'.format(
                    err_len, 's' if err_len != 1 else ''
                )
                ex_msg += '\n'.join(read_errors)
            if cmp_errors:
                err_len = len(cmp_errors)
                ex_msg += '{}Checksums do not match for {} file{}:\n'.format(
                    '\n' if read_errors else '',
                    err_len,
                    's' if err_len != 1 else '',
                )
                ex_msg += '\n'.join(cmp_errors)
            self.raise_irods_exception(Exception(), ex_msg)
        super().execute(*args, **kwargs)

    def revert(
        self,
        landing_zone,
        file_paths,
        zone_path,
        irods_backend,
        *args,
        **kwargs,
    ):
        pass  # Nothing is modified so no need for revert


class BatchCreateCollectionsTask(IrodsBaseTask):
    """Batch create collections from a list (imkdir)"""

    def execute(self, coll_paths, *args, **kwargs):
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
                        'Failed to create collection: {}'.format(sub_path),
                    )
        super().execute(*args, **kwargs)

    def revert(self, coll_paths, *args, **kwargs):
        if self.data_modified:
            for coll_path in reversed(self.execute_data['created_colls']):
                if self.irods.collections.exists(coll_path):
                    self.irods.collections.remove(coll_path, recurse=True)


class BatchMoveDataObjectsTask(ProgressCounterMixin, IrodsBaseTask):
    """Batch move files (imv) and set access to user group (ichmod)"""

    @staticmethod
    def get_dest_coll_path(src_path, src_root, dest_root):
        src_depth = len(src_root.split('/'))
        return dest_root + '/' + '/'.join(src_path.split('/')[src_depth:-1])

    @staticmethod
    def get_dest_obj_path(src_path, dest_path):
        return (
            dest_path
            + ('/' if dest_path[-1] != '/' else '')
            + src_path.split('/')[-1]
        )

    def execute(
        self,
        landing_zone,
        src_root,
        dest_root,
        src_paths,
        access_name,
        user_name,
        irods_backend,
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
                    msg = 'Target file already exists: {}'.format(dest_obj_path)
                else:
                    msg = 'Error moving move data object "{}" to "{}"'.format(
                        src_path, dest_obj_path
                    )
                self.raise_irods_exception(ex, msg)
            try:
                target = self.irods.data_objects.get(dest_obj_path)
            except Exception as ex:
                self.raise_irods_exception(
                    ex,
                    'Error retrieving destination object "{}"'.format(
                        dest_obj_path
                    ),
                )
            try:
                target_access = self.irods.acls.get(target=target)
            except Exception as ex:
                self.raise_irods_exception(
                    ex,
                    'Error getting permissions of target "{}"'.format(target),
                )

            # TODO: Remove repetition, use IrodsAccessMixin
            user_access = next(
                (x for x in target_access if x.user_name == user_name), None
            )
            prev_access = None
            if (
                user_access
                and user_access.access_name != ACCESS_LOOKUP[access_name]
            ):
                prev_access = ACCESS_LOOKUP[user_access.access_name]
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
                        'Error setting permission for "{}"'.format(
                            dest_coll_path
                        ),
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
        landing_zone,
        src_root,
        dest_root,
        access_name,
        user_name,
        irods_backend,
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
            new_dest_obj = new_dest + '/' + src_path.split('/')[-1]
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

    def _raise_checksum_exception(self, ex, replica, data_obj, info=None):
        info_str = (': ' + info) if info else ''
        self.raise_irods_exception(
            ex,
            f'Failed to calculate checksum{info_str}\nReplica: '
            f'{replica.resc_hier}\nFile: {data_obj.path}',
        )

    def _compute_checksum(self, data_obj, replica, force):
        if replica.checksum and not force:
            return
        for j in range(CHECKSUM_RETRY):
            if j > 0:  # Retry if iRODS times out (see #1941)
                logger.info('Retrying ({})..'.format(j + 1))
            try:
                data_obj.chksum(**{kw.RESC_HIER_STR_KW: replica.resc_hier})
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
                    self._raise_checksum_exception(ex, replica, data_obj, info)
            # Raise other exceptions normally
            except Exception as ex:
                self._raise_checksum_exception(ex, replica, data_obj)

    def execute(self, landing_zone, file_paths, force, *args, **kwargs):
        file_count = len(file_paths)
        if file_count == 0:  # Nothing to do
            super().execute(*args, **kwargs)
            return
        status_base = landing_zone.status_info
        i = 0
        i_prev = 0
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
            i_prev, time_start = self.update_zone_progress(
                landing_zone, status_base, i, i_prev, file_count, time_start
            )
            i += 1
        self.set_zone_final_status(landing_zone, status_base, file_count)
        super().execute(*args, **kwargs)
        # NOTE: We don't need revert for this
