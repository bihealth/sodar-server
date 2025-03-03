"""Tests for API view permissions in the irodsinfo app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import SiteAppPermissionTestBase
from projectroles.tests.test_permissions_api import SODARAPIPermissionTestMixin

from irodsinfo.views_api import (
    IRODSINFO_API_MEDIA_TYPE,
    IRODSINFO_API_DEFAULT_VERSION,
)


class TestIrodsConfigRetrieveAPIView(
    SODARAPIPermissionTestMixin, SiteAppPermissionTestBase
):
    """Tests for irodsinfo API"""

    media_type = IRODSINFO_API_MEDIA_TYPE
    api_version = IRODSINFO_API_DEFAULT_VERSION

    def test_get_irods_config(self):
        """Test IrodsConfigRetrieveAPIView GET"""
        url = reverse('irodsinfo:api_env')
        good_users = [self.superuser, self.regular_user]
        bad_users = [self.anonymous]
        self.assert_response_api(url, good_users, 200)
        self.assert_response_api(url, bad_users, 401)
