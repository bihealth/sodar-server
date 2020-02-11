"""Tests for REST API views in the landingzones app"""

import pytz
from unittest import skipIf

from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.utils import timezone

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views import SODARAPIViewMixin
from projectroles.tests.test_views_taskflow import TestTaskflowBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

from landingzones.models import LandingZone, DEFAULT_STATUS_INFO
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views import (
    TestViewsBase,
    IRODS_BACKEND_ENABLED,
    IRODS_BACKEND_SKIP_MSG,
)
from landingzones.tests.test_views_taskflow import (
    LandingZoneTaskflowMixin,
    ZONE_TITLE,
    ZONE_DESC,
)


# Global constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_STATUS = 'VALIDATING'
ZONE_STATUS_INFO = 'Testing'
LOCAL_TZ = pytz.timezone(settings.TIME_ZONE)
INVALID_UUID = '11111111-1111-1111-1111-111111111111'


# TODO: Move to SODAR Core
# TODO: Combine with SODARAPIViewMixin
class GenericAPIViewTestMixin(SODARAPIViewMixin):
    """Mixin with generic DRF API view test helpers"""

    @classmethod
    def _get_drf_datetime(cls, obj_dt):
        """
        Return datetime in DRF compatible format.

        :param obj_dt: Object DateTime field
        :return: String
        """
        return timezone.localtime(
            obj_dt, pytz.timezone(settings.TIME_ZONE)
        ).isoformat()


class LandingZoneAPITaskflowBase(
    GenericAPIViewTestMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneTaskflowMixin,
    TestTaskflowBase,
):
    """Base landing zone API view test class with Taskflow enabled"""

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

        # Create dirs in iRODS
        self._make_irods_dirs(self.investigation)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class LandingZoneListAPIView(GenericAPIViewTestMixin, TestViewsBase):
    """Tests for LandingZoneListAPIView"""

    def test_get_owner(self):
        """Test LandingZoneListAPIView get() as project owner"""
        irods_backend = get_backend_api('omics_irods', conn=False)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:api_list',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                format='json',
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        expected = {
            'title': self.landing_zone.title,
            'project': str(self.project.sodar_uuid),
            'user': self.user.username,
            'assay': str(self.assay.sodar_uuid),
            'status': self.landing_zone.status,
            'status_info': self.landing_zone.status_info,
            'date_modified': self._get_drf_datetime(
                self.landing_zone.date_modified
            ),
            'description': self.landing_zone.description,
            'configuration': self.landing_zone.configuration,
            'config_data': self.landing_zone.config_data,
            'irods_path': irods_backend.get_path(self.landing_zone),
            'sodar_uuid': str(self.landing_zone.sodar_uuid),
        }
        self.assertEqual(dict(response.data[0]), expected)

    def test_get_no_own_zones(self):
        """Test LandingZoneListAPIView get() as user with no own zones"""
        with self.login(self.user_contrib):
            response = self.client.get(
                reverse(
                    'landingzones:api_list',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                format='json',
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class LandingZoneRetrieveAPIView(GenericAPIViewTestMixin, TestViewsBase):
    """Tests for LandingZoneRetrieveAPIView"""

    def test_get(self):
        """Test LandingZoneRetrieveAPIView get() as zone owner"""
        irods_backend = get_backend_api('omics_irods', conn=False)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:api_retrieve',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                format='json',
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        self.assertEqual(response.status_code, 200)

        expected = {
            'title': self.landing_zone.title,
            'project': str(self.project.sodar_uuid),
            'user': self.user.username,
            'assay': str(self.assay.sodar_uuid),
            'status': self.landing_zone.status,
            'status_info': self.landing_zone.status_info,
            'date_modified': self._get_drf_datetime(
                self.landing_zone.date_modified
            ),
            'description': self.landing_zone.description,
            'configuration': self.landing_zone.configuration,
            'config_data': self.landing_zone.config_data,
            'irods_path': irods_backend.get_path(self.landing_zone),
            'sodar_uuid': str(self.landing_zone.sodar_uuid),
        }
        self.assertEqual(response.data, expected)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestLandingZoneCreateAPIView(LandingZoneAPITaskflowBase):
    """Tests for LandingZoneCreateAPIView"""

    def test_post(self):
        """Test LandingZoneCreateAPIView post()"""
        post_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'config_data': {},
            'sodar_url': self.live_server_url,
        }

        # Assert preconditions
        self.assertEqual(LandingZone.objects.all().count(), 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after creation
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 1)

        # Assert status after taskflow has finished
        self._wait_for_taskflow(
            zone_uuid=response.data['sodar_uuid'], status='ACTIVE'
        )
        zone = LandingZone.objects.first()

        # Check result
        zone_dict = model_to_dict(zone)
        expected = {
            'id': zone.pk,
            'title': zone.title[:16] + 'new_zone',
            'project': self.project.pk,
            'user': self.user.pk,
            'assay': self.assay.pk,
            'status': 'ACTIVE',
            'status_info': DEFAULT_STATUS_INFO['ACTIVE'],
            'description': zone.description,
            'configuration': zone.configuration,
            'config_data': zone.config_data,
            'sodar_uuid': zone.sodar_uuid,
        }
        self.assertEqual(zone_dict, expected)

        # Check API response
        # NOTE: This is still in CREATING state with no iRODS path
        # NOTE: Only checking UUID
        self.assertEqual(response.data['sodar_uuid'], str(zone.sodar_uuid))

    def test_post_no_investigation(self):
        """Test LandingZoneCreateAPIView post() with no investigation"""
        self.investigation.delete()

        post_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'config_data': {},
            'sodar_url': self.live_server_url,
        }

        # Assert preconditions
        self.assertEqual(LandingZone.objects.all().count(), 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after creation
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 0)

    def test_post_no_irods_collections(self):
        """Test LandingZoneCreateAPIView post() with no iRODS collections"""
        self.investigation.irods_status = False
        self.investigation.save()

        post_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'config_data': {},
            'sodar_url': self.live_server_url,
        }

        # Assert preconditions
        self.assertEqual(LandingZone.objects.all().count(), 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after creation
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 0)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestLandingZoneSubmitDeleteAPIView(
    LandingZoneMixin, LandingZoneAPITaskflowBase
):
    """Tests for LandingZoneSubmitDeleteAPIView"""

    def setUp(self):
        super().setUp()

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

    def test_post(self):
        """Test LandingZoneSubmitDeleteAPIView post()"""
        post_data = {'sodar_url': self.live_server_url}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_submit_delete',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after deletion
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )

        # Assert status after taskflow has finished
        self._wait_for_taskflow(
            zone_uuid=response.data['sodar_uuid'], status='DELETED'
        )
        self.assertEqual(LandingZone.objects.all().count(), 1)
        self.assertEqual(LandingZone.objects.first().status, 'DELETED')

    def test_post_invalid_status(self):
        """Test post() with invalid zone status (should fail)"""
        post_data = {'sodar_url': self.live_server_url}
        self.landing_zone.status = 'MOVED'
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_submit_delete',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after deletion
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.all().count(), 1)
        self.assertEqual(LandingZone.objects.first().status, 'MOVED')

    def test_post_invalid_uuid(self):
        """Test post() with invalid zone UUID (should fail)"""
        # irods_backend = get_backend_api('omics_irods', conn=True)
        post_data = {'sodar_url': self.live_server_url}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_submit_delete',
                    kwargs={'landingzone': INVALID_UUID},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after deletion
        self.assertEqual(response.status_code, 404)
        self.assertEqual(LandingZone.objects.all().count(), 1)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestLandingZoneSubmitMoveAPIView(
    LandingZoneMixin, LandingZoneAPITaskflowBase
):
    """Tests for TestLandingZoneSubmitMoveAPIView"""

    def setUp(self):
        super().setUp()

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

    def test_post_validate(self):
        """Test post() for validation"""
        post_data = {'sodar_url': self.live_server_url}
        self.landing_zone.status = 'FAILED'  # Update to check status change
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_submit_validate',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after deletion
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )

        # Assert status after taskflow has finished
        self._wait_for_taskflow(
            zone_uuid=response.data['sodar_uuid'], status='ACTIVE'
        )
        self.assertEqual(LandingZone.objects.all().count(), 1)
        self.assertEqual(LandingZone.objects.first().status, 'ACTIVE')
        self.assertEqual(
            LandingZone.objects.first().status_info,
            'Successfully validated 0 files',
        )

    def test_post_validate_invalid_status(self):
        """Test post() for validation with invalid zone status (should fail)"""
        post_data = {'sodar_url': self.live_server_url}
        self.landing_zone.status = 'MOVED'
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_submit_validate',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after deletion
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.all().count(), 1)
        self.assertEqual(LandingZone.objects.first().status, 'MOVED')

    def test_post_move(self):
        """Test post() for moving"""
        post_data = {'sodar_url': self.live_server_url}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_submit_move',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after deletion
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )

        # Assert status after taskflow has finished
        self._wait_for_taskflow(
            zone_uuid=response.data['sodar_uuid'], status='MOVED'
        )
        self.assertEqual(LandingZone.objects.all().count(), 1)
        self.assertEqual(LandingZone.objects.first().status, 'MOVED')

    def test_post_move_invalid_status(self):
        """Test post() for moving with invalid zone status (should fail)"""
        post_data = {'sodar_url': self.live_server_url}
        self.landing_zone.status = 'DELETED'
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:api_submit_move',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data=post_data,
                HTTP_ACCEPT=self.get_accept_header(
                    media_type=settings.SODAR_API_MEDIA_TYPE,
                    version=settings.SODAR_API_DEFAULT_VERSION,
                ),
            )

        # Assert status after deletion
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.all().count(), 1)
        self.assertEqual(LandingZone.objects.first().status, 'DELETED')
