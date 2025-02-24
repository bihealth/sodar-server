"""Signals tests for the irodsbackend app"""

from irods.exception import UserDoesNotExist
from irods.user import iRODSUser

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Appalerts dependency
from appalerts.models import AppAlert

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from irodsbackend.signals import REGULAR_USER_PW_MSG, OIDC_USER_PW_MSG

# SODAR constants
OIDC_USER_GROUP = SODAR_CONSTANTS['OIDC_USER_GROUP']

# Local constants
USER_NAME = 'test_user'
ALERT_NAME = 'irods_user_create'


class TestCreateIrodsUser(TaskflowViewTestBase):
    """Tests for create_irods_user() signal"""

    def setUp(self):
        super().setUp()
        self.user_new = self.make_user(USER_NAME)

    def test_create(self):
        """Test create_irods_user() by logging in"""
        self.assertEqual(
            AppAlert.objects.filter(alert_name=ALERT_NAME).count(), 0
        )
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(USER_NAME)
        with self.login(self.user_new):
            self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)
        self.assertEqual(
            AppAlert.objects.filter(alert_name=ALERT_NAME).count(), 1
        )
        alert = AppAlert.objects.filter(alert_name=ALERT_NAME).first()
        self.assertIn(REGULAR_USER_PW_MSG, alert.message)
        self.assertEqual(alert.url, reverse('irodsinfo:info'))

    def test_create_oidc(self):
        """Test create_irods_user() as OIDC user"""
        group, _ = Group.objects.get_or_create(name=OIDC_USER_GROUP)
        group.user_set.add(self.user_new)
        self.assertEqual(
            AppAlert.objects.filter(alert_name=ALERT_NAME).count(), 0
        )
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(USER_NAME)
        with self.login(self.user_new):
            self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)
        self.assertEqual(
            AppAlert.objects.filter(alert_name=ALERT_NAME).count(), 1
        )
        alert = AppAlert.objects.filter(alert_name=ALERT_NAME).first()
        self.assertIn(OIDC_USER_PW_MSG, alert.message)
        self.assertEqual(alert.url, reverse('tokens:list'))

    def test_create_user_exists(self):
        """Test create_irods_user() as existing user"""
        self.irods.users.create(USER_NAME, 'rodsuser', settings.IRODS_ZONE)
        self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)
        with self.login(self.user_new):
            # No crash should happen
            self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_create_auth_disabled(self):
        """Test create_irods_user() with IRODS_SODAR_AUTH disabled"""
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(USER_NAME)
        with self.login(self.user_new):
            with self.assertRaises(UserDoesNotExist):
                self.irods.users.get(USER_NAME)
