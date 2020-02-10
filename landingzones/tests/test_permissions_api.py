"""Tests for REST API view permissions in the landingzones app"""

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
    LandingZoneMixin, SampleSheetIOMixin, TestProjectPermissionBase
):
    """Tests for landingzones REST API view permissions"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create LandingZone for project owner
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )

    def test_list(self):
        """Test permissions for LandingZoneListAPIView"""
        url = reverse(
            'landingzones:api_list', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
        ]
        bad_users = [self.as_guest.user, self.user_no_roles, self.anonymous]

        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_retrieve(self):
        """Test permissions for LandingZoneRetrieveAPIView"""
        url = reverse(
            'landingzones:api_retrieve',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
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

    # TODO: How to nicely test taskflow submitting API view permissions?
