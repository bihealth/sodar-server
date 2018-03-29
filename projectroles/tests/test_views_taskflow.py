"""Integration tests for views in the projectroles Django app with taskflow"""

# NOTE: You must supply 'omics_url': self.live_server_url in taskflow requests!
#       This is due to the Django 1.10.x feature described here:
#       https://code.djangoproject.com/ticket/27596

from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test import LiveServerTestCase

# HACK to get around https://stackoverflow.com/a/25081791
from .taskflow_testcase import TestCase

from unittest import skipIf     # Could also use tags..

from ..models import Project, Role, RoleAssignment, ProjectInvite, \
    OMICS_CONSTANTS
from .test_models import ProjectInviteMixin
from projectroles.plugins import get_backend_api, change_plugin_status


User = auth.get_user_model()


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']


# Local constants
INVITE_EMAIL = 'test@example.com'
SECRET = 'rsd886hi8276nypuvw066sbvv0rb2a6x'
TASKFLOW_ENABLED = True if \
    'taskflow' in settings.ENABLED_BACKEND_PLUGINS else False
TASKFLOW_SKIP_MSG = 'Taskflow not enabled in settings'


class TaskflowMixin:
    def _make_project_taskflow(
            self, title, type, parent, owner, description):
        values = {
            'title': title,
            'type': type,
            'parent': None,
            'owner': owner.pk,
            'description': 'description',
            'omics_url': self.live_server_url}  # HACK: Override callback URL

        with self.login(self.user):
            response = self.client.post(
                reverse('projectroles:create'),
                values)
            project = Project.objects.get(title=title)
            self.assertRedirects(
                response, reverse('projectroles:detail', kwargs={'pk': project.omics_uuid}))

        project = Project.objects.get(title=title)
        owner_as = project.get_owner()
        return project, owner_as

    def _make_assignment_taskflow(
            self, project, user, role):
        values = {
            'project': project.pk,
            'user': user.pk,
            'role': role.pk,
            'omics_url': self.live_server_url}

        with self.login(self.user):
            response = self.client.post(
                reverse('projectroles:create', kwargs={
                    'project': project.omics_uuid}),
                values)
            role_as = RoleAssignment.objects.get(
                project=project, user=user)
            self.assertRedirects(response, reverse(
                'project_roles', kwargs={'pk': project.omics_uuid}))

        role_as = RoleAssignment.objects.get(project=project, user=user)
        return role_as


class TestViewsTaskflowBase(LiveServerTestCase, TestCase):
    """Base class for view testing with taskflow"""

    def setUp(self):
        # Get taskflow plugin (or None if taskflow not enabled)
        change_plugin_status(
            name='taskflow',
            status=0,   # 0 = Enabled
            plugin_type='backend')
        self.taskflow = get_backend_api('taskflow', force=True)

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_staff = Role.objects.get_or_create(
            name=PROJECT_ROLE_STAFF)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init superuser
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

    def tearDown(self):
        self.taskflow.cleanup()


class TestProjectCreateView(TestViewsTaskflowBase, TaskflowMixin):
    """Tests for Project creation view with taskflow"""

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_create_project(self):
        """Test Project creation with taskflow"""

        # Assert precondition
        self.assertEqual(Project.objects.all().count(), 0)

        # Issue POST request
        values = {
            'title': 'TestProject',
            'type': PROJECT_TYPE_PROJECT,
            'parent': None,
            'owner': self.user.pk,
            'description': 'description',
            'omics_url': self.live_server_url}  # HACK: Override callback URL

        with self.login(self.user):
            response = self.client.post(
                reverse('projectroles:create'),
                values)

        # Assert Project state after creation
        self.assertEqual(Project.objects.all().count(), 1)
        project = Project.objects.all()[0]
        self.assertIsNotNone(project)

        expected = {
            'id': project.pk,
            'title': 'TestProject',
            'type': PROJECT_TYPE_PROJECT,
            'parent': None,
            'submit_status': SUBMIT_STATUS_OK,
            'description': 'description'}

        model_dict = model_to_dict(project)
        model_dict.pop('readme', None)
        self.assertEqual(model_dict, expected)

        # Assert owner role assignment
        owner_as = RoleAssignment.objects.get(
            project=project, role=self.role_owner)

        expected = {
            'id': owner_as.pk,
            'project': project.pk,
            'role': self.role_owner.pk,
            'user': self.user.pk}

        self.assertEqual(model_to_dict(owner_as), expected)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response, reverse(
                    'projectroles:detail',
                    kwargs={'project': project.omics_uuid}))


class TestProjectUpdateView(TestViewsTaskflowBase, TaskflowMixin):
    """Tests for Project updating view"""

    def setUp(self):
        super(TestProjectUpdateView, self).setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None,
            owner=self.user,
            description='description')

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_update_project(self):
        """Test Project updating with taskflow"""

        # Assert precondition
        self.assertEqual(Project.objects.all().count(), 1)

        values = model_to_dict(self.project)
        values['title'] = 'updated title'
        values['description'] = 'updated description'
        values['owner'] = self.user.pk  # NOTE: Must add owner
        values['omics_url'] = self.live_server_url  # HACK

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:update',
                    kwargs={'project': self.project.omics_uuid}),
                values)

        # Assert Project state after update
        self.assertEqual(Project.objects.all().count(), 1)
        project = Project.objects.all()[0]
        self.assertIsNotNone(project)

        expected = {
            'id': project.pk,
            'title': 'updated title',
            'type': PROJECT_TYPE_PROJECT,
            'parent': None,
            'submit_status': SUBMIT_STATUS_OK,
            'description': 'updated description'}

        model_dict = model_to_dict(project)
        model_dict.pop('readme', None)
        self.assertEqual(model_dict, expected)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response, reverse(
                    'projectroles:detail',
                    kwargs={'project': project.omics_uuid}))


class TestRoleAssignmentCreateView(TestViewsTaskflowBase, TaskflowMixin):
    """Tests for RoleAssignment creation view"""

    def setUp(self):
        super(TestRoleAssignmentCreateView, self).setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None,
            owner=self.user,
            description='description')

        self.user_new = self.make_user('guest')

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_create_assignment(self):
        """Test RoleAssignment creation with taskflow"""
        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 1)

        # Issue POST request
        values = {
            'project': self.project.pk,
            'user': self.user_new.pk,
            'role': self.role_guest.pk,
            'omics_url': self.live_server_url}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_create',
                    kwargs={'project': self.project.omics_uuid}),
                values)

        # Assert RoleAssignment state after creation
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        role_as = RoleAssignment.objects.get(
            project=self.project, user=self.user_new)
        self.assertIsNotNone(role_as)

        expected = {
            'id': role_as.pk,
            'project': self.project.pk,
            'user': self.user_new.pk,
            'role': self.role_guest.pk}

        self.assertEqual(model_to_dict(role_as), expected)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(response, reverse(
                'projectroles:roles',
                kwargs={'project': self.project.omics_uuid}))


class TestRoleAssignmentUpdateView(TestViewsTaskflowBase, TaskflowMixin):
    """Tests for RoleAssignment update view with taskflow"""

    def setUp(self):
        super(TestRoleAssignmentUpdateView, self).setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None,
            owner=self.user,
            description='description')

        # Create guest user and role
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment_taskflow(
            self.project, self.user_new, self.role_guest)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_update_assignment(self):
        """Test RoleAssignment updating with taskflow"""

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        values = model_to_dict(self.role_as)
        values['role'] = self.role_contributor.pk
        values['omics_url'] = self.live_server_url

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_update',
                    kwargs={'roleassignment': self.role_as.omics_uuid}),
                values)

        # Assert RoleAssignment state after update
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        role_as = RoleAssignment.objects.get(
            project=self.project, user=self.user_new)
        self.assertIsNotNone(role_as)

        expected = {
            'id': role_as.pk,
            'project': self.project.pk,
            'user': self.user_new.pk,
            'role': self.role_contributor.pk}

        self.assertEqual(model_to_dict(role_as), expected)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(response, reverse(
                'projectroles:roles',
                kwargs={'project': self.project.omics_uuid}))


class TestRoleAssignmentDeleteView(TestViewsTaskflowBase, TaskflowMixin):
    """Tests for RoleAssignment delete view """

    def setUp(self):
        super(TestRoleAssignmentDeleteView, self).setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None,
            owner=self.user,
            description='description')

        # Create guest user and role
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment_taskflow(
            self.project, self.user_new, self.role_guest)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_delete_assignment(self):
        """Test RoleAssignment deleting with taskflow"""

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': self.role_as.omics_uuid}),
                {'omics_url': self.live_server_url})

        # Assert RoleAssignment state after update
        self.assertEqual(RoleAssignment.objects.all().count(), 1)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(response, reverse(
                'projectroles:roles',
                kwargs={'project': self.project.omics_uuid}))


class TestProjectInviteAcceptView(
        TestViewsTaskflowBase, TaskflowMixin, ProjectInviteMixin):
    """Tests for ProjectInvite accepting view with taskflow"""

    def setUp(self):
        super(TestProjectInviteAcceptView, self).setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None,
            owner=self.user,
            description='description')

        # Create guest user and role
        self.user_new = self.make_user('newuser')

        # Init invite
        self.invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='')

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_accept_invite(self):
        """Test user accepting an invite with taskflow"""

        # Assert preconditions
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        self.assertEqual(RoleAssignment.objects.filter(
            project=self.project,
            user=self.user_new,
            role=self.role_contributor).count(), 0)

        with self.login(self.user_new):
            response = self.client.get(reverse(
                'projectroles:invite_accept',
                kwargs={'secret': self.invite.secret}),
                {'omics_url': self.live_server_url})

            self.assertRedirects(response, reverse(
                'projectroles:detail',
                kwargs={'project': self.project.omics_uuid}))

            # Assert postconditions
            self.assertEqual(
                ProjectInvite.objects.filter(active=True).count(), 0)

            self.assertEqual(RoleAssignment.objects.filter(
                project=self.project,
                user=self.user_new,
                role=self.role_contributor).count(), 1)
