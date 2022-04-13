"""Tests for projectroles views with taskflow"""

# TODO: SkipIf both taskflow and irods are not enabled
# TODO: Test for created things in iRODS

from irods.collection import iRODSCollection
from irods.exception import CollectionDoesNotExist
from irods.models import UserGroup
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.forms.models import model_to_dict
from django.test import override_settings
from django.urls import reverse

from unittest import skipIf

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


app_settings = AppSettingAPI()
User = auth.get_user_model()


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

IRODS_ACCESS_READ = 'read object'
IRODS_ACCESS_WRITE = 'modify object'
IRODS_ACCESS_NULL = 'null'


# Base Classes -----------------------------------------------------------------


# TODO: Move base classes into a base module
class TestTaskflowBase(ProjectMixin, RoleAssignmentMixin, TestCase):
    """Base class for testing UI views with taskflow"""

    def _make_project_taskflow(
        self, title, type, parent, owner, description, public_guest_access=False
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
        post_data = {
            'project': project.sodar_uuid,
            'user': user.sodar_uuid,
            'role': role.pk,
        }
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

    def _assert_access(self, user_name, target, expected):
        """
        Return access for a specific user for a target object or collection.
        Returns None if not found.

        :param user_name: String
        :param target: iRODSCollection or DataObject
        :param expected: Expected access (string or None)
        :return: String or None
        """
        access_list = self.irods_session.permissions.get(target=target)
        access = next(
            (x for x in access_list if x.user_name == user_name), None
        )
        if access:
            access = access.access_name
        self.assertEqual(access, expected)

    def setUp(self):
        # Ensure TASKFLOW_TEST_MODE is True to avoid data loss
        if not TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, testing with SODAR Taskflow '
                'disabled'
            )
        # Get taskflow plugin (or None if taskflow not enabled)
        change_plugin_status(
            name='taskflow', status=0, plugin_type='backend'  # 0 = Enabled
        )
        self.taskflow = get_backend_api('taskflow', force=True)
        self.irods_backend = get_backend_api('omics_irods')
        self.irods_session = self.irods_backend.get_session()

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
        with self.assertRaises(CollectionDoesNotExist):
            self.irods_session.collections.get(
                self.irods_backend.get_projects_path()
            )
        for user in self.irods_session.query(UserGroup).all():
            self.assertIn(
                user[UserGroup.name], settings.TASKFLOW_TEST_PERMANENT_USERS
            )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestProjectCreateView(TestTaskflowBase):
    """Tests for Project creation view with taskflow"""

    def test_create_project(self):
        """Test Project creation with taskflow"""
        self.assertEqual(Project.objects.count(), 1)
        with self.assertRaises(CollectionDoesNotExist):
            self.irods_session.collections.get(
                self.irods_backend.get_projects_path()
            )

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.assertEqual(Project.objects.count(), 2)
        project = Project.objects.first()
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

        # Assert iRODS collections
        root_coll = self.irods_session.collections.get(
            self.irods_backend.get_projects_path()
        )
        self.assertIsInstance(root_coll, iRODSCollection)
        project_coll = self.irods_session.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertIsInstance(project_coll, iRODSCollection)
        # Assert collection metadata
        self.assertEqual(
            project_coll.metadata.get_one('title').value, self.project.title
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value,
            self.project.description,
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        # Assert user group and owner access
        group_name = self.irods_backend.get_user_group_name(self.project)
        group = self.irods_session.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self._assert_access(group_name, project_coll, IRODS_ACCESS_READ)
        self.assertIsInstance(
            self.irods_session.users.get(self.user.username), iRODSUser
        )
        self.assertEqual(group.hasmember(self.user.username), True)

    # TODO: Test with inherited roles


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
        self.assertEqual(Project.objects.count(), 2)

        request_data = model_to_dict(self.project)
        request_data.update(
            {
                'title': 'updated title',
                'description': 'updated description',
                'owner': str(self.user.sodar_uuid),  # NOTE: Must add owner
                'readme': 'updated readme',
                'parent': str(self.category.sodar_uuid),
                'public_guest_access': True,
            }
        )
        request_data.update(
            app_settings.get_all_settings(project=self.project, post_safe=True)
        )  # Add default settings
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:update',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                request_data,
            )
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:detail',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(Project.objects.count(), 2)
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

        project_coll = self.irods_session.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('title').value, self.project.title
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value,
            self.project.description,
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentCreateView(TestTaskflowBase):
    """Tests for RoleAssignment creation view"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('guest')
        self.irods_user_group = self.irods_session.user_groups.get(
            self.irods_backend.get_user_group_name(self.project)
        )

    def test_create_assignment(self):
        """Test RoleAssignment creation with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 2)
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), False
        )

        request_data = {
            'project': self.project.sodar_uuid,
            'user': self.user_new.sodar_uuid,
            'role': self.role_guest.pk,
        }
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                request_data,
            )
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:roles',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(RoleAssignment.objects.count(), 3)
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
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), True
        )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentUpdateView(TestTaskflowBase):
    """Tests for RoleAssignment update view with taskflow"""

    def setUp(self):
        super().setUp()
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
        self.irods_user_group = self.irods_session.user_groups.get(
            self.irods_backend.get_user_group_name(self.project)
        )

    def test_update_assignment(self):
        """Test RoleAssignment updating with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), True
        )

        request_data = {
            'project': self.project.sodar_uuid,
            'user': self.user_new.sodar_uuid,
            'role': self.role_contributor.pk,
        }
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_update',
                    kwargs={'roleassignment': self.role_as.sodar_uuid},
                ),
                request_data,
            )
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:roles',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(RoleAssignment.objects.count(), 3)
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
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), True
        )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentOwnerTransferView(TestTaskflowBase):
    """Tests for ownership transfer view with taskflow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.irods_user_group = self.irods_session.user_groups.get(
            self.irods_backend.get_user_group_name(self.project)
        )

    def test_transfer_owner(self):
        """Test ownership transfer with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assertEqual(
            self.irods_user_group.hasmember(self.user.username), True
        )
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), True
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

        self.assertEqual(RoleAssignment.objects.count(), 3)
        role_as = RoleAssignment.objects.get(
            project=self.project, user=self.user_new
        )
        self.assertEqual(role_as.role, self.role_owner)
        self.assertEqual(
            self.irods_user_group.hasmember(self.user.username), True
        )
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), True
        )

    # TODO: Test with inherited roles


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestRoleAssignmentDeleteView(TestTaskflowBase):
    """Tests for RoleAssignment delete view"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('newuser')
        self.role_as = self._make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.irods_user_group = self.irods_session.user_groups.get(
            self.irods_backend.get_user_group_name(self.project)
        )

    def test_delete_assignment(self):
        """Test RoleAssignment deleting with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), True
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': self.role_as.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:roles',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(RoleAssignment.objects.count(), 2)
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), False
        )


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestProjectInviteAcceptView(ProjectInviteMixin, TestTaskflowBase):
    """Tests for ProjectInvite accepting view with taskflow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('newuser')
        self.irods_user_group = self.irods_session.user_groups.get(
            self.irods_backend.get_user_group_name(self.project)
        )

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
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)
        self.assertEqual(
            RoleAssignment.objects.filter(
                project=self.project,
                user=self.user_new,
                role=self.role_contributor,
            ).count(),
            0,
        )
        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), False
        )

        with self.login(self.user_new):
            response = self.client.get(
                reverse(
                    'projectroles:invite_accept',
                    kwargs={'secret': invite.secret},
                ),
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
                            kwargs={'project': self.project.sodar_uuid},
                        ),
                        302,
                    ),
                ],
            )

        self.assertEqual(
            self.irods_user_group.hasmember(self.user_new.username), True
        )

    @override_settings(PROJECTROLES_ALLOW_LOCAL_USERS=True)
    @override_settings(AUTH_LDAP_USERNAME_DOMAIN='EXAMPLE')
    @override_settings(AUTH_LDAP_DOMAIN_PRINTABLE='EXAMPLE')
    @override_settings(ENABLE_LDAP=True)
    def test_accept_invite_ldap_category(self):
        """Test LDAP user accepting an invite with taskflow for a category"""
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.category,
            role=self.role_contributor,
            issuer=self.user,
            message='',
        )
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
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.project,
            role=self.role_contributor,
            issuer=self.user,
            message='',
        )
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

        with self.login(self.user_new):
            response = self.client.get(
                reverse(
                    'projectroles:invite_accept',
                    kwargs={'secret': invite.secret},
                ),
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

        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)

    def test_accept_invite_local_category(self):
        """Test local user accepting an invite with taskflow for a category"""
        invite = self._make_invite(
            email=INVITE_EMAIL,
            project=self.category,
            role=self.role_contributor,
            issuer=self.user,
            message='',
        )
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

        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)
