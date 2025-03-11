"""Tests for projectroles views with taskflow"""

import os

from irods.collection import iRODSCollection
from irods.exception import GroupDoesNotExist
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
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectInviteMixin

# Timeline dependency
from timeline.models import TimelineEvent

from taskflowbackend.tests.base import TaskflowViewTestBase


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
APP_NAME = 'taskflowbackend'
INVITE_EMAIL = 'test@example.com'
SECRET = 'rsd886hi8276nypuvw066sbvv0rb2a6x'
TASKFLOW_TEST_MODE = getattr(settings, 'TASKFLOW_TEST_MODE', False)
OBJ_NAME = 'test_file.txt'


# Base Classes -----------------------------------------------------------------


class TestProjectCreateView(TaskflowViewTestBase):
    """Tests for Project creation view with taskflow"""

    def setUp(self):
        super().setUp()
        self.timeline = get_backend_api('timeline_backend')

    def test_create_project(self):
        """Test Project creation with taskflow"""
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(
            self.irods.collections.exists(
                self.irods_backend.get_projects_path()
            ),
            False,
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
            'archive': False,
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
        root_coll = self.irods.collections.get(
            self.irods_backend.get_projects_path()
        )
        self.assertIsInstance(root_coll, iRODSCollection)
        project_coll = self.irods.collections.get(
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
        group = self.irods.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name, project_coll, self.irods_access_read
        )
        self.assertIsInstance(
            self.irods.users.get(self.user.username), iRODSUser
        )
        self.assertEqual(group.hasmember(self.user.username), True)
        # Assert inherited role updating for category owner
        self.assertIsInstance(
            self.irods.users.get(self.user_owner_cat.username), iRODSUser
        )
        self.assertEqual(group.hasmember(self.user_owner_cat.username), True)
        # Assert timeline event
        tl_events = TimelineEvent.objects.filter(
            project=project,
            plugin='taskflow',
            user=self.user,
            event_name='project_create',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type,
            self.timeline.TL_STATUS_OK,
        )


class TestProjectUpdateView(TaskflowViewTestBase):
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
        self.user_new = self.make_user('user_new')
        self.timeline = get_backend_api('timeline_backend')

    def test_update(self):
        """Test project update with taskflow"""
        self.assertEqual(Project.objects.count(), 2)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

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
            app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project, post_safe=True
            )
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
            'archive': False,
            'full_title': self.category.title + ' / updated title',
            'has_public_children': False,
            'sodar_uuid': self.project.sodar_uuid,
        }
        model_dict = model_to_dict(self.project)
        model_dict.pop('readme', None)
        self.assertEqual(model_dict, expected)
        self.assertEqual(self.project.readme.raw, 'updated readme')

        project_coll = self.irods.collections.get(
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
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        tl_events = TimelineEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='project_update',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type,
            self.timeline.TL_STATUS_OK,
        )

    def test_update_parent(self):
        """Test project update with changed parent"""
        new_category = self.make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.make_assignment(new_category, self.user_new, self.role_owner)
        self.assertEqual(Project.objects.count(), 3)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, self.user_new, False)

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
            app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project, post_safe=True
            )
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
        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(new_category.sodar_uuid),
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, False)
        self.assert_group_member(self.project, self.user_new, True)


class TestRoleAssignmentCreateView(TaskflowViewTestBase):
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
        self.user_new = self.make_user('user_new')
        self.irods_user_group = self.irods.user_groups.get(
            self.irods_backend.get_user_group_name(self.project)
        )

    def test_create(self):
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

    def test_create_parent(self):
        """Test RoleAssignment creation in parent with member role"""
        self.assertEqual(RoleAssignment.objects.count(), 2)
        self.assert_group_member(self.project, self.user_new, False)
        request_data = {
            'project': self.category.sodar_uuid,
            'user': self.user_new.sodar_uuid,
            'role': self.role_guest.pk,
        }
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_create',
                    kwargs={'project': self.category.sodar_uuid},
                ),
                request_data,
            )
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_new, True)

    def test_create_parent_finder(self):
        """Test RoleAssignment creation in parent with finder role"""
        self.assertEqual(RoleAssignment.objects.count(), 2)
        self.assert_group_member(self.project, self.user_new, False)
        request_data = {
            'project': self.category.sodar_uuid,
            'user': self.user_new.sodar_uuid,
            'role': self.role_finder.pk,
        }
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_create',
                    kwargs={'project': self.category.sodar_uuid},
                ),
                request_data,
            )
        self.assertEqual(RoleAssignment.objects.count(), 3)
        # iRODS access should not be granted
        self.assert_group_member(self.project, self.user_new, False)


class TestRoleAssignmentUpdateView(TaskflowViewTestBase):
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
        self.user_update = self.make_user('user_update')
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_update, self.role_guest
        )

    def test_update(self):
        """Test RoleAssignment updating with taskflow"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_update, True)

        request_data = {
            'project': self.project.sodar_uuid,
            'user': self.user_update.sodar_uuid,
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
            project=self.project, user=self.user_update
        )
        self.assertIsNotNone(role_as)
        expected = {
            'id': role_as.pk,
            'project': self.project.pk,
            'user': self.user_update.pk,
            'role': self.role_contributor.pk,
            'sodar_uuid': role_as.sodar_uuid,
        }
        self.assertEqual(model_to_dict(role_as), expected)
        self.assert_group_member(self.project, self.user_update, True)

    def test_update_parent_from_finder(self):
        """Test RoleAssignment updating from finder role in parent"""
        user_new = self.make_user('user_new')
        role_as = self.make_assignment_taskflow(
            self.category, user_new, self.role_finder
        )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, user_new, False)
        request_data = {
            'project': self.category.sodar_uuid,
            'user': user_new.sodar_uuid,
            'role': self.role_guest.pk,
        }
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_update',
                    kwargs={'roleassignment': role_as.sodar_uuid},
                ),
                request_data,
            )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, user_new, True)

    def test_update_parent_to_finder(self):
        """Test RoleAssignment updating to finder role in parent"""
        user_new = self.make_user('user_new')
        role_as = self.make_assignment_taskflow(
            self.category, user_new, self.role_guest
        )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, user_new, True)
        request_data = {
            'project': self.category.sodar_uuid,
            'user': user_new.sodar_uuid,
            'role': self.role_finder.pk,
        }
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_update',
                    kwargs={'roleassignment': role_as.sodar_uuid},
                ),
                request_data,
            )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, user_new, False)


class TestRoleAssignmentOwnerTransferView(TaskflowViewTestBase):
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
        self.assert_group_member(self.project, self.user_owner_cat, True)

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
        self.assert_group_member(self.project, self.user_owner_cat, True)

    def test_transfer_category(self):
        """Test ownership transfer with category and owner inheritance"""
        self.make_assignment_taskflow(
            self.category, self.user, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

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
        self.assert_group_member(self.project, self.user_owner_cat, True)

    def test_transfer_category_finder(self):
        """Test ownership transfer with category into finder role"""
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_owner_transfer',
                    kwargs={'project': self.category.sodar_uuid},
                ),
                data={
                    'project': self.category.sodar_uuid,
                    'old_owner_role': self.role_finder.pk,
                    'new_owner': self.user.sodar_uuid,
                },
            )

        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)


class TestRoleAssignmentDeleteView(TaskflowViewTestBase):
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

    def test_delete_role(self):
        """Test RoleAssignment deleting with taskflow"""
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_new, True)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': role_as.sodar_uuid},
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

    def test_delete_inherited(self):
        """Test deleting inherited role with no local role"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_guest
        )
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_new, True)
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': role_as.sodar_uuid},
                ),
            )
        self.assertEqual(RoleAssignment.objects.count(), 2)
        self.assert_group_member(self.project, self.user_new, False)

    def test_delete_inherited_with_local(self):
        """Test deleting inherited role with local role"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_guest
        )
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, self.user_new, True)
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': role_as.sodar_uuid},
                ),
            )
        self.assertEqual(RoleAssignment.objects.count(), 3)
        # Access should remain due to local guest role
        self.assert_group_member(self.project, self.user_new, True)

    def test_delete_local_with_inherited(self):
        """Test deleting local role with inherited role"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_guest
        )
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, self.user_new, True)
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': role_as.sodar_uuid},
                ),
            )
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_new, True)

    def test_delete_local_with_inherited_finder(self):
        """Test deleting local role with inherited finder role"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assertEqual(RoleAssignment.objects.count(), 4)
        self.assert_group_member(self.project, self.user_new, True)
        with self.login(self.user):
            self.client.post(
                reverse(
                    'projectroles:role_delete',
                    kwargs={'roleassignment': role_as.sodar_uuid},
                ),
            )
        self.assertEqual(RoleAssignment.objects.count(), 3)
        self.assert_group_member(self.project, self.user_new, False)


class TestProjectInviteAcceptView(ProjectInviteMixin, TaskflowViewTestBase):
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
        invite = self.make_invite(
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
                            'projectroles:invite_process_login',
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
        invite = self.make_invite(
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
                            'projectroles:invite_process_login',
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
        invite = self.make_invite(
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
                            'projectroles:invite_process_new_user',
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
        invite = self.make_invite(
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
                            'projectroles:invite_process_new_user',
                            kwargs={'secret': invite.secret},
                        ),
                        302,
                    ),
                    (reverse('home'), 302),
                ],
            )
        self.assertEqual(ProjectInvite.objects.filter(active=True).count(), 1)


class TestProjectDeleteView(TaskflowViewTestBase):
    """Tests for ProjectDeleteView"""

    def _assert_tl_event(self, count):
        """Assert timeline event count"""
        tl_events = TimelineEvent.objects.filter(
            app=APP_NAME, event_name='project_delete'
        )
        self.assertEqual(tl_events.count(), count)

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
        self.project_uuid = self.project.sodar_uuid
        self.project_path = self.irods_backend.get_path(self.project)
        self.group_name = self.irods_backend.get_user_group_name(self.project)
        self.timeline = get_backend_api('timeline_backend')
        self.url = reverse(
            'projectroles:delete',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {'delete_host_confirm': 'testserver'}

    def test_post(self):
        """Test ProjectDeleteView POST with taskflow"""
        self.assertTrue(self.irods.collections.exists(self.project_path))
        self.assertIsNotNone(self.irods.groups.get(self.group_name))
        self._assert_tl_event(0)

        with self.login(self.user):
            response = self.client.post(self.url, data=self.post_data)
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:detail',
                    kwargs={'project': self.category.sodar_uuid},
                ),
            )
        self.assertFalse(self.irods.collections.exists(self.project_path))
        with self.assertRaises(GroupDoesNotExist):
            self.irods.groups.get(self.group_name)
        self._assert_tl_event(1)
        tl_event = TimelineEvent.objects.filter(
            app=APP_NAME, event_name='project_delete'
        ).first()
        self.assertEqual(
            tl_event.get_status().status_type, self.timeline.TL_STATUS_OK
        )
        self.assertIsNone(
            Project.objects.filter(sodar_uuid=self.project_uuid).first()
        )

    def test_post_file(self):
        """Test POST with uploaded file"""
        obj_coll_path = os.path.join(self.project_path, 'subcoll')
        self.irods.collections.create(obj_coll_path)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        self.irods.data_objects.create(obj_path)

        self.assertTrue(self.irods.collections.exists(self.project_path))
        self.assertTrue(self.irods.collections.exists(obj_coll_path))
        self.assertTrue(self.irods.data_objects.exists(obj_path))
        self.assertIsNotNone(self.irods.groups.get(self.group_name))

        with self.login(self.user):
            self.client.post(self.url, data=self.post_data)

        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(obj_coll_path))
        self.assertFalse(self.irods.data_objects.exists(obj_path))
        with self.assertRaises(GroupDoesNotExist):
            self.irods.groups.get(self.group_name)
        self.assertIsNone(
            Project.objects.filter(sodar_uuid=self.project_uuid).first()
        )
