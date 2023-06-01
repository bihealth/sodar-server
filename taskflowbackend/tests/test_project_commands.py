"""Management command tests for the projectroles app with taskflow"""

import os

from tempfile import NamedTemporaryFile

from irods.exception import (
    CollectionDoesNotExist,
    UserDoesNotExist,
    UserGroupDoesNotExist,
)
from irods.user import iRODSUserGroup

# Projectroles dependency
from projectroles.management.commands.batchupdateroles import (
    Command as BatchUpdateRolesCommand,
)
from projectroles.management.commands.syncmodifyapi import (
    Command as SyncModifyAPICommand,
)
from projectroles.models import (
    RoleAssignment,
    ProjectInvite,
    SODAR_CONSTANTS,
)
from projectroles.tests.test_commands import BatchUpdateRolesMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import (
    TaskflowbackendTestBase,
    IRODS_ACCESS_READ,
)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']


class TestBatchUpdateRoles(BatchUpdateRolesMixin, TaskflowbackendTestBase):
    """Tests for the batchupdateroles command"""

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
        # Init command class
        self.command = BatchUpdateRolesCommand()
        # Init file
        self.file = NamedTemporaryFile(delete=False)

    def tearDown(self):
        if self.file:
            os.remove(self.file.name)
        super().tearDown()

    def test_role_update(self):
        """Test updating an existing role for user with taskflow"""
        p_uuid = str(self.project.sodar_uuid)
        email = 'new@example.com'
        user_new = self.make_user('user_new')
        user_new.email = email
        user_new.save()
        role_as = self.make_assignment_taskflow(
            self.project, user_new, self.role_guest
        )

        self.assertEqual(
            RoleAssignment.objects.filter(
                project=self.project, user=user_new
            ).count(),
            1,
        )

        self.write_file([p_uuid, email, PROJECT_ROLE_CONTRIBUTOR])
        self.command.handle(
            **{'file': self.file.name, 'issuer': self.user.username}
        )
        self.assertEqual(ProjectInvite.objects.count(), 0)
        role_as.refresh_from_db()
        self.assertEqual(role_as.role, self.role_contributor)


class TestSyncModifyAPI(TaskflowbackendTestBase):
    """Tests for the syncmofidyapi command"""

    def setUp(self):
        super().setUp()
        # Create project locally
        self.project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(self.project, self.user, self.role_owner)
        self.group_name = self.irods_backend.get_user_group_name(self.project)
        self.category_path = self.irods_backend.get_path(self.category)
        self.project_path = self.irods_backend.get_path(self.project)
        # Create extra user
        self.user_new = self.make_user('user_new')
        # Init command
        self.command = SyncModifyAPICommand()

    def test_sync(self):
        """Test synchronizing project and roles in iRODS"""
        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.category_path)
        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.project_path)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(self.group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_new.username)

        self.command.handle()

        # Category collection should not be created
        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.category_path)
        self.assertEqual(self.irods.collections.exists(self.project_path), True)
        self.assertIsInstance(
            self.irods.user_groups.get(self.group_name), iRODSUserGroup
        )
        self.assert_irods_access(
            self.group_name, self.project_path, IRODS_ACCESS_READ
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_new.username)

    def test_sync_member(self):
        """Test sync with project member role"""
        self.make_assignment(self.project, self.user_new, self.role_guest)

        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.project_path)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(self.group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_new.username)

        self.command.handle()

        self.assertEqual(self.irods.collections.exists(self.project_path), True)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, self.user_new, True)

    def test_sync_inherited_member(self):
        """Test sync with inherited member role"""
        self.make_assignment(self.category, self.user_new, self.role_guest)

        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.project_path)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(self.group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_new.username)

        self.command.handle()

        self.assertEqual(self.irods.collections.exists(self.project_path), True)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, self.user_new, True)

    def test_sync_inherited_finder(self):
        """Test sync with inherited finder role"""
        self.make_assignment(self.category, self.user_new, self.role_finder)

        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.project_path)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(self.group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_new.username)

        self.command.handle()

        self.assertEqual(self.irods.collections.exists(self.project_path), True)
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        # Access should not be granted to finder
        self.assert_group_member(self.project, self.user_new, False)

    def test_sync_remove_member(self):
        """Test sync removing project member role"""
        role_as = self.make_assignment(
            self.project, self.user_new, self.role_guest
        )
        self.command.handle()
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, self.user_new, True)
        role_as.delete()
        self.command.handle()
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, self.user_new, False)

    def test_sync_remove_inherited_member(self):
        """Test sync removing inherited member role"""
        role_as = self.make_assignment(
            self.category, self.user_new, self.role_guest
        )
        self.command.handle()
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, self.user_new, True)
        role_as.delete()
        self.command.handle()
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, self.user_new, False)
