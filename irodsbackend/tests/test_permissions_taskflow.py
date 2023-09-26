"""Tests for permissions in the irodsbackend app"""

from django.test import override_settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowPermissionTestBase


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_NAME = 'i_small.zip'
SHEET_PATH = SHEET_DIR + SHEET_NAME
TEST_COLL_NAME = 'test_coll'
TEST_FILE_NAME = 'test1'
NON_PROJECT_PATH = '/sodarZone/projects'


class IrodsbackendPermissionsTestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowPermissionTestBase,
):
    """Base class for irodsbackend API view permission tests"""

    def setUp(self):
        super().setUp()
        # Set up investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Set up test paths
        self.project_path = self.irods_backend.get_path(self.project)
        self.sample_path = self.irods_backend.get_sample_path(self.project)


class TestIrodsStatisticsAjaxView(IrodsbackendPermissionsTestBase):
    """Tests for IrodsStatisticsAjaxView permissions"""

    def setUp(self):
        super().setUp()
        self.url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.sample_path
        )

    def test_get(self):
        """Test IrodsStatisticsAjaxView GET"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited
            self.user_delegate_cat,  # Inherited
            self.user_contributor_cat,  # Inherited
            self.user_guest_cat,  # Inherited
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 200)
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 200)
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon_no_perms(self):
        """Test GET with anonymous access and no collection perms"""
        self.project.set_public()
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.project_path
        )
        self.assert_response(url, self.anonymous, 403)

    def test_get_not_in_project(self):
        """Test GET with path not in project"""
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=NON_PROJECT_PATH
        )
        bad_users = [
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
            self.anonymous,
        ]
        self.assert_response(url, bad_users, 400)

    def test_get_no_perms(self):
        """Test GET without collection perms"""
        test_path = self.project_path + '/' + TEST_COLL_NAME
        self.irods.collections.create(test_path)  # NOTE: No perms given
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=test_path
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_post(self):
        """Test POST"""
        url = self.irods_backend.get_url(
            view='stats',
            project=self.project,
            path=self.sample_path,
            method='POST',
        )
        post_data = {'paths': [self.sample_path]}
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(
            url, good_users, 200, method='POST', data=post_data
        )
        self.assert_response(url, bad_users, 403, method='POST', data=post_data)


class TestIrodsObjectListAjaxView(IrodsbackendPermissionsTestBase):
    """Tests for IrodsObjectListAjaxView permissions"""

    def setUp(self):
        super().setUp()
        self.url = self.irods_backend.get_url(
            view='list', project=self.project, path=self.sample_path, md5=0
        )

    def test_get(self):
        """Test IrodsObjectListAjaxView GET"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 200)
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 403)
        self.project.set_public()
        self.assert_response(self.url, self.user_no_roles, 200)
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon_no_perms(self):
        """Test GET with anonymous access and no permission"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=self.project_path, md5=0
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403)

    def test_get_not_in_project(self):
        """Test GET with path not in project"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=NON_PROJECT_PATH, md5=0
        )
        bad_users = [
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
            self.anonymous,
        ]
        self.assert_response(url, bad_users, 400)

    def test_get_no_perms(self):
        """Test GET without collection perms"""
        test_path = self.project_path + '/' + TEST_COLL_NAME
        self.irods.collections.create(test_path)  # NOTE: No perms given
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=test_path, md5=0
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
