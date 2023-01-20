"""
Base test classes and mixins for the taskflowbackend and other apps testing
against it.
"""

from irods.exception import CollectionDoesNotExist
from irods.models import UserGroup

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from rest_framework.test import APILiveServerTestCase
from test_plus import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, RoleAssignment, Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.tests.test_permissions_api import SODARAPIPermissionTestMixin
from projectroles.tests.test_views_api import SODARAPIViewTestMixin
from projectroles.views_api import CORE_API_MEDIA_TYPE, CORE_API_DEFAULT_VERSION


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']

# Local constants
IRODS_ACCESS_READ = 'read object'
IRODS_ACCESS_OWN = 'own'
IRODS_ACCESS_WRITE = 'modify object'
IRODS_ACCESS_NULL = 'null'
IRODS_GROUP_PUBLIC = 'public'
TICKET_STR = 'ei8iomuDoazeiD2z'


class TaskflowTestMixin:
    """Helpers for taskflow tests"""

    #: iRODS backend object
    irods_backend = None
    #: iRODS session object
    irods = None

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
        """Make Project with taskflow for API view tests."""
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
        """Make RoleAssignment with taskflow for API view tests."""
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


class TaskflowbackendTestBase(
    ProjectMixin,
    RoleAssignmentMixin,
    TaskflowTestMixin,
    TaskflowProjectTestMixin,
    TestCase,
):
    """Base class for testing with taskflow"""

    def setUp(self):
        # Ensure TASKFLOW_TEST_MODE is True to avoid data loss
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, testing with SODAR Taskflow '
                'disabled'
            )
        self.taskflow = get_backend_api('taskflow', force=True)
        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session_obj()

        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE
        )[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR
        )[0]
        self.role_guest = Role.objects.get_or_create(name=PROJECT_ROLE_GUEST)[0]

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
        self.as_cat_owner = self.make_assignment(
            self.category, self.user_owner_cat, self.role_owner
        )

    def tearDown(self):
        self.taskflow.cleanup()
        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.irods_backend.get_projects_path())
        for user in self.irods.query(UserGroup).all():
            self.assertIn(
                user[UserGroup.name], settings.TASKFLOW_TEST_PERMANENT_USERS
            )
        self.irods.cleanup()


class TaskflowAPIViewTestBase(
    ProjectMixin,
    RoleAssignmentMixin,
    SODARAPIViewTestMixin,
    TaskflowTestMixin,
    TaskflowAPIProjectTestMixin,
    APILiveServerTestCase,
    TestCase,
):
    """Base class for testing API views with taskflow"""

    def setUp(self):
        # Ensure TASKFLOW_TEST_MODE is True to avoid data loss
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, '
                'testing with SODAR Taskflow disabled'
            )
        self.taskflow = get_backend_api('taskflow', force=True)
        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session_obj()

        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE
        )[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR
        )[0]
        self.role_guest = Role.objects.get_or_create(name=PROJECT_ROLE_GUEST)[0]

        # Init user
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        # Get knox token for self.user
        self.knox_token = self.get_token(self.user)

        # Create category locally (categories are not handled with taskflow)
        self.category = self.make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.make_assignment(self.category, self.user, self.role_owner)

    def tearDown(self):
        self.taskflow.cleanup()
        self.irods.cleanup()


class TaskflowAPIPermissionTestBase(
    ProjectMixin,
    RoleAssignmentMixin,
    TaskflowAPIProjectTestMixin,
    SODARAPIPermissionTestMixin,
    TestCase,
):
    """Base class for testing API view permissions with taskflow"""

    def setUp(self):
        # Ensure TASKFLOW_TEST_MODE is True to avoid data loss
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, testing with SODAR Taskflow '
                'disabled'
            )
        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE
        )[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR
        )[0]
        self.role_guest = Role.objects.get_or_create(name=PROJECT_ROLE_GUEST)[0]

        # Init users
        # Superuser
        self.superuser = self.make_user('superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()
        self.knox_token = self.get_token(self.superuser)
        # No user
        self.anonymous = None
        # Users with role assignments
        self.user_owner_cat = self.make_user('user_owner_cat')
        self.user_owner = self.make_user('user_owner')
        self.user_delegate = self.make_user('user_delegate')
        self.user_contributor = self.make_user('user_contributor')
        self.user_guest = self.make_user('user_guest')
        # User without role assignments
        self.user_no_roles = self.make_user('user_no_roles')

        # Make category and owner locally
        self.category = self.make_project(
            title='TestCategoryTop', type=PROJECT_TYPE_CATEGORY, parent=None
        )
        self.owner_as_cat = self.make_assignment(
            self.category, self.user_owner_cat, self.role_owner
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

        # Init taskflow and iRODS backend
        self.taskflow = get_backend_api('taskflow')
        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session_obj()

    def tearDown(self):
        self.irods.cleanup()
        super().tearDown()
