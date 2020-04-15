"""Tests for Ajax API View permissions in the samplesheets app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.utils import build_secret

from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


# App settings API
app_settings = AppSettingAPI()


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_SECRET = build_secret()
INVALID_SECRET = build_secret()


# TODO: Update to match sodar_core v0.8 conventions


class TestSampleSheetsAjaxPermissions(
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

    def test_api_study_tables(self):
        """Test SampleSheetStudyTablesAjaxView"""
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
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

    def test_api_study_tables_edit(self):
        """Test SampleSheetStudyTablesAjaxView with edit mode enabled"""
        app_settings.set_app_setting(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        get_data = {'edit': 1}
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200, data=get_data)
        self.assert_response(url, bad_users, status_code=403, data=get_data)

    def test_api_study_tables_not_allowed(self):
        """Test SampleSheetStudyTablesAjaxView with edit mode enabled but disallowed"""
        app_settings.set_app_setting(
            'samplesheets', 'allow_editing', False, project=self.project
        )
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        get_data = {'edit': 1}
        users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
            self.anonymous,
            self.user_no_roles,
        ]
        self.assert_response(url, users, status_code=403, data=get_data)

    def test_api_study_links(self):
        """Test SampleSheetStudyLinksAjaxView"""
        url = reverse(
            'samplesheets:ajax_study_links',
            kwargs={'study': self.study.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=404)  # No plugin
        self.assert_response(url, bad_users, status_code=403)

    def test_ajax_edit(self):
        """Test SampleSheetEditAjaxView"""
        url = reverse(
            'samplesheets:ajax_edit',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200, method='POST')
        self.assert_response(url, bad_users, status_code=403, method='POST')

    def test_ajax_edit_finish(self):
        """Test SampleSheetEditFinishAjaxView"""
        url = reverse(
            'samplesheets:ajax_edit_finish',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200, method='POST')
        self.assert_response(url, bad_users, status_code=403, method='POST')

    def test_sheet_warnings(self):
        """Test SampleSheetWarningsAjaxView"""
        url = reverse(
            'samplesheets:ajax_warnings',
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
