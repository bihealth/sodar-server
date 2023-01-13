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
from samplesheets.tests.test_views_ajax import IrodsAccessTicketMixin


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
    """Tests for samplesheets view permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.ticket = self.make_ticket(
            project=self.project,
            path='/some/path',
            study=self.study,
            assay=self.assay,
            user=self.user_owner,
        )

    def test_project_sheets(self):
        """Test the project sheets view"""
        url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        # Test public project
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_project_sheets_anon(self):
        """Test project sheets view with anonymous guest access"""
        self.project.set_public()
        url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_import(self):
        """Test sheet import view"""
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_import_anon(self):
        """Test sheet import view with anonymous guest access"""
        self.project.set_public()
        url = reverse(
            'samplesheets:import',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_import_sync(self):
        """Test sheet import view with sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )
        bad_users = [
            self.superuser,
            self.user_owner_cat,
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
        """Test sheet template select view"""
        self.investigation.delete()
        url = reverse(
            'samplesheets:template_select',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_template_select_anon(self):
        """Test sheet template select view with anonymous guest access"""
        self.project.set_public()
        url = reverse(
            'samplesheets:template_select',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.assert_response(url, self.anonymous, 302)

    def test_sheet_template_select_sync(self):
        """Test sheet template select view with sync enabled"""
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
        """Test sheet template creation view"""
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_template_create_anon(self):
        """Test sheet template creation view with anonymous guest access"""
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

    def test_sheet_template_create_sync(self):
        """Test sheet template create view with sync enabled"""
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
        """Test sheet Excel export view for study table"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'study': self.study.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_export_excel_study_anon(self):
        """Test Excel export for study table with anonymous guest access"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'study': self.study.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_export_excel_assay(self):
        """Test sheet Excel export view for assay table"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'assay': self.assay.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_export_excel_assay_anon(self):
        """Test Excel export for assay table with anonymous guest access"""
        url = reverse(
            'samplesheets:export_excel', kwargs={'assay': self.assay.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_export_isa(self):
        """Test sheet ISA export view"""
        url = reverse(
            'samplesheets:export_isa',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_export_isa_anon(self):
        """Test sheet ISA export view with anonymous guest access"""
        url = reverse(
            'samplesheets:export_isa',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_sheet_delete(self):
        """Test sheet delete view"""
        url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sheet_delete_anon(self):
        """Test sheet delete view with anonymous guest access"""
        url = reverse(
            'samplesheets:delete', kwargs={'project': self.project.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_version_list(self):
        """Test sheet version list view"""
        url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_list_anon(self):
        """Test sheet version list view with anonymous guest access"""
        url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 200)

    def test_version_compare(self):
        """Test sheet version compare view"""
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_compare_anon(self):
        """Test sheet version compare view  with anonymous guest access"""
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

    def test_version_compare_file(self):
        """Test sheet version compare file view"""
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
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, self.user_no_roles, 200)
        self.assert_response(url, self.anonymous, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_version_compare_file_anon(self):
        """Test sheet version compare file view"""
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

    def test_version_restore(self):
        """Test sheet restoring view"""
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
            self.user_owner,
            self.delegate_as.user,
        ]
        bad_users = [
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
        """Test sheet restoring view"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_restore',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_version_update(self):
        """Test sheet update view"""
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
            self.user_owner,
            self.delegate_as.user,
        ]
        bad_users = [
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
        """Test sheet update view with anonymous guest access"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_update',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_version_delete(self):
        """Test sheet delete view"""
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
            self.user_owner,
            self.delegate_as.user,
        ]
        bad_users = [
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
        """Test sheet delete view with anonymous guest access"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        url = reverse(
            'samplesheets:version_delete',
            kwargs={'isatab': isa_version.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_version_delete_batch(self):
        """Test batch sheet delete view"""
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
            self.user_owner,
            self.delegate_as.user,
        ]
        bad_users = [
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
        """Test batch sheet delete view with anonymous guest access"""
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

    def test_ticket_list(self):
        """Test ticket list view"""
        url = reverse(
            'samplesheets:irods_tickets',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_list_anon(self):
        """Test ticket list view with anonymous guest access"""
        url = reverse(
            'samplesheets:irods_tickets',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_ticket_create(self):
        """Test ticket create view"""
        url = reverse(
            'samplesheets:irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_create_anon(self):
        """Test ticket create view with anonymous guest access"""
        url = reverse(
            'samplesheets:irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_ticket_update(self):
        """Test ticket update view"""
        url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_update_anon(self):
        """Test ticket update view with anonymous guest access"""
        url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)

    def test_ticket_delete(self):
        """Test ticket delete view"""
        url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 302)
        self.project.set_public()
        self.assert_response(url, bad_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_ticket_delete_anon(self):
        """Test ticket delete view with anonymous guest access"""
        url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response(url, self.anonymous, 302)
