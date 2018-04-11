"""Tests for models in the projectroles Django app"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils import timezone

from test_plus.test import TestCase

from ..models import Project, Role, RoleAssignment, ProjectInvite, \
    ProjectSetting, ProjectUserTag, OMICS_CONSTANTS, PROJECT_TAG_STARRED
from ..plugins import get_app_plugin

# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']


# Settings
INVITE_EXPIRY_DAYS = settings.PROJECTROLES_INVITE_EXPIRY_DAYS


# Local constants
SECRET = 'rsd886hi8276nypuvw066sbvv0rb2a6x'


class ProjectMixin:
    """Helper mixin for Project creation"""

    @classmethod
    def _make_project(
            cls, title, type, parent, description='',
            submit_status=SUBMIT_STATUS_OK):
        """Make and save a Project"""
        values = {
            'title': title,
            'type': type,
            'parent': parent,
            'submit_status': submit_status,
            'description': description}
        project = Project(**values)
        project.save()

        return project


class ProjectInviteMixin:
    """Helper mixin for ProjectInvite creation"""
    @classmethod
    def _make_invite(
            cls, email, project, role, issuer, message, date_expire=None):
        """Make and save a ProjectInvite"""
        values = {
            'email': email,
            'project': project,
            'role': role,
            'issuer': issuer,
            'message': message,
            'date_expire': date_expire if date_expire else (
                timezone.now() + timezone.timedelta(days=INVITE_EXPIRY_DAYS)),
            'secret': SECRET,
            'active': True}
        invite = ProjectInvite(**values)
        invite.save()

        return invite


class ProjectSettingMixin:
    """Helper mixin for ProjectSetting creation"""

    @classmethod
    def _make_setting(cls, app_name, project, name, setting_type, value):
        """Make and save a ProjectSetting"""
        values = {
            'app_plugin': get_app_plugin(app_name).get_model(),
            'project': project,
            'name': name,
            'type': setting_type,
            'value': value}
        setting = ProjectSetting(**values)
        setting.save()
        return setting


class ProjectUserTagMixin:
    """Helper mixin for ProjectUserTag creation"""

    @classmethod
    def _make_tag(cls, project, user, name):
        """Make and save a ProjectUserTag"""
        values = {
            'project': project,
            'user': user,
            'name': name}
        tag = ProjectUserTag(**values)
        tag.save()
        return tag


class TestProject(TestCase, ProjectMixin):
    """Tests for model.Project"""

    def setUp(self):
        # Top level category
        self.category_top = self._make_project(
            title='TestCategoryTop',
            type=PROJECT_TYPE_CATEGORY,
            parent=None)
        # Subproject under category_top
        self.project_sub = self._make_project(
            title='TestProjectSub',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category_top)
        # Top level project
        self.project_top = self._make_project(
            title='TestProjectTop',
            type=PROJECT_TYPE_PROJECT,
            parent=None)

    def test_initialization(self):
        expected = {
            'id': self.project_sub.pk,
            'title': 'TestProjectSub',
            'type': PROJECT_TYPE_PROJECT,
            'parent': self.category_top.pk,
            'submit_status': SUBMIT_STATUS_OK,
            'omics_uuid': self.project_sub.omics_uuid,
            'description': ''}
        model_dict = model_to_dict(self.project_sub)
        # HACK: Can't compare markupfields like this. Better solution?
        model_dict.pop('readme', None)
        self.assertEqual(model_dict, expected)

    def test__str__(self):
        expected = 'TestCategoryTop / TestProjectSub'
        self.assertEqual(str(self.project_sub), expected)

    def test__repr__(self):
        expected = "Project('TestProjectSub', 'PROJECT', " \
            "'TestCategoryTop')"
        self.assertEqual(repr(self.project_sub), expected)

    def test_get_children_top(self):
        """Test children getting function for top category"""
        children = self.category_top.get_children()
        self.assertEqual(children[0], self.project_sub)

    def test_get_children_sub(self):
        """Test children getting function for sub project"""
        children = self.project_sub.get_children()
        self.assertEqual(children.count(), 0)

    def test_get_depth_top(self):
        """Test project depth getting function for top category"""
        self.assertEqual(self.category_top.get_depth(), 0)

    def test_get_depth_sub(self):
        """Test children getting function for sub project"""
        self.assertEqual(self.project_sub.get_depth(), 1)

    def test_get_parents_top(self):
        """Test get parents function for top category"""
        self.assertEqual(self.category_top.get_parents(), None)

    def test_get_parents_sub(self):
        """Test get parents function for sub project"""
        self.assertEqual(
            list(self.project_sub.get_parents()), [self.category_top])

    def test_get_full_title_top(self):
        """Test full title function for top category"""
        self.assertEqual(
            self.category_top.get_full_title(), self.category_top.title)

    def test_get_full_title_sub(self):
        """Test full title function for sub project"""
        expected = self.category_top.title + ' / ' + self.project_sub.title
        self.assertEqual(
            self.project_sub.get_full_title(), expected)

    def test_validate_parent(self):
        """Test parent ForeignKey validation: project can't be its own
        parent"""
        with self.assertRaises(ValidationError):
            project_tmp = self.project_top
            project_tmp.parent = project_tmp
            project_tmp.save()

    def test_validate_title(self):
        """Test title validation: title can't be equal between subproject and
        parent"""
        with self.assertRaises(ValidationError):
            self._make_project(
                title='TestCategoryTop',
                type=PROJECT_TYPE_PROJECT,
                parent=self.category_top)

    def test_validate_parent_type(self):
        """Test parent type validation"""
        with self.assertRaises(ValidationError):
            self._make_project(
                title='FailProject',
                type=PROJECT_TYPE_PROJECT,
                parent=self.project_top)

    def test_get_absolute_url(self):
        """Test get_absolute_url()"""
        expected_url = reverse(
            'projectroles:detail',
            kwargs={'project': self.project_sub.omics_uuid})
        self.assertEqual(self.project_sub.get_absolute_url(), expected_url)


class TestRole(TestCase):

    def setUp(self):
        self.role = Role.objects.get(
            name=PROJECT_ROLE_OWNER)

    def test_initialization(self):
        expected = {
            'id': self.role.pk,
            'name': PROJECT_ROLE_OWNER,
            'description': self.role.description}
        self.assertEqual(model_to_dict(self.role), expected)

    def test__str__(self):
        expected = PROJECT_ROLE_OWNER
        self.assertEqual(str(self.role), expected)

    def test__repr__(self):
        expected = "Role('{}')".format(PROJECT_ROLE_OWNER)
        self.assertEqual(repr(self.role), expected)


class RoleAssignmentMixin:
    """Helper mixin for RoleAssignment creation
    """

    @classmethod
    def _make_assignment(cls, project, user, role):
        """Make and save a RoleAssignment"""
        values = {
            'project': project,
            'user': user,
            'role': role}
        result = RoleAssignment(**values)
        result.save()
        return result


class TestRoleAssignment(TestCase, ProjectMixin, RoleAssignmentMixin):
    """Tests for model.RoleAssignment"""

    def setUp(self):
        # Init projects/categories
        # Top level category
        self.category_top = self._make_project(
            title='TestCategoryTop',
            type=PROJECT_TYPE_CATEGORY,
            parent=None)
        # Subproject under category_top
        self.project_sub = self._make_project(
            title='TestProjectSub',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category_top)
        # Top level project
        self.project_top = self._make_project(
            title='TestProjectTop',
            type=PROJECT_TYPE_PROJECT,
            parent=None)

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init users
        self.user_alice = self.make_user('alice')
        self.user_bob = self.make_user('bob')
        self.user_carol = self.make_user('carol')
        self.user_dan = self.make_user('dan')
        self.user_erin = self.make_user('erin')
        self.user_frank = self.make_user('frank')

        # Init assignment
        self.assignment_owner = self._make_assignment(
            self.category_top, self.user_alice, self.role_owner)

        self.expected_default = {
            'id': self.assignment_owner.pk,
            'project': self.category_top.pk,
            'user': self.user_alice.pk,
            'role': self.role_owner.pk,
            'omics_uuid': self.assignment_owner.omics_uuid}

    def test_initialization(self):
        self.assertEqual(
            model_to_dict(self.assignment_owner), self.expected_default)

    def test__str__(self):
        expected = 'TestCategoryTop: {}: alice'.format(PROJECT_ROLE_OWNER)
        self.assertEqual(str(self.assignment_owner), expected)

    def test__repr__(self):
        expected = "RoleAssignment('TestCategoryTop', 'alice', '{}')".format(
            PROJECT_ROLE_OWNER)
        self.assertEqual(repr(self.assignment_owner), expected)

    def test_validate_user(self):
        """Test user role uniqueness validation: can't add more than one
        role for user in project at once"""
        with self.assertRaises(ValidationError):
            self._make_assignment(
                self.category_top, self.user_alice, self.role_contributor)

    def test_validate_owner(self):
        """Test owner uniqueness validation: can't add owner for project if
        one already exists"""
        with self.assertRaises(ValidationError):
            self._make_assignment(
                self.category_top, self.user_bob, self.role_owner)

    def test_validate_delegate(self):
        """Test delegate validation: can't add delegate for project if one
        already exists"""
        self._make_assignment(
            self.project_sub, self.user_bob, self.role_delegate)

        with self.assertRaises(ValidationError):
            self._make_assignment(
                self.project_sub, self.user_carol, self.role_delegate)

    def test_validate_category(self):
        """Test category validation: can't add roles other than owner for
        projects of type CATEGORY"""
        with self.assertRaises(ValidationError):
            self._make_assignment(
                self.category_top, self.user_bob, self.role_contributor)

    # Tests for RoleAssignmentManager

    def test_get_assignment(self):
        """Test get_assignment() results"""
        self.assertEqual(
            model_to_dict(RoleAssignment.objects.get_assignment(
                self.user_alice, self.category_top)), self.expected_default)

    def test_get_project_owner(self):
        """Test get_project_owner() results"""
        self.assertEqual(self.category_top.get_owner().user, self.user_alice)

    def test_get_project_delegate(self):
        """Test get_project_delegate() results"""
        assignment_del = self._make_assignment(
            self.project_top, self.user_carol, self.role_delegate)
        self.assertEqual(
            self.project_top.get_delegate().user, self.user_carol)

    def test_get_project_members(self):
        """Test get_project_members() results"""
        assignment_c0 = self._make_assignment(
            self.project_top, self.user_erin, self.role_contributor)
        assignment_c1 = self._make_assignment(
            self.project_top, self.user_frank, self.role_contributor)

        expected = [
            {
                'id': assignment_c0.pk,
                'project': self.project_top.pk,
                'user': self.user_erin.pk,
                'role': self.role_contributor.pk,
                'omics_uuid': assignment_c0.omics_uuid
            },
            {
                'id': assignment_c1.pk,
                'project': self.project_top.pk,
                'user': self.user_frank.pk,
                'role': self.role_contributor.pk,
                'omics_uuid': assignment_c1.omics_uuid
            }
        ]

        members = self.project_top.get_members()

        for i in range(0, members.count()):
            self.assertEqual(model_to_dict(members[i]), expected[i])

    def test_has_role(self):
        """Test the has_role() function for an existing role"""
        self.assertEqual(self.category_top.has_role(self.user_alice), True)

    def test_has_role_norole(self):
        """Test the has_role() function for a non-existing role without
        recursion"""
        self._make_assignment(
            self.project_sub, self.user_bob, self.role_contributor)
        self.assertEqual(self.category_top.has_role(self.user_bob), False)

    def test_has_role_norole_children(self):
        """Test the has_role() function for a non-existing role with
        recursion using include_children"""
        self._make_assignment(
            self.project_sub, self.user_bob, self.role_contributor)
        self.assertEqual(self.category_top.has_role(
            self.user_bob, include_children=True), True)


class TestProjectInvite(
        TestCase, ProjectMixin, RoleAssignmentMixin, ProjectInviteMixin):
    """Tests for model.ProjectInvite"""

    def setUp(self):
        # Init project
        self.project = self._make_project(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None)

        # Init roles
        self.role_owner = Role.objects.get(
            name=PROJECT_ROLE_OWNER)
        self.role_delegate = Role.objects.get(
            name=PROJECT_ROLE_DELEGATE)
        self.role_contributor = Role.objects.get(
            name=PROJECT_ROLE_CONTRIBUTOR)

        # Init user & role
        self.user = self.make_user('owner')
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init invite
        self.invite = self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='')

    def test_initialization(self):
        expected = {
            'id': self.invite.pk,
            'email': 'test@example.com',
            'project': self.project.pk,
            'role': self.role_contributor.pk,
            'issuer': self.user.pk,
            'date_expire': self.invite.date_expire,
            'message': '',
            'secret': SECRET,
            'omics_uuid': self.invite.omics_uuid,
            'active': True}
        self.assertEqual(model_to_dict(self.invite), expected)

    def test__str__(self):
        expected = 'TestProject: test@example.com (project contributor) ' \
                   '[ACTIVE]'
        self.assertEqual(str(self.invite), expected)

    def test__repr__(self):
        expected = "ProjectInvite('TestProject', 'test@example.com', " \
            "'project contributor', True)"
        self.assertEqual(repr(self.invite), expected)


class TestProjectManager(TestCase, ProjectMixin, RoleAssignmentMixin):
    """Tests for ProjectManager"""

    def setUp(self):
        # Init projects/categories
        # Top level category
        self.category_top = self._make_project(
            title='TestCategoryTop',
            type=PROJECT_TYPE_CATEGORY,
            parent=None,
            description='XXX')
        # Subproject under category_top
        self.project_sub = self._make_project(
            title='TestProjectSub',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category_top,
            description='YYY')

    def test_find_all(self):
        """Test find() with any project type"""
        result = Project.objects.find(
            'Test', project_type=None)
        self.assertEqual(len(result), 2)
        result = Project.objects.find(
            'ThisFails', project_type=None)
        self.assertEqual(len(result), 0)

    def test_find_project(self):
        """Test find() with project_type=PROJECT"""
        result = Project.objects.find(
            'Test', project_type=PROJECT_TYPE_PROJECT)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.project_sub)

    def test_find_category(self):
        """Test find() with project_type=CATEGORY"""
        result = Project.objects.find(
            'Test', project_type=PROJECT_TYPE_CATEGORY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.category_top)

    def test_find_description(self):
        """Test find() with search term for description"""
        result = Project.objects.find(
            'XXX', project_type=None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.category_top)


class TestProjectSetting(
        TestCase, ProjectMixin, RoleAssignmentMixin, ProjectSettingMixin):
    """Tests for model.ProjectSetting"""
    # NOTE: This assumes the filesfolders app is available!
    def setUp(self):
        # Init project
        self.project = self._make_project(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None)

        # Init role
        self.role_owner = Role.objects.get(
            name=PROJECT_ROLE_OWNER)

        # Init user & role
        self.user = self.make_user('owner')
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init test setting
        self.setting_str = self._make_setting(
            app_name='filesfolders',
            project=self.project,
            name='str_setting',
            setting_type='STRING',
            value='test')

        # Init integer setting
        self.setting_int = self._make_setting(
            app_name='filesfolders',
            project=self.project,
            name='int_setting',
            setting_type='INTEGER',
            value=170)

        # Init boolean setting
        self.setting_bool = self._make_setting(
            app_name='filesfolders',
            project=self.project,
            name='bool_setting',
            setting_type='BOOLEAN',
            value=True)

    def test_initialization(self):
        expected = {
            'id': self.setting_str.pk,
            'app_plugin': get_app_plugin('filesfolders').get_model().pk,
            'project': self.project.pk,
            'name': 'str_setting',
            'type': 'STRING',
            'value': 'test',
            'omics_uuid': self.setting_str.omics_uuid}
        self.assertEqual(model_to_dict(self.setting_str), expected)

    def test_initialization_integer(self):
        """Test initialization with integer value"""
        expected = {
            'id': self.setting_int.pk,
            'app_plugin': get_app_plugin('filesfolders').get_model().pk,
            'project': self.project.pk,
            'name': 'int_setting',
            'type': 'INTEGER',
            'value': '170',
            'omics_uuid': self.setting_int.omics_uuid}
        self.assertEqual(model_to_dict(self.setting_int), expected)

    def test__str__(self):
        expected = 'TestProject: filesfolders / str_setting'
        self.assertEqual(str(self.setting_str), expected)

    def test__repr__(self):
        expected = "ProjectSetting('TestProject', 'filesfolders', " \
            "'str_setting')"
        self.assertEqual(repr(self.setting_str), expected)

    def test_get_value_str(self):
        """Test get_value() with type STRING"""
        val = self.setting_str.get_value()
        self.assertIsInstance(val, str)
        self.assertEqual(val, 'test')

    def test_get_value_int(self):
        """Test get_value() with type INTEGER"""
        val = self.setting_int.get_value()
        self.assertIsInstance(val, int)
        self.assertEqual(val, 170)

    def test_get_value_bool(self):
        """Test get_value() with type BOOLEAN"""
        val = self.setting_bool.get_value()
        self.assertIsInstance(val, bool)
        self.assertEqual(val, True)

# TODO: Test manager


class TestProjectUserTag(
        TestCase, ProjectMixin, RoleAssignmentMixin, ProjectUserTagMixin):
    """Tests for model.ProjectUserTag"""

    def setUp(self):
        # Init project
        self.project = self._make_project(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=None)

        # Init role
        self.role_owner = Role.objects.get(
            name=PROJECT_ROLE_OWNER)

        # Init user & role
        self.user = self.make_user('owner')
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init tag
        self.tag = self._make_tag(self.project, self.user, PROJECT_TAG_STARRED)

    def test_initialization(self):
        expected = {
            'id': self.tag.pk,
            'project': self.project.pk,
            'user': self.user.pk,
            'name': PROJECT_TAG_STARRED,
            'omics_uuid': self.tag.omics_uuid}
        self.assertEqual(model_to_dict(self.tag), expected)

    def test__str__(self):
        expected = 'TestProject: owner: STARRED'
        self.assertEqual(str(self.tag), expected)

    def test__repr__(self):
        expected = "ProjectUserTag('TestProject', 'owner', 'STARRED')"
        self.assertEqual(repr(self.tag), expected)
