"""UI tests for the samplesheets app"""

import json
from unittest import skipIf

from cubi_tk.isa_tpl import _TEMPLATES as TK_TEMPLATES

from django.conf import settings
from django.urls import reverse
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
    IrodsDataRequest,
    IRODS_DATA_REQUEST_STATUS_CHOICES,
    Investigation,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_sheet_config import (
    SheetConfigMixin,
    CONFIG_PATH_DEFAULT,
    CONFIG_PATH_UPDATED,
)
from samplesheets.tests.test_views import (
    SHEET_PATH_SMALL2,
)
from samplesheets.views_ajax import ALERT_ACTIVE_REQS


# App settings API
app_settings = AppSettingAPI()


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
DEFAULT_WAIT_ID = 'sodar-ss-vue-content'
with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)
with open(CONFIG_PATH_UPDATED) as fp:
    CONFIG_DATA_UPDATED = json.load(fp)
IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'Irodsbackend not enabled in settings'


class TestProjectSheetsVueAppBase(
    SampleSheetIOMixin, SheetConfigMixin, TestUIBase
):
    """Base view for the project sheets vue app UI"""

    # Helper functions ---------------------------------------------------------

    def _setup_investigation(self, config_data=None):
        """Setup Investigation, Study and Assay"""
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        if config_data:
            # Set up UUIDs and default config
            self._update_uuids(self.investigation, config_data)
            app_settings.set_app_setting(
                'samplesheets',
                'sheet_config',
                config_data,
                project=self.project,
            )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

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

    def _get_route(self):
        """Return the Vue.js route part (query string) of the current URL"""
        return self.selenium.current_url.split('#')[1]

    @classmethod
    def _get_enabled_state(cls, elem):
        """Return enabled state of an a/button element regardless of its type"""
        # HACK for issue #499
        # if elem.tag_name == 'button':
        #     return
        if elem.tag_name == 'button':
            return elem.is_enabled()
        elif elem.tag_name == 'a':
            return False if 'disabled' in elem.get_attribute('class') else True

    def _start_editing(self, wait_for_study=True):
        """Enable edit mode in the UI"""
        op_div = self.selenium.find_element(By.ID, 'sodar-ss-op-dropdown')
        op_div.click()
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'sodar-ss-op-item-edit'))
        )
        elem = op_div.find_element(By.ID, 'sodar-ss-op-item-edit')
        # NOTE: Must use execute_script() due to bootstrap-vue wrapping
        self.selenium.execute_script("arguments[0].click();", elem)
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.ID, 'sodar-ss-vue-btn-edit-finish')
            )
        )
        if wait_for_study:
            WebDriverWait(self.selenium, self.wait_time).until(
                ec.presence_of_element_located((By.ID, 'sodar-ss-grid-study'))
            )

    def _stop_editing(self, wait_for_study=True):
        """Finish editing and exit from edit mode"""
        self.selenium.find_element(
            By.ID, 'sodar-ss-vue-btn-edit-finish'
        ).click()
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'sodar-ss-op-dropdown'))
        )
        if wait_for_study:
            WebDriverWait(self.selenium, self.wait_time).until(
                ec.presence_of_element_located((By.ID, 'sodar-ss-grid-study'))
            )

    @classmethod
    def _make_irods_data_request(
        cls,
        project,
        action,
        path,
        status,
        target_path='',
        status_info='',
        description='',
        user=None,
    ):
        """Create an iRODS access ticket object in the database"""
        values = {
            'project': project,
            'action': action,
            'path': path,
            'status': status,
            'target_path': target_path,
            'status_info': status_info,
            'user': user,
            'description': description,
        }
        obj = IrodsDataRequest(**values)
        obj.save()
        return obj

    # Setup --------------------------------------------------------------------

    def setUp(self):
        super().setUp()
        self.default_user = self.contributor_as.user


class TestProjectSheetsView(TestProjectSheetsVueAppBase):
    """Tests for the project sheets view UI"""

    def setUp(self):
        super().setUp()
        self._setup_investigation()

    def test_render(self):
        """Test rendering the view with study and assay grids"""
        users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
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
        """Test rendering the view with no sheet"""
        self.investigation.delete()
        users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
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

    @skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
    def test_render_alert(self):
        """Test rendering an alert retrieved from SODAR context"""
        # NOTE: Testing here as we don't (yet) have vue tests for entire app
        irods_backend = get_backend_api('omics_irods', conn=False)
        self.investigation.irods_status = True
        self.investigation.save()
        # TODO: Use model helper instead (see #1088)
        IrodsDataRequest.objects.create(
            project=self.project,
            path=irods_backend.get_path(self.assay) + '/test/xxx.bam',
            user=self.contributor_as.user,
        )
        users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
        ]

        for user in users:
            self._login_and_render(user=user, wait_elem='sodar-ss-grid-study')
            if user in [
                self.superuser,
                self.owner_as.user,
                self.delegate_as.user,
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


class TestSheetTemplateCreateFormView(TestProjectSheetsVueAppBase):
    """Tests for the sheet template creation view UI"""

    def test_render_hidden_fields(self):
        """Test rendering hidden fields in the sheet template form"""
        for t in TK_TEMPLATES:
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


class TestSheetVersionListView(TestProjectSheetsVueAppBase):
    """Tests for the sheet version list view UI"""

    def setUp(self):
        super().setUp()
        self._setup_investigation()
        self.url = reverse(
            'samplesheets:versions', kwargs={'project': self.project.sodar_uuid}
        )

    def test_list(self):
        """Test UI rendering for list items"""
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-version-list', True
        )
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-version-alert', False
        )

    def test_list_no_versions(self):
        """Test UI rendering for list items with no versions"""
        ISATab.objects.filter(
            investigation_uuid=self.investigation.sodar_uuid
        ).delete()
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-version-list', True
        )
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-version-list-item', False
        )

    def test_list_buttons(self):
        """Test list button rendering"""
        expected = [
            (self.superuser, 1),
            (self.owner_as.user, 1),
            (self.delegate_as.user, 1),
            (self.contributor_as.user, 0),
            (self.guest_as.user, 0),
        ]
        self.assert_element_count(
            expected, self.url, 'sodar-ss-version-btn-group', 'class'
        )


class TestIrodsRequestCreateView(TestProjectSheetsVueAppBase):
    """Tests for irods request create view UI"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render_form(self):
        """Test UI rendering for form"""
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-btn-import-submit', True
        )


class TestIrodsRequestUpdateView(TestProjectSheetsVueAppBase):
    """Tests for irods request update view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self._make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.default_user,
        )
        self.url = reverse(
            'samplesheets:irods_request_update',
            kwargs={'irodsdatarequest': self.irods_data_request.sodar_uuid},
        )

    def test_render_form(self):
        """Test UI rendering for form"""
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-btn-import-submit', True
        )


class TestIrodsRequestDeleteView(TestProjectSheetsVueAppBase):
    """Tests for irods request delete view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self._make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.default_user,
        )
        self.url = reverse(
            'samplesheets:irods_request_delete',
            kwargs={'irodsdatarequest': self.irods_data_request.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for form"""

        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-btn-confirm-delete', True
        )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsRequestAcceptView(TestProjectSheetsVueAppBase):
    """Tests for irods request accept view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self._make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.default_user,
        )
        self.url = reverse(
            'samplesheets:irods_request_accept',
            kwargs={'irodsdatarequest': self.irods_data_request.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for confirm accept page"""

        self.assert_element_exists(
            [self.superuser], self.url, 'sodar-ss-btn-delete-submit', True
        )


class TestIrodsDataRequestListView(TestProjectSheetsVueAppBase):
    """Tests for irods request reject view UI"""

    def setUp(self):
        super().setUp()
        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.path = '/some/path/to/a/file'
        self.irods_data_request = self._make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.default_user,
        )
        self.url = reverse(
            'samplesheets:irods_requests',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render(self):
        """Test UI rendering for listing irods requests"""
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-request-table', True
        )


class TestSheetVersionCompareView(
    SampleSheetIOMixin, SheetConfigMixin, TestUIBase
):
    """Tests for sheet version compare view UI"""

    def setUp(self):
        super().setUp()
        self._import_isa_from_file(SHEET_PATH_SMALL2, self.project)

        # Assert preconditions
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
        self._import_isa_from_file(SHEET_PATH_SMALL2, self.project)

        # Assert preconditions
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
