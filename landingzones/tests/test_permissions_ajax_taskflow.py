"""Tests for Ajax API view permissions in the landingzones app with Taskflow"""

from django.test import override_settings
from django.urls import reverse

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowPermissionTestBase

from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20190703_172456'


class TestZoneIrodsListRetrieveAjaxView(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    TaskflowPermissionTestBase,
):
    """Tests for ZoneIrodsListRetrieveAjaxView permissions"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create LandingZone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,
            assay=self.assay,
            description='Description',
            configuration=None,
            config_data={},
        )
        # Create zone and file in taskflow
        self.make_zone_taskflow(self.zone)
        self.zone_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.zone)
        )
        self.url = reverse(
            'landingzones:ajax_irods_list',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )
        self.good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited
            self.user_delegate_cat,  # Inherited
            self.user_owner,
            self.user_delegate,
            self.user_contributor,  # Zone owner
        ]
        self.bad_users = [
            self.user_guest_cat,  # Inherited
            self.user_finder_cat,  # Inherited
            self.user_contributor_cat,  # Inherited, no access to zone
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]

    def test_get(self):
        """Test ZoneIrodsListRetrieveAjaxView GET"""
        self.assert_response(self.url, self.good_users, 200)
        self.assert_response(self.url, self.bad_users, 403)
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users, 200)
        self.assert_response(self.url, self.bad_users, 403)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users, 200)
        self.assert_response(self.url, self.bad_users, 403)
