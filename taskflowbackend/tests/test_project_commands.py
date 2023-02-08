"""Management command tests for the projectroles app with taskflow"""

import os
from tempfile import NamedTemporaryFile

# Projectroles dependency
from projectroles.management.commands.batchupdateroles import (
    Command as BatchUpdateRolesCommand,
)
from projectroles.models import (
    RoleAssignment,
    ProjectInvite,
    SODAR_CONSTANTS,
)
from projectroles.tests.test_commands import BatchUpdateRolesMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowbackendTestBase


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']


# TODO: Add tests for syncmodifyapi


class TestBatchUpdateRoles(BatchUpdateRolesMixin, TaskflowbackendTestBase):
    """Tests for batchupdateroles command"""

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
