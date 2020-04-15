"""Tests for UI view permissions in the samplesheets app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.utils import build_secret

from samplesheets.models import ISATab
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


# App settings API
app_settings = AppSettingAPI()


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
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_sheet_import(self):
        """Test the project sheets import view"""
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_sheet_export_excel_study(self):
        """Test the project sheets Excel export view for study table"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'study': self.study.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_sheet_export_excel_assay(self):
        """Test the project sheets Excel export view for assay table"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'assay': self.assay.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_sheet_export_isa(self):
        """Test the project sheets ISA export view"""
        url = reverse(
            'samplesheets:export_isa',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_sheet_delete(self):
        """Test the project sheets delete view"""
        url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_version_list(self):
        """Test the sheet version list view"""
        url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_version_restore(self):
        """Test the sheet restoring view"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_restore',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        good_users = [self.superuser, self.owner_as.user, self.delegate_as.user]
        bad_users = [
            self.contributor_as.user,
            self.guest_as.user,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_version_delete(self):
        """Test the sheet delete view"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        good_users = [self.superuser, self.owner_as.user, self.delegate_as.user]
        bad_users = [
            self.contributor_as.user,
            self.guest_as.user,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)

    def test_api_context(self):
        """Test SampleSheetContextAjaxView"""
        url = reverse(
            'samplesheets:ajax_context',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200)
        self.assert_response(url, bad_users, status_code=403)
