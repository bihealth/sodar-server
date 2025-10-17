"""Management command tests for the landingzones app with taskflow"""

from typing import Optional

from irods.path import iRODSPath

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Timeline dependency
from timeline.models import TimelineEvent, TL_STATUS_OK, TL_STATUS_FAILED
from timeline.tests.test_models import TimelineEventMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views import MISC_FILES_COLL

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

import landingzones.constants as lc
from landingzones.management.commands.resetzone import (
    Command as ResetZoneCommand,
)
from landingzones.management.commands.verifyzone import (
    Command as VerifyZoneCommand,
    MOVE_EVENT_NOT_FOUND_MSG,
    MOVE_NOT_SUCCESSFUL_MSG,
    NO_TL_EXTRA_DATA_MSG,
)
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'landingzones'
LOGGER_PREFIX = 'landingzones.management.commands.'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20190703_172456'
TEST_OBJ_NAME = 'test1.txt'


class TestResetZone(
    SampleSheetIOMixin,
    LandingZoneMixin,
    SampleSheetTaskflowMixin,
    LandingZoneTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for the resetzone command"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'TestProject',
            PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Create zone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
        )
        self.command = ResetZoneCommand()
        self.cmd_kw = {'zone': str(self.zone.sodar_uuid)}

    def test_reset(self):
        """Test resetzone"""
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        self.zone.set_status(lc.ZONE_STATUS_VALIDATING)
        self.command.handle(**self.cmd_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)

    def test_reset_restrict_colls(self):
        """Test resetzone with restrict_colls"""
        self.make_zone_taskflow(
            self.zone, colls=[MISC_FILES_COLL], restrict_colls=True
        )
        self.zone.set_status(lc.ZONE_STATUS_VALIDATING)
        self.command.handle(**self.cmd_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)


class TestVerifyZone(
    SampleSheetIOMixin,
    LandingZoneMixin,
    SampleSheetTaskflowMixin,
    LandingZoneTaskflowMixin,
    TimelineEventMixin,
    TaskflowViewTestBase,
):
    """Tests for the verifyzone command"""

    @classmethod
    def _get_verify_tl_event(cls) -> Optional[TimelineEvent]:
        """
        Return zone_verify timeline event.

        :return: TimelineEvent object or None if not found
        """
        return TimelineEvent.objects.filter(event_name='zone_verify').first()

    def _make_zone_object(self):
        """
        Make zone object with checksum, set paths and collections.
        """
        self.obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(self.obj)
        self.obj_zone_path = self.obj.path
        self.obj_sample_path = iRODSPath(
            self.assay_path, MISC_FILES_COLL, TEST_OBJ_NAME
        )

    def _move_zone(self) -> TimelineEvent:
        """
        Run landing_zone_move flow on self.zone.

        :return: TimelineEvent object for zone move
        """
        tl_event = self.make_event(
            project=self.project,
            app=APP_NAME,
            user=self.user,
            event_name='zone_move',
        )
        tl_event.add_object(
            obj=self.zone, label='zone', name=self.zone.title
        )  # NOTE: We have to add this because of ugly hacks
        flow = self.taskflow.get_flow(
            flow_name='landing_zone_move',
            flow_data={'zone_uuid': str(self.zone.sodar_uuid)},
            tl_event=tl_event,
            irods_backend=self.irods_backend,
            project=self.project,
            user=self.user,
        )
        flow.build()
        flow.run()
        tl_event.set_status('OK')
        return tl_event

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'TestProject',
            PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.assay_path = self.irods_backend.get_path(self.assay)
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Create zone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
        )
        # Set up zone with data object in iRODS
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.misc_path = iRODSPath(self.zone_path, MISC_FILES_COLL)
        self.misc_coll = self.irods.collections.get(self.misc_path)
        # Set up command
        self.command = VerifyZoneCommand()
        self.cmd_kw = {'zone': str(self.zone.sodar_uuid), 'sync': True}
        self.logger_name = LOGGER_PREFIX + 'verifyzone'

    def test_verify(self):
        """Test verify on moved zone"""
        self._make_zone_object()
        self.assertTrue(self.irods.data_objects.exists(self.obj_zone_path))
        self.assertFalse(self.irods.data_objects.exists(self.obj_sample_path))
        self.assertIsNone(self._get_verify_tl_event())
        self._move_zone()
        self.assertFalse(self.irods.data_objects.exists(self.obj_zone_path))
        self.assertTrue(self.irods.data_objects.exists(self.obj_sample_path))
        self.command.handle(**self.cmd_kw)
        verify_tl_event = self._get_verify_tl_event()
        self.assertIsNotNone(verify_tl_event)
        self.assertEqual(verify_tl_event.get_status().status_type, TL_STATUS_OK)

    def test_verify_non_moved(self):
        """Test verify on non-moved zone"""
        # No move
        with self.assertLogs(self.logger_name) as cm_logs, self.assertRaises(
            SystemExit
        ) as cm_exit:
            self.command.handle(**self.cmd_kw)
        self.assertIn(MOVE_EVENT_NOT_FOUND_MSG, cm_logs[-1][0])
        self.assertEqual(cm_exit.exception.code, 1)

    def test_verify_move_failed(self):
        """Test verify on failed zone move timeline event"""
        self._make_zone_object()
        move_tl_event = self._move_zone()
        move_tl_event.set_status(TL_STATUS_FAILED)
        with self.assertLogs(self.logger_name) as cm, self.assertRaises(
            SystemExit
        ):
            self.command.handle(**self.cmd_kw)
        self.assertIn(MOVE_NOT_SUCCESSFUL_MSG, cm[-1][0])

    def test_verify_no_tl_extra_data(self):
        """Test verify with no timeline event extra data"""
        self._make_zone_object()
        move_tl_event = self._move_zone()
        move_tl_event.extra_data = {}
        move_tl_event.save()
        with self.assertLogs(self.logger_name) as cm, self.assertRaises(
            SystemExit
        ):
            self.command.handle(**self.cmd_kw)
        self.assertIn(NO_TL_EXTRA_DATA_MSG, cm[-1][0])
