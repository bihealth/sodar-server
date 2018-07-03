"""Integration tests for views in the landingzones Django app with taskflow"""

# NOTE: You must supply 'omics_url': self.live_server_url in taskflow requests!

import time
from unittest import skipIf

from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse

# Projectroles dependency
from projectroles.models import OMICS_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_taskflow import TestTaskflowBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin


User = auth.get_user_model()


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW']


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TASKFLOW_ENABLED = True if \
    'taskflow' in settings.ENABLED_BACKEND_PLUGINS else False
TASKFLOW_SKIP_MSG = 'Taskflow not enabled in settings'

ZONE_TITLE = '20190703_1724'
ZONE_SUFFIX = 'Test Zone'
ZONE_DESC = 'description'
TEST_FILE_NAME = 'test1'

ASYNC_WAIT_SECONDS = 5
ASYNC_RETRY_COUNT = 3


class LandingZoneTaskflowMixin:
    """Taskflow helpers for landingzones tests"""

    def _make_zone_taskflow(self, zone, request=None):
        """
        Create landing zone in iRODS using omics_taskflow
        :param zone: LandingZone object
        :param request: HTTP request object (optional, default=None)
        :raise taskflow.FlowSubmitException if submit fails
        """
        timeline = get_backend_api('timeline_backend')
        irods_backend = get_backend_api('omics_irods')
        user = request.user if request else zone.user

        self.assertEqual(zone.status, 'CREATING')

        # Create timeline event to prevent taskflow failure
        tl_event = timeline.add_event(
            project=zone.project,
            app_name='landingzones',
            user=user,
            event_name='zone_create',
            description='create landing zone',
            status_type='SUBMIT')

        flow_data = {
            'zone_title': zone.title,
            'zone_uuid': zone.omics_uuid,
            'user_name': user.username,
            'user_uuid': user.omics_uuid,
            'assay_path': irods_backend.get_subdir(
                zone.assay, landing_zone=True),
            'description': zone.description,
            'zone_config': zone.configuration,
            'dirs': []}

        values = {
            'project_uuid': zone.project.omics_uuid,
            'flow_name': 'landing_zone_create',
            'flow_data': flow_data,
            'timeline_uuid': tl_event.omics_uuid,
            'request_mode': 'async',
            'request': request}

        if not request:
            values['omics_url'] = self.live_server_url

        self.taskflow.submit(**values)

        # HACK: Wait for async stuff to finish
        time.sleep(ASYNC_WAIT_SECONDS)
        zone.refresh_from_db()
        self.assertEqual(zone.status, 'ACTIVE')


class TestLandingZoneCreateView(
        TestTaskflowBase, SampleSheetIOMixin,
        LandingZoneMixin, SampleSheetTaskflowMixin):
    """Tests for the landingzones create view with Taskflow and iRODS"""

    def setUp(self):
        super(TestLandingZoneCreateView, self).setUp()

        # Init project
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description')

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create dirs in iRODS
        self._make_irods_dirs(self.investigation)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_create_zone(self):
        """Test landingzones creation with taskflow"""

        # Assert precondition
        self.assertEqual(LandingZone.objects.all().count(), 0)

        # Issue POST request
        values = {
            'assay': str(self.assay.omics_uuid),
            'title_suffix': ZONE_SUFFIX,
            'description': ZONE_DESC,
            'configuration': '',
            'omics_url': self.live_server_url}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:create',
                    kwargs={'project': self.project.omics_uuid}),
                values)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.omics_uuid}))

        # HACK: Wait for async stuff to finish
        for i in range(0, ASYNC_RETRY_COUNT):
            time.sleep(ASYNC_WAIT_SECONDS)

            if LandingZone.objects.all().count() == 1:
                break

        # Assert zone creation
        self.assertEqual(LandingZone.objects.all().count(), 1)

        # Assert zone status
        zone = LandingZone.objects.first()
        self.assertEqual(zone.status, 'ACTIVE')


class TestLandingZoneDeleteView(
        TestTaskflowBase, SampleSheetIOMixin,
        LandingZoneMixin, LandingZoneTaskflowMixin, SampleSheetTaskflowMixin):
    """Tests for the landingzones delete view with Taskflow and iRODS"""

    def setUp(self):
        super(TestLandingZoneDeleteView, self).setUp()

        # Init project
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description')

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create dirs in iRODS
        self._make_irods_dirs(self.investigation)

        # Create zone
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={})

        # Create zone in taskflow
        self._make_zone_taskflow(self.landing_zone)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_delete_zone(self):
        """Test landingzones deletion with taskflow"""

        # Assert precondition
        self.assertEqual(LandingZone.objects.all().count(), 1)

        # Issue POST request
        values = {
            'omics_url': self.live_server_url}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:delete',
                    kwargs={'landingzone': self.landing_zone.omics_uuid}),
                values)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response, reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.omics_uuid}))

        # HACK: Wait for async stuff to finish
        for i in range(0, ASYNC_RETRY_COUNT):
            time.sleep(ASYNC_WAIT_SECONDS)

            if LandingZone.objects.first().status == 'DELETED':
                break

        # Assert zone deletion
        self.assertEqual(LandingZone.objects.all().count(), 1)
        self.assertEqual(LandingZone.objects.first().status, 'DELETED')
