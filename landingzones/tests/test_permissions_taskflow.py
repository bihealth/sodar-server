"""Tests for UI view permissions with taskflow"""

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowPermissionTestBase

from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TEST_OBJ_NAME = 'test1.txt'


class ZonePermissionTaskflowTestBase(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    TaskflowPermissionTestBase,
):
    """Base view for landingzones permissions tests with taskflow"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create LandingZone
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,  # NOTE: owner = user_contributor
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        # Create zone and file in taskflow
        self.make_zone_taskflow(self.landing_zone)
        self.zone_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.landing_zone)
        )
        self.irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_irods_md5_object(self.irods_obj)


class TestZoneMoveView(ZonePermissionTaskflowTestBase):
    """Tests for ZoneMoveView permissions with taskflow"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:move',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneMoveView GET"""
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
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 302)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_disable(self):
        """Test GET with disabled non-superuser access"""
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)
