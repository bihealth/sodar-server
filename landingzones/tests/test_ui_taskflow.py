"""UI tests for the landingzones app with taskflow"""

import pytz
import time

from irods.path import iRODSPath

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views import MISC_FILES_COLL

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowUITestBase

from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import (
    LandingZoneTaskflowMixin,
    ZONE_TITLE,
    ZONE_DESC,
)


app_settings = AppSettingAPI()


# Local constants
APP_NAME = 'landingzones'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TEST_OBJ_NAME = 'test1.txt'
TEST_COLL_NAME = 'test_coll'
MODAL_CONTAINER_ID = 'sodar-lz-obj-list-container'
MODAL_EMPTY_ID = 'sodar-lz-obj-list-empty'
MODAL_BTN_CLASS = 'sodar-lz-list-modal-btn'
MODAL_HEADER_TITLE_ID = 'sodar-lz-obj-list-title'
MODAL_HEADER_PAGE_ID = 'sodar-lz-obj-list-title-page'
MODAL_HEADER_TOGGLE_BTN_ID = 'sodar-lz-obj-list-coll-toggle-btn'
MODAL_TABLE_ID = 'sodar-lz-obj-list-table'
MODAL_COLL_ITEM_CLASS = 'sodar-lz-obj-list-item-coll'
MODAL_OBJ_ITEM_CLASS = 'sodar-lz-obj-list-item-obj'
MODAL_CHK_ICON_CLASS = 'sodar-lz-obj-list-checksum-icon'
MODAL_PAGINATE_ID = 'sodar-lz-obj-pagination'
MODAL_PAGE_PREV_ID = 'sodar-lz-modal-page-item-prev'
MODAL_PAGE_NEXT_ID = 'sodar-lz-modal-page-item-next'


class TestZoneFileListModal(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    TaskflowUITestBase,
):
    """Tests for landing zone iRODS file list modal UI"""

    def _open_modal(self, wait_by: str, wait_selector: str):
        """
        Open the landing zone iRODS file list modal for self.zone. Waits for
        a specific element to be present before returning modal content
        container.

        :param wait_by: Locator for element waiting
        :param wait_selector: Selcetor for element waiting
        :return: Modal content container element
        """
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.element_to_be_clickable((By.CLASS_NAME, MODAL_BTN_CLASS))
        )
        btn_elem = self.selenium.find_element(By.CLASS_NAME, MODAL_BTN_CLASS)
        btn_elem.click()
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, MODAL_CONTAINER_ID))
        )
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((wait_by, wait_selector))
        )
        return self.selenium.find_element(By.CLASS_NAME, 'modal-content')

    def _wait_for_header_page(self, modal_elem: WebElement, expected):
        """Wait for expected text in the header pagination element"""
        for i in range(0, 25):
            h_page_elem = modal_elem.find_element(By.ID, MODAL_HEADER_PAGE_ID)
            if h_page_elem.text == expected:
                break
            time.sleep(0.5)
        self.assertEqual(h_page_elem.text, expected)

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)
        # Create zone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_render_empty(self):
        """Test rendering modal with empty zone"""
        self.make_zone_taskflow(self.zone)  # No colls
        self.login_and_redirect(self.user_owner, self.url)
        # Ensure we can see the zone
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)
        # Open modal
        modal_elem = self._open_modal(By.ID, MODAL_EMPTY_ID)

        # Assert header
        title_elem = modal_elem.find_element(By.ID, MODAL_HEADER_TITLE_ID)
        self.assertEqual(title_elem.text, f'Files in iRODS: {self.zone.title}')
        page_elem = modal_elem.find_element(By.ID, MODAL_HEADER_PAGE_ID)
        self.assertEqual(page_elem.text, '')
        toggle_elem = modal_elem.find_element(By.ID, MODAL_HEADER_TOGGLE_BTN_ID)
        self.assertEqual(toggle_elem.get_attribute('title'), 'Hide collections')

        # Assert table elements
        table_elem = modal_elem.find_element(By.ID, MODAL_TABLE_ID)
        with self.assertRaises(NoSuchElementException):
            table_elem.find_element(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        with self.assertRaises(NoSuchElementException):
            table_elem.find_element(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)
        self.assertIsNotNone(table_elem.find_element(By.ID, MODAL_EMPTY_ID))
        empty_elem = table_elem.find_element(By.ID, MODAL_EMPTY_ID)
        self.assertEqual(
            empty_elem.text, 'No collections or files in this landing zone.'
        )

        # Assert pagination (should not be visible)
        page_elem = modal_elem.find_element(By.ID, MODAL_PAGINATE_ID)
        with self.assertRaises(NoSuchElementException):
            page_elem.find_element(By.ID, MODAL_PAGE_PREV_ID)
        with self.assertRaises(NoSuchElementException):
            page_elem.find_element(By.ID, MODAL_PAGE_NEXT_ID)

    def test_render_coll(self):
        """Test rendering modal with collection"""
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)

        # Assert collection row content
        coll_elem = modal_elem.find_element(
            By.CLASS_NAME, MODAL_COLL_ITEM_CLASS
        )
        coll_icon = coll_elem.find_element(
            By.CLASS_NAME, 'sodar-lz-obj-list-icon-coll'
        )
        self.assertEqual(
            coll_icon.get_attribute('data-icon'), 'mdi:folder-open'
        )

        # Assert column content
        columns = coll_elem.find_elements(By.TAG_NAME, 'td')
        self.assertEqual(len(columns), 3)  # Middle columns joined with colspan
        link = columns[0].find_element(By.TAG_NAME, 'a')
        self.assertEqual(link.text, MISC_FILES_COLL)
        self.assertTrue(
            link.get_attribute('href').endswith(
                iRODSPath(self.zone_path, MISC_FILES_COLL)
            )
        )
        self.assertEqual(columns[1].text, '')

        # Assert no object row displayed
        with self.assertRaises(NoSuchElementException):
            modal_elem.find_element(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)

        # Assert pagination (visible but disabled)
        page_elem = modal_elem.find_element(By.ID, MODAL_PAGINATE_ID)
        prev_elem = page_elem.find_element(By.ID, MODAL_PAGE_PREV_ID)
        self.assertEqual(prev_elem.get_attribute('class'), 'page-item disabled')
        next_elem = page_elem.find_element(By.ID, MODAL_PAGE_NEXT_ID)
        self.assertEqual(next_elem.get_attribute('class'), 'page-item disabled')

    def test_render_coll_nested(self):
        """Test rendering modal with nested collection"""
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        nested_path = iRODSPath(self.zone_path, MISC_FILES_COLL, TEST_COLL_NAME)
        self.irods.collections.create(nested_path)
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 2)
        self.assertEqual(
            colls[0]
            .find_elements(By.TAG_NAME, 'td')[0]
            .find_element(By.TAG_NAME, 'a')
            .text,
            MISC_FILES_COLL,
        )
        self.assertEqual(
            colls[1]
            .find_elements(By.TAG_NAME, 'td')[0]
            .find_element(By.TAG_NAME, 'a')
            .text,
            iRODSPath(MISC_FILES_COLL, TEST_COLL_NAME, absolute=False),
        )  # Subcoll path should be displayed for nested coll

    def test_render_obj(self):
        """test rendering modal with data object"""
        self.make_zone_taskflow(self.zone)
        zone_coll = self.irods.collections.get(self.zone_path)
        data_obj = self.make_irods_object(zone_coll, TEST_OBJ_NAME)
        # NOTE: No checksum file generated
        self.login_and_redirect(self.user_owner, self.url)
        # NOTE: Wait for checksum icons to be loaded by separate Ajax call
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_CHK_ICON_CLASS)

        with self.assertRaises(NoSuchElementException):
            modal_elem.find_element(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        obj_elem = modal_elem.find_element(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)
        obj_icon = obj_elem.find_element(
            By.CLASS_NAME, 'sodar-lz-obj-list-icon-obj'
        )
        self.assertEqual(
            obj_icon.get_attribute('data-icon'), 'mdi:file-document-outline'
        )
        columns = obj_elem.find_elements(By.TAG_NAME, 'td')
        self.assertEqual(len(columns), 5)
        link = columns[0].find_element(By.TAG_NAME, 'a')
        self.assertEqual(link.text, TEST_OBJ_NAME)
        self.assertTrue(link.get_attribute('href').endswith(data_obj.path))
        self.assertEqual(columns[1].text, '1.0 kB')
        self.assertEqual(
            columns[2].text,
            data_obj.modify_time.astimezone(
                pytz.timezone(settings.TIME_ZONE)
            ).strftime('%Y-%m-%d %H:%M'),
        )
        self.assertEqual(
            columns[3]
            .find_element(By.CLASS_NAME, MODAL_CHK_ICON_CLASS)
            .get_attribute('data-icon'),
            'mdi:close-thick',
        )

    def test_render_obj_checksum(self):
        """test rendering modal with data object and checksum file"""
        self.make_zone_taskflow(self.zone)
        zone_coll = self.irods.collections.get(self.zone_path)
        data_obj = self.make_irods_object(zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(data_obj)
        self.login_and_redirect(self.user_owner, self.url)
        # NOTE: Wait for checksum icons to be loaded by separate Ajax call
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_CHK_ICON_CLASS)

        with self.assertRaises(NoSuchElementException):
            modal_elem.find_element(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        # Assert only one data object is shown
        objs = modal_elem.find_elements(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)
        self.assertEqual(len(objs), 1)
        columns = objs[0].find_elements(By.TAG_NAME, 'td')
        self.assertEqual(
            columns[3]
            .find_element(By.CLASS_NAME, MODAL_CHK_ICON_CLASS)
            .get_attribute('data-icon'),
            'mdi:check-bold',
        )

    def test_render_coll_obj(self):
        """Test rendering modal with collection and data object"""
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        # Create object in subcoll
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)

        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 1)
        objs = modal_elem.find_elements(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)
        self.assertEqual(len(objs), 1)
        # Assert object name column contains subpath
        obj_title_col = objs[0].find_elements(By.TAG_NAME, 'td')[0]
        self.assertEqual(
            obj_title_col.find_element(By.TAG_NAME, 'a').text,
            iRODSPath(MISC_FILES_COLL, TEST_OBJ_NAME, absolute=False),
        )

    def test_render_disable_colls_empty(self):
        """Test rendering modal with disabled collection display and empty zone"""
        app_settings.set(
            APP_NAME, 'zone_file_list_colls', False, user=self.user_owner
        )
        self.make_zone_taskflow(self.zone)
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.ID, MODAL_EMPTY_ID)
        self.assertIsNotNone(modal_elem.find_element(By.ID, MODAL_EMPTY_ID))
        empty_elem = modal_elem.find_element(By.ID, MODAL_EMPTY_ID)
        self.assertEqual(empty_elem.text, 'No files in this landing zone.')

    def test_render_disable_colls_obj(self):
        """Test rendering  modal with disabled collection display and data object"""
        app_settings.set(
            APP_NAME, 'zone_file_list_colls', False, user=self.user_owner
        )
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)

        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 0)  # Should not be included
        objs = modal_elem.find_elements(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)
        self.assertEqual(len(objs), 1)
        toggle_elem = modal_elem.find_element(By.ID, MODAL_HEADER_TOGGLE_BTN_ID)
        self.assertEqual(toggle_elem.get_attribute('title'), 'Show collections')

    def test_update_disable_colls(self):
        """Test updating collection display setting"""
        app_settings.set(
            APP_NAME, 'zone_file_list_colls', False, user=self.user_owner
        )
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.ID, MODAL_EMPTY_ID)

        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 0)
        self.assertIsNotNone(modal_elem.find_element(By.ID, MODAL_EMPTY_ID))
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.element_to_be_clickable((By.ID, MODAL_HEADER_TOGGLE_BTN_ID))
        )
        toggle_elem = modal_elem.find_element(By.ID, MODAL_HEADER_TOGGLE_BTN_ID)
        self.assertEqual(toggle_elem.get_attribute('title'), 'Show collections')
        # Enable collection display and assert results
        toggle_elem.click()
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
            )
        )
        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 1)
        with self.assertRaises(NoSuchElementException):
            modal_elem.find_element(By.ID, MODAL_EMPTY_ID)
        toggle_elem = modal_elem.find_element(By.ID, MODAL_HEADER_TOGGLE_BTN_ID)
        self.assertEqual(toggle_elem.get_attribute('title'), 'Hide collections')
        # Assert user setting has been updated
        self.assertEqual(
            app_settings.get(
                APP_NAME, 'zone_file_list_colls', user=self.user_owner
            ),
            True,
        )

    @override_settings(LANDINGZONES_FILE_LIST_PAGINATION=3)
    def test_render_pagination(self):
        """Test rendering modal with pagination"""
        self.make_zone_taskflow(self.zone)
        for i in range(0, 5):
            self.irods.collections.create(
                iRODSPath(self.zone_path, f'{TEST_COLL_NAME}{i}')
            )
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)

        title_elem = modal_elem.find_element(By.ID, MODAL_HEADER_TITLE_ID)
        self.assertEqual(title_elem.text, f'Files in iRODS: {self.zone.title}')
        h_page_elem = modal_elem.find_element(By.ID, MODAL_HEADER_PAGE_ID)
        self.assertEqual(h_page_elem.text, '(1/2)')
        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 3)
        page_elem = modal_elem.find_element(By.ID, MODAL_PAGINATE_ID)
        prev_elem = page_elem.find_element(By.ID, MODAL_PAGE_PREV_ID)
        self.assertEqual(prev_elem.get_attribute('class'), 'page-item disabled')
        next_elem = page_elem.find_element(By.ID, MODAL_PAGE_NEXT_ID)
        self.assertEqual(next_elem.get_attribute('class'), 'page-item')

    @override_settings(LANDINGZONES_FILE_LIST_PAGINATION=3)
    def test_update_pagination(self):
        """Test updating pagination"""
        self.make_zone_taskflow(self.zone)
        for i in range(0, 5):
            self.irods.collections.create(
                iRODSPath(self.zone_path, f'{TEST_COLL_NAME}{i}')
            )
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)

        h_page_elem = modal_elem.find_element(By.ID, MODAL_HEADER_PAGE_ID)
        self.assertEqual(h_page_elem.text, '(1/2)')
        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 3)
        self.assertEqual(
            colls[0]
            .find_elements(By.TAG_NAME, 'td')[0]
            .find_element(By.TAG_NAME, 'a')
            .text,
            f'{TEST_COLL_NAME}0',
        )

        # Navigate to page 2
        next_elem = modal_elem.find_element(By.ID, MODAL_PAGE_NEXT_ID)
        next_elem.click()

        self._wait_for_header_page(modal_elem, '(2/2)')
        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 2)
        self.assertEqual(
            colls[0]
            .find_elements(By.TAG_NAME, 'td')[0]
            .find_element(By.TAG_NAME, 'a')
            .text,
            f'{TEST_COLL_NAME}3',
        )
        prev_elem = modal_elem.find_element(By.ID, MODAL_PAGE_PREV_ID)
        self.assertEqual(prev_elem.get_attribute('class'), 'page-item')
        next_elem = modal_elem.find_element(By.ID, MODAL_PAGE_NEXT_ID)
        self.assertEqual(next_elem.get_attribute('class'), 'page-item disabled')

    @override_settings(LANDINGZONES_FILE_LIST_PAGINATION=3)
    def test_update_disable_colls_pagination(self):
        """Test updating collection display setting with pagination"""
        self.make_zone_taskflow(self.zone)
        for i in range(0, 5):
            self.irods.collections.create(
                iRODSPath(self.zone_path, f'{TEST_COLL_NAME}{i}')
            )
        zone_coll = self.irods.collections.get(self.zone_path)
        self.make_irods_object(zone_coll, TEST_OBJ_NAME)
        self.login_and_redirect(self.user_owner, self.url)
        modal_elem = self._open_modal(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)

        next_elem = modal_elem.find_element(By.ID, MODAL_PAGE_NEXT_ID)
        next_elem.click()
        self._wait_for_header_page(modal_elem, '(2/2)')
        toggle_elem = modal_elem.find_element(By.ID, MODAL_HEADER_TOGGLE_BTN_ID)
        toggle_elem.click()

        self._wait_for_header_page(modal_elem, '')
        h_page_elem = modal_elem.find_element(By.ID, MODAL_HEADER_PAGE_ID)
        self.assertEqual(h_page_elem.text, '')
        # Only object should be visible
        colls = modal_elem.find_elements(By.CLASS_NAME, MODAL_COLL_ITEM_CLASS)
        self.assertEqual(len(colls), 0)
        objs = modal_elem.find_elements(By.CLASS_NAME, MODAL_OBJ_ITEM_CLASS)
        self.assertEqual(len(objs), 1)
        prev_elem = modal_elem.find_element(By.ID, MODAL_PAGE_PREV_ID)
        self.assertEqual(prev_elem.get_attribute('class'), 'page-item disabled')
        next_elem = modal_elem.find_element(By.ID, MODAL_PAGE_NEXT_ID)
        self.assertEqual(next_elem.get_attribute('class'), 'page-item disabled')
