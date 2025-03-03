"""Tests for views in the irodsbackend app"""

import base64

from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.tests.test_views_api import (
    SODARAPIViewTestMixin,
    EMPTY_KNOX_TOKEN,
)


# Local constants
LOCAL_USER_NAME = 'local_user'
LOCAL_USER_PASS = 'password'


class TestBasicAuthView(SODARAPIViewTestMixin, TestCase):
    """Tests for BasicAuthView"""

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
        self.url = reverse('irodsbackend:api_auth')

    def test_post(self):
        """Test TestBasicAuthView POST with existing local user"""
        response = self.client.get(
            self.url, **self._get_auth_header(LOCAL_USER_NAME, LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_post_disabled(self):
        """Test POST with local and auth check disabled"""
        response = self.client.get(
            self.url, **self._get_auth_header(LOCAL_USER_NAME, LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 500)

    def test_post_invalid_user(self):
        """Test POST with invalid user"""
        response = self.client.get(
            self.url,
            **self._get_auth_header(LOCAL_USER_NAME, 'invalid_password')
        )
        self.assertEqual(response.status_code, 401)

    def test_post_invalid_password(self):
        """Test POST with invalid password"""
        response = self.client.get(
            self.url, **self._get_auth_header('invalid_user', LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 401)

    def test_post_token(self):
        """Test POST with knox token"""
        knox_token = self.get_token(self.user)
        response = self.client.get(
            self.url, **self._get_auth_header(LOCAL_USER_NAME, knox_token)
        )
        self.assertEqual(response.status_code, 200)

    def test_post_token_invalid(self):
        """Test POST with invalid knox token (should fail)"""
        self.get_token(self.user)  # Making sure the user has A token
        response = self.client.get(
            self.url, **self._get_auth_header(LOCAL_USER_NAME, EMPTY_KNOX_TOKEN)
        )
        self.assertEqual(response.status_code, 401)

    def test_post_token_invalid_username(self):
        """Test POST with username not matching token (should fail)"""
        knox_token = self.get_token(self.user)
        response = self.client.get(
            self.url, **self._get_auth_header('invalid_user', knox_token)
        )
        self.assertEqual(response.status_code, 401)
