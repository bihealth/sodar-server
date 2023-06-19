"""Tests for API views in the irodsinfo app"""

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from test_plus.test import TestCase

from irodsinfo.tests.test_views import PLUGINS_DISABLE_IRODS


class TestIrodsConfigRetrieveAPIView(TestCase):
    """Tests for IrodsConfigRetrieveAPIView"""

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.save()
        self.regular_user = self.make_user('regular_user')

    def test_get_irods_config(self):
        """Test GET request to retrieve iRODS config"""
        url = reverse('irodsinfo:api_config')
        with self.login(self.regular_user):
            response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('irods_environment', response.data)

    @override_settings(ENABLED_BACKEND_PLUGINS=PLUGINS_DISABLE_IRODS)
    def test_get_irods_config_with_disabled_backend(self):
        """Test GET request to retrieve iRODS config with disabled backend"""
        url = reverse('irodsinfo:api_config')
        with self.login(self.regular_user):
            response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('iRODS backend not enabled', response.data['detail'])
