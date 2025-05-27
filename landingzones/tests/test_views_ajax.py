"""Tests for Ajax API views in the landingzones app"""

import json
import random
import string

from django.test import override_settings
from django.urls import reverse

# Taskflowbackend dependency
from taskflowbackend.lock_api import ProjectLockAPI

from landingzones.constants import ZONE_STATUS_VALIDATING, ZONE_STATUS_MOVED
from landingzones.tests.test_views import ViewTestBase
from landingzones.views_ajax import STATUS_TRUNCATE_LEN


lock_api = ProjectLockAPI()


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
            'project_lock': False,
            'zone_active_count': 1,
            'zone_create_limit': None,
            'zone_create_limit_reached': False,
            'zone_validate_count': 0,
            'zone_validate_limit': 4,
            'zone_validate_limit_reached': False,
            'zones': {
                str(self.zone.sodar_uuid): {
                    'modified': self.zone.date_modified.timestamp(),
                    'status': self.zone.status,
                    'status_info': self.zone.status_info,
                    'truncated': False,
                }
            },
        }
        self.assertEqual(response.data, expected)

    def test_post_modified(self):
        """Test POST with date_modified set"""
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
            response.data,
            {
                'project_lock': False,
                'zone_active_count': 1,
                'zone_create_limit': None,
                'zone_create_limit_reached': False,
                'zone_validate_count': 0,
                'zone_validate_limit': 4,
                'zone_validate_limit_reached': False,
                'zones': {},
            },
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
        rd = response.data
        expected = {
            str(self.zone.sodar_uuid): {
                'modified': self.zone.date_modified.timestamp(),
                'status': self.zone.status,
                'status_info': self.zone.status_info[:STATUS_TRUNCATE_LEN],
                'truncated': True,
            }
        }
        self.assertEqual(rd['zones'], expected)

    def test_post_no_zones(self):
        """Test POST with no zones"""
        post_data = {'zones': {}}
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                'zones': {},
                'project_lock': False,
                'zone_active_count': 1,
                'zone_create_limit': None,
                'zone_create_limit_reached': False,
                'zone_validate_count': 0,
                'zone_validate_limit': 4,
                'zone_validate_limit_reached': False,
            },
        )

    def test_post_locked(self):
        """Test POST with locked project"""
        self.coordinator = lock_api.get_coordinator()
        lock_id = str(self.project.sodar_uuid)
        lock = self.coordinator.get_lock(lock_id)
        lock_api.acquire(lock)
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        rd = response.data
        self.assertEqual(rd['project_lock'], True)
        self.assertEqual(rd['zone_create_limit_reached'], False)
        self.assertEqual(rd['zone_validate_limit_reached'], False)

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_post_create_limit(self):
        """Test POST with zone creation limit reached"""
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        rd = response.data
        self.assertEqual(rd['project_lock'], False)
        self.assertEqual(rd['zone_active_count'], 1)
        self.assertEqual(rd['zone_create_limit'], 1)
        self.assertEqual(rd['zone_create_limit_reached'], True)
        self.assertEqual(rd['zone_validate_limit_reached'], False)

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_post_create_limit_existing_finished(self):
        """Test POST with zone creation limit and finished zone"""
        self.zone.set_status(ZONE_STATUS_MOVED)
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        rd = response.data
        self.assertEqual(rd['project_lock'], False)
        self.assertEqual(rd['zone_active_count'], 0)
        self.assertEqual(rd['zone_create_limit'], 1)
        self.assertEqual(rd['zone_create_limit_reached'], False)
        self.assertEqual(rd['zone_validate_limit_reached'], False)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_validate_limit(self):
        """Test POST with zone validation limit reached"""
        self.zone.set_status(ZONE_STATUS_VALIDATING)
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        rd = response.data
        self.assertEqual(rd['project_lock'], False)
        self.assertEqual(rd['zone_create_limit_reached'], False)
        self.assertEqual(rd['zone_validate_count'], 1)
        self.assertEqual(rd['zone_validate_limit'], 1)
        self.assertEqual(rd['zone_validate_limit_reached'], True)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_validate_limit_other_zone_moved(self):
        """Test POST to move with validation limit and other zone in moved status"""
        self.zone.set_status(ZONE_STATUS_MOVED)
        with self.login(self.user):
            response = self.client.post(
                self.url, data=json.dumps(self.post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        rd = response.data
        self.assertEqual(rd['project_lock'], False)
        self.assertEqual(rd['zone_create_limit_reached'], False)
        self.assertEqual(rd['zone_validate_count'], 0)
        self.assertEqual(rd['zone_validate_limit'], 1)
        self.assertEqual(rd['zone_validate_limit_reached'], False)


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
