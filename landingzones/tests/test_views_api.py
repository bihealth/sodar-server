"""Tests for REST API views in the landingzones app"""

import json

from unittest import skipIf

from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_api import TestAPIViewsBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views import (
    IRODS_BACKEND_ENABLED,
    IRODS_BACKEND_SKIP_MSG,
)
from landingzones.tests.test_views_taskflow import (
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
INVALID_UUID = '11111111-1111-1111-1111-111111111111'


# Base Views and Classes -------------------------------------------------------


class TestLandingZoneAPIViewsBase(
    LandingZoneMixin, SampleSheetIOMixin, TestAPIViewsBase
):
    """Base class for Landingzones API view testing"""

    def setUp(self):
        super().setUp()

        # Init contributor user and assignment
        self.user_contrib = self.make_user('user_contrib')
        self.contrib_as = self._make_assignment(
            self.project, self.user_contrib, self.role_contributor
        )

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create LandingZone
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.owner_as.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='ACTIVE',
        )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestLandingZoneListAPIView(TestLandingZoneAPIViewsBase):
    """Tests for LandingZoneListAPIView"""

    def test_get_owner(self):
        """Test LandingZoneListAPIView get() as project owner"""
        irods_backend = get_backend_api('omics_irods', conn=False)
        url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )

        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        expected = {
            'title': self.landing_zone.title,
            'project': str(self.project.sodar_uuid),
            'user': self.get_serialized_user(self.user),
            'assay': str(self.assay.sodar_uuid),
            'status': self.landing_zone.status,
            'status_info': self.landing_zone.status_info,
            'status_locked': False,
            'date_modified': self.get_drf_datetime(
                self.landing_zone.date_modified
            ),
            'description': self.landing_zone.description,
            'user_message': self.landing_zone.user_message,
            'configuration': self.landing_zone.configuration,
            'config_data': self.landing_zone.config_data,
            'irods_path': irods_backend.get_path(self.landing_zone),
            'sodar_uuid': str(self.landing_zone.sodar_uuid),
        }
        self.assertEqual(json.loads(response.content)[0], expected)

    def test_get_no_own_zones(self):
        """Test LandingZoneListAPIView get() as user with no own zones"""
        url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )
        response = self.request_knox(
            url, token=self.get_token(self.user_contrib)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_finished_default(self):
        """Test get() with a finished zone and no finished parameter"""
        self._make_landing_zone(
            title=ZONE_TITLE + '_moved',
            project=self.project,
            user=self.owner_as.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='MOVED',
        )
        url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            json.loads(response.content)[0]['sodar_uuid'],
            str(self.landing_zone.sodar_uuid),
        )

    def test_get_finished_false(self):
        """Test get() with a finished zone and finished=0"""
        self._make_landing_zone(
            title=ZONE_TITLE + '_moved',
            project=self.project,
            user=self.owner_as.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='MOVED',
        )
        url = (
            reverse(
                'landingzones:api_list',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?finished=0'
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            json.loads(response.content)[0]['sodar_uuid'],
            str(self.landing_zone.sodar_uuid),
        )

    def test_get_finished_true(self):
        """Test get() with a finished zone and finished=1"""
        self._make_landing_zone(
            title=ZONE_TITLE + '_moved',
            project=self.project,
            user=self.owner_as.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='MOVED',
        )
        url = (
            reverse(
                'landingzones:api_list',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?finished=1'
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestLandingZoneRetrieveAPIView(TestLandingZoneAPIViewsBase):
    """Tests for LandingZoneRetrieveAPIView"""

    def test_get(self):
        """Test LandingZoneRetrieveAPIView get() as zone owner"""
        irods_backend = get_backend_api('omics_irods', conn=False)
        url = reverse(
            'landingzones:api_retrieve',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)

        expected = {
            'title': self.landing_zone.title,
            'project': str(self.project.sodar_uuid),
            'user': self.get_serialized_user(self.user),
            'assay': str(self.assay.sodar_uuid),
            'status': self.landing_zone.status,
            'status_info': self.landing_zone.status_info,
            'status_locked': False,
            'date_modified': self.get_drf_datetime(
                self.landing_zone.date_modified
            ),
            'description': self.landing_zone.description,
            'user_message': self.landing_zone.user_message,
            'configuration': self.landing_zone.configuration,
            'config_data': self.landing_zone.config_data,
            'irods_path': irods_backend.get_path(self.landing_zone),
            'sodar_uuid': str(self.landing_zone.sodar_uuid),
        }
        self.assertEqual(json.loads(response.content), expected)

    def test_get_locked(self):
        """Test get() with locked landing zone status"""
        self.landing_zone.status = 'MOVING'
        self.landing_zone.save()
        url = reverse(
            'landingzones:api_retrieve',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status_locked'], True)
