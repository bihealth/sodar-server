"""Tests for UI view permissions in the irodsinfo app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import TestProjectPermissionBase


class TestIrodsinfoPermissions(TestProjectPermissionBase):
    """Tests for irodsinfo UI view permissions"""

    def test_irods_info(self):
        """Test permissions for IrodsInfoView"""
        url = reverse('irodsinfo:info')
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_irods_config(self):
        """Test permissions for IrodsConfigView"""
        url = reverse('irodsinfo:config')
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
