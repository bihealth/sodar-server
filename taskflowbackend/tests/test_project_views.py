"""Tests for projectroles views with taskflow"""

# TODO: We shouldn't need to use LiveServerTestCase anymore

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.forms.models import model_to_dict
from django.test import (
    # LiveServerTestCase,
    RequestFactory,
    tag,
    override_settings,
)

# HACK to get around https://stackoverflow.com/a/25081791
from django.urls import reverse

from unittest import skipIf

from projectroles import views_taskflow
from projectroles.app_settings import AppSettingAPI
from projectroles.models import (
    Project,
    Role,
    RoleAssignment,
    ProjectInvite,
    SODAR_CONSTANTS,
)
from projectroles.plugins import get_backend_api, change_plugin_status
from projectroles.tests.taskflow_testcase import TestCase
from projectroles.tests.test_models import (
    ProjectInviteMixin,
    ProjectMixin,
    RoleAssignmentMixin,
)
from projectroles.tests.test_views import TestViewsBase, TASKFLOW_SECRET_INVALID

# Access Django user model
User = auth.get_user_model()

# App settings API
app_settings = AppSettingAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = SODAR_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = SODAR_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = SODAR_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW'
]
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']

# Local constants
INVITE_EMAIL = 'test@example.com'
SECRET = 'rsd886hi8276nypuvw066sbvv0rb2a6x'
TASKFLOW_ENABLED = (
    True if 'taskflow' in settings.ENABLED_BACKEND_PLUGINS else False
)
TASKFLOW_SKIP_MSG = 'Taskflow not enabled in settings'
TASKFLOW_TEST_MODE = getattr(settings, 'TASKFLOW_TEST_MODE', False)


# Base Classes -----------------------------------------------------------------


@tag('Taskflow')  # Run tests if iRODS and SODAR Taskflow are enabled
class TestTaskflowBase(ProjectMixin, RoleAssignmentMixin, TestCase):
    """Base class for testing UI views with taskflow"""

    def _make_project_taskflow(
        self, title, type, parent, owner, description, public_guest_access=False
    ):
        """Make Project with taskflow for UI view tests"""
        post_data = dict(self.request_data)
        post_data.update(
            {
                'title': title,
                'type': type,
                'parent': parent.sodar_uuid if parent else None,
                'owner': owner.sodar_uuid,
                'description': description,
                'public_guest_access': public_guest_access,
            }
        )
        post_data.update(
            app_settings.get_all_defaults(
                APP_SETTING_SCOPE_PROJECT, post_safe=True
            )
        )  # Add default settings

        post_kwargs = {'project': parent.sodar_uuid} if parent else {}

        with self.login(self.user):
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

    def _make_assignment_taskflow(self, project, user, role):
        """Make RoleAssignment with taskflow for UI view tests"""
        post_data = dict(self.request_data)
        post_data.update(
            {
                'project': project.sodar_uuid,
                'user': user.sodar_uuid,
                'role': role.pk,
            }
        )

        with self.login(self.user):
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

    def setUp(self):
        # Ensure TASKFLOW_TEST_MODE is True to avoid data loss
        if not TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, '
                'testing with SODAR Taskflow disabled'
            )

        # Set up live server URL for requests
        self.request_data = {'sodar_url': self.live_server_url}

        # Get taskflow plugin (or None if taskflow not enabled)
        change_plugin_status(
            name='taskflow', status=0, plugin_type='backend'  # 0 = Enabled
        )
        self.taskflow = get_backend_api('taskflow', force=True)

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
        self.user_cat = self.make_user('user_cat')
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Create category locally
        self.category = self._make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self._make_assignment(self.category, self.user_cat, self.role_owner)

    def tearDown(self):
        self.taskflow.cleanup()


# Local Tests ------------------------------------------------------------------


class TestTaskflowLocalAPIBase(
    ProjectMixin, RoleAssignmentMixin, TestViewsBase
):
    """Base class for testing the local taskflow API views"""

    def setUp(self):
        super().setUp()
        self.req_factory = RequestFactory()


@override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
class TestProjectGetAPIView(TestTaskflowLocalAPIBase):
    """Tests for the project retrieve API view"""

    def setUp(self):
        super().setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )

    def test_post(self):
        """Test POST request for getting a project"""
        request = self.req_factory.post(
            reverse('projectroles:taskflow_project_get'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowProjectGetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        expected = {
            'project_uuid': str(self.project.sodar_uuid),
            'title': self.project.title,
            'description': self.project.description,
        }
        self.assertEqual(response.data, expected)

    @override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
    def test_get_pending(self):
        """Test POST request to get a pending project"""
        pd_project = self._make_project(
            title='TestProject2',
            type=PROJECT_TYPE_PROJECT,
            parent=None,
            submit_status=SUBMIT_STATUS_PENDING_TASKFLOW,
        )
        request = self.req_factory.post(
            reverse('projectroles:taskflow_project_get'),
            data={
                'project_uuid': str(pd_project.sodar_uuid),
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowProjectGetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 404)


@override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
class TestProjectUpdateAPIView(TestTaskflowLocalAPIBase):
    """Tests for the project updating API view"""

    def setUp(self):
        super().setUp()
        self.category = self._make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.cat_owner_as = self._make_assignment(
            self.category, self.user, self.role_owner
        )
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )

    def test_post(self):
        """Test POST request for updating a project"""
        # NOTE: Duplicate titles not checked here, not allowed in the form
        title = 'New title'
        desc = 'New desc'
        readme = 'New readme'
        request = self.req_factory.post(
            reverse('projectroles:taskflow_project_update'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'title': title,
                'parent_uuid': str(self.category.sodar_uuid),
                'description': desc,
                'readme': readme,
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowProjectUpdateAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, title)
        self.assertEqual(self.project.description, desc)
        self.assertEqual(self.project.readme.raw, readme)

    def test_post_no_description(self):
        """Test POST request without a description field"""
        # NOTE: Duplicate titles not checked here, not allowed in the form
        title = 'New title'
        readme = 'New readme'
        request = self.req_factory.post(
            reverse('projectroles:taskflow_project_update'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'title': title,
                'parent_uuid': str(self.category.sodar_uuid),
                'readme': readme,
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowProjectUpdateAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, title)
        self.assertEqual(self.project.description, '')
        self.assertEqual(self.project.readme.raw, readme)

    def test_post_move(self):
        """Test POST request for moving a project"""
        new_category = self._make_project('NewCat', PROJECT_TYPE_CATEGORY, None)
        request = self.req_factory.post(
            reverse('projectroles:taskflow_project_update'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'title': self.project.title,
                'parent_uuid': str(new_category.sodar_uuid),
                'description': self.project.description,
                'readme': '',
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowProjectUpdateAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.parent, new_category)


@override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
class TestRoleAssignmentGetAPIView(TestTaskflowLocalAPIBase):
    """Tests for the role assignment getting API view"""

    def setUp(self):
        super().setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )

    def test_post(self):
        """Test POST request for getting a role assignment"""
        request = self.req_factory.post(
            reverse('projectroles:taskflow_role_get'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'user_uuid': str(self.user.sodar_uuid),
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowRoleAssignmentGetAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 200)
        expected = {
            'assignment_uuid': str(self.owner_as.sodar_uuid),
            'project_uuid': str(self.project.sodar_uuid),
            'user_uuid': str(self.user.sodar_uuid),
            'role_pk': self.role_owner.pk,
            'role_name': self.role_owner.name,
        }
        self.assertEqual(response.data, expected)


@override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
class TestRoleAssignmentSetAPIView(TestTaskflowLocalAPIBase):
    """Tests for the role assignment setting API view"""

    def setUp(self):
        super().setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )

    def test_post_new(self):
        """Test POST request for assigning a new role"""
        new_user = self.make_user('new_user')
        self.assertEqual(RoleAssignment.objects.all().count(), 1)
        request = self.req_factory.post(
            reverse('projectroles:taskflow_role_set'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'user_uuid': str(new_user.sodar_uuid),
                'role_pk': self.role_contributor.pk,
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowRoleAssignmentSetAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        new_as = RoleAssignment.objects.get(project=self.project, user=new_user)
        self.assertEqual(new_as.role.pk, self.role_contributor.pk)

    def test_post_existing(self):
        """Test POST request for updating an existing role"""
        new_user = self.make_user('new_user')
        self._make_assignment(self.project, new_user, self.role_guest)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        request = self.req_factory.post(
            reverse('projectroles:taskflow_role_set'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'user_uuid': str(new_user.sodar_uuid),
                'role_pk': self.role_contributor.pk,
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowRoleAssignmentSetAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        new_as = RoleAssignment.objects.get(project=self.project, user=new_user)
        self.assertEqual(new_as.role.pk, self.role_contributor.pk)


@override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
class TestRoleAssignmentDeleteAPIView(TestTaskflowLocalAPIBase):
    """Tests for the role assignment deletion API view"""

    def setUp(self):
        super().setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )

    def test_post(self):
        """Test POST request for removing a role assignment"""
        new_user = self.make_user('new_user')
        self._make_assignment(self.project, new_user, self.role_guest)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        request = self.req_factory.post(
            reverse('projectroles:taskflow_role_delete'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'user_uuid': str(new_user.sodar_uuid),
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowRoleAssignmentDeleteAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoleAssignment.objects.all().count(), 1)

    def test_post_not_found(self):
        """Test POST request for removing a non-existing role assignment"""
        new_user = self.make_user('new_user')
        self.assertEqual(RoleAssignment.objects.all().count(), 1)
        request = self.req_factory.post(
            reverse('projectroles:taskflow_role_delete'),
            data={
                'project_uuid': str(self.project.sodar_uuid),
                'user_uuid': str(new_user.sodar_uuid),
                'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
            },
        )
        response = views_taskflow.TaskflowRoleAssignmentDeleteAPIView.as_view()(
            request
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(RoleAssignment.objects.all().count(), 1)


class TestTaskflowAPIViewAccess(TestTaskflowLocalAPIBase):
    """Tests for taskflow API view access"""

    def setUp(self):
        super().setUp()
        self.category = self._make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )

    @override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
    def test_access_invalid_token(self):
        """Test access with an invalid token"""
        urls = [
            reverse('projectroles:taskflow_project_get'),
            reverse('projectroles:taskflow_project_update'),
            reverse('projectroles:taskflow_role_get'),
            reverse('projectroles:taskflow_role_set'),
            reverse('projectroles:taskflow_role_delete'),
            reverse('projectroles:taskflow_settings_get'),
            reverse('projectroles:taskflow_settings_set'),
        ]
        for url in urls:
            request = self.req_factory.post(
                url, data={'sodar_secret': TASKFLOW_SECRET_INVALID}
            )
            response = views_taskflow.TaskflowProjectGetAPIView.as_view()(
                request
            )
            self.assertEqual(response.status_code, 403)

    @override_settings(ENABLED_BACKEND_PLUGINS=['taskflow'])
    def test_access_no_token(self):
        """Test access with no token"""
        urls = [
            reverse('projectroles:taskflow_project_get'),
            reverse('projectroles:taskflow_project_update'),
            reverse('projectroles:taskflow_role_get'),
            reverse('projectroles:taskflow_role_set'),
            reverse('projectroles:taskflow_role_delete'),
            reverse('projectroles:taskflow_settings_get'),
            reverse('projectroles:taskflow_settings_set'),
        ]
        for url in urls:
            request = self.req_factory.post(url)
            response = views_taskflow.TaskflowProjectGetAPIView.as_view()(
                request
            )
            self.assertEqual(response.status_code, 403)

    @override_settings(ENABLED_BACKEND_PLUGINS=[])
    def test_disable_api_views(self):
        """Test to make sure API views are disabled without taskflow"""
        urls = [
            reverse('projectroles:taskflow_project_get'),
            reverse('projectroles:taskflow_project_update'),
            reverse('projectroles:taskflow_role_get'),
            reverse('projectroles:taskflow_role_set'),
            reverse('projectroles:taskflow_role_delete'),
            reverse('projectroles:taskflow_settings_get'),
            reverse('projectroles:taskflow_settings_set'),
        ]
        for url in urls:
            request = self.req_factory.post(
                url, data={'sodar_secret': settings.TASKFLOW_SODAR_SECRET}
            )
            response = views_taskflow.TaskflowProjectGetAPIView.as_view()(
                request
            )
            self.assertEqual(response.status_code, 403)


# Tests Requiring iRODS --------------------------------------------------------


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestProjectCreateView(TestTaskflowBase):
    """Tests for Project creation view with taskflow"""

    def test_create_project(self):
        """Test Project creation with taskflow"""

        # Assert precondition
        self.assertEqual(Project.objects.all().count(), 1)

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Assert Project state after creation
        self.assertEqual(Project.objects.all().count(), 2)
        project = Project.objects.all()[0]
        self.assertIsNotNone(project)

        expected = {
            'id': project.pk,
            'title': 'TestProject',
            'type': PROJECT_TYPE_PROJECT,
            'parent': self.category.pk,
            'submit_status': SUBMIT_STATUS_OK,
            'description': 'description',
            'public_guest_access': False,
            'full_title': self.category.title + ' / TestProject',
            'has_public_children': False,
            'sodar_uuid': project.sodar_uuid,
        }

        model_dict = model_to_dict(project)
        model_dict.pop('readme', None)
        self.assertEqual(model_dict, expected)

        # Assert owner role assignment
        owner_as = RoleAssignment.objects.get(
            project=project, role=self.role_owner
        )

        expected = {
            'id': owner_as.pk,
            'project': project.pk,
            'role': self.role_owner.pk,
            'user': self.user.pk,
            'sodar_uuid': owner_as.sodar_uuid,
        }

        self.assertEqual(model_to_dict(owner_as), expected)


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestProjectUpdateView(TestTaskflowBase):
    """Tests for Project updating view"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

    def test_update_project(self):
        """Test Project updating with taskflow"""

        # Assert precondition
        self.assertEqual(Project.objects.all().count(), 2)

        request_data = model_to_dict(self.project)
        request_data['title'] = 'updated title'
        request_data['description'] = 'updated description'
        request_data['owner'] = self.user.sodar_uuid  # NOTE: Must add owner
        request_data['readme'] = 'updated readme'
        request_data['parent'] = str(self.category.sodar_uuid)
        request_data['public_guest_access'] = True
        request_data.update(
            app_settings.get_all_settings(project=self.project, post_safe=True)
        )  # Add default settings
        request_data['sodar_url'] = self.live_server_url  # HACK

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:update',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                request_data,
            )

        # Assert Project state after update
        self.assertEqual(Project.objects.all().count(), 2)
        self.project.refresh_from_db()

        expected = {
            'id': self.project.pk,
            'title': 'updated title',
            'type': PROJECT_TYPE_PROJECT,
            'parent': self.category.pk,
            'submit_status': SUBMIT_STATUS_OK,
            'description': 'updated description',
            'public_guest_access': True,
            'full_title': self.category.title + ' / updated title',
            'has_public_children': False,
            'sodar_uuid': self.project.sodar_uuid,
        }

        model_dict = model_to_dict(self.project)
        model_dict.pop('readme', None)
        self.assertEqual(model_dict, expected)
        self.assertEqual(self.project.readme.raw, 'updated readme')

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:detail',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentCreateView(TestTaskflowBase):
    """Tests for RoleAssignment creation view"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        self.user_new = self.make_user('guest')

    def test_create_assignment(self):
        """Test RoleAssignment creation with taskflow"""
        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        # Issue POST request
        self.request_data.update(
            {
                'project': self.project.sodar_uuid,
                'user': self.user_new.sodar_uuid,
                'role': self.role_guest.pk,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.request_data,
            )

        # Assert RoleAssignment state after creation
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        role_as = RoleAssignment.objects.get(
            project=self.project, user=self.user_new
        )
        self.assertIsNotNone(role_as)

        expected = {
            'id': role_as.pk,
            'project': self.project.pk,
            'user': self.user_new.pk,
            'role': self.role_guest.pk,
            'sodar_uuid': role_as.sodar_uuid,
        }

        self.assertEqual(model_to_dict(role_as), expected)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:roles',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentUpdateView(TestTaskflowBase):
    """Tests for RoleAssignment update view with taskflow"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Create guest user and role
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )

    def test_update_assignment(self):
        """Test RoleAssignment updating with taskflow"""

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 3)

        self.request_data.update(
            {
                'project': self.project.sodar_uuid,
                'user': self.user_new.sodar_uuid,
                'role': self.role_contributor.pk,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_update',
                    kwargs={'roleassignment': self.role_as.sodar_uuid},
                ),
                self.request_data,
            )

        # Assert RoleAssignment state after update
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        role_as = RoleAssignment.objects.get(
            project=self.project, user=self.user_new
        )
        self.assertIsNotNone(role_as)

        expected = {
            'id': role_as.pk,
            'project': self.project.pk,
            'user': self.user_new.pk,
            'role': self.role_contributor.pk,
            'sodar_uuid': role_as.sodar_uuid,
        }

        self.assertEqual(model_to_dict(role_as), expected)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:roles',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentOwnerTransferView(TestTaskflowBase):
    """Tests for ownership transfer view with taskflow"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Create guest user and role
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment(
            self.project, self.user_new, self.role_guest
        )

    def test_transfer_owner(self):
        """Test ownership transfer with taskflow"""

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 3)

        self.request_data.update(
            {
                'project': self.project.sodar_uuid,
                'user': self.user_new.sodar_uuid,
                'role': self.role_contributor.pk,
            }
        )

        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_owner_transfer',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={
                    'project': self.project.sodar_uuid,
                    'old_owner_role': self.role_guest.pk,
                    'new_owner': self.user_new.sodar_uuid,
                },
            )

        # Assert RoleAssignment state after update
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        role_as = RoleAssignment.objects.get(
            project=self.project, user=self.user_new
        )
        self.assertEqual(role_as.role, self.role_owner)
        # TODO: Test resulting users in iRODS once we do issue #387


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentDeleteView(TestTaskflowBase):
    """Tests for RoleAssignment delete view"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Create guest user and role
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )

    def test_delete_assignment(self):
        """Test RoleAssignment deleting with taskflow"""

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 3)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': self.role_as.sodar_uuid},
                ),
                self.request_data,
            )

        # Assert RoleAssignment state after update
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:roles',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestProjectInviteAcceptView(ProjectInviteMixin, TestTaskflowBase):
    """Tests for ProjectInvite accepting view with taskflow"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Create guest user and role
        self.user_new = self.make_user('newuser')

    @override_settings(PROJECTROLES_ALLOW_LOCAL_USERS=True)
    @override_settings(AUTH_LDAP_USERNAME_DOMAIN='EXAMPLE')
    @override_settings(AUTH_LDAP_DOMAIN_PRINTABLE='EXAMPLE')
    @override_settings(ENABLE_LDAP=True)
    def test_accept_invite_ldap(self):
        """Test LDAP user accepting an invite with taskflow"""

        # Init invite
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='',
        )

        # Assert preconditions
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        self.assertEqual(
            RoleAssignment.objects.filter(
                project=self.project,
                user=self.user_new,
                role=self.role_contributor,
            ).count(),
            0,
        )

        with self.login(self.user_new):
            response = self.client.get(
                reverse(
                    'projectroles:invite_accept',
                    kwargs={'secret': invite.secret},
                ),
                self.request_data,
                follow=True,
            )

            self.assertListEqual(
                response.redirect_chain,
                [
                    (
                        reverse(
                            'projectroles:invite_process_ldap',
                            kwargs={'secret': invite.secret},
                        ),
                        302,
                    ),
                    (
                        reverse('home'),
                        302,
                    ),
                ],
            )

    @override_settings(PROJECTROLES_ALLOW_LOCAL_USERS=True)
    @override_settings(AUTH_LDAP_USERNAME_DOMAIN='EXAMPLE')
    @override_settings(AUTH_LDAP_DOMAIN_PRINTABLE='EXAMPLE')
    @override_settings(ENABLE_LDAP=True)
    def test_accept_invite_ldap_category(self):
        """Test LDAP user accepting an invite with taskflow for a category"""

        # Init invite
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.category,
            role=self.role_contributor,
            issuer=self.user,
            message='',
        )

        # Assert preconditions
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        self.assertEqual(
            RoleAssignment.objects.filter(
                project=self.category,
                user=self.user_new,
                role=self.role_contributor,
            ).count(),
            0,
        )

        with self.login(self.user_new):
            response = self.client.get(
                reverse(
                    'projectroles:invite_accept',
                    kwargs={'secret': invite.secret},
                ),
                self.request_data,
                follow=True,
            )

            self.assertListEqual(
                response.redirect_chain,
                [
                    (
                        reverse(
                            'projectroles:invite_process_ldap',
                            kwargs={'secret': invite.secret},
                        ),
                        302,
                    ),
                    (
                        reverse(
                            'projectroles:detail',
                            kwargs={'project': self.category.sodar_uuid},
                        ),
                        302,
                    ),
                ],
            )

    def test_accept_invite_local(self):
        """Test local user accepting an invite with taskflow"""

        # Init invite
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='',
        )

        # Assert preconditions
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        with self.login(self.user_new):
            response = self.client.get(
                reverse(
                    'projectroles:invite_accept',
                    kwargs={'secret': invite.secret},
                ),
                self.request_data,
                follow=True,
            )

            self.assertListEqual(
                response.redirect_chain,
                [
                    (
                        reverse(
                            'projectroles:invite_process_local',
                            kwargs={'secret': invite.secret},
                        ),
                        302,
                    ),
                    (
                        reverse('home'),
                        302,
                    ),
                ],
            )

            # Assert postconditions
            self.assertEqual(
                ProjectInvite.objects.filter(active=True).count(), 1
            )

    def test_accept_invite_local_category(self):
        """Test local user accepting an invite with taskflow for a category"""

        # Init invite
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.category,
            role=self.role_contributor,
            issuer=self.user,
            message='',
        )

        # Assert preconditions
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        self.assertEqual(
            RoleAssignment.objects.filter(
                project=self.category,
                user=self.user_new,
                role=self.role_contributor,
            ).count(),
            0,
        )

        with self.login(self.user_new):
            response = self.client.get(
                reverse(
                    'projectroles:invite_accept',
                    kwargs={'secret': invite.secret},
                ),
                self.request_data,
                follow=True,
            )

            self.assertListEqual(
                response.redirect_chain,
                [
                    (
                        reverse(
                            'projectroles:invite_process_local',
                            kwargs={'secret': invite.secret},
                        ),
                        302,
                    ),
                    (
                        reverse('home'),
                        302,
                    ),
                ],
            )

            # Assert postconditions
            self.assertEqual(
                ProjectInvite.objects.filter(active=True).count(), 1
            )
