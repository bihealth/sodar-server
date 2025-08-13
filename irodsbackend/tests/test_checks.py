"""Tests for Django checks in the irodsbackend app"""

from django.conf import settings
from django.test import override_settings
from test_plus.test import TestCase

# Projectroles dependency
from projectroles.plugins import PluginAPI, DISABLED

import irodsbackend.checks as checks
from irodsbackend.apps import IrodsbackendConfig


plugin_api = PluginAPI()


# Local constants
AC = [IrodsbackendConfig]


class TestIrodsbackendChecks(TestCase):
    """Tests for irodsbackend checks"""

    def test_check_sodar_auth_oidc(self):
        """Test check_sodar_auth_oidc() with default settings"""
        self.assertEqual(settings.ENABLE_IRODS, True)
        self.assertEqual(settings.IRODS_SODAR_AUTH, True)
        self.assertEqual(settings.ENABLE_OIDC, False)
        self.assertEqual(checks.check_sodar_auth_oidc(AC), [])

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_check_sodar_auth_oidc_disable_sodar_auth(self):
        """Test check_sodar_auth_oidc() with disabled SODAR auth"""
        self.assertEqual(checks.check_sodar_auth_oidc(AC), [])

    @override_settings(IRODS_SODAR_AUTH=False, ENABLE_OIDC=True)
    def test_check_sodar_auth_oidc_disable_sodar_auth_enable_oidc(self):
        """Test check_sodar_auth_oidc() with disabled SODAR auth and enabled OIDC"""
        self.assertEqual(checks.check_sodar_auth_oidc(AC), [checks.W001])

    def test_check_sodar_auth_local(self):
        """Test check_sodar_auth_local() with default settings"""
        self.assertEqual(settings.ENABLE_IRODS, True)
        self.assertEqual(settings.IRODS_SODAR_AUTH, True)
        self.assertEqual(settings.ENABLE_LDAP, False)
        self.assertEqual(settings.ENABLE_OIDC, False)
        self.assertEqual(checks.check_sodar_auth_local(AC), [])

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_check_sodar_auth_local_disable_sodar_auth(self):
        """Test check_sodar_auth_local() with disabled SODAR auth"""
        self.assertEqual(checks.check_sodar_auth_local(AC), [checks.W002])

    def test_check_token_app_oidc(self):
        """Test check_token_app_oidc() with default settings"""
        self.assertEqual(settings.ENABLE_IRODS, True)
        self.assertEqual(settings.ENABLE_OIDC, False)
        self.assertIsNotNone(plugin_api.get_app_plugin('tokens'))
        self.assertEqual(checks.check_token_app_oidc(AC), [])

    def test_check_token_app_oidc_disable_plugin(self):
        """Test check_token_app_oidc() with tokens plugin disabled"""
        plugin_model = plugin_api.get_app_plugin('tokens').get_model()
        plugin_model.status = DISABLED
        plugin_model.save()
        self.assertEqual(settings.ENABLE_OIDC, False)
        self.assertIsNone(plugin_api.get_app_plugin('tokens'))
        self.assertEqual(checks.check_token_app_oidc(AC), [])

    @override_settings(ENABLE_OIDC=True)
    def test_check_token_app_oidc_disable_plugin_enable_oidc(self):
        """Test check_token_app_oidc() with tokens plugin disabled and OIDC enabled"""
        plugin_model = plugin_api.get_app_plugin('tokens').get_model()
        plugin_model.status = DISABLED
        plugin_model.save()
        self.assertIsNone(plugin_api.get_app_plugin('tokens'))
        self.assertEqual(settings.ENABLE_OIDC, True)
        self.assertEqual(checks.check_token_app_oidc(AC), [checks.W003])
