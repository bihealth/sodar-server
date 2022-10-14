"""Tests for projectroles views with taskflow"""

from irods.collection import iRODSCollection
from irods.exception import CollectionDoesNotExist
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings
from django.contrib import auth
from django.forms.models import model_to_dict
from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import (
    Project,
    RoleAssignment,
    ProjectInvite,
    SODAR_CONSTANTS,
)
from projectroles.tests.test_models import (
    ProjectInviteMixin,
)

from taskflowbackend.tests.base import (
    TaskflowbackendTestBase,
    IRODS_ACCESS_READ,
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
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']


# Local constants
INVITE_EMAIL = 'test@example.com'
SECRET = 'rsd886hi8276nypuvw066sbvv0rb2a6x'
TASKFLOW_TEST_MODE = getattr(settings, 'TASKFLOW_TEST_MODE', False)


# Base Classes -----------------------------------------------------------------


class TestProjectCreateView(TaskflowbackendTestBase):
    """Tests for Project creation view with taskflow"""

    def test_create_project(self):
        """Test Project creation with taskflow"""
        self.assertEqual(Project.objects.count(), 1)
        with self.assertRaises(CollectionDoesNotExist):
            self.irods_session.collections.get(
                self.irods_backend.get_projects_path()
            )

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
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
        self.assert_irods_access(group_name, project_coll, IRODS_ACCESS_READ)
        self.assertIsInstance(
            self.irods_session.users.get(self.user.username), iRODSUser
        )
        self.assertEqual(group.hasmember(self.user.username), True)
        # Assert inherited role updating for category owner
        self.assertIsInstance(
            self.irods_session.users.get(self.user_cat.username), iRODSUser
        )
        self.assertEqual(group.hasmember(self.user_cat.username), True)


class TestProjectUpdateView(TaskflowbackendTestBase):
    """Tests for Project updating view"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
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

    def test_move_project(self):
        """Test moving Project under another category with taskflow"""
        new_category = self._make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        self._make_assignment(new_category, self.user, self.role_owner)
        self.assertEqual(Project.objects.count(), 3)

        request_data = model_to_dict(self.project)
        request_data.update(
            {
                'title': 'updated title',
                'description': 'updated description',
                'owner': str(self.user.sodar_uuid),  # NOTE: Must add owner
                'readme': 'updated readme',
                'parent': str(new_category.sodar_uuid),
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

        self.assertEqual(Project.objects.count(), 3)
        self.project.refresh_from_db()
        self.assertEqual(self.project.parent, new_category)
        project_coll = self.irods_session.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(new_category.sodar_uuid),
        )


class TestRoleAssignmentCreateView(TaskflowbackendTestBase):
    """Tests for RoleAssignment creation view"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
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
        self.assert_group_member(self.project, self.user_new, False)

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
        self.assert_group_member(self.project, self.user_new, True)


class TestRoleAssignmentUpdateView(TaskflowbackendTestBase):
    """Tests for RoleAssignment update view with taskflow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        # Create guest user and role
        self.user_new = self.make_user('newuser')
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )

    def test_update_assignment(self):
        """Test RoleAssignment updating with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_new, True)

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
        self.assert_group_member(self.project, self.user_new, True)


class TestRoleAssignmentOwnerTransferView(TaskflowbackendTestBase):
    """Tests for ownership transfer view with taskflow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('newuser')
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )

    def test_transfer_owner(self):
        """Test ownership transfer with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_cat, True)

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
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_cat, True)

    def test_transfer_category(self):
        """Test ownership transfer with category and owner inheritance"""
        self.make_assignment_taskflow(
            self.category, self.user, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_cat, True)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_owner_transfer',
                    kwargs={'project': self.category.sodar_uuid},
                ),
                data={
                    'project': self.category.sodar_uuid,
                    'old_owner_role': self.role_guest.pk,
                    'new_owner': self.user.sodar_uuid,
                },
            )

        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_cat, False)


class TestRoleAssignmentDeleteView(TaskflowbackendTestBase):
    """Tests for RoleAssignment delete view"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('newuser')
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )

    def test_delete_assignment(self):
        """Test RoleAssignment deleting with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_new, True)

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
        self.assert_group_member(self.project, self.user_new, False)


class TestProjectInviteAcceptView(ProjectInviteMixin, TaskflowbackendTestBase):
    """Tests for ProjectInvite accepting view with taskflow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
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
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)
        self.assertEqual(
            RoleAssignment.objects.filter(
                project=self.project,
                user=self.user_new,
                role=self.role_contributor,
            ).count(),
            0,
        )
        self.assert_group_member(self.project, self.user_new, False)

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

        self.assert_group_member(self.project, self.user_new, True)

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
                    (reverse('home'), 302),
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
                    (reverse('home'), 302),
                ],
            )

        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)
