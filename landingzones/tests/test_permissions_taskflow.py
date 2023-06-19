"""Tests for UI view permissions with taskflow"""

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_permissions import (
    TestPermissionMixin,
)

from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)
from taskflowbackend.tests.base import (
    TaskflowAPIPermissionTestBase,
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
TEST_OBJ_NAME = 'test1.txt'


class TestLandingZonePermissionTaskflowBase(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    TestPermissionMixin,
    TaskflowAPIPermissionTestBase,
):
    """Base view for landingzones permissions tests"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create LandingZone
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,  # NOTE: Zone owner = user_contributor
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
        # Add files to zone
        self.irods_obj = self.make_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_md5_object(self.irods_obj)


class TestLandingZonePermissions(TestLandingZonePermissionTaskflowBase):
    """Tests for landingzones UI view permissions"""

    def test_zone_update(self):
        """Test ZoneUpdateView permissions"""
        url = reverse(
            'landingzones:update',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        redirect_url = reverse(
            'landingzones:list',
            kwargs={'project': self.landing_zone.project.sodar_uuid},
        )
        self.assert_response(url, bad_users, 302, redirect_user=redirect_url)

    def test_zone_update_archive(self):
        """Test ZoneUpdateView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:update',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
        ]
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        redirect_url = reverse(
            'landingzones:list',
            kwargs={'project': self.landing_zone.project.sodar_uuid},
        )
        self.assert_response(url, bad_users, 302, redirect_user=redirect_url)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_zone_update_disable(self):
        """Test ZoneUpdateView with disabled non-superuser access"""
        url = reverse(
            'landingzones:update',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
        ]
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        redirect_url = reverse(
            'landingzones:list',
            kwargs={'project': self.landing_zone.project.sodar_uuid},
        )
        self.assert_response(url, bad_users, 302, redirect_user=redirect_url)

    def test_zone_delete(self):
        """Test ZoneDeleteView permissions"""
        url = reverse(
            'landingzones:delete',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_delete_archive(self):
        """Test ZoneDeleteView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:delete',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_zone_delete_disable(self):
        """Test ZoneDeleteView with disabled non-superuser access"""
        url = reverse(
            'landingzones:delete',
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_move(self):
        """Test ZoneMoveView permissions"""
        url = reverse(
            'landingzones:move',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_move_archive(self):
        """Test ZoneMoveView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:move',
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_zone_move_disable(self):
        """Test ZoneMoveView with disabled non-superuser access"""
        url = reverse(
            'landingzones:move',
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_validate(self):
        """Test ZoneMoveView for zone validation"""
        url = reverse(
            'landingzones:validate',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_validate_archive(self):
        """Test ZoneMoveView for zone validation with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:validate',
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_zone_validate_disable(self):
        """Test ZoneMoveView for zone validation with disabled non-superuser access"""
        url = reverse(
            'landingzones:validate',
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
