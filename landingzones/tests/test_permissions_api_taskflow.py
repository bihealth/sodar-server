"""Tests for landingzones REST API view permissions with taskflow"""

import time

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import PermissionTestMixin
from projectroles.utils import build_secret

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowAPIPermissionTestBase

from landingzones.constants import (
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_PREPARING,
)
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import (
    LandingZoneTaskflowMixin,
    ZONE_TITLE,
    ZONE_DESC,
)
from landingzones.views_api import (
    LANDINGZONES_API_MEDIA_TYPE,
    LANDINGZONES_API_DEFAULT_VERSION,
)


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class ZoneAPIPermissionTaskflowTestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    PermissionTestMixin,
    TaskflowAPIPermissionTestBase,
):
    """Base class for landing zone permission tests with Taskflow"""

    media_type = LANDINGZONES_API_MEDIA_TYPE
    api_version = LANDINGZONES_API_DEFAULT_VERSION

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)


class TestZoneCreateAPIViewPermissions(ZoneAPIPermissionTaskflowTestBase):
    """Tests for ZoneCreateAPIView permissions with Taskflow"""

    def _get_post_data(self):
        return {
            'assay': str(self.assay.sodar_uuid),
            'description': ZONE_DESC,
            'title': build_secret(32),  # NOTE: Random string to avoid cleanup
            'user_message': 'user message',
            'configuration': '',
            'config_data': {},
        }

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:api_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test ZoneCreateAPIView POST"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(
            self.url, good_users, 201, method='POST', data=self._get_post_data()
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='POST', data=self._get_post_data()
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            good_users,
            201,
            method='POST',
            data=self._get_post_data(),
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
            data=self._get_post_data(),
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self._get_post_data(),
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='POST',
            data=self._get_post_data(),
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
            data=self._get_post_data(),
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self._get_post_data(),
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self._get_post_data(),
        )

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_post_disable(self):
        """Test POST with disabled non-superuser access"""
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self._get_post_data(),
        )
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='POST',
            data=self._get_post_data(),
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
            data=self._get_post_data(),
        )


class TestZoneSubmitDeleteAPIViewPermissions(ZoneAPIPermissionTaskflowTestBase):
    """Tests for ZoneSubmitDeleteAPIView permissions with Taskflow"""

    def _cleanup(self):
        self.landing_zone.status = ZONE_STATUS_ACTIVE
        self.landing_zone.save()

    def setUp(self):
        super().setUp()
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,  # NOTE: Contributor is owner
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.make_zone_taskflow(self.landing_zone)
        self.url = reverse(
            'landingzones:api_submit_delete',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        self.good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        self.bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]

    def test_post(self):
        """Test ZoneSubmitDeleteAPIView POST"""
        self.assert_response_api(
            self.url,
            self.good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.bad_users,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        # NOTE: Should still be allowed
        self.project.set_archive()
        self.assert_response_api(
            self.url,
            self.good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.bad_users,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        # NOTE: Unlike archive mode, we don't allow this
        self.set_site_read_only()
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_post_disable(self):
        """Test POST with disabled non-superuser access"""
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
        )


class TestZoneSubmitMoveAPIViewPermissions(ZoneAPIPermissionTaskflowTestBase):
    """Tests for ZoneSubmitMoveAPIView permissions with Taskflow"""

    # NOTE: Using validate_only in tests, perms are identical to move

    def _cleanup(self):
        self.landing_zone.refresh_from_db()
        retry_count = 0
        # Wait for async activity to finish
        while (
            self.landing_zone.status
            in [ZONE_STATUS_PREPARING, ZONE_STATUS_VALIDATING]
            and retry_count < 5
        ):
            time.sleep(1)
            self.landing_zone.refrsh_from_db()
            retry_count += 1
        if self.landing_zone.status != ZONE_STATUS_ACTIVE:
            self.landing_zone.status = ZONE_STATUS_ACTIVE
            self.landing_zone.save()

    def setUp(self):
        super().setUp()
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,  # NOTE: Contributor is owner
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.make_zone_taskflow(self.landing_zone)
        self.url = reverse(
            'landingzones:api_submit_validate',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )

    def test_post(self):
        """Test ZoneSubmitMoveAPIView POST"""
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
        ]
        self.assert_response_api(
            self.url,
            good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            bad_users,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        # NOTE: We don't allow move OR validate for archived projects
        self.project.set_archive()
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_post_disable(self):
        """Test POST with disabled non-superuser access"""
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
        )
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
            knox=True,
        )
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.user_no_roles,
            403,
            method='POST',
        )
