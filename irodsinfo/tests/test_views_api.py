"""Tests for API views in the irodsinfo app"""

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from test_plus.test import TestCase

from irodsinfo.tests.test_views import PLUGINS_DISABLE_IRODS
from irodsinfo.views_api import (
    IRODSINFO_API_MEDIA_TYPE,
    IRODSINFO_API_DEFAULT_VERSION,
)


class TestIrodsConfigRetrieveAPIView(TestCase):
    """Tests for IrodsConfigRetrieveAPIView"""

    media_type = IRODSINFO_API_MEDIA_TYPE
    api_version = IRODSINFO_API_DEFAULT_VERSION

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.save()
        self.regular_user = self.make_user('regular_user')
        self.url = reverse('irodsinfo:api_env')

    def test_get(self):
        """Test IrodsConfigRetrieveAPIView GET"""
        with self.login(self.regular_user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('irods_environment', response.data)

    @override_settings(ENABLED_BACKEND_PLUGINS=PLUGINS_DISABLE_IRODS)
    def test_get_irods_config_with_disabled_backend(self):
        """Test GET with disabled backend"""
        with self.login(self.regular_user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('iRODS backend not enabled', response.data['detail'])
