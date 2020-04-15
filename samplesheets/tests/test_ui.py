"""UI tests for the samplesheets app"""
import json

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from unittest import skipIf

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_ui import TestUIBase

from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_utils import (
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
                self.selenium.find_element_by_id('sodar-ss-vue-alert-error')

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
                self.selenium.find_element_by_id('sodar-ss-vue-alert-empty')
            )
            # Ensure no grids are present
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element_by_id(
                    'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid)
                )

    def test_overview(self):
        """Test rendering the overview view"""
        self._login_and_render(self.default_user, url_suffix='#/overview')

        # Ensure the overview elements exist
        self.assertIsNotNone(
            self.selenium.find_element_by_id('sodar-ss-overview-investigation')
        )
        self.assertIsNotNone(
            self.selenium.find_element_by_id(
                'sodar-ss-overview-study-{}'.format(self.study.sodar_uuid)
            )
        )
        self.assertIsNotNone(
            self.selenium.find_element_by_id('sodar-ss-overview-stats')
        )

    # TODO: Test overview redirect if no ISAtab is available (pending #496)

    def test_nav_tabs(self):
        """Test rendering the navigation tabs"""
        self._login_and_render(self.default_user)

        self.assertIsNotNone(
            self.selenium.find_element_by_id('sodar-ss-nav-tabs')
        )

    def test_nav_tabs_no_sheet(self):
        """Test rendering the navigation tabs with no ISAtab"""
        self.investigation.delete()
        self._login_and_render(self.default_user)

        with self.assertRaises(NoSuchElementException):
            self.assertIsNotNone(
                self.selenium.find_element_by_id('sodar-ss-nav-tabs')
            )

    def test_nav_dropdown(self):
        """Test rendering the navigation dropdown"""
        self._login_and_render(self.default_user)

        nav_elem = self.selenium.find_element_by_id('sodar-ss-nav-dropdown')
        nav_btn = nav_elem.find_element_by_tag_name('button')
        nav_links = nav_elem.find_elements_by_class_name('sodar-ss-nav-item')

        self.assertEqual(nav_btn.is_enabled(), True)
        self.assertEqual(len(nav_links), 3)

    def test_nav_dropdown_no_sheet(self):
        """Test rendering the navigation dropdown with no ISAtab"""
        self.investigation.delete()
        self._login_and_render(self.default_user)

        elem = self.selenium.find_element_by_id(
            'sodar-ss-nav-dropdown'
        ).find_element_by_tag_name('button')

        self.assertEqual(elem.is_enabled(), False)

    def test_op_dropdown(self):
        """Test the operations dropdown"""
        users = [
            (self.superuser, 7),
            (self.owner_as.user, 7),
            (self.delegate_as.user, 7),
            (self.contributor_as.user, 7),
            (self.guest_as.user, 6),  # Links available but disabled
        ]

        for user in users:
            self._login_and_render(user[0])

            nav_elem = self.selenium.find_element_by_id('sodar-ss-op-dropdown')
            nav_links = nav_elem.find_elements_by_class_name('sodar-ss-op-item')
            enabled_state = False if user == self.guest_as.user else True

            self.assertEqual(nav_elem.is_enabled(), enabled_state)
            self.assertEqual(len(nav_links), user[1])

    def test_navigation_from_tabs(self):
        """Test navigation from tabs"""
        self._login_and_render(self.default_user)

        # Navigate to overview
        ov_tab = self.selenium.find_element_by_id('sodar-ss-tab-overview')
        ov_link = ov_tab.find_element_by_tag_name('a')
        ov_link.click()

        # Wait and assert overview
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.ID, 'sodar-ss-overview-investigation')
            )
        )
        self.assertIsNotNone(
            self.selenium.find_element_by_id('sodar-ss-overview-investigation')
        )
        self.assertEqual(self._get_route(), '/overview')

        # Navigate back to study
        study_tab = self.selenium.find_element_by_id(
            'sodar-ss-tab-study-{}'.format(self.study.sodar_uuid)
        )
        study_link = study_tab.find_element_by_tag_name('a')
        study_link.click()

        # Wait and assert presence of study
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'sodar-ss-grid-study'))
        )
        self.assertIsNotNone(
            self.selenium.find_element_by_id('sodar-ss-grid-study')
        )
        self.assertEqual(
            self._get_route(), '/study/{}'.format(self.study.sodar_uuid)
        )

    def test_navigation_from_dropdown(self):
        """Test navigation from dropdown"""
        self._login_and_render(self.default_user)
        dd_btn = self.selenium.find_element_by_id('sodar-ss-nav-dropdown')

        # Open dropdown
        dd_btn.click()

        # Navigate to overview
        ov_link = self.selenium.find_element_by_id('sodar-ss-nav-overview')
        ov_link.click()

        # Wait and assert overview
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.ID, 'sodar-ss-overview-investigation')
            )
        )
        self.assertIsNotNone(
            self.selenium.find_element_by_id('sodar-ss-overview-investigation')
        )
        self.assertEqual(self._get_route(), '/overview')

        # Open dropdown
        dd_btn.click()

        # Navigate to study
        study_link = self.selenium.find_element_by_id(
            'sodar-ss-nav-study-{}'.format(self.study.sodar_uuid)
        )
        study_link.click()

        # Wait and assert presence of study
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'sodar-ss-grid-study'))
        )
        self.assertIsNotNone(
            self.selenium.find_element_by_id('sodar-ss-grid-study')
        )
        self.assertEqual(
            self._get_route(), '/study/{}'.format(self.study.sodar_uuid)
        )

        # Open dropdown
        dd_btn.click()

        # Navigate to assay
        assay_link = self.selenium.find_element_by_id(
            'sodar-ss-nav-assay-{}'.format(self.assay.sodar_uuid)
        )
        assay_link.click()

        # Wait and assert presence of study & assay
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'sodar-ss-grid-study'))
        )
        self.assertIsNotNone(
            self.selenium.find_element_by_id(
                'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid)
            )
        )
        self.assertEqual(
            self._get_route(), '/assay/{}'.format(self.assay.sodar_uuid)
        )

    # TODO: Test study links with ISAtab examples using BIH configs (see #434)

    # TODO: Test with plugin-containing ISAtab example (see #434)
    def test_assay_shortcuts_no_colls(self):
        """Test assay shortcuts table with no iRODS collections"""
        self._login_and_render(self.default_user)

        # Assert the table exists
        with self.assertRaises(NoSuchElementException):
            self.assertIsNotNone(
                self.selenium.find_element_by_class_name(
                    'sodar-ss-vue-assay-shortcut-card'
                )
            )

    @skipIf(not IRODS_ENABLED, IRODS_SKIP_MSG)
    def test_assay_shortcuts_with_colls(self):
        """Test assay shortcuts table with iRODS collections"""
        self.investigation.irods_status = True  # Fake the coll creation
        self.investigation.save()

        self._login_and_render(self.default_user)

        # Assert the table exists
        self.assertIsNotNone(
            self.selenium.find_element_by_class_name(
                'sodar-ss-vue-assay-shortcut-card'
            )
        )
        self.assertEqual(
            len(
                self.selenium.find_elements_by_class_name(
                    'sodar-ss-vue-assay-shortcut'
                )
            ),
            2,
        )

    # TODO: Test with realistic ISAtab examples using BIH configs (see #434)
    def test_assay_links_no_colls(self):
        """Test assay links column with no iRODS collections"""
        self._login_and_render(self.default_user)

        assay_grid = self.selenium.find_element_by_id(
            'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid)
        )

        # Assert the link column exists
        with self.assertRaises(NoSuchElementException):
            self.assertIsNotNone(
                assay_grid.find_element_by_class_name(
                    'sodar-ss-data-links-header'
                )
            )

    def test_assay_links_with_colls(self):
        """Test assay links column with iRODS collections"""
        self.investigation.irods_status = True  # Fake the coll creation
        self.investigation.save()

        self._login_and_render(self.default_user)

        assay_grid = self.selenium.find_element_by_id(
            'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid)
        )

        # Assert the link column exists
        self.assertIsNotNone(
            assay_grid.find_element_by_class_name('sodar-ss-data-links-header')
        )

    def test_irods_buttons_no_colls(self):
        """Test study/assay iRODS button status with no iRODS collections"""
        self._login_and_render(self.default_user)

        # Check study buttons
        study_header = self.selenium.find_element_by_id(
            'sodar-ss-section-study'
        )
        study_btns = study_header.find_element_by_class_name(
            'sodar-ss-irods-links'
        ).find_elements_by_class_name('sodar-ss-irods-btn')

        for btn in study_btns:
            self.assertEqual(self._get_enabled_state(btn), False)

        # Check assay buttons
        assay_header = self.selenium.find_element_by_id(
            'sodar-ss-section-assay-{}'.format(self.assay.sodar_uuid)
        )
        assay_btns = assay_header.find_element_by_class_name(
            'sodar-ss-irods-links'
        ).find_elements_by_class_name('sodar-ss-irods-btn')

        for btn in assay_btns:
            self.assertEqual(self._get_enabled_state(btn), False)

    def test_irods_buttons_with_colls(self):
        """Test study/assay iRODS button status with iRODS collections"""
        self.investigation.irods_status = True  # Fake the coll creation
        self.investigation.save()

        self._login_and_render(self.default_user)

        # Check study buttons
        study_header = self.selenium.find_element_by_id(
            'sodar-ss-section-study'
        )
        study_btns = study_header.find_element_by_class_name(
            'sodar-ss-irods-links'
        ).find_elements_by_class_name('sodar-ss-irods-btn')

        for btn in study_btns:
            self.assertEqual(self._get_enabled_state(btn), True)

        # Check assay buttons
        assay_header = self.selenium.find_element_by_id(
            'sodar-ss-section-assay-{}'.format(self.assay.sodar_uuid)
        )
        assay_btns = assay_header.find_element_by_class_name(
            'sodar-ss-irods-links'
        ).find_elements_by_class_name('sodar-ss-irods-btn')

        for btn in assay_btns:
            self.assertEqual(self._get_enabled_state(btn), True)


class TestProjectSheetsEditModeDefault(TestProjectSheetsVueAppBase):
    """Tests for the samplesheets UI edit mode with a default config"""

    def setUp(self):
        super().setUp()
        app_settings.set_app_setting(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        self._setup_investigation(config_data=CONFIG_DATA_DEFAULT)

    def test_edit_mode(self):
        """Test entering and exiting edit mode"""
        self._login_and_render(self.default_user)
        self._start_editing()
        self.assertIsNotNone(
            self.selenium.find_element_by_xpath(
                '//span[contains(., "Edit Mode")]'
            )
        )
        self._stop_editing()
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element_by_xpath(
                '//span[contains(., "Edit Mode")]'
            )


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
        self.investigation.delete()
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
