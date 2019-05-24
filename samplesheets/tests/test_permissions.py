"""Tests for permissions in the samplesheets app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_models import (
    RemoteSiteMixin,
    RemoteProjectMixin,
    SODAR_CONSTANTS,
)
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.utils import build_secret

from .test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_SECRET = build_secret()
INVALID_SECRET = build_secret()


class TestSampleSheetsPermissions(
    SampleSheetIOMixin, TestProjectPermissionBase
):
    """Tests for samplesheets view permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_project_sheets(self):
        """Test the project sheets view"""
        url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_import(self):
        """Test the project sheets import view"""
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
        ]
        bad_users = [self.as_guest.user, self.anonymous, self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_export_tsv_study(self):
        """Test the project sheets TSV export view for study table"""
        url = reverse(
            'samplesheets:export_tsv', kwargs={'study': self.study.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
        ]
        bad_users = [self.as_guest.user, self.anonymous, self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_export_tsv_assay(self):
        """Test the project sheets TSV export view for assay table"""
        url = reverse(
            'samplesheets:export_tsv', kwargs={'assay': self.assay.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
        ]
        bad_users = [self.as_guest.user, self.anonymous, self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_delete(self):
        """Test the project sheets delete view"""
        url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
        ]
        bad_users = [self.as_guest.user, self.anonymous, self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_api_context(self):
        """Test SampleSheetContextGetAPIView"""
        url = reverse(
            'samplesheets:api_context_get',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200)
        self.assert_response(url, bad_users, status_code=403)

    def test_api_study_tables(self):
        """Test SampleSheetStudyTablesGetAPIView"""
        url = reverse(
            'samplesheets:api_study_tables_get',
            kwargs={'study': self.study.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200)
        self.assert_response(url, bad_users, status_code=403)

    def test_api_study_links(self):
        """Test SampleSheetStudyLinksGetAPIView"""
        url = reverse(
            'samplesheets:api_study_links_get',
            kwargs={'study': self.study.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=404)  # No plugin
        self.assert_response(url, bad_users, status_code=403)


class RemoteSheetGetAPIView(
    SampleSheetIOMixin,
    RemoteSiteMixin,
    RemoteProjectMixin,
    TestProjectPermissionBase,
):
    """Tests for RemoteSheetGetAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # No user
        self.anonymous = None

        # Create remote site
        self.target_site = self._make_site(
            name=REMOTE_SITE_NAME,
            url=REMOTE_SITE_URL,
            mode=SODAR_CONSTANTS['SITE_MODE_TARGET'],
            description='',
            secret=REMOTE_SITE_SECRET,
        )

    def test_view(self):
        """Test RemoteSheetGetAPIView with correct access"""

        # Create remote project
        self._make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES'],
        )

        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, [self.anonymous], 200)

    def test_view_invalid_access(self):
        """Test RemoteSheetGetAPIView with invalid access level"""

        # Create remote project
        self._make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_VIEW_AVAIL'],
        )

        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, [self.anonymous], 401)

    def test_view_no_access(self):
        """Test RemoteSheetGetAPIView with no remote access rights"""

        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, [self.anonymous], 401)

    def test_view_invalid_secret(self):
        """Test RemoteSheetGetAPIView with invalid remote site secret"""

        # Create remote project
        self._make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_VIEW_AVAIL'],
        )

        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': INVALID_SECRET,
            },
        )
        self.assert_response(url, [self.anonymous], 401)
