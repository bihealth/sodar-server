"""Tests for views in the irodsbackend app"""

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.tests.base import (
    SODARAPIViewTestMixin,
    AUTHENTICATION_BACKENDS_AXES,
    EMPTY_KNOX_TOKEN,
)


# Local constants
LOCAL_USER_NAME = 'local_user'
LOCAL_USER_PW = 'password'
INVALID_PW = 'INVALID_PASSWORD'


class BasicAuthViewTestBase(SODARAPIViewTestMixin, TestCase):
    """Base class for BasicAuthView tests"""

    def setUp(self):
        self.user = self.make_user(LOCAL_USER_NAME, LOCAL_USER_PW)
        self.url = reverse('irodsbackend:api_auth')


class TestBasicAuthView(BasicAuthViewTestBase):
    """Tests for BasicAuthView"""

    def test_get(self):
        """Test TestBasicAuthView GET with existing local user"""
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(LOCAL_USER_NAME, LOCAL_USER_PW),
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_get_disabled(self):
        """Test GET with local and auth check disabled"""
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(LOCAL_USER_NAME, LOCAL_USER_PW),
        )
        self.assertEqual(response.status_code, 500)

    def test_get_invalid_user(self):
        """Test GET with invalid user"""
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(LOCAL_USER_NAME, 'invalid_password'),
        )
        self.assertEqual(response.status_code, 401)

    def test_get_invalid_password(self):
        """Test GET with invalid password"""
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header('invalid_user', LOCAL_USER_PW),
        )
        self.assertEqual(response.status_code, 401)

    def test_get_token(self):
        """Test GET with knox token"""
        knox_token = self.get_token(self.user)
        response = self.client.get(
            self.url, **self.get_basic_auth_header(LOCAL_USER_NAME, knox_token)
        )
        self.assertEqual(response.status_code, 200)

    def test_get_token_invalid(self):
        """Test GET with invalid knox token (should fail)"""
        self.get_token(self.user)  # Making sure the user has A token
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(LOCAL_USER_NAME, EMPTY_KNOX_TOKEN),
        )
        self.assertEqual(response.status_code, 401)

    def test_get_token_invalid_username(self):
        """Test GET with username not matching token (should fail)"""
        knox_token = self.get_token(self.user)
        response = self.client.get(
            self.url, **self.get_basic_auth_header('invalid_user', knox_token)
        )
        self.assertEqual(response.status_code, 401)


@override_settings(
    AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS_AXES, AXES_ENABLED=True
)
class TestBasicAuthViewAxes(BasicAuthViewTestBase):
    """Tests for BasicAuthView with django-axes"""

    def test_get(self):
        """Test TestBasicAuthView GET with valid credentials"""
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(LOCAL_USER_NAME, LOCAL_USER_PW),
        )
        self.assertEqual(response.status_code, 200)

    def test_get_invalid(self):
        """Test GET with invalid credentials"""
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header('invalid_user', LOCAL_USER_PW),
        )
        self.assertEqual(response.status_code, 401)

    def test_get_lock(self):
        """Test GET with account locking"""
        header = self.get_basic_auth_header(LOCAL_USER_NAME, INVALID_PW)
        for i in range(0, settings.AXES_FAILURE_LIMIT - 1):
            response = self.client.get(self.url, **header)
            self.assertEqual(response.status_code, 401)
        # User should now be locked, attempt login one more time
        response = self.client.get(self.url, **header)
        self.assertEqual(response.status_code, 429)
