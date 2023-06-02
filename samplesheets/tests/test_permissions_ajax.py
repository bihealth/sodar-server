"""Tests for Ajax API View permissions in the samplesheets app"""

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.utils import build_secret

from samplesheets.models import ISATab
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


app_settings = AppSettingAPI()


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_SECRET = build_secret()
INVALID_SECRET = build_secret()


class TestSampleSheetsAjaxPermissions(
    SampleSheetIOMixin, TestProjectPermissionBase
):
    """Tests for samplesheets Ajax view permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_context(self):
        """Test SheetContextAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_context',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        # Test public project
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_context_anon(self):
        """Test SheetContextAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_context',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_context_archive(self):
        """Test SheetContextAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_context',
            kwargs={'project': self.project.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        # Test public project
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 403)

    def test_study_tables(self):
        """Test StudyTablesAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_study_tables_anon(self):
        """Test StudyTablesAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_study_tables_archive(self):
        """Test StudyTablesAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 403)

    def test_study_tables_edit(self):
        """Test StudyTablesAjaxView with edit mode"""
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        get_data = {'edit': 1}
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, data=get_data)
        self.assert_response(url, bad_users, 403, data=get_data)
        self.project.set_public()
        self.assert_response(url, bad_users, 403, data=get_data)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_study_tables_edit_anon(self):
        """Test StudyTablesAjaxView with edit mode and anon access"""
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        get_data = {'edit': 1}
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403, data=get_data)

    def test_study_tables_edit_archive(self):
        """Test StudyTablesAjaxView with edit mode and archived project"""
        self.project.set_archive()
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        get_data = {'edit': 1}
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, data=get_data)
        self.assert_response(url, bad_users, 403, data=get_data)
        self.project.set_public()
        self.assert_response(url, bad_users, 403, data=get_data)

    def test_study_tables_not_allowed(self):
        """Test StudyTablesAjaxView with edit mode but disallowed"""
        app_settings.set(
            'samplesheets', 'allow_editing', False, project=self.project
        )
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        get_data = {'edit': 1}
        users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, users, 403, data=get_data)
        self.project.set_public()
        self.assert_response(url, users, 403, data=get_data)

    def test_study_tables_not_allowed_archive(self):
        """Test StudyTablesAjaxView with disallowed edit mode and archived project"""
        self.project.set_archive()
        app_settings.set(
            'samplesheets', 'allow_editing', False, project=self.project
        )
        url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        get_data = {'edit': 1}
        users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, users, 403, data=get_data)
        self.project.set_public()
        self.assert_response(url, users, 403, data=get_data)

    def test_study_links(self):
        """Test StudyLinksAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_study_links',
            kwargs={'study': self.study.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 404)  # No plugin
        self.assert_response(url, bad_users, 403)

    def test_study_links_archive(self):
        """Test StudyLinksAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_study_links',
            kwargs={'study': self.study.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 404)  # No plugin
        self.assert_response(url, bad_users, 403)

    def test_sheet_warnings(self):
        """Test SheetWarningsAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_warnings',
            kwargs={'project': self.project.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_warnings_anon(self):
        """Test SampleSheetWarningsAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_warnings',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_warnings_archive(self):
        """Test SheetWarningsAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_warnings',
            kwargs={'project': self.project.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 403)

    def test_cell_edit(self):
        """Test SheetCellEditAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_edit_cell',
            kwargs={'project': self.project.sodar_uuid},
        )
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_cell_edit_anon(self):
        """Test SheetCellEditAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_edit_cell',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403, method='POST')

    def test_cell_edit_archive(self):
        """Test SheetCellEditAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_edit_cell',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    def test_row_insert(self):
        """Test SheetRowInsertAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_edit_row_insert',
            kwargs={'project': self.project.sodar_uuid},
        )
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_row_insert_anon(self):
        """Test SheetRowInsertAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_edit_row_insert',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403, method='POST')

    def test_row_insert_archive(self):
        """Test SheetRowInsertAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_edit_row_insert',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    def test_row_delete(self):
        """Test SheetRowDeleteAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_edit_row_delete',
            kwargs={'project': self.project.sodar_uuid},
        )
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_row_delete_anon(self):
        """Test SheetRowDeleteAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_edit_row_delete',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403, method='POST')

    def test_row_delete_archive(self):
        """Test SheetRowDeleteAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_edit_row_delete',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    def test_version_save(self):
        """Test SheetVersionSaveAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_version_save',
            kwargs={'project': self.project.sodar_uuid},
        )
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_save_anon(self):
        """Test SheetVersionSaveAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_version_save',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403, method='POST')

    def test_version_save_archive(self):
        """Test SheetVersionSaveAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_version_save',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    def test_edit_finish(self):
        """Test SheetEditFinishAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_edit_finish',
            kwargs={'project': self.project.sodar_uuid},
        )
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_edit_finish_anon(self):
        """Test SheetEditFinishAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_edit_finish',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403, method='POST')

    def test_edit_finish_archive(self):
        """Test SheetEditFinishAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_edit_finish',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    def test_edit_config(self):
        """Test SheetEditConfigAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_config_update',
            kwargs={'project': self.project.sodar_uuid},
        )
        # TODO: Set up request data
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
            self.anonymous,
        ]
        self.assert_response(url, good_users, 400, method='POST')  # No fields
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_edit_config_anon(self):
        """Test SheetEditConfigAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_config_update',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 403, method='POST')

    def test_edit_config_archive(self):
        """Test SheetEditConfigAjaxView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_config_update',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 400, method='POST')  # No fields
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, bad_users, 403, method='POST')

    def test_display_config(self):
        """Test StudyDisplayConfigAjaxView permissions"""
        url = reverse(
            'samplesheets:ajax_display_update',
            kwargs={'study': self.study.sodar_uuid},
        )
        # TODO: Set up request data
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 400, method='POST')  # No config
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, self.user_guest, 400, method='POST')
        self.assert_response(url, self.anonymous, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_display_config_anon(self):
        """Test StudyDisplayConfigAjaxView with anonymous guest access"""
        url = reverse(
            'samplesheets:ajax_display_update',
            kwargs={'study': self.study.sodar_uuid},
        )
        # TODO: Set up request data
        self.project.set_public()
        self.assert_response(url, self.anonymous, 400, method='POST')

    def test_display_config_archive(self):
        """Test StudyDisplayConfigAjaxView with archived project"""
        # NOTE: This is allowed with archived projects
        self.project.set_archive()
        url = reverse(
            'samplesheets:ajax_display_update',
            kwargs={'study': self.study.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 400, method='POST')  # No config
        self.assert_response(url, bad_users, 403, method='POST')
        self.project.set_public()
        self.assert_response(url, self.user_guest, 400, method='POST')
        self.assert_response(url, self.anonymous, 403, method='POST')

    # TODO: Test IrodsRequestCreateAjaxView (see sodar_core#823)
    # TODO: Test IrodsRequestDeleteAjaxView (see sodar_core#823)

    def test_version_compare(self):
        """Test SheetVersionCompareAjaxView permissions"""
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:ajax_version_compare',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(isa.sodar_uuid),
            str(isa.sodar_uuid),
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_compare_anon(self):
        """Test SheetVersionCompareAjaxView with anonymous guest access"""
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:ajax_version_compare',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(isa.sodar_uuid),
            str(isa.sodar_uuid),
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_version_compare_archive(self):
        """Test SheetVersionCompareAjaxView with archived project"""
        self.project.set_archive()
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:ajax_version_compare',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(isa.sodar_uuid),
            str(isa.sodar_uuid),
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
        self.project.set_public()
        self.assert_response(url, [self.user_no_roles], 200)
        self.assert_response(url, [self.anonymous], 403)
