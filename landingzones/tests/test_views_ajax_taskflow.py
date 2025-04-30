"""Tests for Ajax API views in the landingzones app with Taskflow"""

import os
import pytz

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
    SHEET_PATH,
)

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'landingzones'
ZONE_TITLE = '20190703_172456'
ZONE_COLLS = ['MiscFiles', 'ResultsReports', 'TrackHubs']
MISC_FILES_DIR = 'MiscFiles'
IRODS_TYPE_COLL = 'coll'
IRODS_TYPE_OBJ = 'obj'
TEST_OBJ_NAME = 'test1.txt'


class TestZoneIrodsListRetrieveAjaxView(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for ZoneIrodsListRetrieveAjaxView with iRODS and taskflow"""

    def setUp(self):
        super().setUp()
        # Make project with owner
        self.user_owner = self.make_user('user_owner')
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner,
            description='description',
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Create landing zone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description='Description',
            configuration=None,
            config_data={},
        )  # NOTE: make_zone_taskflow() called in tests
        # Set up helpers
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.url = reverse(
            'landingzones:ajax_irods_list',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneIrodsListRetrieveAjaxView GET"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': ZONE_COLLS[i],
                'type': IRODS_TYPE_COLL,
                'path': os.path.join(self.zone_path, ZONE_COLLS[i]),
            }
            for i in range(len(ZONE_COLLS))
        ]
        self.assertEqual(response.data['irods_data'], expected)

    def test_get_file(self):
        """Test GET with file in iRODS"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        coll = self.irods.collections.get(
            os.path.join(self.zone_path, MISC_FILES_DIR)
        )
        irods_obj = self.make_irods_object(coll, TEST_OBJ_NAME)
        # NOTE: No .md5 file created here
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rd = response.data['irods_data']
        self.assertEqual(len(rd), 4)
        expected = {
            'name': TEST_OBJ_NAME,
            'type': IRODS_TYPE_OBJ,
            'path': irods_obj.path,
            'md5_file': False,
            'size': 1024,
            'modify_time': irods_obj.modify_time.astimezone(
                pytz.timezone(settings.TIME_ZONE)
            ).strftime('%Y-%m-%d %H:%M'),
        }
        self.assertEqual(rd[1], expected)

    def test_get_file_md5(self):
        """Test GET with file and corresponding MD5 file"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        coll = self.irods.collections.get(
            os.path.join(self.zone_path, MISC_FILES_DIR)
        )
        irods_obj = self.make_irods_object(coll, TEST_OBJ_NAME)
        self.make_irods_md5_object(irods_obj)
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rd = response.data['irods_data']
        self.assertEqual(len(rd), 4)
        expected = {
            'name': TEST_OBJ_NAME,
            'type': IRODS_TYPE_OBJ,
            'path': irods_obj.path,
            'md5_file': True,
            'size': 1024,
            'modify_time': irods_obj.modify_time.astimezone(
                pytz.timezone(settings.TIME_ZONE)
            ).strftime('%Y-%m-%d %H:%M'),
        }
        self.assertEqual(rd[1], expected)

    def test_get_empty(self):
        """Test GET with empty zone"""
        self.make_zone_taskflow(self.zone)  # No colls
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['irods_data'], [])
