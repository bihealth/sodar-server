"""
Base test classes and mixins for the taskflowbackend and other apps testing
against it.

- TaskflowViewTestBase: Use for view tests of UI and Ajax views
- TaskflowViewAPIBTestase: Use for view tests of REST API views
- TaskflowPermissionTestBase: Use for permission tests of UI and Ajax views
- TaskflowAPIPermissionTestBase: Use for permission tests of REST API views

Test category is automatically created for each test. Project creation has to be
done manually using make_project_taskflow() and make_assignment_taskflow().
"""

import hashlib
import logging
import os


from irods.exception import CollectionDoesNotExist
from irods.keywords import REG_CHKSUM_KW
from irods.models import TicketQuery, UserGroup
from irods.test.helpers import make_object

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from rest_framework.test import APILiveServerTestCase
from test_plus import TestCase, APITestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, RoleAssignment, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)
from projectroles.tests.test_permissions import TestPermissionMixin
from projectroles.tests.test_permissions_api import SODARAPIPermissionTestMixin
from projectroles.tests.test_views_api import SODARAPIViewTestMixin
from projectroles.views_api import CORE_API_MEDIA_TYPE, CORE_API_DEFAULT_VERSION


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']

# Local constants
IRODS_ACCESS_OWN = 'own'
IRODS_ACCESS_NULL = 'null'
IRODS_GROUP_PUBLIC = 'public'
TICKET_STR = 'ei8iomuDoazeiD2z'
TEST_MODE_ERR_MSG = (
    'TASKFLOW_TEST_MODE not True, testing with SODAR Taskflow disabled'
)
DEFAULT_PERMANENT_USERS = ['client_user', 'rods', 'rodsadmin', 'public']


class TaskflowTestMixin(ProjectMixin, RoleMixin, RoleAssignmentMixin):
    """Setup/teardown methods and helpers for taskflow tests"""

    #: iRODS backend object
    irods_backend = None
    #: iRODS session object
    irods = None

    def make_irods_object(
        self, coll, obj_name, content=None, content_length=1024, checksum=True
    ):
        """
        Create and put a data object into iRODS.

        :param coll: iRODSCollection object
        :param obj_name: String
        :param content: Content data (optional)
        :param content_length: Random content length (if content not specified)
        :param checksum: Calculate checksum if True (bool)
        :return: iRODSDataObject object
        """
        if not content:
            content = ''.join('x' for _ in range(content_length))
        obj_path = os.path.join(coll.path, obj_name)
        obj_kwargs = {REG_CHKSUM_KW: ''} if checksum else {}
        return make_object(self.irods, obj_path, content, **obj_kwargs)

    def make_irods_md5_object(self, obj):
        """
        Create and put an MD5 checksum object for an existing object in iRODS.

        :param obj: iRODSDataObject
        :return: iRODSDataObject
        """
        md5_path = obj.path + '.md5'
        md5_content = self.get_md5_checksum(obj)
        return make_object(self.irods, md5_path, md5_content)

    def get_md5_checksum(self, obj):
        """
        Return the md5 checksum for an iRODS object.

        :param obj: iRODSDataObject
        :return: String
        """
        with obj.open() as obj_fp:
            return hashlib.md5(obj_fp.read()).hexdigest()

    def assert_irods_access(self, user_name, target, expected):
        """
        Assert access for a specific user for a target object or collection.

        :param user_name: String
        :param target: iRODSCollection, DataObject or iRODS path as string
        :param expected: Expected access (string or None)
        """
        if isinstance(target, str):
            try:
                target = self.irods.collections.get(target)
            except CollectionDoesNotExist:
                target = self.irods.data_objects.get(target)
        access_list = self.irods.permissions.get(target=target)
        access = next(
            (x for x in access_list if x.user_name == user_name), None
        )
        if access:
            access = access.access_name
        self.assertEqual(access, expected)

    def assert_group_member(self, project, user, status=True):
        """
        Assert user membership in iRODS project group. Requires irods_backend
        and irods_session to be present in the class.

        :param project: Project object
        :param user: SODARUser object
        :param status: Expected membership status (boolean)
        """
        user_group = self.irods.user_groups.get(
            self.irods_backend.get_user_group_name(project)
        )
        self.assertEqual(user_group.hasmember(user.username), status)

    def assert_irods_coll(self, target, sub_path=None, expected=True):
        """
        Assert the existence of iRODS collection by object or path. Requires
        irods_backend and irods to be present in the class.

        :param target: Object supported by irodsbackend or full path as string
        :param sub_path: Subpath below object path (string, optional)
        :param expected: Expected state of existence (boolean)
        """
        if isinstance(target, str):
            path = target
        else:
            path = self.irods_backend.get_path(target)
        if sub_path:
            path += '/' + sub_path
        self.assertEqual(self.irods.collections.exists(path), expected)

    def assert_irods_obj(self, path, expected=True):
        """
        Assert the existence of an iRODS data object. Requires irods to be
        present in the class.

        :param path: Full iRODS path to data object (string)
        :param expected: Expected state of existence (boolean)
        """
        self.assertEqual(self.irods.data_objects.exists(path), expected)

    @classmethod
    def clear_irods_test_data(cls):
        """
        Cleanup all data from an iRODS test server. Only allowed in test mode.
        Should never be used on a dev/production server!

        :return: Boolean
        :raise: ImproperlyConfigured if TASKFLOW_TEST_MODE is not set True
        :raise: Exception if iRODS cleanup fails
        """
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, cleanup command not allowed'
            )
        irods_backend = get_backend_api('omics_irods')
        projects_root = irods_backend.get_projects_path()
        permanent_users = getattr(
            settings, 'TASKFLOW_TEST_PERMANENT_USERS', DEFAULT_PERMANENT_USERS
        )
        # TODO: Remove stuff from user home collections

        with irods_backend.get_session() as irods:
            # Remove project folders
            try:
                irods.collections.remove(
                    projects_root, recurse=True, force=True
                )
                logger.debug('Removed projects root: {}'.format(projects_root))
            except Exception:
                pass  # This is OK, the root just wasn't there
                # Remove created user groups and users

            # NOTE: user_groups.remove does both
            for g in irods.query(UserGroup).all():
                if g[UserGroup.name] not in permanent_users:
                    irods.user_groups.remove(user_name=g[UserGroup.name])
                    logger.debug('Removed user: {}'.format(g[UserGroup.name]))

            # Remove all tickets
            ticket_query = irods.query(TicketQuery.Ticket).all()
            for ticket in ticket_query:
                ticket_str = ticket[TicketQuery.Ticket.string]
                irods_backend.delete_ticket(irods, ticket_str)
                logger.debug('Deleted ticket: {}'.format(ticket_str))

            # Remove data objects and unneeded collections from trash
            trash_path = irods_backend.get_trash_path()
            trash_coll = irods.collections.get(trash_path)
            # NOTE: We can't delete the home trash collection
            trash_home_path = os.path.join(trash_path, 'home')
            for coll in irods_backend.get_colls_recursively(trash_coll):
                if irods.collections.exists(
                    coll.path
                ) and not coll.path.startswith(trash_home_path):
                    irods.collections.remove(
                        coll.path, recurse=True, force=True
                    )
            obj_paths = [
                o['path']
                for o in irods_backend.get_objs_recursively(irods, trash_coll)
                + irods_backend.get_objs_recursively(
                    irods, trash_coll, md5=True
                )
            ]
            for path in obj_paths:
                irods.data_objects.unlink(path, force=True)

    def setUp(self):
        # Ensure TASKFLOW_TEST_MODE is True to avoid data loss
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(TEST_MODE_ERR_MSG)
        self.taskflow = get_backend_api('taskflow', force=True)
        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session_obj()
        # Init roles
        self.init_roles()
        # Init users
        self.user_owner_cat = self.make_user('user_owner_cat')
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        # Create category locally
        self.category = self.make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.owner_as_cat = self.make_assignment(
            self.category, self.user_owner_cat, self.role_owner
        )
        # Set iRODS 4.2/4.3 compatible ACL params
        new_ver = self.irods_backend.is_irods_version(self.irods, '4.3')
        acl_dl = '_' if new_ver else ' '
        self.irods_access_read = 'read{}object'.format(acl_dl)
        self.irods_access_write = 'modify{}object'.format(acl_dl)

    def tearDown(self):
        self.clear_irods_test_data()
        self.irods.cleanup()


class TaskflowPermissionTestMixin(
    SODARAPIPermissionTestMixin, TaskflowTestMixin
):
    """Setup method mixin for permission tests"""

    def setUp(self):
        super().setUp()
        # Init users
        # Superuser
        self.superuser = self.user
        # Get knox token for self.user
        self.knox_token = self.get_token(self.superuser)
        # No user
        self.anonymous = None
        # Users with role assignments
        # NOTE: user_owner_cate created in super()
        self.user_delegate_cat = self.make_user('user_delegate_cat')
        self.user_contributor_cat = self.make_user('user_contributor_cat')
        self.user_guest_cat = self.make_user('user_guest_cat')
        self.user_finder_cat = self.make_user('user_finder_cat')
        self.user_owner = self.make_user('user_owner')
        self.user_delegate = self.make_user('user_delegate')
        self.user_contributor = self.make_user('user_contributor')
        self.user_guest = self.make_user('user_guest')
        # User without role assignments
        self.user_no_roles = self.make_user('user_no_roles')

        # Make Category users locally
        # NOTE: owner_as_cat created in super()
        self.delegate_as_cat = self.make_assignment(
            self.category, self.user_delegate_cat, self.role_delegate
        )
        self.contributor_as_cat = self.make_assignment(
            self.category, self.user_contributor_cat, self.role_contributor
        )
        self.guest_as_cat = self.make_assignment(
            self.category, self.user_guest_cat, self.role_guest
        )
        self.finder_as_cat = self.make_assignment(
            self.category, self.user_finder_cat, self.role_finder
        )
        # Make project and roles with Taskflow
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner,
            description='description',
        )
        self.delegate_as = self.make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self.contributor_as = self.make_assignment_taskflow(
            self.project, self.user_contributor, self.role_contributor
        )
        self.guest_as = self.make_assignment_taskflow(
            self.project, self.user_guest, self.role_guest
        )


class TaskflowProjectTestMixin:
    """Helpers for UI/Ajax view project management with Taskflow"""

    def make_project_taskflow(
        self,
        title,
        type,
        parent,
        owner,
        description='',
        public_guest_access=False,
    ):
        """Make Project with taskflow for UI view tests"""
        post_data = {
            'title': title,
            'type': type,
            'parent': parent.sodar_uuid if parent else None,
            'owner': owner.sodar_uuid,
            'description': description,
            'public_guest_access': public_guest_access,
        }
        post_data.update(
            app_settings.get_defaults(APP_SETTING_SCOPE_PROJECT, post_safe=True)
        )  # Add default settings
        post_kwargs = {'project': parent.sodar_uuid} if parent else {}
        with self.login(self.user):  # TODO: Replace with owner
            response = self.client.post(
                reverse('projectroles:create', kwargs=post_kwargs), post_data
            )
            self.assertEqual(response.status_code, 302)
            project = Project.objects.get(title=title)
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:detail',
                    kwargs={'project': project.sodar_uuid},
                ),
            )
        owner_as = project.get_owner()
        return project, owner_as

    def make_assignment_taskflow(self, project, user, role):
        """Make RoleAssignment with taskflow for UI view tests"""
        post_data = {
            'project': project.sodar_uuid,
            'user': user.sodar_uuid,
            'role': role.pk,
        }
        with self.login(self.user):  # TODO: Use project owner instead
            response = self.client.post(
                reverse(
                    'projectroles:role_create',
                    kwargs={'project': project.sodar_uuid},
                ),
                post_data,
            )
            role_as = RoleAssignment.objects.get(project=project, user=user)
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:roles', kwargs={'project': project.sodar_uuid}
                ),
            )
        return role_as


class TaskflowAPIProjectTestMixin:
    """Helpers for API view project management with Taskflow"""

    def make_project_taskflow(
        self, title, type, parent, owner, description='', readme=''
    ):
        """Make Project with taskflow for API view tests"""
        post_data = {
            'title': title,
            'type': type,
            'parent': parent.sodar_uuid if parent else None,
            'owner': owner.sodar_uuid,
            'description': description,
            'readme': readme,
        }
        response = self.request_knox(
            reverse('projectroles:api_project_create'),
            method='POST',
            data=post_data,
            media_type=CORE_API_MEDIA_TYPE,
            version=CORE_API_DEFAULT_VERSION,
        )
        # Assert response and object status
        self.assertEqual(response.status_code, 201, msg=response.content)
        project = Project.objects.get(title=title)
        return project, project.get_owner()

    def make_assignment_taskflow(self, project, user, role):
        """Make RoleAssignment with taskflow for API view tests"""
        url = reverse(
            'projectroles:api_role_create',
            kwargs={'project': project.sodar_uuid},
        )
        request_data = {'role': role.name, 'user': str(user.sodar_uuid)}
        response = self.request_knox(
            url,
            method='POST',
            data=request_data,
            media_type=CORE_API_MEDIA_TYPE,
            version=CORE_API_DEFAULT_VERSION,
        )
        self.assertEqual(response.status_code, 201, msg=response.content)
        return RoleAssignment.objects.get(project=project, user=user, role=role)


class TaskflowViewTestBase(
    TaskflowTestMixin,
    TaskflowProjectTestMixin,
    TestCase,
):
    """Base class for testing with taskflow"""


class TaskflowAPIViewTestBase(
    SODARAPIViewTestMixin,
    TaskflowTestMixin,
    TaskflowAPIProjectTestMixin,
    APILiveServerTestCase,
    TestCase,
):
    """Base class for testing API views with taskflow"""

    def setUp(self):
        super().setUp()
        # Get knox token for self.user
        self.knox_token = self.get_token(self.user)


class TaskflowPermissionTestBase(
    TaskflowProjectTestMixin,
    TaskflowPermissionTestMixin,
    TestPermissionMixin,
    TestCase,
):
    """Base class for testing UI and Ajax view permissions with taskflow"""


class TaskflowAPIPermissionTestBase(
    TaskflowAPIProjectTestMixin, TaskflowPermissionTestMixin, APITestCase
):
    """Base class for testing API view permissions with taskflow"""

    def setUp(self):
        super().setUp()
        # Get knox token for self.user
        self.knox_token = self.get_token(self.superuser)
