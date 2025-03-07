"""Tests for Ajax API view permissions in the landingzones app"""

from django.test import override_settings
from django.urls import reverse

# Samplesheets dependency
from samplesheets.tests.test_io import SHEET_DIR

from landingzones.tests.test_models import ZONE_TITLE, ZONE_DESC
from landingzones.tests.test_permissions import LandingzonesPermissionTestBase


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestZoneStatusRetrieveAjaxViewPermissions(LandingzonesPermissionTestBase):
    """Tests for ZoneStatusRetrieveAjaxView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,  # NOTE: Zone owner = user_contributor
            assay=self.assay,
            description=ZONE_DESC,
            status='ACTIVE',
            configuration=None,
            config_data={},
        )
        self.url = reverse(
            'landingzones:ajax_status',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {'zone_uuids': [str(zone.sodar_uuid)]}
        self.good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,  # Zone owner
        ]
        self.bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]

    def test_post(self):
        """Test ZoneStatusRetrieveAjaxView POST"""
        self.assert_response(
            self.url, self.good_users, 200, method='post', data=self.post_data
        )
        self.assert_response(
            self.url, self.bad_users, 403, method='post', data=self.post_data
        )
        self.project.set_public()
        self.assert_response(
            self.url,
            self.no_role_users,
            403,
            method='post',
            data=self.post_data,
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous access"""
        self.project.set_public()
        self.assert_response(
            self.url, self.anonymous, 403, method='post', data=self.post_data
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(
            self.url, self.good_users, 200, method='post', data=self.post_data
        )
        self.assert_response(
            self.url, self.bad_users, 403, method='post', data=self.post_data
        )
        self.project.set_public()
        self.assert_response(
            self.url,
            self.no_role_users,
            403,
            method='post',
            data=self.post_data,
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(
            self.url, self.good_users, 200, method='post', data=self.post_data
        )
        self.assert_response(
            self.url, self.bad_users, 403, method='post', data=self.post_data
        )
