"""Tests for UI view permissions in the irodsinfo app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import SiteAppPermissionTestBase


class TestIrodsinfoPermissions(SiteAppPermissionTestBase):
    """Tests for irodsinfo UI view permissions"""

    def test_get_irods_info(self):
        """Test IrodsInfoView GET"""
        url = reverse('irodsinfo:info')
        self.assert_response(url, [self.superuser, self.regular_user], 200)
        self.assert_response(url, self.anonymous, 302)

    def test_get_irods_config(self):
        """Test IrodsConfigView GET"""
        url = reverse('irodsinfo:config')
        self.assert_response(url, [self.superuser, self.regular_user], 200)
        self.assert_response(url, self.anonymous, 302)
