"""UI tests for the irodsinfo app"""

from django.contrib.auth.models import Group
from django.test import override_settings
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_ui import UITestBase


# SODAR constants
AUTH_TYPE_LOCAL = SODAR_CONSTANTS['AUTH_TYPE_LOCAL']
AUTH_TYPE_LDAP = SODAR_CONSTANTS['AUTH_TYPE_LDAP']
AUTH_TYPE_OIDC = SODAR_CONSTANTS['AUTH_TYPE_OIDC']
OIDC_USER_GROUP = SODAR_CONSTANTS['OIDC_USER_GROUP']


class TestIrodsInfoView(UITestBase):
    """Tests for IrodsInfoView"""

    def setUp(self):
        super().setUp()
        self.url = reverse('irodsinfo:info')

    def test_render_oidc_alert_local(self):
        """Test rendering of OIDC alert as local user"""
        self.assertEqual(self.user_owner.get_auth_type(), AUTH_TYPE_LOCAL)
        self.login_and_redirect(self.user_owner, self.url)
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-ii-alert-oidc')

    @override_settings(AUTH_LDAP_USERNAME_DOMAIN='TEST')
    def test_render_oidc_alert_ldap(self):
        """Test rendering of OIDC alert as LDAP user"""
        self.user_owner.username = 'user_owner@TEST'
        self.user_owner.save()  # NOTE: set_group() is called on user save()
        self.assertEqual(self.user_owner.get_auth_type(), AUTH_TYPE_LDAP)
        self.login_and_redirect(self.user_owner, self.url)
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-ii-alert-oidc')

    def test_render_oidc_alert_oidc(self):
        """Test rendering of OIDC alert as OIDC user"""
        group, _ = Group.objects.get_or_create(name=OIDC_USER_GROUP)
        group.user_set.add(self.user_owner)
        self.assertEqual(self.user_owner.get_auth_type(), AUTH_TYPE_OIDC)
        self.login_and_redirect(self.user_owner, self.url)
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-ii-alert-oidc')
        )
