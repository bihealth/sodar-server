"""Tests for Ajax API views in the landingzones app"""

import json
import random
import string

from django.test import override_settings
from django.urls import reverse

from landingzones.constants import ZONE_STATUS_MOVED
from landingzones.tests.test_views import ViewTestBase
from landingzones.views_ajax import STATUS_TRUNCATE_LEN


class TestZoneStatusRetrieveAjaxView(ViewTestBase):
    """Tests for ZoneStatusRetrieveAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:ajax_status',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {
            'zones': {str(self.zone.sodar_uuid): {'modified': ''}}
        }
        self.post_kw = {'content_type': 'application/json'}

    def test_post(self):
        """Test ZoneStatusRetrieveAjaxView POST"""
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        expected = {
            str(self.zone.sodar_uuid): {
                'modified': self.zone.date_modified.timestamp(),
                'status': self.zone.status,
                'status_info': self.zone.status_info,
                'truncated': False,
            }
        }
        self.assertEqual(response.data['zones'], expected)
        self.assertEqual(response.data['zone_create_limit'], False)

    def test_post_modified(self):
        """Test ZoneStatusRetrieveAjaxView POST"""
        post_data = {
            'zones': {
                str(self.zone.sodar_uuid): {
                    'modified': self.zone.date_modified.timestamp()
                }
            }
        }
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {'zones': {}, 'zone_create_limit': False}
        )

    def test_post_truncate(self):
        """Test POST with truncated status_info"""
        self.zone.status_info = ''.join(
            random.choice(string.ascii_letters)
            for _ in range(STATUS_TRUNCATE_LEN * 2)
        )
        self.zone.save()
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        expected = {
            str(self.zone.sodar_uuid): {
                'modified': self.zone.date_modified.timestamp(),
                'status': self.zone.status,
                'status_info': self.zone.status_info[:STATUS_TRUNCATE_LEN],
                'truncated': True,
            }
        }
        self.assertEqual(response.data['zones'], expected)
        self.assertEqual(response.data['zone_create_limit'], False)

    def test_post_no_zone(self):
        """Test POST with no zones"""
        post_data = {'zones': {}}
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {'zones': {}, 'zone_create_limit': False}
        )

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_post_limit(self):
        """Test POST with zone creation limit reached"""
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['zone_create_limit'], True)

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_post_limit_existing_finished(self):
        """Test POST with zone creation limit and finished zone"""
        self.zone.set_status(ZONE_STATUS_MOVED)
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['zone_create_limit'], False)


class TestZoneStatusInfoRetrieveAjaxView(ViewTestBase):
    """Tests for ZoneStatusInfoRetrieveAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:ajax_status_info',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneStatusInfoRetrieveAjaxView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'status_info': self.zone.status_info})

    def test_get_long(self):
        """Test GET with long value (should not be truncated)"""
        self.zone.status_info = ''.join(
            random.choice(string.ascii_letters)
            for _ in range(STATUS_TRUNCATE_LEN * 2)
        )
        self.zone.save()
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'status_info': self.zone.status_info})
