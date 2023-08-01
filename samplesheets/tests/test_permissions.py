"""Tests for UI view permissions in the samplesheets app"""

from urllib.parse import urlencode

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.utils import build_secret

from samplesheets.models import (
    ISATab,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import (
    IrodsAccessTicketMixin,
    IrodsDataRequestMixin,
)


app_settings = AppSettingAPI()


# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_SECRET = build_secret()
INVALID_SECRET = build_secret()
IRODS_TICKET_PATH = '/sodarZone/ticket/path'
IRODS_FILE_PATH = '/sodarZone/path/test1.txt'


class SamplesheetsPermissionTestBase(
    SampleSheetIOMixin, TestProjectPermissionBase
):
    """Base test class for samplesheets UI view permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()


class TestProjectSheetsView(SamplesheetsPermissionTestBase):
    """Permission tests for ProjectSheetsView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test ProjectSheetsView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        # Test public project
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        # Test public project
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)


class TestSheetImportView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetImportView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get(self):
        """Test SheetImportView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    def test_get_sync(self):
        """Test GET with sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
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
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    def test_get_sync_archive(self):
        """Test GET with sync enabled and archived project"""
        self.project.set_archive()
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
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
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestSheetTemplateSelectView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetTemplateSelectView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:template_select',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetTemplateSelectView GET"""
        self.investigation.delete()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.investigation.delete()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    def test_get_sync(self):
        """Test GET with sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
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
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestSheetTemplateCreateView(TestProjectPermissionBase):
    """Permission tests for SheetTemplateCreateView"""

    def setUp(self):
        super().setUp()
        self.url = (
            reverse(
                'samplesheets:template_create',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?'
            + urlencode({'sheet_tpl': 'generic'})
        )

    def test_get(self):
        """Test SheetTemplateCreateView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    def test_get_sync(self):
        """Test GET with sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
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
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestSheetExcelExportView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetExcelExportView"""

    def setUp(self):
        super().setUp()
        self.study_url = reverse(
            'samplesheets:export_excel', kwargs={'study': self.study.sodar_uuid}
        )
        self.assay_url = reverse(
            'samplesheets:export_excel', kwargs={'assay': self.assay.sodar_uuid}
        )

    def test_get_study(self):
        """Test SheetExcelExportView GET for study table"""
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
        self.assert_response(self.study_url, good_users, 200)
        self.assert_response(self.study_url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.study_url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.study_url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_study_anon(self):
        """Test GET for study table with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.study_url, self.anonymous, 200)

    def test_get_study_archive(self):
        """Test GET for study table with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.study_url, good_users, 200)
        self.assert_response(self.study_url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.study_url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.study_url, self.anonymous, 302)

    def test_get_assay(self):
        """Test GET permissions for assay table"""
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
        self.assert_response(self.assay_url, good_users, 200)
        self.assert_response(self.assay_url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.assay_url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.assay_url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_assay_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.assay_url, self.anonymous, 200)

    def test_get_assay_archive(self):
        """Test GET for assay table with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.assay_url, good_users, 200)
        self.assert_response(self.assay_url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.assay_url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.assay_url, self.anonymous, 302)


class TestSheetISAExportView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetISAExportView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:export_isa',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetISAExportView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)


class TestSheetDeleteView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetDeleteView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get(self):
        """Test SheetDeleteView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestSheetVersionListView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetVersionListView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get(self):
        """Test SheetVersionListView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET permissions with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)


class TestSheetVersionCompareView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetVersionCompareView"""

    def setUp(self):
        super().setUp()
        self.isa_version = ISATab.objects.first()
        self.url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:version_compare',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(self.isa_version.sodar_uuid),
            str(self.isa_version.sodar_uuid),
        )

    def test_get(self):
        """Test SheetVersionCompareView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)


class TestSheetVersionCompareFileView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetVersionCompareFileView"""

    def setUp(self):
        super().setUp()
        self.isa_version = ISATab.objects.first()
        self.url = '{}?source={}&target={}&filename={}&category={}'.format(
            reverse(
                'samplesheets:version_compare_file',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(self.isa_version.sodar_uuid),
            str(self.isa_version.sodar_uuid),
            's_small.txt',
            'studies',
        )

    def test_get(self):
        """Test SheetVersionCompareFileView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 302)


class TestSheetVersionRestoreView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetVersionRestoreView"""

    def setUp(self):
        super().setUp()
        self.isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        self.url = reverse(
            'samplesheets:version_restore',
            kwargs={'isatab': self.isa_version.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionRestoreView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestSheetVersionUpdateView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetVersionUpdateView"""

    def setUp(self):
        super().setUp()
        self.isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        self.url = reverse(
            'samplesheets:version_update',
            kwargs={'isatab': self.isa_version.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionUpdateView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestSheetVersionDeleteView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetVersionDeleteView"""

    def setUp(self):
        super().setUp()
        self.isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        self.url = reverse(
            'samplesheets:version_delete',
            kwargs={'isatab': self.isa_version.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionDeleteView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestSheetVersionDeleteBatchView(SamplesheetsPermissionTestBase):
    """Permission tests for SheetVersionDeleteBatchView"""

    def setUp(self):
        super().setUp()
        self.isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        self.url = reverse(
            'samplesheets:version_delete_batch',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {
            'confirm': '1',
            'version_check': str(self.isa_version.sodar_uuid),
        }

    def test_post(self):
        """Test SheetVersionDeleteBatchView POST"""
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
        self.assert_response(
            self.url, good_users, 200, method='POST', data=self.post_data
        )
        self.assert_response(
            self.url, bad_users, 302, method='POST', data=self.post_data
        )
        self.project.set_public()
        self.assert_response(
            self.url, bad_users, 302, method='POST', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(
            self.url, self.anonymous, 302, method='POST', data=self.post_data
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
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
        self.assert_response(
            self.url, good_users, 200, method='POST', data=self.post_data
        )
        self.assert_response(
            self.url, bad_users, 302, method='POST', data=self.post_data
        )
        self.project.set_public()
        self.assert_response(
            self.url, bad_users, 302, method='POST', data=self.post_data
        )


class TestIrodsAccessTicketListView(SamplesheetsPermissionTestBase):
    """Permission tests for IrodsAccessTicketListView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_tickets',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketListView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestIrodsAccessTicketCreateView(SamplesheetsPermissionTestBase):
    """Permission tests for IrodsAccessTicketCreateView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketCreateView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        # NOTE: Ticket creation should still be allowed
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestIrodsAccessTicketUpdateView(
    IrodsAccessTicketMixin, SamplesheetsPermissionTestBase
):
    """Permission tests for IrodsAccessTicketUpdateView"""

    def setUp(self):
        super().setUp()
        self.ticket = self.make_irods_ticket(
            path=IRODS_TICKET_PATH,
            study=self.study,
            assay=self.assay,
            user=self.user_owner,
        )
        self.url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketUpdateView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestIrodsAccessTicketDeleteView(
    IrodsAccessTicketMixin, SamplesheetsPermissionTestBase
):
    """Permission tests for IrodsAccessTicketDeleteView"""

    def setUp(self):
        super().setUp()
        self.ticket = self.make_irods_ticket(
            path=IRODS_TICKET_PATH,
            study=self.study,
            assay=self.assay,
            user=self.user_owner,
        )
        self.url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketDeleteView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestIrodsDataRequestListView(SamplesheetsPermissionTestBase):
    """Permission tests for IrodsDataRequestListView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_requests',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestListView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestIrodsDataRequestCreateView(SamplesheetsPermissionTestBase):
    """Permission tests for IrodsDataRequestCreateView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestCreateView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestIrodsDataRequestUpdateView(
    IrodsDataRequestMixin, SamplesheetsPermissionTestBase
):
    """Permission tests for IrodsDataRequestUpdateView"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_update',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestUpdateView GET"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,  # Request creator
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


class TestIrodsDataRequestAcceptView(
    IrodsDataRequestMixin, SamplesheetsPermissionTestBase
):
    """Permission tests for IrodsDataRequestAcceptView"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_accept',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestAcceptView GET"""
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
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)


# NOTE: Batch views always redirect, they should be tested in taskflow view
#       tests instead


class TestIrodsDataRequestDeleteView(
    IrodsDataRequestMixin, SamplesheetsPermissionTestBase
):
    """Permission tests for TestIrodsDataRequestDeleteAPIView"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_delete',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_get(self):
        """Test TestIrodsDataRequestDeleteAPIView GET"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,  # Request creator
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.project.set_public()
        self.assert_response(self.url, bad_users, 302)
