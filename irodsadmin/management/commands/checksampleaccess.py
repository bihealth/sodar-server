"""Checkaccess management command"""

import os

from irods.column import Like
from irods.models import (
    Collection,
    CollectionAccess,
    CollectionUser,
    DataObject,
    DataAccess,
    User,
)

from django.conf import settings
from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.models import Investigation


logger = ManagementCommandLogger(__name__)


# Local constants
ACCESS_OWN = 'own'
ACCESS_READ = 'read_object'
CHECK_ACCESS_ADMIN_MSG = 'Invalid admin user access'
CHECK_ACCESS_GROUP_MSG = 'Invalid project group access'
CHECK_ACCESS_USER_MSG = 'Access granted for invalid user'
CHECK_ACCESS_START_MSG = 'Checking sample data access..'
CHECK_ACCESS_DONE_MSG = 'Check done, found {count} invalid ACL{plural}'


class Command(BaseCommand):
    """
    Command for checking for expected access in iRODS project sample data
    collections.
    """

    help = 'Check for expected access in iRODS project sample data collections.'

    def __init__(self):
        super().__init__()
        self.irods_backend = get_backend_api('omics_irods')

    @classmethod
    def _check_access(
        cls, user_id, user_name, access_name, path, admin_id, group_id
    ):
        """
        Check a single ACL to see if it corresponds to expected access types.

        :param user_id: ACL user ID (int)
        :param user_name: ACL user name (string)
        :param access_name: ACL access name (string)
        :param path: iRODS path to collection or data object (string)
        :param admin_id: Admin user ID (int)
        :param group_id: Project user group ID (int)
        """
        if user_id == admin_id and access_name != ACCESS_OWN:
            logger.info(f'{CHECK_ACCESS_ADMIN_MSG}: {access_name};{path}')
            return 1
        # HACK: Ignore PRC query reporting all group users for each group
        elif (
            user_id == group_id
            and user_name.startswith('omics_project_')
            and access_name != ACCESS_READ
        ):
            logger.info(f'{CHECK_ACCESS_GROUP_MSG}: {access_name};{path}')
            return 1
        elif user_id not in [admin_id, group_id]:
            logger.info(
                f'{CHECK_ACCESS_USER_MSG}: {user_name};{access_name};{path}'
            )
            return 1
        return 0

    @classmethod
    def _check_coll_access(cls, sample_path, admin_id, group_id, irods):
        """
        Check collection ACLs under a project sample path.

        :param sample_path: iRODS path for project sample data (string)
        :param admin_id: Admin user ID (int)
        :param group_id: Project user group ID (int)
        :param irods: iRODSSession object
        :return: Invalid access count (int)
        """
        ret = 0
        query = irods.query(
            Collection, CollectionAccess, CollectionUser
        ).filter(Like(Collection.name, sample_path + '%'))
        for r in query:
            ret += cls._check_access(
                r[CollectionAccess.user_id],
                r[CollectionUser.name],
                r[CollectionAccess.name],
                r[Collection.name],  # Path
                admin_id,
                group_id,
            )
        query.close()
        return ret

    @classmethod
    def _check_obj_access(cls, sample_path, admin_id, group_id, irods):
        """
        Check data object ACLs under a project sample path.

        :param sample_path: iRODS path for project sample data (string)
        :param admin_id: Admin user ID (int)
        :param group_id: Project user group ID (int)
        :param irods: iRODSSession object
        :return: Invalid access count (int)
        """
        ret = 0
        query = irods.query(DataObject, DataAccess, Collection, User).filter(
            Like(Collection.name, sample_path + '%')
        )
        for r in query:
            path = os.path.join(r[Collection.name], r[DataObject.name])
            ret += cls._check_access(
                r[DataAccess.user_id],
                r[User.name],
                r[DataAccess.name],
                path,
                admin_id,
                group_id,
            )
        query.close()
        return ret

    def _check_project(self, project, admin_id, irods):
        """
        Check ACLs for a single project.

        :param project: Project object
        :param admin_id: Admin user ID (int)
        :param irods: iRODSSession object
        :returns: Invalid access count (int)
        """
        sample_path = self.irods_backend.get_sample_path(project)
        project_group = self.irods_backend.get_group_name(project)
        group_id = irods.users.get(project_group).id
        check_args = [sample_path, admin_id, group_id, irods]
        ret = 0
        ret += self._check_coll_access(*check_args)
        ret += self._check_obj_access(*check_args)
        return ret

    def handle(self, *args, **options):
        logger.info(CHECK_ACCESS_START_MSG)
        investigations = Investigation.objects.filter(
            active=True, irods_status=True
        ).order_by('project__full_title')
        if not investigations:
            logger.info(
                'No investigations with iRODS data found, nothing to do'
            )
            return  # Nothing to do
        with self.irods_backend.get_session() as irods:
            admin_id = irods.users.get(settings.IRODS_USER).id
            for inv in investigations:
                count = self._check_project(inv.project, admin_id, irods)
        logger.info(
            CHECK_ACCESS_DONE_MSG.format(
                count=count, plural='s' if count != 1 else ''
            )
        )
