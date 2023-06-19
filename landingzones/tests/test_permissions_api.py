"""Tests for REST API view permissions in the landingzones app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_permissions_api import TestProjectAPIPermissionBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestLandingZonePermissions(
    LandingZoneMixin,
    SampleSheetIOMixin,
    TestProjectAPIPermissionBase,
):
    """Tests for landingzones REST API view permissions"""

    def _get_update_post_data(self):
        return {'description': 'Test description updated'}

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create LandingZone for project owner
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )

    def test_list(self):
        """Test LandingZoneListAPIView permissions"""
        url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited
            self.user_delegate_cat,  # Inherited
            self.user_contributor_cat,  # Inherited
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,  # Inherited
            self.user_finder_cat,  # Inherited
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.assert_response(url, [self.anonymous], 401)

    def test_list_archive(self):
        """Test LandingZoneListAPIView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.assert_response(url, [self.anonymous], 401)

    def test_retrieve(self):
        """Test LandingZoneRetrieveAPIView permissions"""
        url = reverse(
            'landingzones:api_retrieve',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.assert_response(url, [self.anonymous], 401)

    def test_retrieve_archive(self):
        """Test LandingZoneRetrieveAPIView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:api_retrieve',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.assert_response(url, [self.anonymous], 401)

    def test_update(self):
        """Test LandingZoneUpdateAPIView permissions"""
        url = reverse(
            'landingzones:api_update',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(
            url,
            good_users,
            200,
            method='PATCH',
            data=self._get_update_post_data(),
            knox=True,
        )
        self.assert_response_api(
            url,
            bad_users,
            403,
            method='PATCH',
            data=self._get_update_post_data(),
            knox=True,
        )
        self.assert_response_api(
            url,
            [self.anonymous],
            401,
            method='PATCH',
            data=self._get_update_post_data(),
        )

    def test_update_archive(self):
        """Test LandingZoneUpdateAPIView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:api_update',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(
            url,
            good_users,
            200,
            method='PATCH',
            data=self._get_update_post_data(),
            knox=True,
        )
        self.assert_response_api(
            url,
            bad_users,
            403,
            method='PATCH',
            data=self._get_update_post_data(),
            knox=True,
        )
        self.assert_response_api(
            url,
            [self.anonymous],
            401,
            method='PATCH',
            data=self._get_update_post_data(),
        )
