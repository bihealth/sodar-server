"""UI tests for the landingzones app"""

from django.test import override_settings
from django.urls import reverse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_ui import TestUIBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_sheet_config import SheetConfigMixin

from landingzones.tests.test_models import LandingZoneMixin


app_settings = AppSettingAPI()


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestProjectZoneView(
    SampleSheetIOMixin, SheetConfigMixin, LandingZoneMixin, TestUIBase
):
    """ProjectZoneView UI tests"""

    investigation = None
    study = None
    assay = None

    def _setup_investigation(self):
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def _assert_element(self, by, element, expected=True):
        """Assert element existence for an already logged in user"""
        # TODO: Add this into TestUIBase (see bihealth/sodar-core#1104)
        if expected:
            self.assertIsNotNone(self.selenium.find_element(by, element))
        else:
            with self.assertRaises(NoSuchElementException):
                self.selenium.find_element(by, element)

    def _assert_btn_enabled(self, element, expected=True):
        """Assert button is enabled"""
        if expected:
            self.assertNotIn('disabled', element.get_attribute('class'))
        else:
            self.assertIn('disabled', element.get_attribute('class'))

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
        self.url = reverse(
            'landingzones:list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_render_no_sheets(self):
        """Test ProjectZoneView rendering with no sheets"""
        # NOTE: Only testing with owner as this doesn't depend on user
        self.login_and_redirect(self.user_owner, self.url)
        self._assert_element(By.ID, 'sodar-lz-alert-archive', False)
        self._assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-sheets', True)
        self._assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', False)

    def test_render_no_colls(self):
        """Test ProjectZoneView with investigation but no colls"""
        self._setup_investigation()
        self.assertIsNotNone(self.investigation)
        self.login_and_redirect(self.user_owner, self.url)
        self._assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-colls', True)
        self._assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', False)

    def test_render_no_zones(self):
        """Test ProjectZoneView with iRODS enabled but no zones"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_owner, self.url)
        self._assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-zones', True)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', False)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_render_disable(self):
        """Test ProjectZoneView with LANDINGZONES_DISABLE_FOR_USERS"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.login_and_redirect(self.user_owner, self.url)
        self._assert_element(By.ID, 'sodar-lz-alert-disable', True)
        self._assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', False)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_render_disable_superuser(self):
        """Test ProjectZoneView with LANDINGZONES_DISABLE_FOR_USERS as superuser"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'superuser_zone', self.project, self.superuser, self.assay
        )
        self.login_and_redirect(self.superuser, self.url)
        self._assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', True)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', False)

    def test_render_own_zone(self):
        """Test ProjectZoneView as contributor with own zone"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self._assert_element(By.ID, 'sodar-lz-alert-disable', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-sheets', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-colls', False)
        self._assert_element(By.ID, 'sodar-lz-alert-no-zones', False)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', True)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', False)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )

    def test_render_other_zone(self):
        """Test ProjectZoneView as owner with other zone"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_owner, self.url)
        # NOTE: Element for own zones is visible while table is empty
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', True)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', True)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 1)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )

    def test_render_both_zones_contrib(self):
        """Test ProjectZoneView as contributor with own and other zones"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', True)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', False)
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
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        owner_zone = self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        contrib_zone = self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_owner, self.url)
        self._assert_element(By.ID, 'sodar-lz-zone-list-own', True)
        self._assert_element(By.ID, 'sodar-lz-zone-list-other', True)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 2)
        self.assertEqual(
            zones[0].get_attribute('data-zone-uuid'),
            str(owner_zone.sodar_uuid),
        )
        self.assertEqual(
            zones[1].get_attribute('data-zone-uuid'),
            str(contrib_zone.sodar_uuid),
        )
        self._assert_element(By.CLASS_NAME, 'sodar-lz-zone-warn-access', False)

    def test_render_other_user_guest_access(self):
        """Test ProjectZoneView with guest access for other user"""
        self._setup_investigation()
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
        self._assert_element(By.CLASS_NAME, 'sodar-lz-zone-warn-access', True)

    def test_render_other_user_no_access(self):
        """Test ProjectZoneView with no project access for other user"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'owner_zone', self.project, self.user_owner, self.assay
        )
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        # Remove contributor's access
        self.contributor_as.delete()
        self.login_and_redirect(self.user_owner, self.url)
        zones = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )
        self.assertEqual(len(zones), 2)
        self._assert_element(By.CLASS_NAME, 'sodar-lz-zone-warn-access', True)

    def test_zone_buttons(self):
        """Test ProjectZoneView zone buttons"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.login_and_redirect(self.user_contributor, self.url)
        zone = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )[0]
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate'),
            True,
        )
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move'),
            True,
        )
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-copy'),
            True,
        )
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-delete'),
            True,
        )

    def test_zone_buttons_archive(self):
        """Test ProjectZoneView zone buttons with archived project"""
        self._setup_investigation()
        self.investigation.irods_status = True
        self.investigation.save()
        self.make_landing_zone(
            'contrib_zone', self.project, self.user_contributor, self.assay
        )
        self.project.set_archive()
        self.login_and_redirect(self.user_contributor, self.url)
        zone = self.selenium.find_elements(
            By.CLASS_NAME, 'sodar-lz-zone-tr-existing'
        )[0]
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-validate'),
            False,
        )
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-move'),
            False,
        )
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-copy'),
            True,
        )
        self._assert_btn_enabled(
            zone.find_element(By.CLASS_NAME, 'sodar-lz-zone-btn-delete'),
            True,
        )
