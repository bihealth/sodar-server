"""Tests for permissions in the irodsbackend app"""

from django.test import override_settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin

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
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Set up test paths
        self.project_path = self.irods_backend.get_path(self.project)
        self.sample_path = self.irods_backend.get_sample_path(self.project)


class TestIrodsStatisticsAjaxView(
    LandingZoneMixin, LandingZoneTaskflowMixin, IrodsbackendPermissionsTestBase
):
    """Tests for IrodsStatisticsAjaxView permissions"""

    def setUp(self):
        super().setUp()
        self.url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.sample_path
        )
        self.good_users = [
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
        self.bad_users = [
            self.user_viewer_cat,  # Inherited
            self.user_finder_cat,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]

    def test_get(self):
        """Test IrodsStatisticsAjaxView GET"""
        self.assert_response(self.url, self.good_users, 200)
        self.assert_response(self.url, self.bad_users, 403)
        self.project.set_public_access(self.role_guest)
        self.assert_response(self.url, self.user_no_roles, 200)
        self.assert_response(self.url, self.anonymous, 403)
        self.project.set_public_access(self.role_viewer)
        self.assert_response(self.url, self.no_role_users, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public_access(self.role_guest)
        self.assert_response(self.url, self.anonymous, 200)
        self.project.set_public_access(self.role_viewer)
        self.assert_response(self.url, self.anonymous, 403)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users, 200)
        self.assert_response(self.url, self.bad_users, 403)
        self.project.set_public_access(self.role_guest)
        self.assert_response(self.url, self.user_no_roles, 200)
        self.assert_response(self.url, self.anonymous, 403)
        self.project.set_public_access(self.role_viewer)
        self.assert_response(self.url, self.no_role_users, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon_no_perms(self):
        """Test GET with anonymous access and no collection perms"""
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.project_path
        )
        self.project.set_public_access(self.role_guest)
        self.assert_response(url, self.anonymous, 403)
        self.project.set_public_access(self.role_viewer)
        self.assert_response(url, self.anonymous, 403)

    def test_get_not_in_project(self):
        """Test GET with path not in project"""
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=NON_PROJECT_PATH
        )
        self.assert_response(url, self.all_users, 400)

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
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_viewer,
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
        bad_users = [
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(
            url, good_users, 200, method='POST', data=post_data
        )
        self.assert_response(url, bad_users, 403, method='POST', data=post_data)

    def test_get_landing_zone(self):
        """Test GET with landing zone collection"""
        zone = self.make_landing_zone(
            title='20240611_135942',
            project=self.project,
            user=self.user_contributor,
            assay=self.assay,
            description='description',
            configuration=None,
            config_data={},
        )
        self.make_zone_taskflow(zone)
        url = self.irods_backend.get_url(
            view='stats',
            project=self.project,
            path=self.irods_backend.get_path(zone),
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public_access(self.role_guest)
        self.assert_response(url, self.bad_users, 403)
        self.project.set_public_access(self.role_viewer)
        self.assert_response(url, self.bad_users, 403)
