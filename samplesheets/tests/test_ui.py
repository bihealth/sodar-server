"""UI tests for the samplesheets app"""
import json

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_ui import TestUIBase

from samplesheets.models import ISATab
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_sheet_config import (
    SheetConfigMixin,
    CONFIG_PATH_DEFAULT,
    CONFIG_PATH_UPDATED,
)


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
DEFAULT_WAIT_ID = 'sodar-ss-vue-content'

with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)

with open(CONFIG_PATH_UPDATED) as fp:
    CONFIG_DATA_UPDATED = json.load(fp)

IRODS_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_SKIP_MSG = 'Irodsbackend not enabled in settings'


# App settings API
app_settings = AppSettingAPI()


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

        op_div = self.selenium.find_element_by_id('sodar-ss-op-dropdown')
        op_div.click()
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'sodar-ss-op-item-edit'))
        )
        elem = op_div.find_element_by_id('sodar-ss-op-item-edit')
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
        self.selenium.find_element_by_id('sodar-ss-vue-btn-edit-finish').click()
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'sodar-ss-op-dropdown'))
        )

        if wait_for_study:
            WebDriverWait(self.selenium, self.wait_time).until(
                ec.presence_of_element_located((By.ID, 'sodar-ss-grid-study'))
            )

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
                self.selenium.find_element_by_id(
                    'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid)
                )
            )
            # Ensure error alert is not generated
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element_by_id('sodar-ss-alert-error')

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
                self.selenium.find_element_by_id('sodar-ss-alert-empty')
            )
            # Ensure no grids are present
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element_by_id(
                    'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid)
                )

    # NOTE: For further vue app tests, see samplesheets/vueapp/tests


class TestSampleSheetVersionListView(TestProjectSheetsVueAppBase):
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
            [self.default_user], self.url, 'sodar-ss-version-list', False
        )
        self.assert_element_exists(
            [self.default_user], self.url, 'sodar-ss-version-alert', True
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
