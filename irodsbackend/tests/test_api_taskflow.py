"""Tests for the API in the irodsbackend app with Taskflow and iRODS"""

import pytz
import random
import string

from datetime import timedelta

from irods.models import TicketQuery
from irods.ticket import Ticket

from django.conf import settings
from django.utils import timezone

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from irodsbackend.api import TICKET_MODE_READ, TICKET_MODE_WRITE


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
TEST_FILE_NAME3 = 'test3'
TICKET_STR = 'Ahn1kah9Lai2hies'


class TestIrodsAPITaskflow(
    SampleSheetIOMixin,
    LandingZoneMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for IrodsAPI with Taskflow and iRODS"""

    def _get_ticket_res(self, ticket):
        """Return iRODS database ticket query result"""
        query = self.irods.query(TicketQuery.Ticket).filter(
            TicketQuery.Ticket.string == ticket._ticket
        )
        return list(query)[0]

    def _get_host_res(self, ticket_id):
        """Return iRODS database ticket allowed hosts query result"""
        query = self.irods.query(TicketQuery.AllowedHosts).filter(
            TicketQuery.AllowedHosts.ticket_id == ticket_id
        )
        return list(query)

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
        self.assertEqual(len(obj_list), 4)

    def test_get_objects_empty_coll(self):
        """Test get_objects() with an empty sample collection"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_COLL
        obj_list = self.irods_backend.get_objects(self.irods, path)
        self.assertEqual(len(obj_list), 0)

    def test_get_objects_no_coll(self):
        """Test get_objects() with no created collections"""
        path = self.irods_backend.get_path(self.project) + '/' + SAMPLE_COLL
        with self.assertRaises(FileNotFoundError):
            self.irods_backend.get_objects(self.irods, path)

    def test_get_objects_limit(self):
        """Test get_objects() with limit"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        obj_list = self.irods_backend.get_objects(
            self.irods, path, include_md5=False, limit=1
        )
        self.assertEqual(len(obj_list), 1)  # Limited to 1
        self.assertEqual(obj_list[0]['name'], TEST_FILE_NAME)

    def test_get_objects_limit_md5(self):
        """Test get_objects() with limit and MD5 inclusion"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        coll = self.irods.collections.get(path)
        data_obj = self.make_irods_object(coll, TEST_FILE_NAME)
        self.make_irods_md5_object(data_obj)  # Create MD5 object
        data_obj2 = self.make_irods_object(coll, TEST_FILE_NAME2)
        self.make_irods_md5_object(data_obj2)
        obj_list = self.irods_backend.get_objects(
            self.irods, path, include_md5=True, limit=2
        )
        self.assertEqual(len(obj_list), 2)
        self.assertEqual(obj_list[0]['name'], TEST_FILE_NAME)
        self.assertEqual(obj_list[1]['name'], TEST_FILE_NAME + '.md5')

    def test_get_objects_offset(self):
        """Test get_objects() with offset"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        obj_list = self.irods_backend.get_objects(
            self.irods, path, include_md5=False, offset=1
        )
        self.assertEqual(len(obj_list), 1)
        self.assertEqual(obj_list[0]['name'], TEST_FILE_NAME2)

    def test_get_objects_limit_offset(self):
        """Test get_objects() with limit and offset"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME2)
        self.irods.data_objects.create(path + '/' + TEST_FILE_NAME3)
        obj_list = self.irods_backend.get_objects(
            self.irods, path, include_md5=False, limit=1, offset=1
        )
        self.assertEqual(len(obj_list), 1)
        # Only the middle file should be returned
        self.assertEqual(obj_list[0]['name'], TEST_FILE_NAME2)

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

    def test_get_objects_checksum(self):
        """Test get_objects() with checksum"""
        self.make_irods_colls(self.investigation)
        path = self.irods_backend.get_path(self.assay)
        coll = self.irods.collections.get(path)
        # Use make_irods_object() to generate checksum on server
        self.make_irods_object(coll, TEST_FILE_NAME, checksum=True)
        obj_list = self.irods_backend.get_objects(
            self.irods, path, checksum=True
        )
        self.assertEqual(len(obj_list), 1)
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
            'size': 1024,
            'modify_time': modify_time,
            'checksum': data_obj.checksum,
        }
        self.assertEqual(obj_list[0], expected)
        self.assertIsNotNone(obj_list[0]['checksum'])

    def test_issue_ticket_read(self):
        """Test issue_ticket() in read mode"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
        )
        self.assertEqual(type(ticket), Ticket)
        self.assertEqual(ticket.string, TICKET_STR)
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.type], TICKET_MODE_READ)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        # Default write file limit, doesn't affect read tickets so default is OK
        self.assertEqual(ticket_res[TicketQuery.Ticket.write_file_limit], 10)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

    def test_issue_ticket_write(self):
        """Test issue_ticket() in write mode"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_WRITE,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.type], TICKET_MODE_WRITE)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        # This should be changed to 0 for write tickets
        self.assertEqual(ticket_res[TicketQuery.Ticket.write_file_limit], 0)

    def test_issue_ticket_expiry_date(self):
        """Test issue_ticket() with expiry date"""
        self.make_irods_colls(self.investigation)
        expiry_date = timezone.now() + timedelta(days=1)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
            date_expires=expiry_date,
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(
            int(ticket_res[TicketQuery.Ticket.expiry_ts]),
            int(expiry_date.timestamp()),
        )

    def test_issue_ticket_hosts(self):
        """Test issue_ticket() with allowed hosts"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
            allowed_hosts=['127.0.0.1'],
        )
        self.assertEqual(type(ticket), Ticket)
        self.assertEqual(ticket.string, TICKET_STR)
        ticket_res = self._get_ticket_res(ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 1)
        self.assertEqual(
            host_res[0][TicketQuery.AllowedHosts.host], '127.0.0.1'
        )

    def test_issue_ticket_hosts_string(self):
        """Test issue_ticket() with allowed hosts as string"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
            allowed_hosts='127.0.0.1,192.168.0.1',
        )
        self.assertEqual(type(ticket), Ticket)
        self.assertEqual(ticket.string, TICKET_STR)
        ticket_res = self._get_ticket_res(ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 2)
        self.assertEqual(
            host_res[0][TicketQuery.AllowedHosts.host], '127.0.0.1'
        )
        self.assertEqual(
            host_res[1][TicketQuery.AllowedHosts.host], '192.168.0.1'
        )

    def test_update_ticket_expiry_date(self):
        """Test update_ticket() with expiry date"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

        date_expires = timezone.now()
        self.irods_backend.update_ticket(
            self.irods, TICKET_STR, date_expires=date_expires
        )
        ticket_res = self._get_ticket_res(ticket)
        obj_exp = date_expires.replace(tzinfo=pytz.timezone('GMT'))
        self.assertEqual(
            int(ticket_res[TicketQuery.Ticket.expiry_ts]),
            int(obj_exp.timestamp()),
        )

    def test_update_ticket_no_expiry_date(self):
        """Test update_ticket() for no expiry date"""
        date_expires = timezone.now()
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
            date_expires=date_expires,
        )
        ticket_res = self._get_ticket_res(ticket)
        obj_exp = date_expires.replace(tzinfo=pytz.timezone('GMT'))
        self.assertEqual(
            int(ticket_res[TicketQuery.Ticket.expiry_ts]),
            int(obj_exp.timestamp()),
        )

        self.irods_backend.update_ticket(
            self.irods, TICKET_STR, date_expires=None
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)

    def test_update_ticket_add_hosts(self):
        """Test update_ticket() to add hosts"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

        self.irods_backend.update_ticket(
            self.irods, TICKET_STR, allowed_hosts=['127.0.0.1', '192.168.0.1']
        )
        ticket_res = self._get_ticket_res(ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        host_res = [h[TicketQuery.AllowedHosts.host] for h in host_res]
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

    def test_update_ticket_add_hosts_string(self):
        """Test update_ticket() to add hosts as string"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

        self.irods_backend.update_ticket(
            self.irods, TICKET_STR, allowed_hosts='127.0.0.1,192.168.0.1'
        )
        ticket_res = self._get_ticket_res(ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        host_res = [h[TicketQuery.AllowedHosts.host] for h in host_res]
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

    def test_update_ticket_add_hosts_existing(self):
        """Test update_ticket() to add hosts with existing host"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
            allowed_hosts=['127.0.0.1'],
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 1)
        host_res = [h[TicketQuery.AllowedHosts.host] for h in host_res]
        self.assertEqual(host_res, ['127.0.0.1'])

        self.irods_backend.update_ticket(
            self.irods, TICKET_STR, allowed_hosts=['127.0.0.1', '192.168.0.1']
        )
        ticket_res = self._get_ticket_res(ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        host_res = [h[TicketQuery.AllowedHosts.host] for h in host_res]
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

    def test_update_ticket_remove_hosts(self):
        """Test update_ticket() to remove hosts"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
            allowed_hosts=['127.0.0.1', '192.168.0.1'],
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 2)
        host_res = [h[TicketQuery.AllowedHosts.host] for h in host_res]
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

        self.irods_backend.update_ticket(
            self.irods, TICKET_STR, allowed_hosts=None
        )
        ticket_res = self._get_ticket_res(ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

    def test_update_ticket_remove_hosts_partial(self):
        """Test update_ticket() to partially remove hosts"""
        self.make_irods_colls(self.investigation)
        ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
            TICKET_STR,
            allowed_hosts=['127.0.0.1', '192.168.0.1'],
        )
        ticket_res = self._get_ticket_res(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 2)
        host_res = [h[TicketQuery.AllowedHosts.host] for h in host_res]
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

        self.irods_backend.update_ticket(
            self.irods, TICKET_STR, allowed_hosts=['192.168.0.1']
        )
        ticket_res = self._get_ticket_res(ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 1)
        host_res = [h[TicketQuery.AllowedHosts.host] for h in host_res]
        self.assertEqual(host_res, ['192.168.0.1'])

    def test_get_delete_ticket(self):
        """Test get_ticket() and delete_ticket()"""
        self.make_irods_colls(self.investigation)
        orig_ticket = self.irods_backend.issue_ticket(
            self.irods,
            TICKET_MODE_READ,
            self.irods_backend.get_sample_path(self.project),
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
