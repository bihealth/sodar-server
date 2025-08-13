"""UI tests for the samplesheets app"""

import json
import os

from cubi_isa_templates import _TEMPLATES as ISA_TEMPLATES
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.plugins import PluginAPI
from projectroles.tests.test_ui import UITestBase

from samplesheets.forms import TPL_DIR_FIELD, TPL_DIR_LABEL
from samplesheets.models import (
    ISATab,
    Investigation,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import (
    IrodsAccessTicketMixin,
    IrodsDataRequestMixin,
    IRODS_REQUEST_DESC,
)
from samplesheets.tests.test_sheet_config import (
    SheetConfigMixin,
    CONFIG_PATH_DEFAULT,
    CONFIG_PATH_UPDATED,
)
from samplesheets.tests.test_views import (
    SHEET_PATH_SMALL2,
)
from samplesheets.views_ajax import ALERT_ACTIVE_REQS


app_settings = AppSettingAPI()
plugin_api = PluginAPI()


# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
DEFAULT_WAIT_ID = 'sodar-ss-vue-content'
IRODS_REQUEST_PATH = '/some/path/to/a/file'

with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)
with open(CONFIG_PATH_UPDATED) as fp:
    CONFIG_DATA_UPDATED = json.load(fp)


class SamplesheetsUITestBase(SampleSheetIOMixin, SheetConfigMixin, UITestBase):
    """Base view samplesheets view UI tests"""

    def setup_investigation(self, config_data=None):
        """Setup Investigation, Study and Assay"""
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        if config_data:
            # Set up UUIDs and default config
            self.update_uuids(self.investigation, config_data)
            app_settings.set(
                'samplesheets',
                'sheet_config',
                config_data,
                project=self.project,
            )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()


class TestProjectSheetsView(IrodsDataRequestMixin, SamplesheetsUITestBase):
    """Tests for the project sheets view UI"""

    def _login_and_render(self, user, wait_elem=DEFAULT_WAIT_ID, url_suffix=''):
        """Login into the sheets view and wait for it to render"""
        url = (
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project.sodar_uuid},
            )
            + url_suffix
        )
        self.login_and_redirect(user=user, url=url, wait_elem=wait_elem)

    def setUp(self):
        super().setUp()
        self.setup_investigation()

    def test_render(self):
        """Test rendering view with study and assay grids"""
        users = [
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
        for user in users:
            self._login_and_render(user=user, wait_elem='sodar-ss-grid-study')
            # Ensure assay grid is found (we already know study is there)
            self.assertIsNotNone(
                self.selenium.find_element(
                    By.ID,
                    'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid),
                )
            )
            # Ensure error alert is not generated
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element(By.ID, 'sodar-ss-alert-error')

    def test_render_no_sheet(self):
        """Test rendering view with no sheet"""
        self.investigation.delete()
        users = [
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
        for user in users:
            self._login_and_render(user)
            # Ensure alert is shown
            self.assertIsNotNone(
                self.selenium.find_element(By.ID, 'sodar-ss-alert-empty')
            )
            # Ensure no grids are present
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element(
                    By.ID,
                    'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid),
                )

    def test_render_alert(self):
        """Test rendering alert retrieved from SODAR context"""
        # NOTE: Testing here as we don't (yet) have vue tests for entire app
        irods_backend = plugin_api.get_backend_api('omics_irods')
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=os.path.join(
                irods_backend.get_path(self.assay), 'test', 'xxx.bam'
            ),
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        users = [
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
        for user in users:
            self._login_and_render(user=user, wait_elem='sodar-ss-grid-study')
            if user in [
                self.superuser,
                self.user_owner_cat,
                self.user_delegate_cat,
                self.user_owner,
                self.user_delegate,
            ]:
                self.assertIsNotNone(
                    self.selenium.find_element(By.CLASS_NAME, 'sodar-ss-alert')
                )
                self.assertEqual(
                    self.selenium.find_element(
                        By.CLASS_NAME, 'sodar-ss-alert'
                    ).get_attribute('innerHTML'),
                    ALERT_ACTIVE_REQS.format(
                        url=reverse(
                            'samplesheets:irods_requests',
                            kwargs={'project': self.project.sodar_uuid},
                        )
                    ),
                    msg=user.username,
                )
            else:
                with self.assertRaises(NoSuchElementException):
                    self.selenium.find_element(By.CLASS_NAME, 'sodar-ss-alert')

    # NOTE: For further vue app tests, see samplesheets/vueapp/tests


class TestSheetTemplateCreateView(SamplesheetsUITestBase):
    """Tests for the sheet template creation view UI"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:template_create',
            kwargs={'project': self.project.sodar_uuid},
        )  # NOTE: Needs sheet_tpl querystring in test

    def test_render_fields(self):
        """Test field visibility in sheet template form"""
        for t in ISA_TEMPLATES:
            url = self.url + '?sheet_tpl=' + t.name
            self.login_and_redirect(self.superuser, url)
            form_elems = self.selenium.find_elements(
                By.CLASS_NAME, 'form-control'
            )
            for e in form_elems:
                e_name = e.get_attribute('name')
                msg = '{}/{}'.format(t.name, e_name)
                if e_name.startswith('_'):
                    self.assertEqual(e.get_attribute('type'), 'hidden', msg=msg)
                else:
                    self.assertNotEqual(
                        e.get_attribute('type'), 'hidden', msg=msg
                    )

    def test_render_labels(self):
        """Test label rendering"""
        for t in ISA_TEMPLATES:
            prompts = t.configuration.get('__prompts__')
            url = self.url + '?sheet_tpl=' + t.name
            self.login_and_redirect(self.superuser, url)
            label_elems = self.selenium.find_elements(By.TAG_NAME, 'label')
            for e in label_elems:
                e_name = e.get_attribute('for')[3:]  # Strip "id_"
                label_text = e.text
                msg = '{}/{}'.format(t.name, e_name)
                if e_name == TPL_DIR_FIELD:
                    self.assertEqual(label_text, TPL_DIR_LABEL + '*')
                # Need to use assertIn() because of extra label characters
                elif prompts and e_name in prompts:
                    self.assertIn(prompts[e_name], label_text, msg=msg)
                else:
                    self.assertIn(e_name, label_text, msg=msg)

    def test_render_output_dir_field(self):
        """Test output dir field visibility with default user setting"""
        self.assertFalse(
            app_settings.get(
                APP_NAME, 'template_output_dir_display', user=self.superuser
            )
        )
        t = ISA_TEMPLATES[0]
        url = self.url + '?sheet_tpl=' + t.name
        self.login_and_redirect(self.superuser, url)
        elem = self.selenium.find_element(By.NAME, TPL_DIR_FIELD)
        self.assertEqual(elem.get_attribute('type'), 'hidden')

    def test_render_output_dir_field_enabled(self):
        """Test output dir field visibility with enabled user setting"""
        app_settings.set(
            APP_NAME, 'template_output_dir_display', True, user=self.superuser
        )
        t = ISA_TEMPLATES[0]
        url = self.url + '?sheet_tpl=' + t.name
        self.login_and_redirect(self.superuser, url)
        form_elems = self.selenium.find_elements(By.CLASS_NAME, 'form-control')
        # Assert other internal fields remain hidden
        for e in form_elems:
            e_name = e.get_attribute('name')
            msg = '{}/{}'.format(t.name, e_name)
            if e_name.startswith('_') and e_name != TPL_DIR_FIELD:
                self.assertEqual(e.get_attribute('type'), 'hidden', msg=msg)
        elem = self.selenium.find_element(By.NAME, TPL_DIR_FIELD)
        self.assertEqual(elem.get_attribute('type'), 'text')


class TestSheetVersionListView(SamplesheetsUITestBase):
    """Tests for the sheet version list view UI"""

    def setUp(self):
        super().setUp()
        self.setup_investigation()
        self.url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )

    def test_render(self):
        """Test UI rendering for list items"""
        self.assert_element_exists(
            [self.user_contributor], self.url, 'sodar-ss-version-list', True
        )
        self.assert_element_exists(
            [self.user_contributor], self.url, 'sodar-ss-version-alert', False
        )
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-version-link-compare',
            True,
        )
        self.assert_element_exists(
            [self.user_owner], self.url, 'sodar-ss-version-link-delete', True
        )
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-version-link-delete',
            False,
        )
        # Ensure badge is shown for current version
        self.login_and_redirect(self.user_contributor, self.url)
        self.assertIsNotNone(
            self.selenium.find_element(By.CLASS_NAME, 'badge-info')
        )

    def test_render_no_versions(self):
        """Test UI rendering for list items with no versions"""
        ISATab.objects.filter(
            investigation_uuid=self.investigation.sodar_uuid
        ).delete()
        self.assert_element_exists(
            [self.user_contributor], self.url, 'sodar-ss-version-list', True
        )
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-version-list-item',
            False,
        )

    def test_render_version_dropdown(self):
        """Test sheet version dropdown rendering"""
        expected = [
            (self.superuser, 1),
            (self.user_owner_cat, 1),
            (self.user_delegate_cat, 1),
            (self.user_contributor_cat, 0),
            (self.user_guest_cat, 0),
            (self.user_owner, 1),
            (self.user_delegate, 1),
            (self.user_contributor, 0),
            (self.user_guest, 0),
        ]
        self.assert_element_count(
            expected, self.url, 'sodar-ss-version-dropdown', 'class'
        )

    def test_render_read_only(self):
        """Test rendering with site read-only-mode"""
        app_settings.set('projectroles', 'site_read_only', True)
        expected = [
            (self.superuser, 1),
            (self.user_owner_cat, 0),
            (self.user_delegate_cat, 0),
            (self.user_contributor_cat, 0),
            (self.user_guest_cat, 0),
            (self.user_owner, 0),
            (self.user_delegate, 0),
            (self.user_contributor, 0),
            (self.user_guest, 0),
        ]
        self.assert_element_count(
            expected, self.url, 'sodar-ss-version-link-delete'
        )
        self.assert_element_count(
            expected, self.url, 'sodar-ss-version-dropdown', 'class'
        )


class TestIrodsAccessTicketListView(
    IrodsAccessTicketMixin, SamplesheetsUITestBase
):
    """Tests for iRODS access ticket list view UI"""

    def setUp(self):
        super().setUp()
        self.setup_investigation()
        self.url = reverse(
            'samplesheets:irods_tickets',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render_empty(self):
        """Test rendering empty list view"""
        self.login_and_redirect(self.user_contributor, self.url)
        elem = self.selenium.find_element(By.ID, 'sodar-ss-btn-ticket-create')
        self.assertIsNotNone(elem)
        self.assertIsNone(elem.get_attribute('disabled'))
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-ss-ticket-alert-empty')
        )
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-ss-ticket-table')

    def test_render_ticket(self):
        """Test rendering list view with ticket"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/sodarZone/some/path',
            user=self.user_contributor,
        )
        self.login_and_redirect(self.user_contributor, self.url)
        elem = self.selenium.find_element(By.ID, 'sodar-ss-btn-ticket-create')
        self.assertIsNone(elem.get_attribute('disabled'))
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-ss-ticket-alert-empty')
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-ss-ticket-table')
        )
        items = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-ss-ticket-item'
        )
        self.assertEqual(len(items), 1)
        elem = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-ss-ticket-item-title'
        ).find_element(By.TAG_NAME, 'a')
        self.assertNotIn('text-strikethrough', elem.get_attribute('class'))
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(
                By.CLASS_NAME, 'sodar-ss-ticket-item-host'
            )
        elem = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-ss-ticket-item-expiry'
        )
        self.assertEqual(elem.text, 'Never')
        self.assertNotIn('text-danger', elem.get_attribute('class'))

    def test_render_expired(self):
        """Test rendering with expired ticket"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/sodarZone/some/path',
            user=self.user_contributor,
            date_expires=timezone.localtime() - timedelta(days=1),
        )
        self.login_and_redirect(self.user_contributor, self.url)
        elem = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-ss-ticket-item-title'
        ).find_element(By.TAG_NAME, 'a')
        self.assertIn('text-strikethrough', elem.get_attribute('class'))
        elem = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-ss-ticket-item-expiry'
        )
        self.assertEqual(elem.text, 'Expired')
        self.assertIn('text-danger', elem.get_attribute('class'))

    def test_render_ticket_hosts(self):
        """Test rendering ticket with allowed hosts set"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/sodarZone/some/path',
            user=self.user_contributor,
            allowed_hosts=['127.0.0.1'],
        )
        self.login_and_redirect(self.user_contributor, self.url)
        items = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-ss-ticket-item'
        )
        self.assertEqual(len(items), 1)
        self.assertIsNotNone(
            self.selenium.find_element(
                By.CLASS_NAME, 'sodar-ss-ticket-item-host'
            )
        )

    def test_render_read_only(self):
        """Test rendering with site read-only mode"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/sodarZone/some/path',
            user=self.user_contributor,
        )
        app_settings.set('projectroles', 'site_read_only', True)
        self.login_and_redirect(self.user_contributor, self.url)
        elem = self.selenium.find_element(By.ID, 'sodar-ss-btn-ticket-create')
        self.assertIsNotNone(elem)
        self.assertEqual(elem.get_attribute('disabled'), 'true')
        items = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-ss-ticket-item'
        )
        self.assertEqual(len(items), 1)
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(
                By.CLASS_NAME, 'sodar-ss-ticket-dropdown'
            )

    def test_render_read_only_superuser(self):
        """Test rendering with site read-only mode as superuser"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/sodarZone/some/path',
            user=self.user_contributor,
        )
        app_settings.set('projectroles', 'site_read_only', True)
        self.login_and_redirect(self.superuser, self.url)
        elem = self.selenium.find_element(By.ID, 'sodar-ss-btn-ticket-create')
        self.assertIsNotNone(elem)
        self.assertIsNone(elem.get_attribute('disabled'))
        items = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-ss-ticket-item'
        )
        self.assertEqual(len(items), 1)
        elem = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-ss-ticket-dropdown'
        )
        self.assertIsNotNone(elem)


class TestIrodsAccessTicketCreateView(SamplesheetsUITestBase):
    """Tests for iRODS access ticket create view UI"""

    def setUp(self):
        super().setUp()
        self.setup_investigation()
        self.url = reverse(
            'samplesheets:irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render(self):
        """Test rendering iRODS access ticket create view"""
        self.login_and_redirect(self.user_contributor, self.url)
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-ss-alert-ticket-create')
        )


class TestIrodsAccessTicketUpdateView(
    IrodsAccessTicketMixin, SamplesheetsUITestBase
):
    """Tests for iRODS access ticket update view UI"""

    def setUp(self):
        super().setUp()
        self.setup_investigation()
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/sodarZone/some/path',
            user=self.user_contributor,
            date_expires=timezone.localtime() - timedelta(days=1),
        )
        self.url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_render(self):
        """Test rendering iRODS access ticket update view"""
        self.login_and_redirect(self.user_contributor, self.url)
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-ss-alert-ticket-create')


class TestIrodsDataRequestCreateView(SamplesheetsUITestBase):
    """Tests for iRODS request create view UI"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render_form(self):
        """Test UI rendering for iRODS request create view"""
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-btn-import-submit',
            True,
        )


class TestIrodsDataRequestUpdateView(
    IrodsDataRequestMixin, SamplesheetsUITestBase
):
    """Tests for irods request update view UI"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            path=IRODS_REQUEST_PATH,
            description=IRODS_REQUEST_DESC,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_update',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_render_form(self):
        """Test UI rendering for iRODS request update view"""
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-btn-import-submit',
            True,
        )


class TestIrodsDataRequestDeleteView(
    IrodsDataRequestMixin, SamplesheetsUITestBase
):
    """Tests for iRODS request delete view UI"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            path=IRODS_REQUEST_PATH,
            description=IRODS_REQUEST_DESC,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_delete',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for iRODS request delete view"""
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-btn-confirm-delete',
            True,
        )


class TestIrodsDataRequestAcceptView(
    IrodsDataRequestMixin, SamplesheetsUITestBase
):
    """Tests for iRODS request accept view UI"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            path=IRODS_REQUEST_PATH,
            description=IRODS_REQUEST_DESC,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_accept',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for iRODS request accept view"""
        self.assert_element_exists(
            [self.superuser], self.url, 'sodar-ss-btn-delete-submit', True
        )


class TestIrodsDataRequestListView(
    IrodsDataRequestMixin, SamplesheetsUITestBase
):
    """Tests for iRODS request reject view UI"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            path=IRODS_REQUEST_PATH,
            description=IRODS_REQUEST_DESC,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_requests',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for listing iRODS requests"""
        self.assert_element_exists(
            [self.user_contributor], self.url, 'sodar-ss-request-table', True
        )

    def test_render_davrods_button(self):
        """Test UI rendering of davrods link button"""
        self.login_and_redirect(
            user=self.user_contributor,
            url=self.url,
            wait_elem='sodar-ss-request-table',
        )
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-ss-davrods-link')
        )


class TestSheetVersionCompareView(
    SampleSheetIOMixin, SheetConfigMixin, UITestBase
):
    """Tests for sheet version compare view UI"""

    def setUp(self):
        super().setUp()
        self.import_isa_from_file(SHEET_PATH_SMALL2, self.project)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        self.isa1 = ISATab.objects.first()
        self.url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:version_compare',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(self.isa1.sodar_uuid),
            str(self.isa1.sodar_uuid),
        )

    def test_render(self):
        """Test UI rendering for comparing samplesheet versions"""
        self.assert_element_exists(
            [self.superuser],
            self.url,
            'sodar-ss-studies-diff0',
            True,
            'sodar-ss-studies-diff0',
        )
        self.assert_element_exists(
            [self.superuser],
            self.url,
            'sodar-ss-assays-diff0',
            True,
            'sodar-ss-assays-diff0',
        )


class TestSheetVersionCompareFileView(
    SampleSheetIOMixin, SheetConfigMixin, UITestBase
):
    """Tests for sheet version compare file view UI"""

    def setUp(self):
        super().setUp()
        self.import_isa_from_file(SHEET_PATH_SMALL2, self.project)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        self.isa1 = ISATab.objects.first()
        self.url_study_file = (
            reverse(
                'samplesheets:version_compare_file',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?'
            + urlencode(
                {
                    'source': str(self.isa1.sodar_uuid),
                    'target': str(self.isa1.sodar_uuid),
                    'filename': 's_small2.txt',
                    'category': 'studies',
                }
            )
        )
        self.url_assay_file = (
            reverse(
                'samplesheets:version_compare_file',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?'
            + urlencode(
                {
                    'source': str(self.isa1.sodar_uuid),
                    'target': str(self.isa1.sodar_uuid),
                    'filename': 'a_small2.txt',
                    'category': 'assays',
                }
            )
        )

    def test_render_study_file(self):
        """Test UI rendering for study table comparison"""
        self.login_and_redirect(
            self.superuser,
            reverse(
                'samplesheets:versions',
                kwargs={'project': self.project.sodar_uuid},
            ),
        )
        self.selenium.get(self.build_selenium_url(self.url_study_file))
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.TAG_NAME, 'table'))
        )
        self.assertIsNotNone(self.selenium.find_element(By.TAG_NAME, 'table'))

    def test_render_assay_file(self):
        """Test UI rendering for assay table comparison"""
        self.login_and_redirect(
            self.superuser,
            reverse(
                'samplesheets:versions',
                kwargs={'project': self.project.sodar_uuid},
            ),
        )
        self.selenium.get(self.build_selenium_url(self.url_assay_file))
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.TAG_NAME, 'table'))
        )
        self.assertIsNotNone(self.selenium.find_element(By.TAG_NAME, 'table'))
