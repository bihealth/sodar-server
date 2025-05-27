"""UI tests for the landingzones app"""

import random
import string
import time

from django.test import override_settings
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_ui import UITestBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_sheet_config import SheetConfigMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import ProjectLockMixin

from landingzones.constants import (
    ZONE_STATUS_CREATING,
    ZONE_STATUS_NOT_CREATED,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_DELETED,
)
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.views_ajax import STATUS_TRUNCATE_LEN


app_settings = AppSettingAPI()


# Local constants
APP_NAME = 'landingzones'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
PROHIBIT_NAME = 'file_name_prohibit'
PROHIBIT_VAL = 'bam,vcf.gz'
ZONE_CONFIG_NAME = 'bih_proteomics_smb'
ZONE_CONFIG_DISPLAY_NAME = 'BIH Proteomics SMB Server'


class LandingZoneUITestBase(
    SampleSheetIOMixin, SheetConfigMixin, LandingZoneMixin, UITestBase
):
    """Base class for landingzones UI tests"""

    investigation = None
    study = None
    assay = None

    def setup_investigation(self):
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def assert_element(self, by, element, expected=True):
        """Assert element existence for an already logged in user"""
        # TODO: Add this into UITestBase (see bihealth/sodar-core#1104)
        if expected:
            self.assertIsNotNone(self.selenium.find_element(by, element))
        else:
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element(by, element)

    def assert_enabled(self, element, expected=True):
        """Assert link or button is enabled"""
        if expected:
            self.assertNotIn('disabled', element.get_attribute('class'))
        else:
            self.assertIn('disabled', element.get_attribute('class'))

    def wait_for_status(self, status_elem, status):
        """Wait for a specific status in the zone status element"""
        for i in range(0, 25):
            if status_elem.text == status:
                return
            time.sleep(1.0)
        raise Exception('Status not changed')

    def wait_for_status_update(self):
        """Wait for JQuery landing zone status updates to finish"""
        for i in range(0, 20):
            if self.selenium.execute_script('return window.zoneStatusUpdated'):
                return
            time.sleep(0.5)

    def setUp(self):
        super().setUp()
        # Users with access to landing zones
        self.zone_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]


class TestProjectZoneView(ProjectLockMixin, LandingZoneUITestBase):
    """UI tests for ProjectZoneView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render_no_sheets(self):
        """Test ProjectZoneView rendering with no sheets"""
        # NOTE: Only testing with owner as this doesn't depend on user
        self.login_and_redirect(self.user_owner, self.url)
        # Lock and limit alert elements exist regardless of status
        self.assert_element(By.ID, 'sodar-lz-alert-lock', True)
        elem = self.selenium.find_element(By.ID, 'sodar-lz-alert-lock')
        self.assertIn('d-none', elem.get_attribute('class'))
        self.assertNotIn('d-block', elem.get_attribute('class'))
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-validate-limit'
        )
        self.assertIn('d-none', elem.get_attribute('class'))
        self.assertNotIn('d-block', elem.get_attribute('class'))
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-create-limit'
        )
        self.assertIn('d-none', elem.get_attribute('class'))
        self.assertNotIn('d-block', elem.get_attribute('class'))
        create_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-create-limit'
        )
        badge_class = create_badge.get_attribute('class')
        self.assertIn('badge-info', badge_class)
        self.assertNotIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(create_badge.text, 'Unlimited')
        valid_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-validate-limit'
        )
        badge_class = valid_badge.get_attribute('class')
        self.assertIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(valid_badge.text, '0 / 4')
        self.assert_element(By.ID, 'sodar-lz-alert-archive', False)
        self.assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-sheets', True)
        self.assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', False)
        self.assert_element(By.ID, 'sodar-lz-zone-list', False)

    def test_render_no_colls(self):
        """Test ProjectZoneView with investigation but no colls"""
        self.setup_investigation()
        self.assertIsNotNone(self.investigation)
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-colls', True)
        self.assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', False)
        self.assert_element(By.ID, 'sodar-lz-zone-list', False)

    def test_render_no_zones(self):
        """Test ProjectZoneView with iRODS enabled but no zones"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-zones', True)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', True)
        self.assert_element(By.ID, 'sodar-lz-zone-list', False)

    def test_render_prohibit(self):
        """Test ProjectZoneView with no zones and file_name_prohibit enabled"""
        app_settings.set(
            APP_NAME, PROHIBIT_NAME, PROHIBIT_VAL, project=self.project
        )
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_owner, self.url)
        # This should still not be visible because there are no zones
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_render_disable(self):
        """Test ProjectZoneView with LANDINGZONES_DISABLE_FOR_USERS"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-disable', True)
        self.assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', False)
        self.assert_element(By.ID, 'sodar-lz-zone-list', False)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_render_disable_superuser(self):
        """Test ProjectZoneView with LANDINGZONES_DISABLE_FOR_USERS as superuser"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'superuser_zone', self.project, self.superuser, self.assay
        )
        self.login_and_redirect(self.superuser, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', True)
        self.assert_element(By.ID, 'sodar-lz-zone-list', True)

    def test_render_own_zone(self):
        """Test ProjectZoneView as contributor with own zone"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        create_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-create-limit'
        )
        badge_class = create_badge.get_attribute('class')
        self.assertIn('badge-info', badge_class)
        self.assertNotIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(create_badge.text, 'Unlimited')
        valid_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-validate-limit'
        )
        badge_class = valid_badge.get_attribute('class')
        self.assertIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(valid_badge.text, '0 / 4')
        self.assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self.assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', True)
        self.assert_element(By.ID, 'sodar-lz-zone-list', True)
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-status-truncate', False
        )
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-status-link', False)
        self.assert_element(By.CLASS_NAME, 'sodar-user-badge', False)
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-badge-config', False)
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-badge-warn-perms', False
        )
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )

    def test_render_own_zone_prohibit(self):
        """Test ProjectZoneView with own zone and prohibit enabled"""
        app_settings.set(
            APP_NAME, PROHIBIT_NAME, PROHIBIT_VAL, project=self.project
        )
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        # With zone list this alert should be visible
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', True)

    def test_render_other_zone(self):
        """Test ProjectZoneView as owner with other zone"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-zone-list', True)
        self.assert_element(By.CLASS_NAME, 'sodar-user-badge', True)
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-badge-config', False)
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-badge-warn-perms', False
        )
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )
        elem = self.selenium.find_element(By.CLASS_NAME, 'sodar-user-badge')
        self.assertEqual(elem.text, self.user_contributor.username)

    def test_render_both_zones_contrib(self):
        """Test ProjectZoneView as contributor with own and other zones"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-zone-list', True)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )

    def test_render_both_zones_owner(self):
        """Test ProjectZoneView as owner with own and other zones"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        owner_zone = self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)
        self.assert_element(By.ID, 'sodar-lz-zone-list', True)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 2)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )
        self.assertEqual(
            zones[1].get_attribute('data-zone-uuid'),
            str(owner_zone.sodar_uuid),
        )
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-badge-warn-perms', False
        )

    def test_render_other_user_guest_access(self):
        """Test ProjectZoneView with guest access for other user"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        # Update contributor's access to guest
        self.contributor_as.role = self.role_guest
        self.contributor_as.save()
        self.login_and_redirect(self.user_owner, self.url)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 2)
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-badge-warn-perms', True
        )

    def test_render_other_user_no_access(self):
        """Test ProjectZoneView with no project access for other user"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        # Remove contributor access
        self.contributor_as.delete()
        self.login_and_redirect(self.user_owner, self.url)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 2)
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-badge-warn-perms', True
        )

    def test_render_read_only_contrib(self):
        """Test ProjectZoneView with site read-only mode as contributor"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        app_settings.set('projectroles', 'site_read_only', True)
        self.login_and_redirect(self.user_contributor, self.url)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', False)
        zone = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate'),
            False,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move'),
            False,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-copy'),
            True,
        )
        with self.assertRaises(NoSuchElementException):
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-update')
        with self.assertRaises(NoSuchElementException):
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-delete')

    def test_render_read_only_superuser(self):
        """Test ProjectZoneView with site read-only mode as superuser"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        app_settings.set('projectroles', 'site_read_only', True)
        self.login_and_redirect(self.superuser, self.url)
        self.assert_element(By.ID, 'sodar-lz-btn-create-zone', True)
        zone = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-copy'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-update'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-delete'),
            True,
        )

    def test_render_locked(self):
        """Test ProjectZoneView with locked project"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.lock_project(self.project)
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-lock', True)
        elem = self.selenium.find_element(By.ID, 'sodar-lz-alert-lock')
        self.assertNotIn('d-none', elem.get_attribute('class'))
        self.assertIn('d-block', elem.get_attribute('class'))
        for elem in self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-btn-validate'
        ):
            self.assert_enabled(elem, True)
        for elem in self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-btn-move'
        ):
            self.assert_enabled(elem, False)

    def test_render_lock_update(self):
        """Test ProjectZoneView with updated lock status"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-lock', True)
        elem = self.selenium.find_element(By.ID, 'sodar-lz-alert-lock')
        self.assertIn('d-none', elem.get_attribute('class'))
        self.assertNotIn('d-block', elem.get_attribute('class'))
        for elem in self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-btn-validate'
        ):
            self.assert_enabled(elem, True)
        for elem in self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-btn-move'
        ):
            self.assert_enabled(elem, True)

        self.lock_project(self.project)

        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'd-block'))
        )
        elem = self.selenium.find_element(By.ID, 'sodar-lz-alert-lock')
        self.assertNotIn('d-none', elem.get_attribute('class'))
        self.assertIn('d-block', elem.get_attribute('class'))
        for elem in self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-btn-validate'
        ):
            self.assert_enabled(elem, True)
        for elem in self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-btn-move'
        ):
            self.assert_enabled(elem, False)

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_render_create_limit(self):
        """Test ProjectZoneView with zone creation limit reached"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.login_and_redirect(self.user_owner, self.url)
        create_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-create-limit'
        )
        badge_class = create_badge.get_attribute('class')
        self.assertNotIn('badge-info', badge_class)
        self.assertNotIn('badge-success', badge_class)
        self.assertIn('badge-warning', badge_class)
        self.assertEqual(create_badge.text, '1 / 1')
        self.assert_enabled(
            self.selenium.find_element(By.ID, 'sodar-lz-btn-create-zone'), False
        )
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-create-limit'
        )
        self.assertNotIn('d-none', elem.get_attribute('class'))
        self.assertIn('d-block', elem.get_attribute('class'))

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_render_create_limit_existing_finished(self):
        """Test ProjectZoneView with zone creation limit and finished zone"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_MOVED,
        )
        self.login_and_redirect(self.user_owner, self.url)
        create_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-create-limit'
        )
        badge_class = create_badge.get_attribute('class')
        self.assertNotIn('badge-info', badge_class)
        self.assertIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(create_badge.text, '0 / 1')
        self.assert_enabled(
            self.selenium.find_element(By.ID, 'sodar-lz-btn-create-zone'), True
        )
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-create-limit'
        )
        self.assertIn('d-none', elem.get_attribute('class'))
        self.assertNotIn('d-block', elem.get_attribute('class'))

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_render_create_limit_update(self):
        """Test ProjectZoneView with zone creation limit update"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        zone = self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )

        self.login_and_redirect(self.user_owner, self.url)
        create_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-create-limit'
        )
        badge_class = create_badge.get_attribute('class')
        self.assertNotIn('badge-info', badge_class)
        self.assertNotIn('badge-success', badge_class)
        self.assertIn('badge-warning', badge_class)
        self.assertEqual(create_badge.text, '1 / 1')
        self.assert_enabled(
            self.selenium.find_element(By.ID, 'sodar-lz-btn-create-zone'), False
        )
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-create-limit'
        )
        self.assertNotIn('d-none', elem.get_attribute('class'))
        self.assertIn('d-block', elem.get_attribute('class'))

        zone.set_status(ZONE_STATUS_MOVED)
        zone_status = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status'
        )
        self.wait_for_status(zone_status, ZONE_STATUS_MOVED)
        # HACK: Wait for badge to be updated
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.XPATH, '//*[contains(text(), "0 / 1")]')
            )
        )
        badge_class = create_badge.get_attribute('class')
        self.assertNotIn('badge-info', badge_class)
        self.assertIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(create_badge.text, '0 / 1')
        self.assert_enabled(
            self.selenium.find_element(By.ID, 'sodar-lz-btn-create-zone'), True
        )
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-create-limit'
        )
        self.assertIn('d-none', elem.get_attribute('class'))
        self.assertNotIn('d-block', elem.get_attribute('class'))

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_render_validate_limit(self):
        """Test ProjectZoneView with zone validation limit reached"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        zone2 = self.make_landing_zone(
            'owner_zone2',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.login_and_redirect(self.user_owner, self.url)
        valid_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-validate-limit'
        )
        badge_class = valid_badge.get_attribute('class')
        self.assertNotIn('badge-success', badge_class)
        self.assertIn('badge-warning', badge_class)
        self.assertEqual(valid_badge.text, '1 / 1')
        alert = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-validate-limit'
        )
        self.assertNotIn('d-none', alert.get_attribute('class'))
        self.assertIn('d-block', alert.get_attribute('class'))
        zone_tr = self.selenium.find_element(
            By.ID, f'sodar-lz-zone-dropdown-{zone2.sodar_uuid}'
        )
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate')
        self.assertIn('disabled', link.get_attribute('class'))
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move')
        self.assertIn('disabled', link.get_attribute('class'))

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_render_validate_limit_other_zone_finished(self):
        """Test ProjectZoneView with zone validation limit and other zone finished"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_MOVED,
        )
        zone2 = self.make_landing_zone(
            'owner_zone2',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.login_and_redirect(self.user_owner, self.url)
        valid_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-validate-limit'
        )
        badge_class = valid_badge.get_attribute('class')
        self.assertIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(valid_badge.text, '0 / 1')
        alert = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-validate-limit'
        )
        self.assertIn('d-none', alert.get_attribute('class'))
        self.assertNotIn('d-block', alert.get_attribute('class'))
        zone_tr = self.selenium.find_element(
            By.ID, f'sodar-lz-zone-dropdown-{zone2.sodar_uuid}'
        )
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate')
        self.assertNotIn('disabled', link.get_attribute('class'))
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move')
        self.assertNotIn('disabled', link.get_attribute('class'))

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_render_validate_limit_update(self):
        """Test ProjectZoneView with zone validation limit update"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        zone = self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        zone2 = self.make_landing_zone(
            'owner_zone2',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )

        self.login_and_redirect(self.user_owner, self.url)
        valid_badge = self.selenium.find_element(
            By.ID, 'sodar-lz-badge-validate-limit'
        )
        badge_class = valid_badge.get_attribute('class')
        self.assertNotIn('badge-success', badge_class)
        self.assertIn('badge-warning', badge_class)
        self.assertEqual(valid_badge.text, '1 / 1')
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-validate-limit'
        )
        self.assertNotIn('d-none', elem.get_attribute('class'))
        self.assertIn('d-block', elem.get_attribute('class'))
        zone_tr = self.selenium.find_element(
            By.ID, f'sodar-lz-zone-dropdown-{zone2.sodar_uuid}'
        )
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate')
        self.assertIn('disabled', link.get_attribute('class'))
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move')
        self.assertIn('disabled', link.get_attribute('class'))

        zone.set_status(ZONE_STATUS_MOVED)
        zone_status = self.selenium.find_element(
            By.ID, f'sodar-lz-zone-status-{zone.sodar_uuid}'
        )
        self.wait_for_status(zone_status, ZONE_STATUS_MOVED)

        badge_class = valid_badge.get_attribute('class')
        self.assertIn('badge-success', badge_class)
        self.assertNotIn('badge-warning', badge_class)
        self.assertEqual(valid_badge.text, '0 / 1')
        elem = self.selenium.find_element(
            By.ID, 'sodar-lz-alert-zone-validate-limit'
        )
        self.assertIn('d-none', elem.get_attribute('class'))
        self.assertNotIn('d-block', elem.get_attribute('class'))
        zone_tr = self.selenium.find_element(
            By.ID, f'sodar-lz-zone-dropdown-{zone2.sodar_uuid}'
        )
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate')
        self.assertNotIn('disabled', link.get_attribute('class'))
        link = zone_tr.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move')
        self.assertNotIn('disabled', link.get_attribute('class'))

    def test_render_zone_config(self):
        """Test ProjectZoneView with zone using special configuration"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            configuration=ZONE_CONFIG_NAME,
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self.assert_element(By.ID, 'sodar-lz-zone-list', True)
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-status-link', False)
        self.assert_element(By.CLASS_NAME, 'sodar-user-badge', False)
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-badge-config', True)
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-badge-warn-perms', False
        )
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )
        elem = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-badge-config'
        )
        self.assertEqual(elem.text, ZONE_CONFIG_DISPLAY_NAME)

    def test_status_truncated(self):
        """Test rendering truncated status"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        zone.set_status(
            ZONE_STATUS_ACTIVE,
            ''.join(
                random.choice(string.ascii_letters)
                for _ in range(STATUS_TRUNCATE_LEN * 2)
            ),
        )
        self.login_and_redirect(self.user_contributor, self.url)
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.CLASS_NAME, 'sodar-lz-zone-status-link')
            )
        )
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-zone-status-truncate', True
        )
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-status-link', True)

    def test_status_truncated_expand(self):
        """Test rendering expanded truncated status"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        status_info = ''.join(
            random.choice(string.ascii_letters)
            for _ in range(STATUS_TRUNCATE_LEN * 2)
        )
        zone.set_status(ZONE_STATUS_ACTIVE, status_info)
        self.login_and_redirect(self.user_contributor, self.url)
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.CLASS_NAME, 'sodar-lz-zone-status-link')
            )
        )
        elem = self.selenium.find_element(
            By.ID, f'sodar-lz-zone-status-info-{zone.sodar_uuid}'
        )
        self.assertNotEqual(elem.text, status_info)
        link = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status-link'
        )
        link.click()
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.invisibility_of_element_located(
                (By.CLASS_NAME, 'sodar-lz-zone-status-link')
            )
        )
        self.assertEqual(elem.text, status_info)

    def test_status_update(self):
        """Test ProjectZoneView with zone status update"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            status='ACTIVE',
        )
        mod_old_db = contrib_zone.date_modified.timestamp()

        self.login_and_redirect(self.user_contributor, self.url)

        zone_status = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status'
        )
        self.assertEqual(zone_status.text, ZONE_STATUS_ACTIVE)
        elem = self.selenium.find_element(By.CLASS_NAME, 'sodar-lz-zone-tr')
        mod_old_dom = elem.get_attribute('data-zone-modified')
        contrib_zone.set_status(ZONE_STATUS_VALIDATING)
        mod_new_db = contrib_zone.date_modified.timestamp()
        self.assertNotEqual(mod_old_db, mod_new_db)
        self.wait_for_status(zone_status, ZONE_STATUS_VALIDATING)
        self.assertEqual(zone_status.text, ZONE_STATUS_VALIDATING)
        mod_new_dom = elem.get_attribute('data-zone-modified')
        self.assertNotEqual(mod_old_dom, mod_new_dom)
        self.assertEqual(float(mod_new_dom), mod_new_db)

    def test_status_update_moved(self):
        """Test ProjectZoneView with zone status update to MOVED"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            status='ACTIVE',
        )
        self.login_and_redirect(self.user_contributor, self.url)
        zone_status = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status'
        )
        self.assertEqual(zone_status.text, ZONE_STATUS_ACTIVE)
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(
                By.CLASS_NAME, 'sodar-lz-zone-sample-link'
            )
        contrib_zone.set_status(ZONE_STATUS_MOVED)
        self.wait_for_status(zone_status, ZONE_STATUS_MOVED)
        self.assertEqual(zone_status.text, ZONE_STATUS_MOVED)
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.CLASS_NAME, 'sodar-lz-zone-sample-link')
            )
        )
        self.assertIsNotNone(
            self.selenium.find_element(
                By.CLASS_NAME, 'sodar-lz-zone-sample-link'
            )
        )

    def test_stats_deleted_owner(self):
        """Test ProjectZoneView stats badge on DELETED zone as owner"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        zone = self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.login_and_redirect(self.user_contributor, self.url)

        zone_status = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status'
        )
        zone_status_info = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status-info'
        )
        self.wait_for_status(zone_status, ZONE_STATUS_ACTIVE)
        self.assertTrue(
            zone_status_info.find_element(
                By.CLASS_NAME, 'sodar-irods-stats'
            ).is_displayed()
        )
        # Update status to deleted, stats badge should no longer be rendered
        zone.set_status(ZONE_STATUS_DELETED)
        self.wait_for_status(zone_status, ZONE_STATUS_DELETED)
        self.assertFalse(
            zone_status_info.find_element(
                By.CLASS_NAME, 'sodar-irods-stats'
            ).is_displayed()
        )

    def test_stats_deleted_superuser(self):
        """Test ProjectZoneView stats badge on DELETED zone as superuser"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        zone = self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.login_and_redirect(self.superuser, self.url)

        zone_status = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status'
        )
        zone_status_info = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status-info'
        )
        self.wait_for_status(zone_status, ZONE_STATUS_ACTIVE)
        self.assertTrue(
            zone_status_info.find_element(
                By.CLASS_NAME, 'sodar-irods-stats'
            ).is_displayed()
        )
        zone.set_status(ZONE_STATUS_DELETED)
        self.wait_for_status(zone_status, ZONE_STATUS_DELETED)
        self.assertFalse(
            zone_status_info.find_element(
                By.CLASS_NAME, 'sodar-irods-stats'
            ).is_displayed()
        )

    def test_zone_buttons(self):
        """Test ProjectZoneView zone buttons"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self.wait_for_status_update()
        zone = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )[0]
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-copy'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-delete'),
            True,
        )

    def test_zone_buttons_archive(self):
        """Test ProjectZoneView zone buttons with archived project"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.project.set_archive()
        self.login_and_redirect(self.user_contributor, self.url)
        self.wait_for_status_update()
        zone = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )[0]
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate'),
            False,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move'),
            False,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-copy'),
            True,
        )
        self.assert_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-delete'),
            True,
        )

    def test_zone_locked_superuser(self):
        """Test ProjectZoneView zone rendering for locked zone as superuser"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.assertEqual(zone.status, ZONE_STATUS_CREATING)
        self.login_and_redirect(self.superuser, self.url)
        self.wait_for_status_update()
        zone_elem = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )[0]
        self.assertNotIn(
            'disabled',
            zone_elem.find_element(
                By.CLASS_NAME, 'sodar-list-dropdown'
            ).get_attribute('class'),
        )
        self.assertNotIn(
            'text-muted',
            zone_elem.find_element(
                By.CLASS_NAME, 'sodar-lz-zone-title'
            ).get_attribute('class'),
        )
        self.assertNotIn(
            'text-muted',
            zone_elem.find_element(
                By.CLASS_NAME, 'sodar-lz-zone-status-info'
            ).get_attribute('class'),
        )
        class_names = [
            'sodar-lz-zone-btn-validate',
            'sodar-lz-zone-btn-move',
            'sodar-lz-zone-btn-copy',
            'sodar-lz-zone-btn-delete',
        ]
        for c in class_names:
            self.assert_enabled(zone_elem.find_element(By.CLASS_NAME, c), True)

    def test_zone_locked_contributor(self):
        """Test ProjectZoneView zone rendering for locked zone as contributor"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self.wait_for_status_update()
        zone_elem = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )[0]
        self.assertIn(
            'disabled',
            zone_elem.find_element(
                By.CLASS_NAME, 'sodar-list-dropdown'
            ).get_attribute('class'),
        )
        self.assertNotIn(
            'text-muted',
            zone_elem.find_element(
                By.CLASS_NAME, 'sodar-lz-zone-title'
            ).get_attribute('class'),
        )
        self.assertNotIn(
            'text-muted',
            zone_elem.find_element(
                By.CLASS_NAME, 'sodar-lz-zone-status-info'
            ).get_attribute('class'),
        )


# TODO: Add file list modal UI tests with Taskflow (see #2167, #2168)


class TestZoneCreateView(LandingZoneUITestBase):
    """UI tests for ZoneCreateView"""

    def setUp(self):
        super().setUp()
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.url = reverse(
            'landingzones:create', kwargs={'project': self.project.sodar_uuid}
        )

    def test_render(self):
        """Test ZoneCreateView rendering"""
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)

    def test_render_prohibit(self):
        """Test ZoneCreateView with file_name_prohibit enabled"""
        app_settings.set(
            APP_NAME, PROHIBIT_NAME, PROHIBIT_VAL, project=self.project
        )
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', True)


class TestZoneUpdateView(LandingZoneUITestBase):
    """UI tests for ZoneUpdateView"""

    def setUp(self):
        super().setUp()
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.zone = self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.url = reverse(
            'landingzones:update', kwargs={'landingzone': self.zone.sodar_uuid}
        )

    def test_render(self):
        """Test ZoneUpdateView rendering"""
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)

    def test_render_prohibit(self):
        """Test ZoneUpdateView with file_name_prohibit enabled"""
        app_settings.set(
            APP_NAME, PROHIBIT_NAME, PROHIBIT_VAL, project=self.project
        )
        self.login_and_redirect(self.superuser, self.url)
        # Not shown in update view
        self.assert_element(By.ID, 'sodar-lz-alert-prohibit', False)


class TestProjectDetailView(LandingZoneUITestBase):
    """UI tests for ProjectDetailView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'projectroles:detail',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render_no_zones(self):
        """Test ProjectDetailView with no zones"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_owner, self.url)
        self.assert_element(By.ID, 'sodar-lz-detail-table-no-zones', True)
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-tr-existing', False)

    def test_render_own_zone(self):
        """Test ProjectDetailView as contributor with own zone"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self.assert_element(By.ID, 'sodar-lz-detail-table-no-zones', False)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )

    def test_render_multiple_zones(self):
        """Test ProjectDetailView as contributor with multiple own zones"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.make_landing_zone(
            'contrib_zone2', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 2)

    def test_render_other_zone(self):
        """Test ProjectDetailView as contributor with other user's zone"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self.assert_element(By.ID, 'sodar-lz-detail-table-no-zones', True)
        self.assert_element(By.CLASS_NAME, 'sodar-lz-zone-tr-existing', False)

    def test_render_as_owner(self):
        """Test ProjectDetailView as owner with own and other zones"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        owner_zone = self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_owner, self.url)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)  # Only own zone should be visible
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(owner_zone.sodar_uuid),
        )

    def test_update_status(self):
        """Test ProjectDetailView with zone status update"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            status='ACTIVE',
        )
        self.login_and_redirect(self.user_contributor, self.url)
        zone_status = self.selenium.find_element(
            By.CLASS_NAME, 'sodar-lz-zone-status'
        )
        self.assertEqual(zone_status.text, ZONE_STATUS_ACTIVE)
        contrib_zone.set_status(ZONE_STATUS_VALIDATING)
        self.wait_for_status(zone_status, ZONE_STATUS_VALIDATING)
        self.assertEqual(zone_status.text, ZONE_STATUS_VALIDATING)


class TestHomeView(LandingZoneUITestBase):
    """Tests for HomeView landingzones content"""

    def _wait_for_elem(self, suffix):
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.CLASS_NAME, 'sodar-lz-project-list-' + suffix)
            )
        )

    def _assert_list_elem(self, suffix, expected):
        self.assert_element(
            By.CLASS_NAME, 'sodar-lz-project-list-' + suffix, expected
        )

    def setUp(self):
        super().setUp()
        self.url = reverse('home')

    def test_render_no_sheets(self):
        """Test project list rendering with no sheets"""
        self.login_and_redirect(self.user_owner, self.url)
        self._wait_for_elem('none')
        self._assert_list_elem('active', False)
        self._assert_list_elem('create', False)
        self._assert_list_elem('none', True)

    def test_render_no_colls(self):
        """Test project list rendering with sheets and no colls"""
        self.setup_investigation()
        self.login_and_redirect(self.user_owner, self.url)
        self._wait_for_elem('none')
        self._assert_list_elem('active', False)
        self._assert_list_elem('create', False)
        self._assert_list_elem('none', True)

    def test_render_no_zones(self):
        """Test project list rendering with iRODS enabled and no zones"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_owner, self.url)
        self._wait_for_elem('create')
        self._assert_list_elem('active', False)
        self._assert_list_elem('create', True)
        self._assert_list_elem('none', False)

    def test_render_no_zones_guest(self):
        """Test project list rendering with no zones as guest"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_guest, self.url)
        self._wait_for_elem('none')
        self._assert_list_elem('active', False)
        # Guest doesn't have perms to create
        self._assert_list_elem('create', False)
        self._assert_list_elem('none', True)

    def test_render_zone_own_active(self):
        """Test project list rendering with own active zone"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self._wait_for_elem('active')
        self._assert_list_elem('active', True)
        self._assert_list_elem('create', False)
        self._assert_list_elem('none', False)

    def test_render_zone_own_finished(self):
        """Test project list rendering with own finished zone"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone',
            self.project,
            self.user_contributor,
            self.assay,
            status=ZONE_STATUS_NOT_CREATED,
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self._wait_for_elem('create')
        self._assert_list_elem('active', False)
        self._assert_list_elem('create', True)
        self._assert_list_elem('none', False)

    def test_render_zone_other_as_contributor(self):
        """Test project list rendering with other user's zone as contributor"""
        self.setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone',
            self.project,
            self.user_owner,
            self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self._wait_for_elem('create')
        self._assert_list_elem('active', False)
        self._assert_list_elem('create', True)
        self._assert_list_elem('none', False)
