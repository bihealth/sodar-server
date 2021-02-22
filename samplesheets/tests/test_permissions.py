"""Tests for UI view permissions in the samplesheets app"""

from django.conf import settings
from django.urls import reverse
from unittest import skipIf
from urllib.parse import urlencode

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.utils import build_secret

from samplesheets.models import ISATab
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


# App settings API
from samplesheets.tests.test_views_ajax import IrodsAccessTicketMixin

app_settings = AppSettingAPI()


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_SECRET = build_secret()
INVALID_SECRET = build_secret()
IRODS_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_SKIP_MSG = 'Irodsbackend not enabled in settings'


class TestSampleSheetsPermissions(
    SampleSheetIOMixin, IrodsAccessTicketMixin, TestProjectPermissionBase
):
    """Tests for samplesheets view permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.ticket = self._make_ticket(
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

    def test_sheet_template_select(self):
        """Test sheet template select view"""
        self.investigation.delete()
        url = reverse(
            'samplesheets:template_select',
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
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        # bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        # TODO: Test bad_users redirect once sodar_core#635 has been fixed
        # self.assert_response(url, bad_users, 302)

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

    @skipIf(not IRODS_ENABLED, IRODS_SKIP_MSG)
    def test_ticket_list(self):
        """Test ticket list view"""

        url = reverse(
            'samplesheets:irods_tickets',
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
        self.assert_response(url, bad_users, status_code=302)

    def test_ticket_create(self):
        """Test ticket create view"""

        url = reverse(
            'samplesheets:irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200)
        self.assert_response(url, bad_users, status_code=302)

    def test_ticket_update(self):
        """Test ticket update view"""

        url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200)
        self.assert_response(url, bad_users, status_code=302)

    def test_ticket_delete(self):
        """Test ticket delete view"""

        url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, status_code=200)
        self.assert_response(url, bad_users, status_code=302)
