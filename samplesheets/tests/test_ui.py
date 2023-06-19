"""UI tests for the samplesheets app"""

import json

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
from projectroles.plugins import get_backend_api
from projectroles.tests.test_ui import TestUIBase

from samplesheets.constants import HIDDEN_SHEET_TEMPLATE_FIELDS
from samplesheets.models import (
    ISATab,
    IRODS_DATA_REQUEST_STATUS_CHOICES,
    Investigation,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import (
    IrodsAccessTicketMixin,
    IrodsDataRequestMixin,
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


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
DEFAULT_WAIT_ID = 'sodar-ss-vue-content'
with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)
with open(CONFIG_PATH_UPDATED) as fp:
    CONFIG_DATA_UPDATED = json.load(fp)


class TestProjectSheetsUIBase(SampleSheetIOMixin, SheetConfigMixin, TestUIBase):
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


class TestProjectSheetsView(IrodsDataRequestMixin, TestProjectSheetsUIBase):
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
        irods_backend = get_backend_api('omics_irods')
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_irods_data_request(
            project=self.project,
            action='delete',
            path=irods_backend.get_path(self.assay) + '/test/xxx.bam',
            status='ACTIVE',
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


class TestSheetTemplateCreateFormView(TestProjectSheetsUIBase):
    """Tests for the sheet template creation view UI"""

    def test_render_hidden_fields(self):
        """Test rendering hidden fields in the sheet template form"""
        for t in ISA_TEMPLATES:
            url = (
                reverse(
                    'samplesheets:template_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?sheet_tpl='
                + t.name
            )
            self.login_and_redirect(self.superuser, url)
            for f in HIDDEN_SHEET_TEMPLATE_FIELDS:
                try:
                    elem = self.selenium.find_element(By.ID, f)
                    self.assertEqual(elem.get_attribute('type'), 'hidden')
                except NoSuchElementException:
                    pass  # This is ok


class TestSheetVersionListView(TestProjectSheetsUIBase):
    """Tests for the sheet version list view UI"""

    def setUp(self):
        super().setUp()
        self.setup_investigation()
        self.url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )

    def test_list(self):
        """Test UI rendering for list items"""
        self.assert_element_exists(
            [self.user_contributor], self.url, 'sodar-ss-version-list', True
        )
        self.assert_element_exists(
            [self.user_contributor], self.url, 'sodar-ss-version-alert', False
        )

    def test_list_no_versions(self):
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

    def test_list_buttons(self):
        """Test list button rendering"""
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
            expected, self.url, 'sodar-ss-version-btn-group', 'class'
        )


class TestIrodsAccessTicketListView(
    IrodsAccessTicketMixin, TestProjectSheetsUIBase
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
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, 'sodar-ss-ticket-alert-empty')
        self.assertIsNotNone(
            self.selenium.find_element(By.ID, 'sodar-ss-ticket-table')
        )
        self.assertEqual(
            len(
                self.selenium.find_elements(
                    By.CLASS_NAME, 'sodar-ss-ticket-item'
                )
            ),
            1,
        )
        elem = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-ss-ticket-item-title'
        ).find_element(By.TAG_NAME, 'a')
        self.assertNotIn('text-strikethrough', elem.get_attribute('class'))
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


class TestIrodsAccessTicketCreateView(TestProjectSheetsUIBase):
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
    IrodsAccessTicketMixin, TestProjectSheetsUIBase
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


class TestIrodsRequestCreateView(TestProjectSheetsUIBase):
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


class TestIrodsRequestUpdateView(
    IrodsDataRequestMixin, TestProjectSheetsUIBase
):
    """Tests for irods request update view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self.make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_update',
            kwargs={'irodsdatarequest': self.irods_data_request.sodar_uuid},
        )

    def test_render_form(self):
        """Test UI rendering for iRODS request update view"""
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-btn-import-submit',
            True,
        )


class TestIrodsRequestDeleteView(
    IrodsDataRequestMixin, TestProjectSheetsUIBase
):
    """Tests for iRODS request delete view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self.make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_delete',
            kwargs={'irodsdatarequest': self.irods_data_request.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for iRODS request delete view"""
        self.assert_element_exists(
            [self.user_contributor],
            self.url,
            'sodar-ss-btn-confirm-delete',
            True,
        )


class TestIrodsRequestAcceptView(
    IrodsDataRequestMixin, TestProjectSheetsUIBase
):
    """Tests for iRODS request accept view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self.make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:irods_request_accept',
            kwargs={'irodsdatarequest': self.irods_data_request.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for iRODS request accept view"""
        self.assert_element_exists(
            [self.superuser], self.url, 'sodar-ss-btn-delete-submit', True
        )


class TestIrodsRequestListView(IrodsDataRequestMixin, TestProjectSheetsUIBase):
    """Tests for iRODS request reject view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self.make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
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
            self.selenium.find_element(By.CLASS_NAME, 'sodar-ss-davrods-link')
        )


class TestSheetVersionCompareView(
    SampleSheetIOMixin, SheetConfigMixin, TestUIBase
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
    SampleSheetIOMixin, SheetConfigMixin, TestUIBase
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
