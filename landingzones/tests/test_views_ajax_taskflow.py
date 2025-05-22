"""Tests for Ajax API views in the landingzones app with Taskflow"""

import json
import os
import pytz

from django.conf import settings
from django.test import override_settings
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
from taskflowbackend.tests.base import TaskflowViewTestBase, HASH_SCHEME_SHA256

from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'landingzones'
ZONE_TITLE = '20190703_172456'
MISC_FILES_DIR = 'MiscFiles'
RESULTS_DIR = 'ResultsReports'
TRACK_HUB_DIR = 'TrackHubs'
ZONE_COLLS = [MISC_FILES_DIR, RESULTS_DIR, TRACK_HUB_DIR]
IRODS_TYPE_COLL = 'coll'
IRODS_TYPE_OBJ = 'obj'
TEST_OBJ_NAME = 'test1.txt'
TEST_OBJ_NAME2 = 'test2.txt'


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
        self.misc_path = os.path.join(self.zone_path, MISC_FILES_DIR)
        self.url = reverse(
            'landingzones:ajax_irods_list',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneIrodsListRetrieveAjaxView GET"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        with self.login(self.user_owner):
            response = self.client.get(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        expected = {
            'results': [
                {
                    'name': ZONE_COLLS[i],
                    'type': IRODS_TYPE_COLL,
                    'path': os.path.join(self.zone_path, ZONE_COLLS[i]),
                }
                for i in range(len(ZONE_COLLS))
            ],
            'count': 3,
            'page': 1,
            'page_count': 1,
            'next': '',
            'previous': '',
        }
        self.assertEqual(response.data, expected)

    def test_get_file(self):
        """Test GET with file in iRODS"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        coll = self.irods.collections.get(self.misc_path)
        irods_obj = self.make_irods_object(coll, TEST_OBJ_NAME)
        # NOTE: No .md5 file created here
        with self.login(self.user_owner):
            response = self.client.get(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        res = response.data['results']
        self.assertEqual(len(res), 4)
        expected = {
            'name': TEST_OBJ_NAME,
            'type': IRODS_TYPE_OBJ,
            'path': irods_obj.path,
            'size': 1024,
            'modify_time': irods_obj.modify_time.astimezone(
                pytz.timezone(settings.TIME_ZONE)
            ).strftime('%Y-%m-%d %H:%M'),
        }
        self.assertEqual(res[1], expected)

    def test_get_file_md5(self):
        """Test GET with file and corresponding MD5 file"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        coll = self.irods.collections.get(self.misc_path)
        irods_obj = self.make_irods_object(coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        with self.login(self.user_owner):
            response = self.client.get(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        # Data object and collection count should not increase
        self.assertEqual(response.data['count'], 4)
        res = response.data['results']
        self.assertEqual(len(res), 4)
        expected = {
            'name': TEST_OBJ_NAME,
            'type': IRODS_TYPE_OBJ,
            'path': irods_obj.path,
            'size': 1024,
            'modify_time': irods_obj.modify_time.astimezone(
                pytz.timezone(settings.TIME_ZONE)
            ).strftime('%Y-%m-%d %H:%M'),
        }
        self.assertEqual(res[1], expected)

    def test_get_empty(self):
        """Test GET with empty zone"""
        self.make_zone_taskflow(self.zone)  # No colls
        with self.login(self.user_owner):
            response = self.client.get(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        expected = {
            'results': [],
            'count': 0,
            'page': 1,
            'page_count': 0,
            'next': '',
            'previous': '',
        }
        self.assertEqual(response.data, expected)

    @override_settings(LANDINGZONES_FILE_LIST_PAGINATION=2)
    def test_get_paginate(self):
        """Test GET with pagination"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        coll = self.irods.collections.get(self.misc_path)
        self.make_irods_object(coll, TEST_OBJ_NAME)
        with self.login(self.user_owner):
            response = self.client.get(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['page_count'], 2)
        self.assertEqual(response.data['next'], self.url + '?page=2')
        self.assertEqual(response.data['previous'], '')
        res = response.data['results']
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['name'], MISC_FILES_DIR)
        self.assertEqual(res[1]['name'], TEST_OBJ_NAME)

    @override_settings(LANDINGZONES_FILE_LIST_PAGINATION=2)
    def test_get_paginate_second_page(self):
        """Test GET with pagination and second page"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        coll = self.irods.collections.get(self.misc_path)
        self.make_irods_object(coll, TEST_OBJ_NAME)
        with self.login(self.user_owner):
            response = self.client.get(self.url + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['page_count'], 2)
        self.assertEqual(response.data['next'], '')
        self.assertEqual(response.data['previous'], self.url + '?page=1')
        res = response.data['results']
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['name'], RESULTS_DIR)
        self.assertEqual(res[1]['name'], TRACK_HUB_DIR)

    @override_settings(LANDINGZONES_FILE_LIST_PAGINATION=2)
    def test_get_paginate_no_page(self):
        """Test GET with pagination and no page number"""
        self.make_zone_taskflow(self.zone, colls=ZONE_COLLS)
        coll = self.irods.collections.get(self.misc_path)
        self.make_irods_object(coll, TEST_OBJ_NAME)
        with self.login(self.user_owner):
            response = self.client.get(self.url)  # No querystring here
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        # We should get the first page
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['page_count'], 2)
        self.assertEqual(response.data['next'], self.url + '?page=2')
        self.assertEqual(response.data['previous'], '')
        res = response.data['results']
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['name'], MISC_FILES_DIR)
        self.assertEqual(res[1]['name'], TEST_OBJ_NAME)


class TestZoneChecksumStatusRetrieveAjaxView(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for ZoneChecksumStatusRetrieveAjaxView with iRODS and taskflow"""

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
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.make_zone_taskflow(self.zone, [MISC_FILES_DIR])
        # Set up helpers
        self.misc_path = os.path.join(self.zone_path, MISC_FILES_DIR)
        self.misc_coll = self.irods.collections.get(self.misc_path)
        self.url = reverse(
            'landingzones:ajax_irods_checksum',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )
        self.post_kw = {'content_type': 'application/json'}

    def test_post(self):
        """Test ZoneChecksumStatusRetrieveAjaxView POST"""
        obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(obj)
        post_data = {'paths': [obj.path]}
        with self.login(self.user_owner):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['checksum_status'], {obj.path: True})

    @override_settings(IRODS_HASH_SCHEME=HASH_SCHEME_SHA256)
    def test_post_checksum_sha256(self):
        """Test POST with SHA256 checksum file"""
        obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(obj, scheme=HASH_SCHEME_SHA256)
        post_data = {'paths': [obj.path]}
        with self.login(self.user_owner):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['checksum_status'], {obj.path: True})

    def test_post_no_checksum_file(self):
        """Test POST with no checksum file"""
        obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        # Not creating checksum file
        post_data = {'paths': [obj.path]}
        with self.login(self.user_owner):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['checksum_status'], {obj.path: False})

    def test_post_multiple(self):
        """Test POST with multiple files"""
        obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(obj)
        obj2 = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME2)
        # No checksum for data_obj2
        post_data = {'paths': [obj.path, obj2.path]}
        with self.login(self.user_owner):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['checksum_status'], {obj.path: True, obj2.path: False}
        )

    def test_post_path_outside_zone(self):
        """Test POST with path outside zone (should fail)"""
        path = os.path.join(
            self.irods_backend.get_sample_path(self.project), TEST_OBJ_NAME
        )
        post_data = {'paths': [path]}
        with self.login(self.user_owner):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 400)

    def test_post_invalid_path(self):
        """Test POST with invalid path (should fail)"""
        path = os.path.join(self.zone_path, '..', TEST_OBJ_NAME)
        post_data = {'paths': [path]}
        with self.login(self.user_owner):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 400)

    def test_post_no_paths(self):
        """Test POST with no paths"""
        post_data = {'paths': []}
        with self.login(self.user_owner):
            response = self.client.post(
                self.url, data=json.dumps(post_data), **self.post_kw
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['checksum_status'], {})
