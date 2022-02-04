"""Tests for UI view permissions in the irodsinfo app"""

from django.conf import settings
from django.urls import reverse

from unittest import skipIf

# Projectroles dependency
from projectroles.tests.test_permissions import TestPermissionBase


IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


class TestIrodsinfoPermissions(TestPermissionBase):
    """Tests for irodsinfo UI view permissions"""

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()
        self.regular_user = self.make_user('regular_user')
        # No user
        self.anonymous = None

    def test_irods_info(self):
        """Test permissions for IrodsInfoView"""
        url = reverse('irodsinfo:info')
        good_users = [self.superuser, self.regular_user]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    @skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
    def test_irods_config(self):
        """Test permissions for IrodsConfigView"""
        url = reverse('irodsinfo:config')
        good_users = [self.superuser, self.regular_user]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
