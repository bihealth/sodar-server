"""Tests for UI view permissions in the samplesheets app"""

from urllib.parse import urlencode

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.utils import build_secret

from samplesheets.models import ISATab
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import IrodsAccessTicketMixin


app_settings = AppSettingAPI()


# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_SECRET = build_secret()
INVALID_SECRET = build_secret()


class TestSampleSheetsPermissions(
    SampleSheetIOMixin, IrodsAccessTicketMixin, TestProjectPermissionBase
):
    """Tests for general samplesheets view permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_project_sheets(self):
        """Test ProjectSheetsView permissions"""
        url = reverse(
            'samplesheets:project_sheets',
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
        self.assert_response(url, bad_users, 302)
        # Test public project
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_project_sheets_anon(self):
        """Test ProjectSheetsView with anonymous guest access"""
        self.project.set_public()
        url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.assert_response(url, self.anonymous, 200)

    def test_project_sheets_archive(self):
        """Test ProjectSheetsView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:project_sheets',
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
        self.assert_response(url, bad_users, 302)
        # Test public project
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_import(self):
        """Test SheetImportView permissions"""
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_import_anon(self):
        """Test SheetImportView with anonymous guest access"""
        self.project.set_public()
        url = reverse(
            'samplesheets:import',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_import_archive(self):
        """Test SheetImportView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_sheet_import_sync(self):
        """Test SheetImportView with sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )
        bad_users = [
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_sheet_import_sync_archive(self):
        """Test SheetImportView with sync enabled and archived project"""
        self.project.set_archive()
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )
        bad_users = [
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_sheet_template_select(self):
        """Test SheetTemplateSelectView permissions"""
        self.investigation.delete()
        url = reverse(
            'samplesheets:template_select',
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_template_select_anon(self):
        """Test SheetTemplateSelectView with anonymous guest access"""
        self.project.set_public()
        url = reverse(
            'samplesheets:template_select',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_template_select_archive(self):
        """Test SheetTemplateSelectView with archived project"""
        self.project.set_archive()
        self.investigation.delete()
        url = reverse(
            'samplesheets:template_select',
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_sheet_template_select_sync(self):
        """Test SheetTemplateSelectView with sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        url = reverse(
            'samplesheets:template_select',
            kwargs={'project': self.project.sodar_uuid},
        )
        bad_users = [
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_sheet_template_create(self):
        """Test SheetTemplateCreateView permissions"""
        self.investigation.delete()
        url = (
            reverse(
                'samplesheets:template_create',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?'
            + urlencode({'sheet_tpl': 'generic'})
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_template_create_anon(self):
        """Test SheetTemplateCreateView with anonymous guest access"""
        self.investigation.delete()
        url = (
            reverse(
                'samplesheets:template_create',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?'
            + urlencode({'sheet_tpl': 'generic'})
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_template_create_archive(self):
        """Test SheetTemplateCreateView with archived project"""
        self.project.set_archive()
        self.investigation.delete()
        url = (
            reverse(
                'samplesheets:template_create',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?'
            + urlencode({'sheet_tpl': 'generic'})
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_sheet_template_create_sync(self):
        """Test SheetTemplateCreateView with sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        url = (
            reverse(
                'samplesheets:template_create',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?'
            + urlencode({'sheet_tpl': 'generic'})
        )
        bad_users = [
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_sheet_export_excel_study(self):
        """Test SheetExcelExportView permissions for study table"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'study': self.study.sodar_uuid}
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_export_excel_study_anon(self):
        """Test Excel export for study table with anonymous guest access"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'study': self.study.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_export_excel_study_archive(self):
        """Test SheetExcelExportView for study table with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:export_excel', kwargs={'study': self.study.sodar_uuid}
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_export_excel_assay(self):
        """Test SheetExcelExportView permissions for assay table"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'assay': self.assay.sodar_uuid}
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_export_excel_assay_anon(self):
        """Test SheetExcelExportView with anonymous guest access"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'assay': self.assay.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_export_excel_assay_archive(self):
        """Test SheetExcelExportView for assay table with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:export_excel', kwargs={'assay': self.assay.sodar_uuid}
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_export_isa(self):
        """Test SheetISAExportView permissions"""
        url = reverse(
            'samplesheets:export_isa',
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_export_isa_anon(self):
        """Test SheetISAExportView with anonymous guest access"""
        url = reverse(
            'samplesheets:export_isa',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_export_isa_archive(self):
        """Test SheetISAExportView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:export_isa',
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_delete(self):
        """Test SheetDeleteView permissions"""
        url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_delete_anon(self):
        """Test SheetDeleteView with anonymous guest access"""
        url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_delete_archive(self):
        """Test SheetDeleteView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_version_list(self):
        """Test SheetVersionListView permissions"""
        url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_list_anon(self):
        """Test SheetVersionListView with anonymous guest access"""
        url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_version_list_archive(self):
        """Test SheetVersionListView permissions with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    def test_version_compare(self):
        """Test SheetVersionCompareView permissions"""
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:version_compare',
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_compare_anon(self):
        """Test SheetVersionCompareView with anonymous guest access"""
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:version_compare',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(isa.sodar_uuid),
            str(isa.sodar_uuid),
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_version_compare_archive(self):
        """Test SheetVersionCompareView with archived project"""
        self.project.set_archive()
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:version_compare',
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    def test_version_compare_file(self):
        """Test SheetVersionCompareFileView permissions"""
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}&filename={}&category={}'.format(
            reverse(
                'samplesheets:version_compare_file',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(isa.sodar_uuid),
            str(isa.sodar_uuid),
            's_small.txt',
            'studies',
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_compare_file_anon(self):
        """Test SheetVersionCompareFileView with anonymous guest access"""
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}&filename={}&category={}'.format(
            reverse(
                'samplesheets:version_compare_file',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(isa.sodar_uuid),
            str(isa.sodar_uuid),
            's_small.txt',
            'studies',
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_version_compare_file_archive(self):
        """Test SheetVersionCompareFileView with archived project"""
        self.project.set_archive()
        isa = ISATab.objects.first()
        url = '{}?source={}&target={}&filename={}&category={}'.format(
            reverse(
                'samplesheets:version_compare_file',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(isa.sodar_uuid),
            str(isa.sodar_uuid),
            's_small.txt',
            'studies',
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
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(url, self.anonymous, 302)

    def test_version_restore(self):
        """Test SheetVersionRestoreView permissions"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_restore',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_restore_anon(self):
        """Test SheetVersionRestoreView with anonymous guest access"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_restore',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_version_restore_archive(self):
        """Test SheetVersionRestoreView with archived project"""
        self.project.set_archive()
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_restore',
            kwargs={'isatab': isa_version.sodar_uuid},
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_version_update(self):
        """Test SheetVersionUpdateView permissions"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_update',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_update_anon(self):
        """Test SheetVersionUpdateView with anonymous guest access"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_update',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_version_update_archive(self):
        """Test SheetVersionUpdateView with archived project"""
        self.project.set_archive()
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_update',
            kwargs={'isatab': isa_version.sodar_uuid},
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_version_delete(self):
        """Test SheetVersionDeleteView permissions"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_delete_anon(self):
        """Test SheetVersionDeleteView with anonymous guest access"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_version_delete_archive(self):
        """Test SheetVersionDeleteView with archived project"""
        self.project.set_archive()
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete',
            kwargs={'isatab': isa_version.sodar_uuid},
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_version_delete_batch(self):
        """Test SheetVersionDeleteBatchView permissions"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete_batch',
            kwargs={'project': self.project.sodar_uuid},
        )
        data = {'confirm': '1', 'version_check': str(isa_version.sodar_uuid)}
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200, method='POST', data=data)
        self.assert_response(url, bad_users, 302, method='POST', data=data)
        self.project.set_public()
        self.assert_response(url, bad_users, 302, method='POST', data=data)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_delete_batch_anon(self):
        """Test SheetVersionDeleteBatchView with anonymous guest access"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete_batch',
            kwargs={'project': self.project.sodar_uuid},
        )
        data = {'confirm': '1', 'version_check': str(isa_version.sodar_uuid)}
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302, method='POST', data=data)

    def test_version_delete_batch_archive(self):
        """Test SheetVersionDeleteBatchView with archived project"""
        self.project.set_archive()
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete_batch',
            kwargs={'project': self.project.sodar_uuid},
        )
        data = {'confirm': '1', 'version_check': str(isa_version.sodar_uuid)}
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
        self.assert_response(url, good_users, 200, method='POST', data=data)
        self.assert_response(url, bad_users, 302, method='POST', data=data)
        self.project.set_public()
        self.assert_response(url, bad_users, 302, method='POST', data=data)


class TestIrodsAccessTicketPermissions(
    SampleSheetIOMixin, IrodsAccessTicketMixin, TestProjectPermissionBase
):
    """Tests for iRORDS access ticket view permissions"""

    def _make_ticket(self):
        """Make iRODS access ticket for testing"""
        self.ticket = self.make_irods_ticket(
            path='/sodarZone/some/path',
            study=self.study,
            assay=self.assay,
            user=self.user_owner,
        )

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_ticket_list(self):
        """Test IrodsAccessTicketListView permissions"""
        url = reverse(
            'samplesheets:irods_tickets',
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_list_anon(self):
        """Test IrodsAccessTicketListView with anonymous guest access"""
        url = reverse(
            'samplesheets:irods_tickets',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_ticket_list_archive(self):
        """Test IrodsAccessTicketListView with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:irods_tickets',
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_ticket_create(self):
        """Test IrodsAccessTicketCreateView permissions"""
        url = reverse(
            'samplesheets:irods_ticket_create',
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_create_anon(self):
        """Test IrodsAccessTicketCreateView with anonymous guest access"""
        url = reverse(
            'samplesheets:irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_ticket_create_archive(self):
        """Test IrodsAccessTicketCreateView with archived project"""
        # NOTE: Ticket creation should still be allowed
        self.project.set_archive()
        url = reverse(
            'samplesheets:irods_ticket_create',
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_ticket_update(self):
        """Test IrodsAccessTicketUpdateView permissions"""
        self._make_ticket()
        url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_update_anon(self):
        """Test IrodsAccessTicketUpdateView with anonymous guest access"""
        self._make_ticket()
        url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_ticket_update_archive(self):
        """Test IrodsAccessTicketUpdateView with archived project"""
        self._make_ticket()
        self.project.set_archive()
        url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
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
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    def test_ticket_delete(self):
        """Test IrodsAccessTicketDeleteView permissions"""
        self._make_ticket()
        url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
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
        self.assert_response(
            url, good_users, 200, cleanup_method=self._make_ticket
        )
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_delete_anon(self):
        """Test IrodsAccessTicketDeleteView with anonymous guest access"""
        self._make_ticket()
        url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_ticket_delete_archive(self):
        """Test IrodsAccessTicketDeleteView with archived project"""
        self._make_ticket()
        self.project.set_archive()
        url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
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
        self.assert_response(
            url, good_users, 200, cleanup_method=self._make_ticket
        )
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)
