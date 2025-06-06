"""
Tests for REST API views in the samplesheets app with SODAR Taskflow enabled
"""

import json
import os
import pytz

from datetime import timedelta, datetime

from irods.models import TicketQuery

from django.forms.models import model_to_dict
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Timeline dependency
from timeline.models import TimelineEvent

# Irodsbackend dependency
from irodsbackend.api import TICKET_MODE_READ

# Taskflowbackend dependency
from taskflowbackend.tests.base import (
    TaskflowAPIViewTestBase,
    HASH_SCHEME_SHA256,
)

from samplesheets.models import (
    IrodsAccessTicket,
    IrodsDataRequest,
    IRODS_REQUEST_STATUS_ACCEPTED,
    IRODS_REQUEST_STATUS_ACTIVE,
    IRODS_REQUEST_STATUS_FAILED,
    IRODS_REQUEST_STATUS_REJECTED,
    IRODS_REQUEST_ACTION_DELETE,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import (
    IrodsAccessTicketMixin,
    IrodsDataRequestMixin,
    IRODS_REQUEST_DESC,
)
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
    IrodsAccessTicketViewTestMixin,
    INVALID_REDIS_URL,
    TICKET_STR,
    TICKET_LABEL,
)
from samplesheets.views import (
    IRODS_REQUEST_EVENT_CREATE as CREATE_ALERT,
    IRODS_REQUEST_EVENT_ACCEPT as ACCEPT_ALERT,
    IRODS_REQUEST_EVENT_REJECT as REJECT_ALERT,
)
from samplesheets.views_api import (
    IRODS_QUERY_ERROR_MSG,
    SAMPLESHEETS_API_MEDIA_TYPE,
    SAMPLESHEETS_API_DEFAULT_VERSION,
    FILE_EXISTS_RESTRICT_MSG,
)


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets'
SHEET_TSV_DIR = SHEET_DIR + 'i_small2/'
SHEET_PATH = SHEET_DIR + 'i_small2.zip'
SHEET_PATH_EDITED = SHEET_DIR + 'i_small2_edited.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2_alt.zip'
IRODS_FILE_NAME = 'test1.txt'
IRODS_FILE_NAME2 = 'test2.txt'
IRODS_REQUEST_DESC_UPDATED = 'updated'
CHECKSUM_MD5 = '7265f4d211b56873a381d321f586e4a9'
CHECKSUM_SHA256_HEX = (
    '49abd65bbf7f7e40c7055093ed2e3fd75f2f602f2c5fcf955c213e3135eb03f7'
)
CHECKSUM_SHA256_BASE64 = 'SavWW79/fkDHBVCT7S4/118vYC8sX8+VXCE+MTXrA/c='
DUMMY_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
LABEL_UPDATE = 'label_update'


# Base Classes and Mixins ------------------------------------------------------


class SampleSheetAPITaskflowTestBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIViewTestBase
):
    """Base samplesheets API view test class with Taskflow enabled"""

    media_type = SAMPLESHEETS_API_MEDIA_TYPE
    api_version = SAMPLESHEETS_API_DEFAULT_VERSION

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


class IrodsAccessTicketAPIViewTestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    TaskflowAPIViewTestBase,
):
    """Base samplesheets API view test class for iRODS access ticket requests"""

    media_type = SAMPLESHEETS_API_MEDIA_TYPE
    api_version = SAMPLESHEETS_API_DEFAULT_VERSION

    def assert_alert_count(self, alert_name, user, count, project=None):
        """
        Assert expected app alert count. If project is not specified, default to
        self.project.

        :param alert_name: String
        :param user: User object
        :param count: Expected count
        :param project: Project object or None
        """
        if not project:
            project = self.project
        self.assertEqual(
            self.app_alert_model.objects.filter(
                alert_name=alert_name,
                active=True,
                project=project,
                user=user,
            ).count(),
            count,
        )

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
        # Set up investigation and collections
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)
        # Init users (owner = user_cat, superuser = user)
        self.user_delegate = self.make_user('user_delegate')
        self.user_contributor = self.make_user('user_contributor')
        self.token_contrib = self.get_token(self.user_contributor)
        self.make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self.make_assignment_taskflow(
            self.project, self.user_contributor, self.role_contributor
        )
        # Create collection under assay
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(self.assay_path, 'coll')
        )
        # Get appalerts API and model
        self.app_alerts = get_backend_api('appalerts_backend')
        self.app_alert_model = self.app_alerts.get_model()


class IrodsDataRequestAPIViewTestBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIViewTestBase
):
    """Base samplesheets API view test class for iRODS delete requests"""

    media_type = SAMPLESHEETS_API_MEDIA_TYPE
    api_version = SAMPLESHEETS_API_DEFAULT_VERSION

    # TODO: Retrieve this from a common base/helper class instead of redef
    def assert_alert_count(self, alert_name, user, count, project=None):
        """
        Assert expected app alert count. If project is not specified, default to
        self.project.

        :param alert_name: String
        :param user: User object
        :param count: Expected count
        :param project: Project object or None
        """
        if not project:
            project = self.project
        self.assertEqual(
            self.app_alert_model.objects.filter(
                alert_name=alert_name,
                active=True,
                project=project,
                user=user,
            ).count(),
            count,
        )

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        # Init users (owner = user_cat, superuser = user)
        self.user_delegate = self.make_user('user_delegate')
        self.user_contributor = self.make_user('user_contributor')
        self.user_guest = self.make_user('user_guest')
        self.make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self.make_assignment_taskflow(
            self.project, self.user_contributor, self.role_contributor
        )
        self.make_assignment_taskflow(
            self.project, self.user_guest, self.role_guest
        )

        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up iRODS data
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.obj_path = os.path.join(self.assay_path, IRODS_FILE_NAME)
        self.file_obj = self.irods.data_objects.create(self.obj_path)

        # Setup for tests
        self.app_alerts = get_backend_api('appalerts_backend')
        self.app_alert_model = self.app_alerts.get_model()
        self.url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {
            'path': self.obj_path,
            'description': IRODS_REQUEST_DESC,
        }
        self.token_contrib = self.get_token(self.user_contributor)


# Test Cases -------------------------------------------------------------------


class TestInvestigationRetrieveAPIView(SampleSheetAPITaskflowTestBase):
    """Tests for InvestigationRetrieveAPIView"""

    def test_get(self):
        """Test InvestigationRetrieveAPIView GET"""
        self.investigation.irods_status = True
        self.investigation.save()

        url = reverse(
            'samplesheets:api_investigation_retrieve',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url)

        self.assertEqual(response.status_code, 200)
        expected = {
            'sodar_uuid': str(self.investigation.sodar_uuid),
            'identifier': self.investigation.identifier,
            'file_name': self.investigation.file_name,
            'project': str(self.project.sodar_uuid),
            'title': self.investigation.title,
            'description': self.investigation.description,
            'irods_status': True,
            'parser_version': self.investigation.parser_version,
            'archive_name': self.investigation.archive_name,
            'comments': self.investigation.comments,
            'studies': {
                str(self.study.sodar_uuid): {
                    'identifier': self.study.identifier,
                    'file_name': self.study.file_name,
                    'title': self.study.title,
                    'description': self.study.description,
                    'comments': self.study.comments,
                    'irods_path': self.irods_backend.get_path(self.study),
                    'sodar_uuid': str(self.study.sodar_uuid),
                    'assays': {
                        str(self.assay.sodar_uuid): {
                            'file_name': self.assay.file_name,
                            'technology_platform': self.assay.technology_platform,
                            'technology_type': self.assay.technology_type,
                            'measurement_type': self.assay.measurement_type,
                            'comments': self.assay.comments,
                            'irods_path': self.irods_backend.get_path(
                                self.assay
                            ),
                            'sodar_uuid': str(self.assay.sodar_uuid),
                        }
                    },
                }
            },
        }
        self.assertEqual(json.loads(response.content), expected)


class TestIrodsCollsCreateAPIView(SampleSheetAPITaskflowTestBase):
    """Tests for IrodsCollsCreateAPIView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:api_irods_colls_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsCollsCreateAPIView POST"""
        self.assertEqual(self.investigation.irods_status, False)
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 200)
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)
        self.assert_irods_coll(self.irods_backend.get_sample_path(self.project))
        self.assert_irods_coll(self.study)
        self.assert_irods_coll(self.assay)

    def test_post_created(self):
        """Test POST with already created collections (should fail)"""
        # Set up iRODS collections
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.investigation.irods_status, True)
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 400)

    def test_post_locked(self):
        """Test POST with locked project (should fail)"""
        self.lock_project(self.project)
        self.assertEqual(self.investigation.irods_status, False)
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 503)
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, False)


# NOTE: For TestIrodsAccessTicketListAPIView, see test_views_api
# NOTE: For TestIrodsAccessTicketRetrieveAPIView, see test_views_api


class TestIrodsAccessTicketCreateAPIView(IrodsAccessTicketAPIViewTestBase):
    """Tests for IrodsAccessTicketCreateAPIView"""

    def setUp(self):
        super().setUp()
        self.path = self.coll.path
        self.date_expires = (
            timezone.localtime() + timedelta(days=1)
        ).isoformat()
        self.url = reverse(
            'samplesheets:api_irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {
            'path': self.path,
            'label': TICKET_LABEL,
            'date_expires': self.date_expires,
            'allowed_hosts': [],
        }

    def test_post(self):
        """Test IrodsAccessTicketCreateAPIView POST as superuser"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.path, self.path)
        self.assertEqual(ticket.label, TICKET_LABEL)
        self.assertEqual(
            ticket.date_expires,
            datetime.strptime(self.date_expires, '%Y-%m-%dT%H:%M:%S.%f%z'),
        )
        self.assertEqual(ticket.allowed_hosts, None)
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.study, self.study)
        self.assertEqual(ticket.assay, self.assay)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self.assertEqual(self.get_tl_event_count('create'), 1)
        self.assertEqual(self.get_app_alert_count('create'), 2)
        self.assertEqual(
            self.app_alert_model.objects.filter(
                alert_name='irods_ticket_create'
            )
            .first()
            .user,
            self.user_delegate,
        )

        # Assert ticket state in iRODS
        ticket_res = self.get_irods_ticket(ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.type], TICKET_MODE_READ)
        self.assertIsNotNone(ticket_res[TicketQuery.Ticket.expiry_ts])
        self.assertEqual(
            ticket_res[TicketQuery.Collection.name], self.coll.path
        )
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

    def test_post_contributor(self):
        """Test POST as contributor"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.user, self.user_contributor)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self.assertEqual(self.get_tl_event_count('create'), 1)
        self.assertEqual(self.get_app_alert_count('create'), 3)
        self.assertEqual(
            self.app_alert_model.objects.filter(
                alert_name='irods_ticket_create'
            )
            .first()
            .user,
            self.user_delegate,
        )

    def test_post_no_expiry(self):
        """Test POST with no expiry date"""
        self.post_data['date_expires'] = None
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertIsNone(ticket.date_expires)
        ticket_res = self.get_irods_ticket(ticket)
        self.assertIsNone(ticket_res[TicketQuery.Ticket.expiry_ts])

    def test_post_hosts(self):
        """Test POST with allowed hosts"""
        self.post_data['allowed_hosts'] = ['127.0.0.1', '192.168.0.1']
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.allowed_hosts, '127.0.0.1,192.168.0.1')
        ticket_res = self.get_irods_ticket(ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

    def test_post_hosts_v1_0(self):
        """Test POST with allowed hosts and API version 1.0 (should fail)"""
        self.post_data['allowed_hosts'] = ['127.0.0.1', '192.168.0.1']
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, version='1.0'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)

    def test_post_hosts_v1_0_default(self):
        """Test POST with default allowed hosts and API version 1.0"""
        app_settings.set(
            APP_NAME,
            'irods_ticket_hosts',
            '127.0.0.1,192.168.0.1',
            project=self.project,
        )
        self.post_data.pop('allowed_hosts', None)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, version='1.0'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.allowed_hosts, '127.0.0.1,192.168.0.1')
        ticket_res = self.get_irods_ticket(ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

    def test_post_invalid_path(self):
        """Test POST with invalid path"""
        self.post_data['path'] = '/invalid/path'
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_post_expired(self):
        """Test POST with expired date"""
        self.post_data['date_expires'] = (
            timezone.localtime() - timedelta(days=1)
        ).isoformat()
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_post_assay_root(self):
        """Test POST with assay root"""
        self.post_data['path'] = self.irods_backend.get_path(self.assay)
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_post_study_path(self):
        """Test POST with study path"""
        self.post_data['path'] = self.irods_backend.get_path(self.study)
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_post_data_object_path(self):
        """Test POST with path to data object"""
        obj = self.make_irods_object(self.coll, 'test.txt')
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.post_data['path'] = obj.path
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)

    def test_post_existing_ticket(self):
        """Test POST for the same path"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path=self.coll.path,
            label='OldTicket',
            user=self.user,
        )
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        response = self.request_knox(self.url, 'POST', data=self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)


class TestIrodsAccessTicketUpdateAPIView(IrodsAccessTicketAPIViewTestBase):
    """Tests for IrodsAccessTicketUpdateAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path=self.coll.path,
            label=TICKET_LABEL,
            user=self.user,
            date_expires=None,
            allowed_hosts=['127.0.0.1', '192.168.0.1'],
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.coll.path,
            ticket_str=TICKET_STR,
            date_expires=None,
            allowed_hosts=['127.0.0.1', '192.168.0.1'],
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        self.date_expires_update = timezone.localtime() + timedelta(days=1)

    def test_put(self):
        """Test IrodsAccessTicketUpdateAPIView PUT"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket_res = self.get_irods_ticket(self.ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.type], TICKET_MODE_READ)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        self.assertEqual(
            ticket_res[TicketQuery.Collection.name], self.coll.path
        )
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)
        put_data = {
            'path': self.coll.path,
            'label': LABEL_UPDATE,
            'date_expires': self.date_expires_update.isoformat(),
            'allowed_hosts': [],
        }
        response = self.request_knox(
            self.url, 'PUT', data=put_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': LABEL_UPDATE,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,  # Path should not be updated
            'date_created': local_date_created.isoformat(),
            'date_expires': self.date_expires_update.isoformat(),
            'allowed_hosts': [],
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(response.json(), expected)
        ticket_res = self.get_irods_ticket(self.ticket)
        obj_exp = self.date_expires_update.replace(tzinfo=pytz.timezone('GMT'))
        self.assertEqual(
            int(ticket_res[TicketQuery.Ticket.expiry_ts]),
            int(obj_exp.timestamp()),
        )
        self.assertEqual(
            ticket_res[TicketQuery.Collection.name], self.coll.path
        )
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, [])
        self.assertEqual(self.get_tl_event_count('update'), 1)
        self.assertEqual(self.get_app_alert_count('update'), 3)
        self.assertEqual(
            self.app_alert_model.objects.filter(
                alert_name='irods_ticket_update'
            )
            .first()
            .user,
            self.user_delegate,
        )

    def test_put_hosts_remove_partial(self):
        """Test PUT to remove partial allowed hosts"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])
        put_data = {
            'path': self.coll.path,
            'label': LABEL_UPDATE,
            'date_expires': self.date_expires_update.isoformat(),
            'allowed_hosts': ['192.168.0.1'],
        }
        response = self.request_knox(
            self.url, 'PUT', data=put_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.allowed_hosts, '192.168.0.1')
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['192.168.0.1'])

    def test_put_hosts_add(self):
        """Test PUT to add allowed hosts"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])
        put_data = {
            'path': self.coll.path,
            'label': LABEL_UPDATE,
            'date_expires': self.date_expires_update.isoformat(),
            'allowed_hosts': ['127.0.0.1', '192.168.0.1', '2.22.231.13'],
        }
        response = self.request_knox(
            self.url, 'PUT', data=put_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(
            self.ticket.allowed_hosts, '127.0.0.1,192.168.0.1,2.22.231.13'
        )
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1', '2.22.231.13'])

    def test_put_v1_0(self):
        """Test PUT with API version 1.0"""
        put_data = {
            'path': self.coll.path,
            'label': LABEL_UPDATE,
            'date_expires': self.date_expires_update.isoformat(),
        }
        response = self.request_knox(
            self.url,
            'PUT',
            data=put_data,
            token=self.token_contrib,
            version='1.0',
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.allowed_hosts, '127.0.0.1,192.168.0.1')
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

    def test_put_v1_0_hosts(self):
        """Test PUT with API version 1.0 and hosts param (should fail)"""
        put_data = {
            'path': self.coll.path,
            'label': LABEL_UPDATE,
            'date_expires': self.date_expires_update.isoformat(),
            'allowed_hosts': ['127.0.0.1', '192.168.0.1', '2.22.231.13'],
        }
        response = self.request_knox(
            self.url,
            'PUT',
            data=put_data,
            token=self.token_contrib,
            version='1.0',
        )
        self.assertEqual(response.status_code, 400)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.allowed_hosts, '127.0.0.1,192.168.0.1')
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])

    def test_put_missing_fields(self):
        """Test PUT with missing fields"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)
        put_data = {'path': self.coll.path}
        response = self.request_knox(
            self.url, 'PUT', data=put_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

    def test_put_invalid_date(self):
        """Test PUT with invalid date"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)
        invalid_date = 'invalid'
        put_data = {
            'path': self.coll.path,
            'label': LABEL_UPDATE,
            'date_expires': invalid_date,
            'allowed_hosts': [],
        }
        response = self.request_knox(
            self.url, 'PUT', data=put_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

    def test_patch(self):
        """Test PATCH"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        irods_ticket = self.get_irods_ticket(self.ticket)
        self.assertEqual(irods_ticket[TicketQuery.Ticket.expiry_ts], None)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)
        patch_data = {'date_expires': self.date_expires_update.isoformat()}
        response = self.request_knox(
            self.url, 'PATCH', data=patch_data, token=self.token_contrib
        )

        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': TICKET_LABEL,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,
            'date_created': local_date_created.isoformat(),
            'date_expires': self.date_expires_update.isoformat(),
            'allowed_hosts': [],
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(response.json(), expected)
        irods_ticket = self.get_irods_ticket(self.ticket)
        obj_exp = self.date_expires_update.replace(tzinfo=pytz.timezone('GMT'))
        self.assertEqual(
            int(irods_ticket[TicketQuery.Ticket.expiry_ts]),
            int(obj_exp.timestamp()),
        )
        self.assertEqual(self.get_tl_event_count('update'), 1)
        self.assertEqual(self.get_app_alert_count('update'), 3)
        self.assertEqual(
            self.app_alert_model.objects.filter(
                alert_name='irods_ticket_update'
            )
            .first()
            .user,
            self.user_delegate,
        )

    def test_patch_hosts(self):
        """Test PATCH with allowed hosts"""
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, ['127.0.0.1', '192.168.0.1'])
        patch_data = {'allowed_hosts': []}
        response = self.request_knox(
            self.url, 'PATCH', data=patch_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 200)
        ticket_res = self.get_irods_ticket(self.ticket)
        host_res = self.get_ticket_hosts(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(host_res, [])

    def test_patch_path(self):
        """Test PATCH with path (should fail)"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)
        patch_data = {'path': self.coll.path}
        response = self.request_knox(
            self.url, 'PATCH', data=patch_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

    def test_patch_invalid_date(self):
        """Test PATCH with invalid date"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)
        invalid_date = 'invalid'
        patch_data = {'date_expires': invalid_date}
        response = self.request_knox(
            self.url, 'PATCH', data=patch_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)


class TestIrodsAccessTicketDestroyAPIView(IrodsAccessTicketAPIViewTestBase):
    """Tests for IrodsAccessTicketDeleteAPIView"""

    def setUp(self):
        super().setUp()
        self.date_expires = (
            timezone.localtime() + timedelta(days=1)
        ).isoformat()
        # Create ticket in database and iRODS
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll.path,
            user=self.user,
            ticket=TICKET_STR,
            label=TICKET_LABEL,
            date_expires=timezone.localtime() + timedelta(days=1),
        )
        self.irods_backend.issue_ticket(
            self.irods,
            'read',
            self.coll.path,
            ticket_str=TICKET_STR,
            date_expires=None,
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_delete(self):
        """Test IrodsAccessTicketDeleteAPIView DELETE"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)
        response = self.request_knox(
            self.url, 'DELETE', token=self.token_contrib
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('delete'), 1)
        self.assertEqual(self.get_app_alert_count('delete'), 3)
        self.assertEqual(
            self.app_alert_model.objects.filter(
                alert_name='irods_ticket_delete'
            )
            .first()
            .user,
            self.user_delegate,
        )

    def test_delete_invalid_url(self):
        """Test DELETE with invalid URL"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)
        invalid_url = reverse(
            'samplesheets:api_irods_ticket_delete',
            kwargs={'irodsaccessticket': DUMMY_UUID},
        )
        response = self.request_knox(
            invalid_url, 'DELETE', token=self.token_contrib
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)


# NOTE: For TestIrodsDataRequestRetrieveAPIView, see test_views_api
# NOTE: For TestIrodsDataRequestListAPIView, see test_views_api


class TestIrodsDataRequestCreateAPIView(IrodsDataRequestAPIViewTestBase):
    """Tests for IrodsDataRequestCreateAPIView"""

    def test_post(self):
        """Test IrodsDataRequestCreateAPIView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 201)
        obj = IrodsDataRequest.objects.first()
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        expected = {
            'id': obj.pk,
            'project': self.project.pk,
            'action': IRODS_REQUEST_ACTION_DELETE,
            'target_path': None,
            'path': self.obj_path,
            'user': self.user_contributor.pk,
            'status': IRODS_REQUEST_STATUS_ACTIVE,
            'status_info': '',
            'description': IRODS_REQUEST_DESC,
            'sodar_uuid': obj.sodar_uuid,
        }
        self.assertEqual(model_to_dict(obj), expected)
        self.assert_alert_count(CREATE_ALERT, self.user, 1)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self.assert_alert_count(CREATE_ALERT, self.user_contributor, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_guest, 0)

    def test_post_no_description(self):
        """Test POST without description"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.post_data['description'] = ''
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 201)
        obj = IrodsDataRequest.objects.first()
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.description, '')

    def test_post_trailing_slash(self):
        """Test POST with trailing slash in path"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.post_data['path'] += '/'
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 201)
        obj = IrodsDataRequest.objects.first()
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.obj_path + '/')
        self.assertEqual(obj.description, IRODS_REQUEST_DESC)

    def test_post_invalid_data(self):
        """Test POST with invalid data"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self.post_data['path'] = '/sodarZone/does/not/exist'
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

    def test_post_invalid_path_assay_collection(self):
        """Test POST with assay path (should fail)"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.post_data['path'] = self.assay_path
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

    def test_post_multiple(self):
        """Test creating multiple requests for same path"""
        path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.irods.data_objects.create(path2)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 201)
        self.post_data['path'] = path2
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self.assert_alert_count(CREATE_ALERT, self.user, 1)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


class TestIrodsDataRequestUpdateAPIView(
    IrodsDataRequestMixin, IrodsDataRequestAPIViewTestBase
):
    """Tests for IrodsDataRequestUpdateAPIView"""

    def _assert_tl_count(self, count):
        """Assert timeline TimelineEvent count"""
        self.assertEqual(
            TimelineEvent.objects.filter(
                event_name='irods_request_update'
            ).count(),
            count,
        )

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            description='',
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )
        self.update_data = {
            'path': self.obj_path,
            'description': IRODS_REQUEST_DESC_UPDATED,
        }

    def test_put(self):
        """Test IrodsDataRequestUpdateAPIView PUT"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_tl_count(0)
        response = self.request_knox(
            self.url, 'PUT', data=self.update_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.request.refresh_from_db()
        expected = {
            'id': self.request.pk,
            'project': self.project.pk,
            'action': IRODS_REQUEST_ACTION_DELETE,
            'target_path': '',
            'path': self.obj_path,
            'user': self.user_contributor.pk,
            'status': IRODS_REQUEST_STATUS_ACTIVE,
            'status_info': '',
            'description': IRODS_REQUEST_DESC_UPDATED,
            'sodar_uuid': self.request.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.request), expected)
        self._assert_tl_count(1)

    def test_put_empty_description(self):
        """Test PUT with empty description"""
        self.update_data['description'] = ''
        response = self.request_knox(
            self.url, 'PUT', data=self.update_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.description, '')

    def test_put_invalid_path(self):
        """Test PUT to update request with invalid path"""
        self._assert_tl_count(0)
        self.update_data['path'] = '/sodarZone/does/not/exist'
        response = self.request_knox(
            self.url, 'PUT', data=self.update_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.request.refresh_from_db()
        self.assertEqual(self.request.description, '')
        self.assertEqual(self.request.path, self.obj_path)
        self._assert_tl_count(0)

    def test_put_assay_path(self):
        """Test PUT to update request with assay path (should fail)"""
        self.update_data['path'] = self.irods_backend.get_path(self.assay)
        response = self.request_knox(
            self.url, 'PUT', data=self.update_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.request.refresh_from_db()
        self.assertEqual(self.request.path, self.obj_path)

    def test_patch(self):
        """Test PATCH to update request"""
        self._assert_tl_count(0)
        update_data = {'description': IRODS_REQUEST_DESC_UPDATED}
        response = self.request_knox(
            self.url, 'PATCH', data=update_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.description, IRODS_REQUEST_DESC_UPDATED)
        self.assertEqual(self.request.path, self.obj_path)
        self._assert_tl_count(1)

    def test_patch_superuser(self):
        """Test PATCH as superuser"""
        self._assert_tl_count(0)
        update_data = {'description': IRODS_REQUEST_DESC_UPDATED}
        response = self.request_knox(
            self.url, 'PATCH', data=update_data, token=self.get_token(self.user)
        )
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.description, IRODS_REQUEST_DESC_UPDATED)
        self.assertEqual(self.request.path, self.obj_path)
        self.assertEqual(self.request.user, self.user_contributor)
        self._assert_tl_count(1)


# NOTE: For TestIrodsDataRequestDestroyAPIView, see test_views_api


class TestIrodsDataRequestAcceptAPIView(
    IrodsDataRequestMixin, IrodsDataRequestAPIViewTestBase
):
    """Tests for IrodsDataRequestAcceptAPIView"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            description=IRODS_REQUEST_DESC,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsDataRequestAcceptAPIView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 0)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 1)
        self.assert_irods_obj(self.obj_path, False)

    def test_post_no_request(self):
        """Test POST to accept non-existing request"""
        url = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': self.category.sodar_uuid},
        )
        response = self.request_knox(url, 'POST')
        self.assertEqual(response.status_code, 404)

    def test_post_delegate(self):
        """Test POST to accept request as delegate"""
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 0)
        response = self.request_knox(
            self.url, 'POST', token=self.get_token(self.user_delegate)
        )
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self.assert_irods_obj(self.obj_path, False)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 1)

    def test_post_contributor(self):
        """Test POST to accept request as contributor (should fail)"""
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 0)
        response = self.request_knox(
            self.url, 'POST', token=self.get_token(self.user_contributor)
        )
        self.assertEqual(response.status_code, 403)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACTIVE)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 0)

    def test_post_locked(self):
        """Test POST to accept request with locked project (should fail)"""
        self.lock_project(self.project)
        self.assert_irods_obj(self.obj_path)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 503)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_FAILED)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 0)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_post_lock_failure(self):
        """Test POST to accept request with project lock failure"""
        self.assert_irods_obj(self.obj_path)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 400)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_FAILED)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contributor, 0)

    def test_post_accepted(self):
        """Test acceptining previously accepted request (should fail)"""
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACTIVE)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)

    def test_post_rejected(self):
        """Test accepting previously rejected request (should fail)"""
        self.assert_irods_obj(self.obj_path, True)
        self.request.status = IRODS_REQUEST_STATUS_REJECTED
        self.request.save()
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 400)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_REJECTED)
        self.assert_irods_obj(self.obj_path, True)


class TestIrodsDataRequestRejectAPIView(
    IrodsDataRequestMixin, IrodsDataRequestAPIViewTestBase
):
    """Tests for IrodsDataRequestRejectAPIView"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            description=IRODS_REQUEST_DESC,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsDataRequestRejectAPIView POST"""
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contributor, 0)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_REJECTED)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contributor, 1)

    def test_post_delegate(self):
        """Test POST to reject request as delegate"""
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contributor, 0)
        response = self.request_knox(
            self.url, 'POST', token=self.get_token(self.user_delegate)
        )
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_REJECTED)
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contributor, 1)

    def test_post_contributor(self):
        """Test POST to reject request as contributor"""
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contributor, 0)
        response = self.request_knox(self.url, 'POST', token=self.token_contrib)
        self.assertEqual(response.status_code, 403)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACTIVE)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contributor, 0)

    def test_post_no_request(self):
        """Test POST to reject non-existing request"""
        url = reverse(
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': self.category.sodar_uuid},
        )
        response = self.request_knox(url, 'POST')
        self.assertEqual(response.status_code, 404)


class TestSampleDataFileExistsAPIView(SampleSheetAPITaskflowTestBase):
    """Tests for SampleDataFileExistsAPIView"""

    def setUp(self):
        super().setUp()
        self.make_irods_colls(self.investigation)
        self.coll_path = self.irods_backend.get_sample_path(self.project)
        self.coll = self.irods.collections.get(self.coll_path)
        self.url = reverse('samplesheets:api_file_exists')

    def test_get_no_file(self):
        """Test SampleDataFileExistsAPIView GET with no file uploaded"""
        response = self.request_knox(self.url, data={'checksum': CHECKSUM_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], False)

    @override_settings(IRODS_HASH_SCHEME=HASH_SCHEME_SHA256)
    def test_get_no_file_sha256(self):
        """Test GET with no file uploaded and SHA256 scheme"""
        response = self.request_knox(
            self.url, data={'checksum': CHECKSUM_SHA256_HEX}
        )
        self.assertEqual(response.status_code, 200)  # Request should succeed
        self.assertEqual(json.loads(response.content)['status'], False)

    def test_get_file(self):
        """Test GET with uploaded file"""
        self.make_irods_object(self.coll, IRODS_FILE_NAME)
        response = self.request_knox(self.url, data={'checksum': CHECKSUM_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], True)

    # TODO: Test with SHA256 and uploaded file

    def test_get_wrong_scheme(self):
        """Test GET with wrong checksum hash scheme"""
        # NOTE: Scheme set to MD5
        response = self.request_knox(
            self.url, data={'checksum': CHECKSUM_SHA256_HEX}
        )
        self.assertEqual(response.status_code, 400)

    def test_get_file_sub_coll(self):
        """Test GET with file in sub collection"""
        sub_coll_path = os.path.join(self.coll_path, 'sub')
        sub_coll = self.irods.collections.create(sub_coll_path)
        self.make_irods_object(sub_coll, IRODS_FILE_NAME)
        response = self.request_knox(self.url, data={'checksum': CHECKSUM_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], True)

    def test_get_no_checksum(self):
        """Test GET with no checksum (should fail)"""
        response = self.request_knox(self.url, data={'checksum': ''})
        self.assertEqual(response.status_code, 400)

    def test_get_invalid_checksum(self):
        """Test GET with invalid checksum (should fail)"""
        response = self.request_knox(
            self.url, data={'checksum': 'Invalid MD5!'}
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(SHEETS_API_FILE_EXISTS_RESTRICT=True)
    def test_get_restrict(self):
        """Test GET with file exists restriction enabled"""
        user_no_roles = self.make_user('user_no_roles')
        response = self.request_knox(
            self.url,
            data={'checksum': CHECKSUM_MD5},
            token=self.get_token(user_no_roles),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['detail'], FILE_EXISTS_RESTRICT_MSG)


class TestProjectIrodsFileListAPIView(SampleSheetAPITaskflowTestBase):
    """Tests for ProjectIrodsFileListAPIView"""

    def setUp(self):
        super().setUp()
        self.taskflow = get_backend_api('taskflow', force=True)
        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session_obj()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TaskProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.url = reverse(
            'samplesheets:api_file_list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get_no_collection(self):
        """Test ProjectIrodsFileListAPIView GET without collection"""
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data['detail'],
            '{}: {}'.format(
                IRODS_QUERY_ERROR_MSG, 'iRODS collection not found'
            ),
        )

    def test_get_empty_collection(self):
        """Test GET with empty collection"""
        # Set up iRODS collections
        self.make_irods_colls(self.investigation)
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_get_files(self):
        """Test GET with files"""
        self.make_irods_colls(self.investigation)
        coll_path = self.irods_backend.get_sample_path(self.project)
        coll = self.irods.collections.get(coll_path)
        data_obj = self.make_irods_object(coll, IRODS_FILE_NAME)
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        expected = {
            'name': IRODS_FILE_NAME,
            'path': data_obj.path,
            'type': 'obj',
            'size': 1024,
            'modify_time': self.get_drf_datetime(data_obj.modify_time),
            'checksum': data_obj.checksum,
        }
        self.assertEqual(response.data[0], expected)
        self.assertIsNotNone(response.data[0]['checksum'])

    def test_get_files_v1_0(self):
        """Test GET with files and API version 1.0"""
        self.make_irods_colls(self.investigation)
        coll_path = self.irods_backend.get_sample_path(self.project)
        coll = self.irods.collections.get(coll_path)
        data_obj = self.make_irods_object(coll, IRODS_FILE_NAME)
        response = self.request_knox(self.url, version='1.0')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        expected = {
            'name': IRODS_FILE_NAME,
            'path': data_obj.path,
            'type': 'obj',
            'size': 1024,
            'modify_time': self.get_drf_datetime(data_obj.modify_time),
        }  # Checksum should not be included
        self.assertEqual(response.data[0], expected)

    def test_get_paginate(self):
        """Test GET with files and pagination"""
        self.make_irods_colls(self.investigation)
        coll_path = self.irods_backend.get_sample_path(self.project)
        coll = self.irods.collections.get(coll_path)
        data_obj = self.make_irods_object(coll, IRODS_FILE_NAME)
        response = self.request_knox(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        expected = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'name': IRODS_FILE_NAME,
                    'path': data_obj.path,
                    'type': 'obj',
                    'size': 1024,
                    'modify_time': self.get_drf_datetime(data_obj.modify_time),
                    'checksum': data_obj.checksum,
                }
            ],
        }
        self.assertEqual(response.data, expected)

    @override_settings(SODAR_API_PAGE_SIZE=5)
    def test_get_paginate_multi(self):
        """Test GET with pagination and multiple pages"""
        self.make_irods_colls(self.investigation)
        coll_path = self.irods_backend.get_sample_path(self.project)
        coll = self.irods.collections.get(coll_path)
        for i in range(0, 11):
            self.make_irods_object(
                coll,
                'test{}.txt'.format(('0' if i < 10 else '') + str(i)),
            )
        stats = self.irods_backend.get_stats(self.irods, coll_path)
        self.assertEqual(stats['file_count'], 11)

        response = self.request_knox(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 11)
        self.assertEqual(response.data['next'], self.url + '?page=2')
        self.assertEqual(response.data['previous'], None)
        self.assertEqual(len(response.data['results']), 5)
        file_names = [r['name'] for r in response.data['results']]
        expected = [f'test0{i}.txt' for i in range(0, 5)]
        self.assertEqual(file_names, expected)

        response = self.request_knox(self.url + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['next'], self.url + '?page=3')
        self.assertEqual(response.data['previous'], self.url + '?page=1')
        self.assertEqual(len(response.data['results']), 5)
        file_names = [r['name'] for r in response.data['results']]
        expected = [
            'test{}.txt'.format(('0' if i < 10 else '') + str(i))
            for i in range(5, 10)
        ]
        self.assertEqual(file_names, expected)

        response = self.request_knox(self.url + '?page=3')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['next'], None)
        self.assertEqual(response.data['previous'], self.url + '?page=2')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'test10.txt')
