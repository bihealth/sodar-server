"""Tests for samplesheets management commands with taskflow and iRODS"""

from irods.path import iRODSPath

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
from samplesheets.management.commands.fixirodstickets import (
    ASSAY_DOES_NOT_EXIST,
    STUDY_DOES_NOT_EXIST,
    STUDY_IS_MISSING,
    TICKET_OBJECT_ACTION_COUNT,
)
from samplesheets.models import IrodsAccessTicket
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import IrodsAccessTicketMixin
from samplesheets.tests.test_plugins_taskflow import (
    SamplesheetsModifyAPITestMixin,
)
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

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
LOGGER_PREFIX = 'samplesheets.management.commands.'


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
    IrodsAccessTicketMixin,
    SampleSheetTaskflowMixin,
    SampleSheetIOMixin,
    TaskflowViewTestBase,
):
    """Tests for the fixirodstickets command"""

    def setUp(self):
        super().setUp()
        self.admin = self.make_user(settings.PROJECTROLES_DEFAULT_ADMIN)
        # Create project with taskflow
        self.project, _ = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        # Import investigation and create iRODS objects
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.sample_path = self.irods_backend.get_sample_path(self.project)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.obj_path = iRODSPath(self.assay_path, 'file.txt')
        self.make_irods_colls(self.investigation)
        # Issue iRODS tickets
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.assay_path,
            ticket_str=COLLECTION_TICKET_STR,
            date_expires=None,
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.assay_path,
            ticket_str=DATA_TICKET_STR,
            date_expires=None,
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.assay_path,
            ticket_str=ORPHAN_TICKET_STR,
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.sample_path,
            ticket_str=NULL_STUDY_TICKET_STR,
        )
        # Create ticket objects
        self.coll_ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.assay_path,
            user=self.user,
            ticket=COLLECTION_TICKET_STR,
        )
        self.data_ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.obj_path,
            user=self.user,
            ticket=DATA_TICKET_STR,
        )
        # Set up test vars
        self.cmd_name = 'fixirodstickets'
        self.logger_name = LOGGER_PREFIX + self.cmd_name

    def test_fixirodstickets(self):
        """Test that fixirodstickets recreates orphaned ticket objects"""
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=ORPHAN_TICKET_STR).count(),
            0,
        )
        call_command(self.cmd_name)
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=ORPHAN_TICKET_STR).count(),
            1,
        )
        ticket_obj = IrodsAccessTicket.objects.get(ticket=ORPHAN_TICKET_STR)
        self.assertEqual(ticket_obj.study, self.study)
        self.assertEqual(ticket_obj.assay, self.assay)
        self.assertEqual(ticket_obj.path, self.assay_path)
        self.assertEqual(ticket_obj.user, self.admin)

    def test_fixirodstickets_after_deletion(self):
        """Test fixirodstickets after deleting the object"""
        ticket = IrodsAccessTicket.objects.get(ticket=DATA_TICKET_STR)
        ticket.delete()
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=DATA_TICKET_STR).count(),
            0,
        )
        call_command(self.cmd_name)
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
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name, check=True)
            # Nothing should have changed in the db
            self.assertEqual(
                IrodsAccessTicket.objects.filter(
                    ticket=ORPHAN_TICKET_STR
                ).count(),
                0,
            )
            self.assertIn(
                TICKET_OBJECT_ACTION_COUNT.format(
                    action='Found', count=1, plural=''
                ),
                cm.output[3],
            )

    def test_fixirodstickets_null_study(self):
        """Test fixirodstickets when ticket study is None"""
        self.irods_backend.get_ticket(self.irods, NULL_STUDY_TICKET_STR)
        self.assertEqual(
            IrodsAccessTicket.objects.filter(
                ticket=NULL_STUDY_TICKET_STR
            ).count(),
            0,
        )
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
            # Tickets without a study are ignored, so the db should not change
            self.assertEqual(
                IrodsAccessTicket.objects.filter(
                    ticket=NULL_STUDY_TICKET_STR
                ).count(),
                0,
            )
            self.assertIn(
                STUDY_IS_MISSING.format(ticket_string=NULL_STUDY_TICKET_STR),
                cm.output[2],
            )

    def test_fixirodstickets_orphaned_study(self):
        """Test fixirodstickets with deleted study"""
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=DATA_TICKET_STR).count(),
            1,
        )
        study_uuid = self.study.sodar_uuid
        self.study.delete()
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=DATA_TICKET_STR).count(),
            0,
        )
        # Nothing should happen to the database, but a warning will be shown
        # to the user running the command
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
            self.assertEqual(
                IrodsAccessTicket.objects.filter(
                    ticket=DATA_TICKET_STR
                ).count(),
                0,
            )
            self.assertIn(
                STUDY_DOES_NOT_EXIST.format(
                    ticket_string=DATA_TICKET_STR, ticket_study=study_uuid
                ),
                cm.output[2],
            )

    def test_fixirodstickets_orphaned_assay(self):
        """Test fixirodstickets with deleted assay"""
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=DATA_TICKET_STR).count(),
            1,
        )
        assay_uuid = self.assay.sodar_uuid
        self.assay.delete()
        self.assertEqual(
            IrodsAccessTicket.objects.filter(ticket=DATA_TICKET_STR).count(),
            0,
        )
        # Nothing should happen to the database, but a warning will be shown
        # to the user running the command
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
            self.assertEqual(
                IrodsAccessTicket.objects.filter(
                    ticket=DATA_TICKET_STR
                ).count(),
                0,
            )
            self.assertIn(
                ASSAY_DOES_NOT_EXIST.format(
                    ticket_string=DATA_TICKET_STR, ticket_assay=assay_uuid
                ),
                cm.output[2],
            )
