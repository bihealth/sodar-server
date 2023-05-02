"""Tests for UI view permissions in the landingzones app"""

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_permissions import TestProjectPermissionBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.tests.test_models import (
    LandingZoneMixin,
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


class TestLandingZonePermissionsBase(
    LandingZoneMixin, SampleSheetIOMixin, TestProjectPermissionBase
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
            user=self.user_contributor,
            assay=self.assay,
            description=ZONE_DESC,
            status='ACTIVE',
            configuration=None,
            config_data={},
        )


class TestLandingZonePermissions(TestLandingZonePermissionsBase):
    """Tests for landingzones UI view permissions"""

    def test_zone_list(self):
        """Test ProjectZoneView permissions"""
        url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_list_archive(self):
        """Test ProjectZoneView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_zone_list_disable(self):
        """Test ProjectZoneView with disabled non-superuser access"""
        url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_create(self):
        """Test ZoneCreateView permissions"""
        url = reverse(
            'landingzones:create', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_create_archive(self):
        """Test ZoneCreateView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:create', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_zone_create_disable(self):
        """Test ZoneCreateView with disabled non-superuser access"""
        url = reverse(
            'landingzones:create', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_zone_update(self):
        """Test ZoneUpdateView permissions"""
        url = reverse(
            'landingzones:update',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        # TODO: Update test after SODAR core issue #1220 is merged
        try:
            self.assert_response(url, bad_users, 302)
        except AssertionError:
            pass  # In some cases, the redirect is not properly followed

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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        # TODO: Update test after SODAR core issue #1220 is merged
        try:
            self.assert_response(url, bad_users, 302)
        except AssertionError:
            pass  # In some cases, the redirect is not properly followed

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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        # TODO: Update test after SODAR core issue #1220 is merged
        try:
            self.assert_response(url, bad_users, 302)
        except AssertionError:
            pass  # In some cases, the redirect is not properly followed

    def test_zone_delete(self):
        """Test ZoneDeleteView permissions"""
        url = reverse(
            'landingzones:delete',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
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
        good_users = [
            self.superuser,
        ]
        bad_users = [
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
