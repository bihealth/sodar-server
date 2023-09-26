"""Tests for API view permissions in the irodsinfo app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import TestSiteAppPermissionBase


class TestIrodsConfigRetrieveAPIView(TestSiteAppPermissionBase):
    """Tests for irodsinfo API"""

    def test_get_irods_config(self):
        """Test IrodsConfigRetrieveAPIView GET"""
        url = reverse('irodsinfo:api_env')
        good_users = [self.superuser, self.regular_user]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 401)
