"""Tests for Ajax API view permissions in the landingzones app"""

from django.urls import reverse

from landingzones.tests.test_permissions import TestLandingZonePermissionsBase


class TestLandingZoneAjaxPermissions(TestLandingZonePermissionsBase):
    """Tests for landingzones Ajax API view permissions"""

    def test_zone_status(self):
        """Test permissions for landing zone Ajax status view"""
        url = reverse(
            'landingzones:ajax_status',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        good_users = [self.superuser, self.owner_as.user, self.delegate_as.user]
        bad_users = [
            self.contributor_as.user,  # NOTE: not the owner of the zone
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
