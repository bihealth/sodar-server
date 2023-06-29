"""Signals tests for the irodsbackend app"""

from irods.exception import UserDoesNotExist
from irods.user import iRODSUser

from django.conf import settings
from django.test import override_settings

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase


USER_NAME = 'test_user'


class TestCreateIrodsUser(TaskflowViewTestBase):
    """Tests for create_irods_user signal"""

    def setUp(self):
        super().setUp()
        self.user_new = self.make_user(USER_NAME)

    def test_create(self):
        """Test create_irods_user by logging in"""
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(USER_NAME)
        with self.login(self.user_new):
            self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)

    def test_create_user_exists(self):
        """Test create_irods_user with an existing user"""
        self.irods.users.create(USER_NAME, 'rodsuser', settings.IRODS_ZONE)
        self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)
        with self.login(self.user_new):
            # No crash should happen
            self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_create_auth_disabled(self):
        """Test create_irods_user with IRODS_SODAR_AUTH disabled"""
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(USER_NAME)
        with self.login(self.user_new):
            with self.assertRaises(UserDoesNotExist):
                self.irods.users.get(USER_NAME)
