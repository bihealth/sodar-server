"""Tests for Ajax API view permissions in the landingzones app"""

from django.urls import reverse

from landingzones.tests.test_permissions import TestLandingZonePermissionsBase


class TestZoneStatusRetrieveAjaxViewPermissions(TestLandingZonePermissionsBase):
    """Tests for ZoneStatusRetrieveAjaxView permissions"""

    def test_zone_status(self):
        """Test ZoneStatusRetrieveAjaxView permissions"""
        url = reverse(
            'landingzones:ajax_status',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
            self.user_contributor,  # Zone owner
        ]
        bad_users = [
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_zone_status_archive(self):
        """Test ZoneStatusRetrieveAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'landingzones:ajax_status',
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
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
