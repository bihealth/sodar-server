"""Signals tests for the irodsbackend app"""

from irods.exception import CollectionDoesNotExist, UserDoesNotExist
from irods.models import UserGroup
from irods.user import iRODSUser

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from test_plus import TestCase

# Projectroles dependency
from projectroles.plugins import get_backend_api

from irodsbackend.api import IrodsAPI


USER_NAME = 'test_user'


class TestCreateIrodsUser(TestCase):
    """Test the create_irods_user signal"""

    def setUp(self):
        # Ensure TASKFLOW_TEST_MODE is True to avoid data loss
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, testing with SODAR Taskflow '
                'disabled'
            )
        self.taskflow = get_backend_api('taskflow', force=True)
        self.user = self.make_user(USER_NAME)
        self.irods_backend = IrodsAPI()
        self.irods = self.irods_backend.get_session_obj()

    def tearDown(self):
        self.taskflow.cleanup()
        with self.assertRaises(CollectionDoesNotExist):
            self.irods.collections.get(self.irods_backend.get_projects_path())
        for user in self.irods.query(UserGroup).all():
            self.assertIn(
                user[UserGroup.name], settings.TASKFLOW_TEST_PERMANENT_USERS
            )
        self.irods.cleanup()
        super().tearDown()

    def test_create(self):
        """Test create_irods_user by logging in"""
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(USER_NAME)
        with self.login(self.user):
            self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)

    def test_create_user_exists(self):
        """Test create_irods_user with an existing user"""
        self.irods.users.create(USER_NAME, 'rodsuser', settings.IRODS_ZONE)
        self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)
        with self.login(self.user):
            # No crash should happen
            self.assertIsInstance(self.irods.users.get(USER_NAME), iRODSUser)

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_create_auth_disabled(self):
        """Test create_irods_user with IRODS_SODAR_AUTH disabled"""
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(USER_NAME)
        with self.login(self.user):
            with self.assertRaises(UserDoesNotExist):
                self.irods.users.get(USER_NAME)
