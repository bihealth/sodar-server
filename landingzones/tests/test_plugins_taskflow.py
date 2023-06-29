"""Tests for plugins in the landingzones app with Taskflow enabled"""

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint

# Samplesheets dependency
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
)
from samplesheets.tests.test_views_taskflow import (
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
)

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']

# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20190703_172456'
ZONE_SUFFIX = 'Test Zone'


class TestPerformProjectSync(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for perform_project_modify()"""

    def setUp(self):
        super().setUp()
        self.plugin = ProjectAppPluginPoint.get_plugin('landingzones')

        # Make project with owner in Taskflow without public guest access
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
            public_guest_access=False,
        )
        self.project_path = self.irods_backend.get_sample_path(self.project)
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)

    def test_create_zone(self):
        """Test creating a landing zone collection in iRODS"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            status='ACTIVE',
        )
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(self.irods.collections.exists(zone_path), False)
        self.plugin.perform_project_sync(self.project)
        self.assertEqual(self.irods.collections.exists(zone_path), True)
        self.assert_irods_access(self.user.username, zone_path, 'own')

    def test_create_zone_moved(self):
        """Test creating a MOVED zone (should not be created)"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            status='MOVED',
        )
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(self.irods.collections.exists(zone_path), False)
        self.plugin.perform_project_sync(self.project)
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    def test_create_zone_existing(self):
        """Test creating an already existing zone (should not crash)"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
        )
        zone = self.make_zone_taskflow(zone)
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(self.irods.collections.exists(zone_path), True)
        self.assert_irods_access(self.user.username, zone_path, 'own')
        self.plugin.perform_project_sync(self.project)
        self.assertEqual(self.irods.collections.exists(zone_path), True)
        self.assert_irods_access(self.user.username, zone_path, 'own')
