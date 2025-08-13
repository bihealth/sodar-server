"""Tests for REST API views in the landingzones app"""

import json

from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI
from projectroles.tests.test_views_api import APIViewTestBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.constants import (
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_MOVING,
    ZONE_STATUS_VALIDATING,
)
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import ZONE_TITLE, ZONE_DESC
from landingzones.views_api import (
    LANDINGZONES_API_MEDIA_TYPE,
    LANDINGZONES_API_DEFAULT_VERSION,
)


plugin_api = PluginAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_STATUS = ZONE_STATUS_VALIDATING
ZONE_STATUS_INFO = 'Testing'
INVALID_UUID = '11111111-1111-1111-1111-111111111111'


class LandingZoneAPIViewTestBase(
    LandingZoneMixin, SampleSheetIOMixin, APIViewTestBase
):
    """Base class for Landingzones API view testing"""

    media_type = LANDINGZONES_API_MEDIA_TYPE
    api_version = LANDINGZONES_API_DEFAULT_VERSION

    def setUp(self):
        super().setUp()
        # Init contributor user and assignment
        self.user_contributor = self.make_user('user_contributor')
        self.contributor_as = self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create LandingZone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )


class TestLandingZoneListAPIView(LandingZoneAPIViewTestBase):
    """Tests for LandingZoneListAPIView"""

    def setUp(self):
        super().setUp()
        self.irods_backend = plugin_api.get_backend_api('omics_irods')
        self.url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get_owner(self):
        """Test LandingZoneListAPIView GET as project owner"""
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        expected = {
            'title': self.zone.title,
            'project': str(self.project.sodar_uuid),
            'user': str(self.user.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'status': self.zone.status,
            'status_info': self.zone.status_info,
            'status_locked': False,
            'date_modified': self.get_drf_datetime(self.zone.date_modified),
            'description': self.zone.description,
            'user_message': self.zone.user_message,
            'configuration': self.zone.configuration,
            'config_data': self.zone.config_data,
            'irods_path': self.irods_backend.get_path(self.zone),
            'sodar_uuid': str(self.zone.sodar_uuid),
        }
        self.assertEqual(json.loads(response.content)[0], expected)

    def test_get_pagination(self):
        """Test GET with pagination"""
        url = self.url + '?page=1'
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        expected = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'title': self.zone.title,
                    'project': str(self.project.sodar_uuid),
                    'user': str(self.user.sodar_uuid),
                    'assay': str(self.assay.sodar_uuid),
                    'status': self.zone.status,
                    'status_info': self.zone.status_info,
                    'status_locked': False,
                    'date_modified': self.get_drf_datetime(
                        self.zone.date_modified
                    ),
                    'description': self.zone.description,
                    'user_message': self.zone.user_message,
                    'configuration': self.zone.configuration,
                    'config_data': self.zone.config_data,
                    'irods_path': self.irods_backend.get_path(self.zone),
                    'sodar_uuid': str(self.zone.sodar_uuid),
                }
            ],
        }
        self.assertEqual(json.loads(response.content), expected)

    def test_get_no_own_zones(self):
        """Test GET as user with no own zones"""
        response = self.request_knox(
            self.url, token=self.get_token(self.user_contributor)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_finished_default(self):
        """Test GET with finished zone and no finished parameter"""
        self.make_landing_zone(
            title=ZONE_TITLE + '_moved',
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_MOVED,
        )
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            json.loads(response.content)[0]['sodar_uuid'],
            str(self.zone.sodar_uuid),
        )

    def test_get_finished_false(self):
        """Test GET with finished zone and finished=0"""
        self.make_landing_zone(
            title=ZONE_TITLE + '_moved',
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_MOVED,
        )
        url = self.url + '?finished=0'
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            json.loads(response.content)[0]['sodar_uuid'],
            str(self.zone.sodar_uuid),
        )

    def test_get_finished_true(self):
        """Test GET with finished zone and finished=1"""
        self.make_landing_zone(
            title=ZONE_TITLE + '_moved',
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_MOVED,
        )
        url = self.url + '?finished=1'
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)


class TestLandingZoneRetrieveAPIView(LandingZoneAPIViewTestBase):
    """Tests for LandingZoneRetrieveAPIView"""

    def test_get(self):
        """Test LandingZoneRetrieveAPIView GET as zone owner"""
        irods_backend = plugin_api.get_backend_api('omics_irods')
        url = reverse(
            'landingzones:api_retrieve',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)

        expected = {
            'title': self.zone.title,
            'project': str(self.project.sodar_uuid),
            'user': str(self.user.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'status': self.zone.status,
            'status_info': self.zone.status_info,
            'status_locked': False,
            'date_modified': self.get_drf_datetime(self.zone.date_modified),
            'description': self.zone.description,
            'user_message': self.zone.user_message,
            'configuration': self.zone.configuration,
            'config_data': self.zone.config_data,
            'irods_path': irods_backend.get_path(self.zone),
            'sodar_uuid': str(self.zone.sodar_uuid),
        }
        self.assertEqual(json.loads(response.content), expected)

    def test_get_locked(self):
        """Test GET with locked landing zone status"""
        self.zone.status = ZONE_STATUS_MOVING
        self.zone.save()
        url = reverse(
            'landingzones:api_retrieve',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status_locked'], True)


class TestLandingZoneUpdateAPIView(LandingZoneAPIViewTestBase):
    """Tests for LandingZoneUpdateAPIView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:api_update',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_patch(self):
        """Test LandingZoneUpdateAPIView PATCH as zone owner"""
        data = {
            'description': 'New description',
            'user_message': 'New user message',
        }
        response = self.request_knox(self.url, method='PATCH', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content)['description'], 'New description'
        )
        self.assertEqual(
            json.loads(response.content)['user_message'], 'New user message'
        )

    def test_patch_title(self):
        """Test PATCH to update title (should fail)"""
        data = {'title': 'New title'}
        response = self.request_knox(self.url, method='PATCH', data=data)
        self.assertEqual(response.status_code, 400)

    def test_put(self):
        """Test PUT as zone owner"""
        data = {
            'description': 'New description',
            'user_message': 'New user message',
        }
        response = self.request_knox(self.url, method='PUT', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content)['description'], 'New description'
        )
        self.assertEqual(
            json.loads(response.content)['user_message'], 'New user message'
        )

    def test_put_title(self):
        """Test PUT to update title (should fail)"""
        data = {'title': 'New title'}
        response = self.request_knox(self.url, method='PUT', data=data)
        self.assertEqual(response.status_code, 400)
