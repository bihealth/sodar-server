"""Management command tests for the landingzones app with taskflow"""

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

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
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20190703_172456'


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
