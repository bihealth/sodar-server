"""Tests for samplesheets management commands with taskflow and iRODS"""

import irods

from django.core.management import call_command
from django.conf import settings
from django.test import override_settings

# Projectroles dependency
from projectroles.management.commands.syncmodifyapi import (
    Command as SyncModifyAPICommand,
)
from projectroles.models import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.constants import IRODS_ACCESS_READ_OBJ
from taskflowbackend.tests.base import TaskflowViewTestBase, IRODS_GROUP_PUBLIC

# Samplesheets dependency
from samplesheets.models import IrodsAccessTicket

# from samplesheets.models import IrodsAccessTicket
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import IrodsAccessTicketMixin
from samplesheets.tests.test_plugins_taskflow import (
    SamplesheetsModifyAPITestMixin,
)

# Irodsbackend dependency
from irodsbackend.api import TICKET_MODE_READ


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
COLLECTION_TICKET_STR = 'collection_ticket'
DATA_TICKET_STR = 'data_ticket'
ORPHAN_TICKET_STR = 'orphan_ticket'
NULL_STUDY_TICKET_STR = 'null_study_ticket'


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
        self.project_group = self.irods_backend.get_group_name(self.project)
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
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_ticket_access(self.project, False)

    def test_sync_public_guest_access(self):
        """Test sync with public guest access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.set_public_access(self.role_guest)
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        # Anonymous access not granted, ticket should not be created
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_guest_access_anon(self):
        """Test sync with public guest access and anonymous access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.set_public_access(self.role_guest)
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        # Ticket access should be granted with anonymous access
        self.assert_ticket_access(self.project, True)

    def test_sync_public_viewer_access(self):
        """Test sync with public viewer access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.set_public_access(self.role_viewer)
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_viewer_access_anon(self):
        """Test sync with public viewer access and anonymous access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.set_public_access(self.role_viewer)
        self.assertFalse(self.irods.collections.exists(self.project_path))
        self.assertFalse(self.irods.collections.exists(self.sample_path))
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        # Ticket access should not be granted for viewer role
        self.assert_ticket_access(self.project, False)

    def test_sync_public_guest_access_revoke(self):
        """Test sync for revoking public guest access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.set_public_access(self.role_guest)
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_ticket_access(self.project, False)
        self.project.set_public_access(None)
        self.command.handle()
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_guest_access_revoke_anon(self):
        """Test sync for revoking public guest access with anonymous access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.set_public_access(self.role_guest)
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_ticket_access(self.project, True)
        self.project.set_public_access(None)
        self.command.handle()
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)

    def test_sync_public_guest_viewer_revoke(self):
        """Test sync for revoking public viewer access"""
        self.investigation.irods_status = True
        self.investigation.save()
        self.project.set_public_access(self.role_viewer)
        self.command.handle()
        self.assertTrue(self.irods.collections.exists(self.sample_path))
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)
        self.project.set_public_access(None)
        self.assert_irods_access(
            self.project_group, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)


class TestFixIrodsTickets(
    IrodsAccessTicketMixin, SampleSheetIOMixin, TaskflowViewTestBase
):
    """Tests for the fixirodstickets command"""

    def setUp(self):
        super().setUp()
        self.admin = self.make_user(settings.PROJECTROLES_DEFAULT_ADMIN)
        # Create project locally
        self.project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(self.project, self.user, self.role_owner)
        # Import investigation and create iRODS objects
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.coll_path = self.irods_backend.get_path(self.assay)
        self.irods.collections.create(self.coll_path)
        self.data_path = irods.path.iRODSPath(self.coll_path, 'file.txt')
        # Issue iRODS tickets
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.coll_path,
            ticket_str=COLLECTION_TICKET_STR,
            date_expires=None,
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.coll_path,
            ticket_str=DATA_TICKET_STR,
            date_expires=None,
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.coll_path,
            ticket_str=ORPHAN_TICKET_STR,
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.irods_backend.get_sample_path(self.project),
            ticket_str=NULL_STUDY_TICKET_STR,
        )
        # Create ticket objects
        self.coll_ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll_path,
            user=self.user,
            ticket=COLLECTION_TICKET_STR,
        )
        self.data_ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.data_path,
            user=self.user,
            ticket=DATA_TICKET_STR,
        )

    def test_fixirodstickets(self):
        """Test that fixirodstickets recreates orphaned ticket objects"""
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=ORPHAN_TICKET_STR).count(),
            0,
        )
        call_command('fixirodstickets')
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=ORPHAN_TICKET_STR).count(),
            1,
        )
        ticket_obj = IrodsAccessTicket.objects.get(ticket=ORPHAN_TICKET_STR)
        self.assertEqual(ticket_obj.study, self.study)
        self.assertEqual(ticket_obj.assay, self.assay)
        self.assertEqual(ticket_obj.path, self.coll_path)
        self.assertEqual(ticket_obj.user, self.admin)

    def test_fixirodstickets_after_deletion(self):
        """Test fixirodstickets after deleting the object"""
        ticket = IrodsAccessTicket.objects.get(ticket=DATA_TICKET_STR)
        ticket.delete()
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=DATA_TICKET_STR).count(),
            0,
        )
        call_command('fixirodstickets')
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=DATA_TICKET_STR).count(),
            1,
        )

    def test_fixirodstickets_check(self):
        """Test fixirodstickets check argument"""
        self.irods_backend.get_ticket(self.irods, ORPHAN_TICKET_STR)
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=ORPHAN_TICKET_STR).count(),
            0,
        )
        call_command('fixirodstickets', check=True)
        # Nothing should have changed
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=ORPHAN_TICKET_STR).count(),
            0,
        )

    def test_fixirodstickets_null_study(self):
        """Test fixirodstickets when ticket study is None"""
        self.irods_backend.get_ticket(self.irods, ORPHAN_TICKET_STR)
        self.assertEqual(
            IrodsAccessTicket.objects.filter(
                ticket=NULL_STUDY_TICKET_STR
            ).count(),
            0,
        )
        call_command('fixirodstickets')
        # Tickets without a study are ignored, so nothing should have changed
        self.assertEqual(
            IrodsAccessTicket.objects.filter(
                ticket=NULL_STUDY_TICKET_STR
            ).count(),
            0,
        )
