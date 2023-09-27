"""Tests for REST API view permissions in the landingzones app"""

from django.test import override_settings
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


class ZoneAPIPermissionTestBase(
    LandingZoneMixin,
    SampleSheetIOMixin,
    TestProjectAPIPermissionBase,
):
    """Base class for landingzones REST API view permission tests"""


class TestZoneListAPIView(ZoneAPIPermissionTestBase):
    """Tests for ZoneListAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get(self):
        """Test ZoneListAPIView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.assert_response(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 403)
        self.assert_response(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.assert_response(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 403)
        self.assert_response(self.url, self.anonymous, 401)


class TestZoneRetrieveAPIView(ZoneAPIPermissionTestBase):
    """Tests for ZoneRetrieveAPIView permissions"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create zone for project owner
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.url = reverse(
            'landingzones:api_retrieve', kwargs={'landingzone': zone.sodar_uuid}
        )

    def test_get(self):
        """Test ZoneRetrieveAPIView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.assert_response(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 403)
        self.assert_response(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.assert_response(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 403)
        self.assert_response(self.url, self.anonymous, 401)


# NOTE: For ZoneCreateAPIView tests, see test_permissions_api_taskflow


class TestZoneUpdateAPIView(ZoneAPIPermissionTestBase):
    """Tests for ZoneUpdateAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.url = reverse(
            'landingzones:api_update', kwargs={'landingzone': zone.sodar_uuid}
        )
        self.post_data = {'description': 'Test description updated'}

    def test_patch(self):
        """Test ZoneUpdateAPIView PATCH"""
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
            self.url,
            good_users,
            200,
            method='PATCH',
            data=self.post_data,
            knox=True,
        )
        self.assert_response_api(
            self.url,
            bad_users,
            403,
            method='PATCH',
            data=self.post_data,
            knox=True,
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='PATCH',
            data=self.post_data,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='PATCH',
            data=self.post_data,
            knox=True,
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='PATCH',
            data=self.post_data,
        )

    def test_patch_anon(self):
        """Test PATCH with anonymous access"""
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='PATCH',
            data=self.post_data,
        )

    def test_patch_archive(self):
        """Test PATCH with archived project"""
        self.project.set_archive()
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
            self.url,
            good_users,
            200,
            method='PATCH',
            data=self.post_data,
            knox=True,
        )
        self.assert_response_api(
            self.url,
            bad_users,
            403,
            method='PATCH',
            data=self.post_data,
            knox=True,
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='PATCH',
            data=self.post_data,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='PATCH',
            data=self.post_data,
            knox=True,
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='PATCH',
            data=self.post_data,
        )


# NOTE: For other API view tests, see test_permissions_api_taskflow
