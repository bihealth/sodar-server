"""Tests for the API in the irodsbackend app with Taskflow and iRODS"""

import pytz
import random
import string

from irods.ticket import Ticket

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase


# SODAR constants
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
TICKET_STR = 'Ahn1kah9Lai2hies'


class TestIrodsBackendAPITaskflow(
    SampleSheetIOMixin,
    LandingZoneMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for the API in the irodsbackend app with Taskflow and iRODS"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get_info(self):
        """Test get_info()"""
        info = self.irods_backend.get_info(self.irods)
        self.assertIsNotNone(info)
        self.assertEqual(info['server_ok'], True)
        self.assertEqual(info['server_status'], SERVER_AVAILABLE)
        self.assertEqual(info['server_host'], IRODS_HOST)
        self.assertEqual(info['server_port'], IRODS_PORT)
        self.assertEqual(info['server_zone'], IRODS_ZONE)
        self.assertEqual(
            info['server_version'],
            '.'.join(
                str(x) for x in self.irods.pool.get_connection().server_version
            ),
        )

    def test_get_version(self):
        """Test get_irods_version()"""
        self.assertEqual(
            self.irods_backend.get_version(self.irods),
            '.'.join(
                str(x) for x in self.irods.pool.get_connection().server_version
            ),
        )

    def test_get_objects(self):
        """Test get_objects() with files in a sample collection"""
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)

        # Create objects
        # TODO: Test with actual files and put() instead
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))
        obj_list = self.irods_backend.get_objects(
            self.irods, path, include_md5=True
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list), 2)

        data_obj = self.irods.data_objects.get(path + '/' + TEST_FILE_NAME)
        modify_time = (
            data_obj.modify_time.replace(tzinfo=pytz.timezone('GMT'))
            .astimezone(pytz.timezone(settings.TIME_ZONE))
            .strftime('%Y-%m-%d %H:%M')
        )
        expected = {
            'name': TEST_FILE_NAME,
            'type': 'obj',
            'path': path + '/' + TEST_FILE_NAME,
            'size': 0,
            'modify_time': modify_time,
        }
        self.assertEqual(obj_list[0], expected)

    def test_get_objects_with_colls(self):
        """Test get_objects() with collections included"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))
        self.irods.collections.create(path + '/subcoll')
        obj_list = self.irods_backend.get_objects(
            self.irods, path, include_md5=True, include_colls=True
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list), 3)

        expected = [
            {
                'name': 'subcoll',
                'type': 'coll',
                'path': path + '/subcoll',
            },
            {
                'name': TEST_FILE_NAME,
                'type': 'obj',
                'path': path + '/' + TEST_FILE_NAME,
                'size': 0,
                'modify_time': obj_list[1]['modify_time'],
            },
            {
                'name': TEST_FILE_NAME + '.md5',
                'type': 'obj',
                'path': path + '/' + TEST_FILE_NAME + '.md5',
                'size': 0,
                'modify_time': obj_list[2]['modify_time'],
            },
        ]
        self.assertEqual(obj_list, expected)

    def test_get_objects_multi(self):
        """Test get_objects() with multiple search terms"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        self.irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME2))
        obj_list = self.irods_backend.get_objects(
            self.irods,
            path,
            name_like=[TEST_FILE_NAME, TEST_FILE_NAME2],
            include_md5=True,
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list), 4)

    def test_get_objects_long_query(self):
        """Test get_objects() with a long query"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME))
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        self.irods.data_objects.create(path + '/{}.md5'.format(TEST_FILE_NAME2))

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
            self.irods,
            path,
            name_like=[TEST_FILE_NAME, TEST_FILE_NAME2],
            include_md5=True,
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list), 4)

    def test_get_objects_empty_coll(self):
        """Test get_objects() with an empty sample collection"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_COLL
        obj_list = self.irods_backend.get_objects(self.irods, path)
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list), 0)

    def test_get_objects_no_coll(self):
        """Test get_objects() with no created collections"""
        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_COLL
        with self.assertRaises(FileNotFoundError):
            self.irods_backend.get_objects(self.irods, path)

    def test_get_objects_limit(self):
        """Test get_objects() with a limit applied"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        obj_list = self.irods_backend.get_objects(
            self.irods, path, include_md5=False, limit=1
        )
        self.assertIsNotNone(obj_list)
        self.assertEqual(len(obj_list), 1)  # Limited to 1

    def test_get_objects_api_format(self):
        """Test get_objects() with api_format=True"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        obj_list = self.irods_backend.get_objects(
            self.irods, path, api_format=True
        )
        self.assertEqual(len(obj_list), 1)
        data_obj = self.irods.data_objects.get(path + '/' + TEST_FILE_NAME)
        modify_time = (
            data_obj.modify_time.replace(tzinfo=pytz.timezone('GMT'))
            .astimezone(pytz.timezone(settings.TIME_ZONE))
            .isoformat()
        )
        expected = {
            'name': TEST_FILE_NAME,
            'type': 'obj',
            'path': path + '/' + TEST_FILE_NAME,
            'size': 0,
            'modify_time': modify_time,
        }
        self.assertEqual(obj_list[0], expected)

    def test_issue_ticket(self):
        """Test issue_ticket()"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            'read',
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
        )
        self.assertEqual(type(ticket), Ticket)
        self.assertEqual(ticket.string, TICKET_STR)

    def test_get_delete_ticket(self):
        """Test get_ticket() and delete_ticket()"""
        self.make_irods_colls(self.investigation)
        orig_ticket = self.irods_backend.issue_ticket(
            self.irods, 'read', self.irods_backend.get_sample_path(self.project)
        )
        retr_ticket = self.irods_backend.get_ticket(
            self.irods, orig_ticket.string
        )
        self.assertEqual(type(retr_ticket), Ticket)
        self.irods_backend.delete_ticket(self.irods, orig_ticket.string)
        retr_ticket = self.irods_backend.get_ticket(
            self.irods, orig_ticket.string
        )
        self.assertIsNone(retr_ticket)
