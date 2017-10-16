"""Tests for views in the projectroles Django app"""

from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test import RequestFactory
from django.utils import timezone

from test_plus.test import TestCase

from .. import views
from ..models import Project, Role, RoleAssignment, ProjectInvite, \
    OMICS_CONSTANTS
from ..plugins import change_plugin_status, get_backend_api
from .test_models import ProjectMixin, RoleAssignmentMixin, ProjectInviteMixin
from projectroles.utils import get_user_display_name


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


class TestViewsBase(TestCase):
    """Base class for view testing"""

    def setUp(self):
        self.req_factory = RequestFactory()

        # Force disabling of taskflow plugin if it's available
        if get_backend_api('taskflow'):
            change_plugin_status(
                name='taskflow',
                status=1,  # 0 = Disabled
                plugin_type='backend')

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


class TestHomeView(TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for the home view"""

    def setUp(self):
        super(TestHomeView, self).setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_render(self):
        """Test to ensure the home view renders correctly"""
        with self.login(self.user):
            response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

        # Assert the project list is provided by context processors
        self.assertIsNotNone(response.context['project_list'])
        self.assertEqual(
            response.context['project_list'][0].pk, self.project.pk)

        # Assert statistics values
        self.assertEqual(response.context['count_categories'], 0)
        self.assertEqual(response.context['count_projects'], 1)
        self.assertEqual(response.context['count_users'], 1)
        self.assertEqual(response.context['count_assignments'], 1)


class TestProjectDetailView(TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for Project detail view"""

    def setUp(self):
        super(TestProjectDetailView, self).setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_render(self):
        """Test rendering of project detail view"""
        with self.login(self.user):
            response = self.client.get(
                reverse('project_detail', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'].pk, self.project.pk)


class TestProjectCreateView(TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for Project creation view"""

    def test_render_top(self):
        """Test rendering of top level Project creation form"""
        with self.login(self.user):
            response = self.client.get(
                reverse('project_create'))

        self.assertEqual(response.status_code, 200)

        # Assert form field values
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertEqual(form.fields['type'].initial, PROJECT_TYPE_PROJECT)
        self.assertEqual(form.fields['parent'].disabled, True)

    def test_render_sub(self):
        """Test rendering of Project creation form if creating a subproject"""
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Create another user to enable checking for owner selection
        self.user_new = self.make_user('newuser')

        with self.login(self.user):
            response = self.client.get(
                reverse('project_create', kwargs={'parent': self.project.pk}))

        self.assertEqual(response.status_code, 200)

        # Assert form field values
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertEqual(form.fields['type'].choices, [
            (PROJECT_TYPE_CATEGORY, 'Category'),
            (PROJECT_TYPE_PROJECT, 'Project')])
        self.assertEqual(form.fields['parent'].widget.attrs['readonly'], True)
        self.assertEqual(
            form.fields['parent'].choices, [
                (self.project.pk, self.project.title)])

    def test_create_project(self):
        """Test Project creation"""

        # Assert precondition
        self.assertEqual(Project.objects.all().count(), 0)

        # Issue POST request
        values = {
            'title': 'TestProject',
            'type': PROJECT_TYPE_PROJECT,
            'parent': None,
            'owner': self.user.pk,
            'submit_status': SUBMIT_STATUS_OK,
            'description': 'description'}

        with self.login(self.user):
            response = self.client.post(
                reverse('project_create'),
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
                response, reverse('project_detail', kwargs={'pk': project.pk}))


class TestProjectUpdateView(TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for Project updating view"""

    def setUp(self):
        super(TestProjectUpdateView, self).setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_render(self):
        """Test rendering of Project updating form"""

        # Create another user to enable checking for owner selection
        self.user_new = self.make_user('newuser')

        with self.login(self.user):
            response = self.client.get(
                reverse('project_update', kwargs={'pk': self.project.pk}))

        self.assertEqual(response.status_code, 200)

        # Assert form field values
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertEqual(form.fields['type'].choices, [
            (PROJECT_TYPE_PROJECT, 'PROJECT')])
        self.assertEqual(form.fields['parent'].disabled, True)

    def test_update_project(self):
        """Test Project updating"""

        # Assert precondition
        self.assertEqual(Project.objects.all().count(), 1)

        values = model_to_dict(self.project)
        values['title'] = 'updated title'
        values['description'] = 'updated description'
        values['owner'] = self.user.pk  # NOTE: Must add owner

        with self.login(self.user):
            response = self.client.post(
                reverse('project_update', kwargs={'pk': self.project.pk}),
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
                response, reverse('project_detail', kwargs={'pk': project.pk}))


class TestProjectRoleView(TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for project roles view"""

    def setUp(self):
        super(TestProjectRoleView, self).setUp()
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)

        # Set superuser as owner
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Set new user as delegate
        self.user_delegate = self.make_user('delegate')
        self.delegate_as = self._make_assignment(
            self.project, self.user_delegate, self.role_delegate)

        # Set another new user as guest (= one of the member roles)
        self.user_new = self.make_user('guest')
        self.guest_as = self._make_assignment(
            self.project, self.user_new, self.role_guest)

    def test_render(self):
        """Test rendering of project roles view"""
        with self.login(self.user):
            response = self.client.get(
                reverse('project_roles', kwargs={'pk': self.project.pk}))

        # Assert page
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'].pk, self.project.pk)

        # Assert owner
        expected = {
            'id': self.owner_as.pk,
            'project': self.project.pk,
            'role': self.role_owner.pk,
            'user': self.user.pk}

        self.assertEqual(
            model_to_dict(response.context['owner']), expected)

        # Assert delegate
        expected = {
            'id': self.delegate_as.pk,
            'project': self.project.pk,
            'role': self.role_delegate.pk,
            'user': self.user_delegate.pk}

        self.assertEqual(
            model_to_dict(response.context['delegate']), expected)

        # Assert member
        expected = {
            'id': self.guest_as.pk,
            'project': self.project.pk,
            'role': self.role_guest.pk,
            'user': self.user_new.pk}

        self.assertEqual(
            model_to_dict(response.context['members'][0]), expected)


class TestRoleAssignmentCreateView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for RoleAssignment creation view"""

    def setUp(self):
        super(TestRoleAssignmentCreateView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init staff user and role
        self.user_staff = self.make_user('staff')
        self.staff_as = self._make_assignment(
            self.project, self.user_staff, self.role_staff)

        self.user_new = self.make_user('guest')

    def test_render(self):
        """Test rendering of RoleAssignment creation form"""

        with self.login(self.user):
            response = self.client.get(
                reverse('role_create', kwargs={'project': self.project.pk}))

        self.assertEqual(response.status_code, 200)

        # Assert form field values
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertEqual(form.fields['project'].widget.attrs['readonly'], True)
        self.assertEqual(
            form.fields['project'].choices, [
                (self.project.pk, self.project.title)])
        # Assert user with previously added role in project is not selectable
        self.assertNotIn([(
            self.owner_as.user.pk,
            get_user_display_name(self.owner_as.user, True))],
            form.fields['user'].choices)
        # Assert owner role is not selectable
        self.assertNotIn([(
            self.role_owner.pk,
            self.role_owner.name)],
            form.fields['role'].choices)
        # Assert delegate role is selectable
        self.assertIn(
            (self.role_delegate.pk, self.role_delegate.name),
            form.fields['role'].choices)

    def test_render_staff(self):
        """Test rendering of form with a project staff role"""

        with self.login(self.user_staff):
            response = self.client.get(
                reverse('role_create', kwargs={'project': self.project.pk}))

            self.assertEqual(response.status_code, 200)

            # Assert form field values
            form = response.context['form']
            self.assertIsNotNone(form)

            # Assert delegate role is not selectable
            self.assertNotIn([(
                self.role_delegate.pk,
                self.role_delegate.name)],
                form.fields['role'].choices)

            # Assert staff role is not selectable
            self.assertNotIn([(
                self.role_staff.pk,
                self.role_staff.name)],
                form.fields['role'].choices)

    def test_create_assignment(self):
        """Test RoleAssignment creation"""
        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        # Issue POST request
        values = {
            'project': self.project.pk,
            'user': self.user_new.pk,
            'role': self.role_guest.pk}

        with self.login(self.user):
            response = self.client.post(
                reverse('role_create', kwargs={
                    'project': self.project.pk}),
                values)

        # Assert RoleAssignment state after creation
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
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
                'project_roles', kwargs={'pk': self.project.pk}))


class TestRoleAssignmentUpdateView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for RoleAssignment update view"""

    def setUp(self):
        super(TestRoleAssignmentUpdateView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init staff user and role
        self.user_staff = self.make_user('staff')
        self.staff_as = self._make_assignment(
            self.project, self.user_staff, self.role_staff)

        # Create guest user and role
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment(
            self.project, self.user_new, self.role_guest)

    def test_render(self):
        """Test rendering of RoleAssignment updating form"""
        with self.login(self.user):
            response = self.client.get(
                reverse('role_update', kwargs={
                    'project': self.project.pk,
                    'pk': self.role_as.pk}))

        self.assertEqual(response.status_code, 200)

        # Assert form field values
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertEqual(form.fields['project'].widget.attrs['readonly'], True)
        self.assertEqual(form.fields['project'].choices, [
            (self.project.pk, self.project.title)])
        self.assertEqual(form.fields['user'].widget.attrs['readonly'], True)
        self.assertEqual(
            form.fields['user'].choices, [
                (self.role_as.user.pk,
                 get_user_display_name(self.role_as.user, True))])
        # Assert owner role is not sectable
        self.assertNotIn([(
            self.role_owner.pk,
            self.role_owner.name)],
            form.fields['role'].choices)
        # Assert delegate role is selectable
        self.assertIn(
            (self.role_delegate.pk, self.role_delegate.name),
            form.fields['role'].choices)

    def test_render_staff(self):
        """Test rendering of form with a project staff role"""

        with self.login(self.user_staff):
            response = self.client.get(
                reverse('role_update', kwargs={
                    'project': self.project.pk,
                    'pk': self.role_as.pk}))

            self.assertEqual(response.status_code, 200)

            # Assert form field values
            form = response.context['form']
            self.assertIsNotNone(form)

            # Assert delegate role is not selectable
            self.assertNotIn([(
                self.role_delegate.pk,
                self.role_delegate.name)],
                form.fields['role'].choices)

            # Assert staff role is not selectable
            self.assertNotIn([(
                self.role_staff.pk,
                self.role_staff.name)],
                form.fields['role'].choices)

    def test_update_assignment(self):
        """Test RoleAssignment updating"""

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 3)

        values = model_to_dict(self.role_as)
        values['role'] = self.role_contributor.pk

        with self.login(self.user):
            response = self.client.post(
                reverse('role_update', kwargs={
                    'project': self.project.pk,
                    'pk': self.role_as.pk}),
                values)

        # Assert RoleAssignment state after update
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
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
                'project_roles', kwargs={'pk': self.project.pk}))


class TestRoleAssignmentDeleteView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for RoleAssignment delete view"""

    def setUp(self):
        super(TestRoleAssignmentDeleteView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Create guest user and role
        self.user_new = self.make_user('guest')
        self.role_as = self._make_assignment(
            self.project, self.user_new, self.role_guest)

    def test_render(self):
        """Test rendering of the RoleAssignment deletion confirmation form"""
        with self.login(self.user):
            response = self.client.get(
                reverse('role_delete', kwargs={
                    'project': self.project.pk,
                    'pk': self.role_as.pk}))

        self.assertEqual(response.status_code, 200)

    def test_delete_assignment(self):
        """Test RoleAssignment deleting"""

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        with self.login(self.user):
            response = self.client.post(
                reverse('role_delete', kwargs={
                    'project': self.project.pk,
                    'pk': self.role_as.pk}))

        # Assert RoleAssignment state after update
        self.assertEqual(RoleAssignment.objects.all().count(), 1)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(response, reverse(
                'project_roles', kwargs={'pk': self.project.pk}))


class TestProjectInviteCreateView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin, ProjectInviteMixin):
    """Tests for ProjectInvite creation view"""

    def setUp(self):
        super(TestProjectInviteCreateView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        self.new_user = self.make_user('new_user')

    def test_render(self):
        """Test rendering of ProjectInvite creation form"""

        with self.login(self.owner_as.user):
            response = self.client.get(
                reverse('role_invite_create', kwargs={
                    'project': self.project.pk}))

        self.assertEqual(response.status_code, 200)

        # Assert form field values
        form = response.context['form']
        self.assertIsNotNone(form)

        # Assert owner role is not selectable
        self.assertNotIn([(
            self.role_owner.pk,
            self.role_owner.name)],
            form.fields['role'].choices)
        # Assert delegate role is not selectable
        self.assertNotIn(
            (self.role_delegate.pk, self.role_delegate.name),
            form.fields['role'].choices)

    def test_create_invite(self):
        """Test ProjectInvite creation"""

        # Assert precondition
        self.assertEqual(ProjectInvite.objects.all().count(), 0)

        # Issue POST request
        values = {
            'email': INVITE_EMAIL,
            'project': self.project.pk,
            'role': self.role_contributor.pk}

        with self.login(self.user):
            response = self.client.post(
                reverse('role_invite_create', kwargs={
                    'project': self.project.pk}),
                values)

        # Assert ProjectInvite state after creation
        self.assertEqual(ProjectInvite.objects.all().count(), 1)

        invite = ProjectInvite.objects.get(
            project=self.project, email=INVITE_EMAIL, active=True)
        self.assertIsNotNone(invite)

        expected = {
            'id': invite.pk,
            'project': self.project.pk,
            'email': INVITE_EMAIL,
            'role': self.role_contributor.pk,
            'issuer': self.user.pk,
            'message': '',
            'date_expire': invite.date_expire,
            'secret': invite.secret,
            'active': True}

        self.assertEqual(model_to_dict(invite), expected)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(response, reverse(
                'role_invites', kwargs={'project': self.project.pk}))

    def test_accept_invite(self):
        """Test user accepting an invite"""

        # Init invite
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='')

        # Assert preconditions
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        self.assertEqual(RoleAssignment.objects.filter(
            project=self.project,
            user=self.new_user,
            role=self.role_contributor).count(), 0)

        with self.login(self.new_user):
            response = self.client.get(reverse(
                'role_invite_accept',
                kwargs={'secret': invite.secret}))

            self.assertRedirects(response, reverse(
                'project_detail', kwargs={'pk': self.project.pk}))

            # Assert postconditions
            self.assertEqual(
                ProjectInvite.objects.filter(active=True).count(), 0)

            self.assertEqual(RoleAssignment.objects.filter(
                project=self.project,
                user=self.new_user,
                role=self.role_contributor).count(), 1)

    def test_accept_invite_expired(self):
        """Test user accepting an expired invite"""

        # Init invite
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='',
            date_expire=timezone.now())

        # Assert preconditions
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        self.assertEqual(RoleAssignment.objects.filter(
            project=self.project,
            user=self.new_user,
            role=self.role_contributor).count(), 0)

        with self.login(self.new_user):
            response = self.client.get(reverse(
                'role_invite_accept',
                kwargs={'secret': invite.secret}))

            self.assertRedirects(response, reverse('home'))

            # Assert postconditions
            self.assertEqual(
                ProjectInvite.objects.filter(active=True).count(), 0)

            self.assertEqual(RoleAssignment.objects.filter(
                project=self.project,
                user=self.new_user,
                role=self.role_contributor).count(), 0)


class TestProjectInviteListView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin, ProjectInviteMixin):
    """Tests for ProjectInvite list view"""

    def setUp(self):
        super(TestProjectInviteListView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        self.invite = self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='')

    def test_render(self):
        """Test rendering of ProjectInvite list form"""

        with self.login(self.owner_as.user):
            response = self.client.get(
                reverse('role_invites', kwargs={
                    'project': self.project.pk}))

        self.assertEqual(response.status_code, 200)


class TestProjectInviteRevokeView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin, ProjectInviteMixin):
    """Tests for ProjectInvite revocation view"""

    def setUp(self):
        super(TestProjectInviteRevokeView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        self.invite = self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='')

    def test_render(self):
        """Test rendering of ProjectInvite revocation form"""

        with self.login(self.owner_as.user):
            response = self.client.get(
                reverse('role_invite_revoke', kwargs={
                    'project': self.project.pk,
                    'pk': self.invite.pk}))

        self.assertEqual(response.status_code, 200)

    def test_revoke_invite(self):
        """Test invite revocation"""

        # Assert precondition
        self.assertEqual(ProjectInvite.objects.all().count(), 1)
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        # Issue POST request
        with self.login(self.user):
            response = self.client.post(
                reverse('role_invite_revoke', kwargs={
                    'project': self.project.pk,
                    'pk': self.invite.pk}))

        # Assert ProjectInvite state after creation
        self.assertEqual(ProjectInvite.objects.all().count(), 1)
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 0)


class TestProjectGetAPIView(TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for the project retrieve API view"""

    def setUp(self):
        super(TestProjectGetAPIView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_post(self):
        """Test POST request for getting a project"""
        request = self.req_factory.post(
            reverse('taskflow_project_get'),
            data={
                'project_pk': self.project.pk})
        response = views.ProjectGetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        expected = {
            'project_pk': self.project.pk,
            'title': self.project.title,
            'description': self.project.description}

        self.assertEqual(response.data, expected)

    def test_get_pending(self):
        """Test POST request to get a pending project"""
        pd_project = self._make_project(
            title='TestProject2',
            type=PROJECT_TYPE_PROJECT,
            parent=None,
            submit_status=SUBMIT_STATUS_PENDING_TASKFLOW)

        request = self.req_factory.post(
            reverse('taskflow_project_get'),
            data={
                'project_pk': pd_project.pk})
        response = views.ProjectGetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 404)


class TestProjectUpdateAPIView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for the project updating API view"""

    def setUp(self):
        super(TestProjectUpdateAPIView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_post(self):
        """Test POST request for updating a project"""

        # NOTE: Duplicate titles not checked here, not allowed in the form
        title = 'New title'
        desc = 'New desc'

        request = self.req_factory.post(
            reverse('taskflow_project_update'),
            data={
                'project_pk': self.project.pk,
                'title': title,
                'description': desc})
        response = views.ProjectUpdateAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        self.project.refresh_from_db()
        self.assertEqual(self.project.title, title)
        self.assertEqual(self.project.description, desc)


class TestRoleAssignmentGetAPIView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for the role assignment getting API view"""

    def setUp(self):
        super(TestRoleAssignmentGetAPIView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_post(self):
        """Test POST request for getting a role assignment"""
        request = self.req_factory.post(
            reverse('taskflow_role_get'),
            data={
                'project_pk': self.project.pk,
                'user_pk': self.user.pk})
        response = views.RoleAssignmentGetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        expected = {
            'assignment_pk': self.owner_as.pk,
            'project_pk': self.project.pk,
            'user_pk': self.user.pk,
            'role_pk': self.role_owner.pk,
            'role_name': self.role_owner.name}
        self.assertEqual(response.data, expected)


class TestRoleAssignmentSetAPIView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for the role assignment setting API view"""

    def setUp(self):
        super(TestRoleAssignmentSetAPIView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_post_new(self):
        """Test POST request for assigning a new role"""
        new_user = self.make_user('new_user')

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 1)

        request = self.req_factory.post(
            reverse('taskflow_role_set'),
            data={
                'project_pk': self.project.pk,
                'user_pk': new_user.pk,
                'role_pk': self.role_contributor.pk})

        response = views.RoleAssignmentSetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        new_as = RoleAssignment.objects.get(project=self.project, user=new_user)
        self.assertEqual(new_as.role.pk, self.role_contributor.pk)

    def test_post_existing(self):
        """Test POST request for updating an existing role"""
        new_user = self.make_user('new_user')
        new_as = self._make_assignment(self.project, new_user, self.role_guest)

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        request = self.req_factory.post(
            reverse('taskflow_role_set'),
            data={
                'project_pk': self.project.pk,
                'user_pk': new_user.pk,
                'role_pk': self.role_staff.pk})

        response = views.RoleAssignmentSetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        new_as = RoleAssignment.objects.get(project=self.project, user=new_user)
        self.assertEqual(new_as.role.pk, self.role_staff.pk)


class TestRoleAssignmentDeleteAPIView(
        TestViewsBase, ProjectMixin, RoleAssignmentMixin):
    """Tests for the role assignment deletion API view"""

    def setUp(self):
        super(TestRoleAssignmentDeleteAPIView, self).setUp()

        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

    def test_post(self):
        """Test POST request for removing a role assignment"""
        new_user = self.make_user('new_user')
        new_as = self._make_assignment(self.project, new_user, self.role_guest)

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 2)

        request = self.req_factory.post(
            reverse('taskflow_role_delete'),
            data={
                'project_pk': self.project.pk,
                'user_pk': new_user.pk})

        response = views.RoleAssignmentDeleteAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoleAssignment.objects.all().count(), 1)

    def test_post_not_found(self):
        """Test POST request for removing a non-existing role assignment"""
        new_user = self.make_user('new_user')

        # Assert precondition
        self.assertEqual(RoleAssignment.objects.all().count(), 1)

        request = self.req_factory.post(
            reverse('taskflow_role_delete'),
            data={
                'project_pk': self.project.pk,
                'user_pk': new_user.pk})

        response = views.RoleAssignmentDeleteAPIView.as_view()(request)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(RoleAssignment.objects.all().count(), 1)
