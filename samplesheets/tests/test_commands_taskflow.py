"""Tests for samplesheets management commands with taskflow and iRODS"""

from django.test import override_settings

# Projectroles dependency
from projectroles.management.commands.syncmodifyapi import (
    Command as SyncModifyAPICommand,
)
from projectroles.models import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_plugins_taskflow import (
    SamplesheetsModifyAPITestMixin,
)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestSyncModifyAPI(
    SampleSheetIOMixin, SamplesheetsModifyAPITestMixin, TaskflowViewTestBase
):
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
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.sample_path = self.irods_backend.get_sample_path(self.project)
        # Create extra user
        self.user_new = self.make_user('user_new')
        # Init command
        self.command = SyncModifyAPICommand()

    def test_sync_no_colls(self):
        """Test sync without iRODS collections"""
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))

    def test_sync_colls(self):
        """Test sync with iRODS collections"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.group_name, self.sample_path, self.irods_access_read
        )
        self.assert_ticket_access(self.project, False)

    def test_sync_public_guest_access(self):
        """Test sync with public guest access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.public_guest_access = True
        self.project.save()
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.group_name, self.sample_path, self.irods_access_read
        )
        # Anonymous access not granted, ticket should not be created
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_guest_access_anon(self):
        """Test sync with public guest access and anonymous access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.public_guest_access = True
        self.project.save()
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.group_name, self.sample_path, self.irods_access_read
        )
        # Ticket access should be granted with anonymous access
        self.assert_ticket_access(self.project, True)

    def test_sync_public_guest_access_revoke(self):
        """Test sync for revoking public guest access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.public_guest_access = True
        self.project.save()
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.group_name, self.sample_path, self.irods_access_read
        )
        self.assert_ticket_access(self.project, False)
        self.project.public_guest_access = False
        self.project.save()
        self.assert_irods_access(
            self.group_name, self.sample_path, self.irods_access_read
        )
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_guest_access_revoke_anon(self):
        """Test sync for revoking public guest access with anonymous access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.public_guest_access = True
        self.project.save()
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.group_name, self.sample_path, self.irods_access_read
        )
        self.assert_ticket_access(self.project, True)
        self.project.public_guest_access = False
        self.project.save()
        self.command.handle()
        self.assert_irods_access(
            self.group_name, self.sample_path, self.irods_access_read
        )
        self.assert_ticket_access(self.project, False)
