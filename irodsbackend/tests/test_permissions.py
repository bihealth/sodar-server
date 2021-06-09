"""Tests for permissions in the irodsbackend app"""

from django.conf import settings
from django.test import override_settings

from unittest import skipIf

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_permissions import TestPermissionMixin
from projectroles.tests.test_views_taskflow import TestTaskflowBase

# Samplesheets dependency
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
)
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_NAME = 'i_small.zip'
SHEET_PATH = SHEET_DIR + SHEET_NAME
TEST_COLL_NAME = 'test_coll'
TEST_FILE_NAME = 'test1'
NON_PROJECT_PATH = '/omicsZone/projects'
BACKENDS_ENABLED = all(
    _ in settings.ENABLED_BACKEND_PLUGINS for _ in ['omics_irods', 'taskflow']
)
BACKEND_SKIP_MSG = (
    'Required backends (taskflow, omics_irods) ' 'not enabled in settings'
)


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsbackendPermissions(
    TestPermissionMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TestTaskflowBase,
):
    """Tests for irodsbackend API view permissions"""

    def setUp(self):
        super().setUp()

        # Init users
        self.superuser = self.user  # HACK
        self.anonymous = None
        self.user_owner = self.make_user('user_owner')
        self.user_delegate = self.make_user('user_delegate')
        self.user_contributor = self.make_user('user_contributor')
        self.user_guest = self.make_user('user_guest')
        self.user_no_roles = self.make_user('user_no_roles')

        # Set up project with taskflow
        self.project, self.as_owner = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner,
            description='description',
        )

        # Set up assignments with taskflow
        self.as_delegate = self._make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self.as_contributor = self._make_assignment_taskflow(
            self.project, self.user_contributor, self.role_contributor
        )
        self.as_guest = self._make_assignment_taskflow(
            self.project, self.user_guest, self.role_guest
        )

        # Set up investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        # Set up irodsbackend
        self.irods_backend = get_backend_api('omics_irods')
        self.irods_session = self.irods_backend.get_session()

        # Set up test paths
        self.project_path = self.irods_backend.get_path(self.project)
        self.sample_path = self.irods_backend.get_sample_path(self.project)

    def tearDown(self):
        if self.irods_session:
            self.irods_session.cleanup()
        super().tearDown()

    def test_stats_get(self):
        """Test stats API view GET"""
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.sample_path
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_stats_get_anon(self):
        """Test stats API view with anonymous access"""
        self.project.set_public()
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.sample_path
        )
        self.assert_response(url, self.anonymous, 200)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_stats_get_anon_no_perms(self):
        """Test stats API view with anonymous access and no perms to collection"""
        self.project.set_public()
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.project_path
        )
        self.assert_response(url, self.anonymous, 403)

    def test_stats_get_not_in_project(self):
        """Test stats API view GET with path not in project"""
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=NON_PROJECT_PATH
        )
        bad_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, bad_users, 400)

    def test_stats_get_no_perms(self):
        """Test stats API view GET without collection perms"""
        test_path = self.project_path + '/' + TEST_COLL_NAME
        self.irods_session.collections.create(test_path)  # NOTE: No perms given

        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=test_path
        )
        good_users = [self.superuser, self.as_owner.user, self.as_delegate.user]
        bad_users = [
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_stats_post(self):
        """Test stats API view POST"""
        url = self.irods_backend.get_url(
            view='stats',
            project=self.project,
            path=self.sample_path,
            method='POST',
        )
        post_data = {'paths': [self.sample_path]}

        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(
            url, good_users, 200, method='POST', data=post_data
        )
        self.assert_response(url, bad_users, 403, method='POST', data=post_data)

    def test_list_get(self):
        """Test object list API view GET"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=self.sample_path, md5=0
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_list_get_anon(self):
        """Test object list API view GET with anonymous access"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=self.sample_path, md5=0
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_list_get_anon_no_perms(self):
        """Test object list API view GET with anonymous access and no permission"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=self.project_path, md5=0
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403)

    def test_list_get_not_in_project(self):
        """Test object list GET with path not in project"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=NON_PROJECT_PATH, md5=0
        )
        bad_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, bad_users, 400)

    def test_list_get_no_perms(self):
        """Test object list GET without collection perms"""
        test_path = self.project_path + '/' + TEST_COLL_NAME
        self.irods_session.collections.create(test_path)  # NOTE: No perms given

        url = self.irods_backend.get_url(
            view='list', project=self.project, path=test_path, md5=0
        )
        good_users = [self.superuser, self.as_owner.user, self.as_delegate.user]
        bad_users = [
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
