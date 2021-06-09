"""Tests for the API in the irodsbackend app with Taskflow and iRODS"""

import random
import string
from unittest import skipIf

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_views_taskflow import (
    TestTaskflowBase,
    TASKFLOW_ENABLED,
    TASKFLOW_SKIP_MSG,
)

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

from irodsbackend.api import IrodsAPI


# Global constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
IRODS_HOST = settings.IRODS_HOST
IRODS_PORT = settings.IRODS_PORT
IRODS_ZONE = settings.IRODS_ZONE
SAMPLE_COLL = settings.IRODS_SAMPLE_COLL
LANDING_ZONE_COLL = settings.IRODS_LANDING_ZONE_COLL
SERVER_AVAILABLE = 'Available'

SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20180503_172456_test_zone'
ZONE_DESC = 'description'
TEST_FILE_NAME = 'test1'
TEST_FILE_NAME2 = 'test2'


class TestIrodsBackendAPITaskflow(
    SampleSheetIOMixin,
    LandingZoneMixin,
    SampleSheetTaskflowMixin,
    TestTaskflowBase,
):
    """Tests for the API in the irodsbackend app with Taskflow and iRODS"""

    def setUp(self):
        super().setUp()

        # Init project
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        self.irods_backend = IrodsAPI()

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_info(self):
        """Test get_info()"""
        info = self.irods_backend.get_info()
        self.assertIsNotNone(info)
        self.assertEqual(info['server_ok'], True)
        self.assertEqual(info['server_status'], SERVER_AVAILABLE)
        self.assertEqual(info['server_host'], IRODS_HOST)
        self.assertEqual(info['server_port'], IRODS_PORT)
        self.assertEqual(info['server_zone'], IRODS_ZONE)
        self.assertIsNotNone(info['server_version'])

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects(self):
        """Test get_objects() with files in a sample collection"""
        # Create iRODS collections
        self._make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)

        # Create objects
        # TODO: Test with actual files and put() instead
        irods = self.irods_backend.get_session()
        irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))
        obj_list = self.irods_backend.get_objects(path, check_md5=True)
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list['data_objects']), 1)  # md5 not listed

        obj = obj_list['data_objects'][0]
        expected = {
            'name': TEST_FILE_NAME,
            'path': path + '/' + TEST_FILE_NAME,
            'size': 0,
            'md5_file': True,
            'modify_time': obj['modify_time'],
        }
        self.assertEqual(obj, expected)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects_multi(self):
        """Test get_objects() with multiple search terms"""
        # Create iRODS collections
        self._make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)

        # Create objects
        # TODO: Test with actual files and put() instead
        irods = self.irods_backend.get_session()
        irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))
        irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME2))
        obj_list = self.irods_backend.get_objects(
            path, name_like=[TEST_FILE_NAME, TEST_FILE_NAME2], check_md5=True
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list['data_objects']), 2)  # md5 not listed

        expected = [
            {
                'name': TEST_FILE_NAME,
                'path': path + '/' + TEST_FILE_NAME,
                'size': 0,
                'md5_file': True,
                'modify_time': obj_list['data_objects'][0]['modify_time'],
            },
            {
                'name': TEST_FILE_NAME2,
                'path': path + '/' + TEST_FILE_NAME2,
                'size': 0,
                'md5_file': True,
                'modify_time': obj_list['data_objects'][1]['modify_time'],
            },
        ]
        self.assertEqual(obj_list['data_objects'], expected)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects_long_query(self):
        """Test get_objects() with a long query"""
        # Create iRODS collections
        self._make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)

        # Create objects
        irods = self.irods_backend.get_session()
        irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))
        irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME2))

        # Generate a large number of name search terms
        name_like = [TEST_FILE_NAME]
        name_like += [
            ''.join(
                random.SystemRandom().choice(
                    string.ascii_lowercase + string.digits
                )
                for _ in range(8)
            )
            for _ in range(100)
        ]
        name_like.append(TEST_FILE_NAME2)

        obj_list = self.irods_backend.get_objects(
            path, name_like=[TEST_FILE_NAME, TEST_FILE_NAME2], check_md5=True
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list['data_objects']), 2)  # md5 not listed

        expected = [
            {
                'name': TEST_FILE_NAME,
                'path': path + '/' + TEST_FILE_NAME,
                'size': 0,
                'md5_file': True,
                'modify_time': obj_list['data_objects'][0]['modify_time'],
            },
            {
                'name': TEST_FILE_NAME2,
                'path': path + '/' + TEST_FILE_NAME2,
                'size': 0,
                'md5_file': True,
                'modify_time': obj_list['data_objects'][1]['modify_time'],
            },
        ]
        self.assertEqual(obj_list['data_objects'], expected)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects_empty_coll(self):
        """Test get_objects() with an empty sample collection"""
        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_COLL
        obj_list = self.irods_backend.get_objects(path)
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list['data_objects']), 0)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects_no_coll(self):
        """Test get_objects() with no created collections"""
        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_COLL
        with self.assertRaises(FileNotFoundError):
            self.irods_backend.get_objects(path)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects_limit(self):
        """Test get_objects() with a limit applied"""
        # Create iRODS collections
        self._make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)

        # Create objects
        irods = self.irods_backend.get_session()
        irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        obj_list = self.irods_backend.get_objects(
            path, check_md5=False, limit=1
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list['data_objects']), 1)  # Limited to 1
