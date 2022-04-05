"""Celery task tests for the landingzones app"""

import time

from django.conf import settings
from django.contrib import auth
from django.test import RequestFactory

from unittest import skipIf

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_taskflow import TestTaskflowBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

from landingzones.tasks_celery import TriggerZoneMoveTask
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = SODAR_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = SODAR_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = SODAR_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW'
]


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TASKFLOW_ENABLED = (
    True if 'taskflow' in settings.ENABLED_BACKEND_PLUGINS else False
)
TASKFLOW_SKIP_MSG = 'Taskflow not enabled in settings'
ZONE_TITLE = '20190703_172456'
ZONE_SUFFIX = 'Test Zone'
ZONE_DESC = 'description'
TEST_OBJ_NAME = 'test1.txt'
ASYNC_WAIT_SECONDS = 5
ASYNC_RETRY_COUNT = 3


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestTriggerZoneMoveTask(
    SampleSheetIOMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetTaskflowMixin,
    TestTaskflowBase,
):
    """Tests for the automated zone move triggering task"""

    def setUp(self):
        super().setUp()

        # Get iRODS backend for session access
        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        self.irods_session = self.irods_backend.get_session()

        # Init project
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        # Create zone
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )

        # Create zone in taskflow
        self._make_zone_taskflow(self.landing_zone)

        # Get collections
        self.zone_coll = self.irods_session.collections.get(
            self.irods_backend.get_path(self.landing_zone)
        )
        self.assay_coll = self.irods_session.collections.get(
            self.irods_backend.get_path(self.assay)
        )

        self.req_factory = RequestFactory()
        self.task = TriggerZoneMoveTask()

    def tearDown(self):
        self.irods_session.cleanup()
        super().tearDown()

    def test_trigger(self):
        """Test triggering automated zone validation and moving"""
        # Assert precondition
        self.assertEqual(self.landing_zone.status, 'ACTIVE')

        # Create file and fake request
        self._make_object(self.zone_coll, settings.LANDINGZONES_TRIGGER_FILE)
        request = self.req_factory.post(
            '/', data={'sodar_url': self.live_server_url}
        )
        request.user = self.user

        # Run task and assert results
        self.task.run(request)
        self._wait_for_taskflow(self.landing_zone.sodar_uuid, 'MOVED')
        self.landing_zone.refresh_from_db()
        self.assertEqual(self.landing_zone.status, 'MOVED')

    def test_trigger_no_file(self):
        """Test triggering without an uploaded file"""
        # Assert precondition
        self.assertEqual(self.landing_zone.status, 'ACTIVE')

        # Run task and assert results
        self.task.run()
        time.sleep(5)  # Wait for async task to finish
        self.landing_zone.refresh_from_db()
        self.assertEqual(self.landing_zone.status, 'ACTIVE')
