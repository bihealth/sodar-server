"""UI tests for the samplesheets app"""

# from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_ui import TestUIBase

from .test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
DEFAULT_WAIT_ID = 'sodar-ss-vue-content'


class TestProjectSheetsView(SampleSheetIOMixin, TestUIBase):
    """Tests for the project sheets view UI"""

    # Helper functions ---------------------------------------------------------

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

    # Setup --------------------------------------------------------------------

    def setUp(self):
        super().setUp()

        self.default_user = self.as_contributor.user

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    # Tests --------------------------------------------------------------------

    def test_render(self):
        """Test rendering the view with study and assay grids"""
        users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
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
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
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
            (self.superuser, 3),
            (self.as_owner.user, 3),
            (self.as_delegate.user, 3),
            (self.as_contributor.user, 3),
            (self.as_guest.user, 0),
        ]

        # TODO: Check if button is disabled (see issue #497)
        for user in users:
            self._login_and_render(user[0])

            nav_elem = self.selenium.find_element_by_id('sodar-ss-op-dropdown')
            nav_links = nav_elem.find_elements_by_class_name('sodar-ss-op-item')
            enabled_state = False if user == self.as_guest.user else True

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

    # TODO: Test with realistic ISAtab examples using BIH configs (see #434)
    def test_assay_links_no_dirs(self):
        """Test assay links column with no iRODS dirs"""
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

    def test_assay_links_with_dirs(self):
        """Test assay links column with iRODS dirs"""
        self.investigation.irods_status = True  # Fake the dir creation
        self.investigation.save()

        self._login_and_render(self.default_user)

        assay_grid = self.selenium.find_element_by_id(
            'sodar-ss-grid-assay-{}'.format(self.assay.sodar_uuid)
        )

        # Assert the link column exists
        self.assertIsNotNone(
            assay_grid.find_element_by_class_name('sodar-ss-data-links-header')
        )

    def test_irods_buttons_no_dirs(self):
        """Test study/assay iRODS button status with no iRODS dirs"""
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

    def test_irods_buttons_with_dirs(self):
        """Test study/assay iRODS button status with iRODS dirs"""
        self.investigation.irods_status = True  # Fake the dir creation
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
