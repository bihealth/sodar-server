"""Tests for API view permissions in the irodsinfo app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.base import (
    SiteAppPermissionTestBase,
    SODARAPIPermissionTestMixin,
)

from irodsinfo.views_api import (
    IRODSINFO_API_MEDIA_TYPE,
    IRODSINFO_API_DEFAULT_VERSION,
)


class TestIrodsConfigRetrieveAPIView(
    SODARAPIPermissionTestMixin, SiteAppPermissionTestBase
):
    """Tests for IrodsConfigRetrieveAPIView permissions"""

    media_type = IRODSINFO_API_MEDIA_TYPE
    api_version = IRODSINFO_API_DEFAULT_VERSION

    def test_get_irods_config(self):
        """Test IrodsConfigRetrieveAPIView GET"""
        url = reverse('irodsinfo:api_env')
        self.assert_response_api(url, [self.superuser, self.regular_user], 200)
        self.assert_response_api(url, self.anonymous, 401)
