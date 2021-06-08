"""Tests for Ajax API views in the landingzones app"""

from django.urls import reverse

from landingzones.tests.test_views import TestViewsBase


class TestLandingZoneStatusGetAjaxView(TestViewsBase):
    """Tests for the landing zone status getting Ajax view"""

    def test_get(self):
        """Test GET request for getting a landing zone status"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:ajax_status',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)

        expected = {
            'status': self.landing_zone.status,
            'status_info': self.landing_zone.status_info,
        }
        self.assertEquals(response.data, expected)
