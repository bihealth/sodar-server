"""Tests for permissions in the landingzones app"""

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_permissions import TestProjectPermissionBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from .test_models import LandingZoneMixin, ZONE_TITLE, ZONE_DESC


# Global constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestLandingZonePermissions(
        TestProjectPermissionBase, LandingZoneMixin, SampleSheetIOMixin):
    """Tests for LandingZone views"""

    def setUp(self):
        super(TestLandingZonePermissions, self).setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create LandingZone
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={})

    def test_zone_list(self):
        """Test permissions for the project landing zone list"""
        url = reverse(
            'landingzones:list',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user]
        bad_users = [
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_zone_create(self):
        """Test permissions for landing zone creation"""
        url = reverse(
            'landingzones:create',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user]
        bad_users = [
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_zone_delete(self):
        """Test permissions for landing zone deletion"""
        url = reverse(
            'landingzones:delete',
            kwargs={'landingzone': self.landing_zone.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the zone
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_zone_status(self):
        """Test permissions for landing zone status"""
        url = reverse(
            'landingzones:status',
            kwargs={'landingzone': self.landing_zone.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the zone
            self.user_no_roles]
        redirect_users = [
            self.anonymous]
        self.assert_render200_ok(url, good_users)
        self.assert_response(url, bad_users, 403)
        self.assert_redirect(url, redirect_users)
