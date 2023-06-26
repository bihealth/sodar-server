"""Tests for Ajax API views in the landingzones app"""

from django.urls import reverse

from landingzones.tests.test_views import TestViewsBase


class TestLandingZoneStatusGetAjaxView(TestViewsBase):
    """Tests for the landing zone status getting Ajax view"""

    def test_post(self):
        """Test POST request for getting a landing zone status"""
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:ajax_status',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'zone_uuids[]': [str(self.landing_zone.sodar_uuid)]},
            )
        self.assertEqual(response.status_code, 200)
        expected = {
            str(self.landing_zone.sodar_uuid): {
                'status': self.landing_zone.status,
                'status_info': self.landing_zone.status_info,
            }
        }
        self.assertEquals(response.data, expected)
