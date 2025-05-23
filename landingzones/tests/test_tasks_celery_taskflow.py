"""Celery task tests for the landingzones app with taskflow enabled"""

from django.conf import settings
from django.contrib import auth
from django.test import RequestFactory

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from landingzones.constants import ZONE_STATUS_ACTIVE, ZONE_STATUS_MOVED
from landingzones.tasks_celery import TriggerZoneMoveTask
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


app_settings = AppSettingAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20190703_172456'
ZONE_SUFFIX = 'Test Zone'
ZONE_DESC = 'description'
TEST_OBJ_NAME = 'test1.txt'
ASYNC_WAIT_SECONDS = 5
ASYNC_RETRY_COUNT = 3


class TestTriggerZoneMoveTask(
    SampleSheetIOMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for the automated zone move triggering task"""

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
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Create zone
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        # Create zone in taskflow
        self.make_zone_taskflow(self.landing_zone)
        # Get collections
        self.zone_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.landing_zone)
        )
        self.assay_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.assay)
        )
        self.req_factory = RequestFactory()
        self.task = TriggerZoneMoveTask()

    def test_trigger(self):
        """Test triggering automated zone validation and moving"""
        self.assertEqual(self.landing_zone.status, ZONE_STATUS_ACTIVE)
        # Create file and fake request
        self.make_irods_object(
            self.zone_coll, settings.LANDINGZONES_TRIGGER_FILE
        )
        request = self.req_factory.post('/')
        request.user = self.user
        # Run task and assert results
        self.task.run(request)
        self.assert_zone_status(self.landing_zone, ZONE_STATUS_MOVED)

    def test_trigger_no_file(self):
        """Test triggering without an uploaded file"""
        self.assertEqual(self.landing_zone.status, ZONE_STATUS_ACTIVE)
        # Run task and assert results
        self.task.run()
        self.assert_zone_status(self.landing_zone, ZONE_STATUS_ACTIVE)

    def test_trigger_read_only(self):
        """Test triggering with site read-only mode"""
        app_settings.set('projectroles', 'site_read_only', True)
        self.assertEqual(self.landing_zone.status, ZONE_STATUS_ACTIVE)
        # Create file and fake request
        self.make_irods_object(
            self.zone_coll, settings.LANDINGZONES_TRIGGER_FILE
        )
        request = self.req_factory.post('/')
        request.user = self.user
        # Run task and assert results
        self.task.run(request)
        self.assert_zone_status(self.landing_zone, ZONE_STATUS_ACTIVE)
