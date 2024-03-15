"""Tests for views in the irodsbackend app"""

import base64

from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase


# Local constants
LOCAL_USER_NAME = 'local_user'
LOCAL_USER_PASS = 'password'


class TestLocalAuthAPIView(TestCase):
    """Tests for LocalAuthAPIView"""

    @staticmethod
    def _get_auth_header(username, password):
        """Return basic auth header"""
        credentials = base64.b64encode(
            '{}:{}'.format(username, password).encode('utf-8')
        ).strip()
        return {
            'HTTP_AUTHORIZATION': 'Basic {}'.format(credentials.decode('utf-8'))
        }

    def setUp(self):
        self.user = self.make_user(LOCAL_USER_NAME, LOCAL_USER_PASS)

    def test_auth(self):
        """Test auth with existing user and auth check enabled"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header(LOCAL_USER_NAME, LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_auth_disabled(self):
        """Test auth with existing user and auth check disabled"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header(LOCAL_USER_NAME, LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 500)

    def test_auth_invalid_user(self):
        """Test auth with invalid user"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header(LOCAL_USER_NAME, 'invalid_password')
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_invalid_password(self):
        """Test auth with invalid password"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header('invalid_user', LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 401)
