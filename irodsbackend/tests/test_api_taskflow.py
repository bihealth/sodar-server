"""Tests for the API in the irodsbackend app with Taskflow and iRODS"""

from unittest import skipIf

from django.conf import settings

# Projectroles dependency
from projectroles.models import OMICS_CONSTANTS
from projectroles.tests.test_views_taskflow import TestTaskflowBase, \
    TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

from ..api import IrodsAPI


# Global constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
IRODS_HOST = settings.IRODS_HOST
IRODS_PORT = settings.IRODS_PORT
IRODS_ZONE = settings.IRODS_ZONE
SAMPLE_DIR = settings.IRODS_SAMPLE_DIR
LANDING_ZONE_DIR = settings.IRODS_LANDING_ZONE_DIR
SERVER_AVAILABLE = 'available'

SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20180503_1724_test_zone'
ZONE_DESC = 'description'
TEST_FILE_NAME = 'test1'


class TestIrodsBackendAPITaskflow(
        TestTaskflowBase, SampleSheetIOMixin,
        LandingZoneMixin, SampleSheetTaskflowMixin):
    """Tests for the API in the irodsbackend app with Taskflow and iRODS"""

    def setUp(self):
        super(TestIrodsBackendAPITaskflow, self).setUp()

        # Init project
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description')

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        self.irods_backend = IrodsAPI()

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_info(self):
        """Test get_info()"""
        info = self.irods_backend.get_info()
        self.assertIsNotNone(info)
        self.assertEqual(info['server_status'], SERVER_AVAILABLE)
        self.assertEqual(info['server_host'], IRODS_HOST)
        self.assertEqual(info['server_port'], IRODS_PORT)
        self.assertEqual(info['server_zone'], IRODS_ZONE)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects(self):
        """Test get_info() with files in a sample dir"""

        # Create iRODS directories
        self._make_irods_dirs(self.investigation)

        path = self.irods_backend.get_path(self.assay)

        # Create objects
        # TODO: Test with actual files and put() instead
        irods = self.irods_backend.get_session()
        irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))

        obj_list = self.irods_backend.get_objects(path)
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list['data_objects']), 1)  # md5 not listed

        obj = obj_list['data_objects'][0]
        expected = {
            'name': TEST_FILE_NAME,
            'path': path + '/' + TEST_FILE_NAME,
            'size': 0,
            'md5_file': False,  # Size of md5 file is 0 -> not true
            'modify_time': obj['modify_time']}
        self.assertEqual(obj, expected)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects_empty_dir(self):
        """Test get_info() with an empty sample directory"""

        # Create iRODS directories
        self._make_irods_dirs(self.investigation)

        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_DIR
        obj_list = self.irods_backend.get_objects(path)
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list['data_objects']), 0)

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_get_objects_no_dir(self):
        """Test get_info() with no created directories"""

        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_DIR

        with self.assertRaises(FileNotFoundError):
            obj_list = self.irods_backend.get_objects(path)
