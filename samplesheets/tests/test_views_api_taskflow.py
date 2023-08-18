"""
Tests for REST API views in the samplesheets app with SODAR Taskflow enabled
"""

import json
import os

from datetime import timedelta, datetime

from irods.keywords import REG_CHKSUM_KW
from irods.models import TicketQuery

from django.forms.models import model_to_dict
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Timeline dependency
from timeline.models import ProjectEvent

# Taskflowbackend dependency
from taskflowbackend.tests.base import (
    TaskflowAPIViewTestBase,
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
from samplesheets.views import (
    IRODS_REQUEST_EVENT_CREATE as CREATE_ALERT,
    IRODS_REQUEST_EVENT_ACCEPT as ACCEPT_ALERT,
    IRODS_REQUEST_EVENT_REJECT as REJECT_ALERT,
)
from samplesheets.views_api import (
    IRODS_QUERY_ERROR_MSG,
    IRODS_TICKETS_NOT_FOUND_MSG,
    IRODS_TICKET_EX_MSG,
    IRODS_TICKET_DELETED_MSG,
    IRODS_TICKET_NO_UPDATE_FIELDS_MSG,
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
    IRODS_FILE_NAME,
    IRODS_FILE_NAME2,
    INVALID_REDIS_URL,
    TICKET_STR,
    TICKET_LABEL,
)

# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_TSV_DIR = SHEET_DIR + 'i_small2/'
SHEET_PATH = SHEET_DIR + 'i_small2.zip'
SHEET_PATH_EDITED = SHEET_DIR + 'i_small2_edited.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2_alt.zip'
IRODS_FILE_PATH = os.path.dirname(__file__) + '/irods/test1.txt'
IRODS_FILE_MD5 = '0b26e313ed4a7ca6904b0e9369e5b957'
IRODS_REQUEST_DESC_UPDATED = 'updated'
DUMMY_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


# Base Classes and Mixins ------------------------------------------------------


class TestSampleSheetAPITaskflowBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIViewTestBase
):
    """Base samplesheets API view test class with Taskflow enabled"""

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


class TestIrodsAccessTicketAPIViewBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    TaskflowAPIViewTestBase,
):
    """Base samplesheets API view test class for iRODS access ticket requests"""

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
        self.user_contrib = self.make_user('user_contrib')
        self.user_contrib2 = self.make_user('user_contrib2')
        self.user_guest = self.make_user('user_guest')

        self.make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self.make_assignment_taskflow(
            self.project, self.user_contrib, self.role_contributor
        )
        self.make_assignment_taskflow(
            self.project, self.user_contrib2, self.role_contributor
        )
        self.make_assignment_taskflow(
            self.project, self.user_guest, self.role_guest
        )

        # Create collection under assay
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(self.assay_path, 'coll')
        )

        # Get appalerts API and model
        self.app_alerts = get_backend_api('appalerts_backend')
        self.app_alert_model = self.app_alerts.get_model()
        # Set create URL
        self.create_url = reverse(
            'samplesheets:api_irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.user.set_password('password')


class TestIrodsDataRequestAPIViewBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIViewTestBase
):
    """Base samplesheets API view test class for iRODS delete requests"""

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
        self.user_contrib = self.make_user('user_contrib')
        self.user_guest = self.make_user('user_guest')
        self.make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self.make_assignment_taskflow(
            self.project, self.user_contrib, self.role_contributor
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
        self.token_contrib = self.get_token(self.user_contrib)


# Test Cases -------------------------------------------------------------------


class TestInvestigationRetrieveAPIView(TestSampleSheetAPITaskflowBase):
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


class TestIrodsCollsCreateAPIView(TestSampleSheetAPITaskflowBase):
    """Tests for IrodsCollsCreateAPIView"""

    def test_post(self):
        """Test IrodsCollsCreateAPIView POST"""
        self.assertEqual(self.investigation.irods_status, False)
        url = reverse(
            'samplesheets:api_irods_colls_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url, method='POST')
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
        url = reverse(
            'samplesheets:api_irods_colls_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url, method='POST')
        self.assertEqual(response.status_code, 400)


class TestIrodsAccessTicketListAPIView(TestIrodsAccessTicketAPIViewBase):
    """Tests for IrodsAccessListAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket_str = TICKET_STR
        self.path = self.coll.path
        self.label = TICKET_LABEL
        self.date_expires = None
        self.url = reverse(
            'samplesheets:api_irods_ticket_list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test get() in IrodsAccessTicketListAPIView"""
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=self.ticket_str,
            path=self.path,
            label=self.label,
            user=self.user,
            date_expires=self.date_expires,
        )
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user_contrib):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = [
            {
                'sodar_uuid': str(self.ticket.sodar_uuid),
                'label': self.ticket.label,
                'ticket': self.ticket.ticket,
                'assay': self.ticket.assay.pk,
                'study': self.ticket.study.pk,
                'path': self.ticket.path,
                'date_created': local_date_created.isoformat(),
                'date_expires': self.ticket.date_expires,
                'user': self.ticket.user.pk,
                'is_active': self.ticket.is_active(),
            }
        ]
        self.assertEqual(json.loads(response.content), expected)

    def test_get_no_tickets(self):
        """Test get() in IrodsAccessTicketListAPIView with no tickets"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        with self.login(self.user_contrib):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        expected = {'detail': IRODS_TICKETS_NOT_FOUND_MSG}
        self.assertEqual(json.loads(response.content), expected)

    def test_get_active(self):
        """Test get() in IrodsAccessTicketListAPIView with active = True"""
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=self.ticket_str,
            path=self.path,
            label=self.label,
            user=self.user,
            date_expires=self.date_expires,
        )
        self.ticket_expired = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=self.ticket_str,
            path=self.path,
            label=self.label,
            user=self.user,
            date_expires=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(IrodsAccessTicket.objects.count(), 2)
        with self.login(self.user_contrib):
            response = self.client.get(self.url + '?active=1')
        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = [
            {
                'sodar_uuid': str(self.ticket.sodar_uuid),
                'label': self.ticket.label,
                'ticket': self.ticket.ticket,
                'assay': self.ticket.assay.pk,
                'study': self.ticket.study.pk,
                'path': self.ticket.path,
                'date_created': local_date_created.isoformat(),
                'date_expires': self.ticket.date_expires,
                'user': self.ticket.user.pk,
                'is_active': self.ticket.is_active(),
            }
        ]
        self.assertEqual(json.loads(response.content), expected)


class TestIrodsAccessTicketRetrieveAPIView(TestIrodsAccessTicketAPIViewBase):
    """Tests for IrodsAccessTicketRetrieveAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket_str = TICKET_STR
        self.path = self.coll.path
        self.label = TICKET_LABEL
        self.date_expires = None
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=self.ticket_str,
            path=self.path,
            label=self.label,
            user=self.user,
            date_expires=self.date_expires,
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_retrieve',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_get(self):
        """Test get() in IrodsAccessTicketRetrieveAPIView"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user_contrib):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.ticket.label,
            'ticket': self.ticket.ticket,
            'assay': self.ticket.assay.pk,
            'study': self.ticket.study.pk,
            'path': self.ticket.path,
            'date_created': local_date_created.isoformat(),
            'date_expires': self.ticket.date_expires,
            'user': self.ticket.user.pk,
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(json.loads(response.content), expected)

    def test_get_no_ticket(self):
        """Test get() in IrodsAccessTicketRetrieveAPIView with no ticket"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.ticket.delete()
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        with self.login(self.user_contrib):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        expected = {'detail': 'Not found.'}
        self.assertEqual(json.loads(response.content), expected)


class TestIrodsAccessTicketCreateAPIView(TestIrodsAccessTicketAPIViewBase):
    """Tests for IrodsAccessTicketCreateAPIView"""

    def setUp(self):
        super().setUp()
        self.path = self.coll.path
        self.label = TICKET_LABEL
        self.date_expires = (
            timezone.localtime() + timedelta(days=1)
        ).isoformat()
        self.url = reverse(
            'samplesheets:api_irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {
            'assay': self.assay.pk,
            'path': self.path,
            'label': self.label,
            'date_expires': self.date_expires,
        }

    def test_create(self):
        """Test post() in IrodsAccessTicketCreateAPIView as admin"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.path, self.path)
        self.assertEqual(ticket.label, self.label)
        self.assertEqual(
            ticket.date_expires,
            datetime.strptime(self.date_expires, '%Y-%m-%dT%H:%M:%S.%f%z'),
        )
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
        irods_ticket = self.get_irods_ticket(ticket)
        self.assertEqual(irods_ticket[TicketQuery.Ticket.type], 'read')
        self.assertIsNotNone(irods_ticket[TicketQuery.Ticket.expiry_ts])
        self.assertEqual(
            irods_ticket[TicketQuery.Collection.name], self.coll.path
        )

    def test_create_contributor(self):
        """Test post() in IrodsAccessTicketCreateAPIView as contributor"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assert_alert_count(CREATE_ALERT, self.user, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

        with self.login(self.user_contrib):
            response = self.client.post(self.url, self.post_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.path, self.path)
        self.assertEqual(ticket.label, self.label)
        self.assertEqual(
            ticket.date_expires,
            datetime.strptime(self.date_expires, '%Y-%m-%dT%H:%M:%S.%f%z'),
        )
        self.assertEqual(ticket.user, self.user_contrib)
        self.assertEqual(ticket.study, self.study)
        self.assertEqual(ticket.assay, self.assay)
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

        # Assert ticket state in iRODS
        irods_ticket = self.get_irods_ticket(ticket)
        self.assertEqual(irods_ticket[TicketQuery.Ticket.type], 'read')
        self.assertIsNotNone(irods_ticket[TicketQuery.Ticket.expiry_ts])
        self.assertEqual(
            irods_ticket[TicketQuery.Collection.name], self.coll.path
        )

    def test_create_no_expiry(self):
        """Test post() in IrodsAccessTicketCreateAPIView with no expiry date"""
        self.post_data['date_expires'] = ''
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.path, self.path)
        self.assertEqual(ticket.label, self.label)
        self.assertIsNone(ticket.date_expires)

        # Assert ticket state in iRODS
        irods_ticket = self.get_irods_ticket(ticket)
        self.assertEqual(irods_ticket[TicketQuery.Ticket.type], 'read')
        self.assertIsNone(irods_ticket[TicketQuery.Ticket.expiry_ts])
        self.assertEqual(
            irods_ticket[TicketQuery.Collection.name], self.coll.path
        )

    def test_create_invalid_path(self):
        """Test post() in IrodsAccessTicketCreateAPIView with invalid path"""
        self.post_data['path'] = '/invalid/path'
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_create_expired(self):
        """Test post() in IrodsAccessTicketCreateAPIView with expired date"""
        self.post_data['date_expires'] = (
            timezone.localtime() - timedelta(days=1)
        ).isoformat()
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_create_assay_root(self):
        """Test post() in IrodsAccessTicketCreateAPIView with assay root"""
        self.post_data['path'] = self.irods_backend.get_path(self.assay)
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_create_study_path(self):
        """Test post() in IrodsAccessTicketCreateAPIView with study path"""
        self.post_data['path'] = self.irods_backend.get_path(self.study)
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_post_existing_ticket(self):
        """Test post() in IrodsAccessTicketCreateAPIView for the same path"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path=self.coll.path,
            label='OldTicket',
            user=self.user,
        )
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)


class TestIrodsAccessTicketUpdateAPIView(TestIrodsAccessTicketAPIViewBase):
    """Tests for IrodsAccessTicketUpdateAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket_str = TICKET_STR
        self.label = TICKET_LABEL
        self.date_expires = None
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=self.ticket_str,
            path=self.coll.path,
            label=self.label,
            user=self.user,
            date_expires=self.date_expires,
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        self.date_expires_update = (
            timezone.localtime() + timedelta(days=1)
        ).isoformat()
        self.label_update = 'label_update'

    def test_update(self):
        """Test put() in IrodsAccessTicketUpdateAPIView"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

        with self.login(self.user_contrib):
            response = self.client.put(
                self.url,
                {
                    'label': self.label_update,
                    'date_expires': self.date_expires_update,
                },
            )

        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.label_update,
            'ticket': self.ticket.ticket,
            'assay': self.ticket.assay.pk,
            'study': self.ticket.study.pk,
            'path': self.ticket.path,
            'date_created': local_date_created.isoformat(),
            'date_expires': self.date_expires_update,
            'user': self.ticket.user.pk,
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(response.json(), expected)
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

    def test_update_with_path(self):
        """Test put() in IrodsAccessTicketUpdateAPIView with path"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

        with self.login(self.user_contrib):
            response = self.client.put(self.url, {'path': self.coll.path})

        self.assertEqual(response.status_code, 400)
        expected = [
            '{} {}'.format(
                'Updating ' + IRODS_TICKET_EX_MSG + ':',
                IRODS_TICKET_NO_UPDATE_FIELDS_MSG + ' path',
            )
        ]
        self.assertEqual(response.json(), expected)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

    def test_update_invalid_date(self):
        """Test put() in IrodsAccessTicketUpdateAPIView with invalid date"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)
        invalid_date = 'invalid'
        with self.login(self.user_contrib):
            response = self.client.put(self.url, {'date_expires': invalid_date})

        self.assertEqual(response.status_code, 400)
        expected = "Updating {}: Invalid data: ".format(IRODS_TICKET_EX_MSG)
        self.assertIn(expected, str(response.json()))
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)


class TestIrodsAccessTicketDestroyAPIView(TestIrodsAccessTicketAPIViewBase):
    """Tests for IrodsAccessTicketDeleteAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket_str = TICKET_STR
        self.label = TICKET_LABEL
        self.date_expires = (
            timezone.localtime() + timedelta(days=1)
        ).isoformat()
        # Create ticket in database and iRODS
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll.path,
            user=self.user,
            ticket=self.ticket_str,
            label=self.label,
            date_expires=timezone.localtime() + timedelta(days=1),
        )
        self.irods_backend.issue_ticket(
            self.irods,
            'read',
            self.coll.path,
            ticket_str=self.ticket_str,
            expiry_date=None,
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_delete(self):
        """Test delete() in IrodsAccessTicketDeleteAPIView"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)

        with self.login(self.user_contrib):
            response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 204)
        expected = {'detail': IRODS_TICKET_DELETED_MSG}
        self.assertEqual(response.data, expected)
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
        """Test delete() in IrodsAccessTicketDeleteAPIView with invalid URL"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)
        invalid_url = reverse(
            'samplesheets:api_irods_ticket_delete',
            kwargs={'irodsaccessticket': DUMMY_UUID},
        )
        with self.login(self.user_contrib):
            response = self.client.delete(invalid_url)

        self.assertEqual(response.status_code, 404)
        expected = {'detail': 'Not found.'}
        self.assertEqual(response.json(), expected)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)


# NOTE: For TestIrodsDataRequestRetrieveAPIView, see test_views_api
# NOTE: For TestIrodsDataRequestListAPIView, see test_views_api


class TestIrodsDataRequestCreateAPIView(TestIrodsDataRequestAPIViewBase):
    """Tests for IrodsDataRequestCreateAPIView"""

    def test_create(self):
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
            'user': self.user_contrib.pk,
            'status': IRODS_REQUEST_STATUS_ACTIVE,
            'status_info': '',
            'description': IRODS_REQUEST_DESC,
            'sodar_uuid': obj.sodar_uuid,
        }
        self.assertEqual(model_to_dict(obj), expected)
        self.assert_alert_count(CREATE_ALERT, self.user, 1)
        self.assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self.assert_alert_count(CREATE_ALERT, self.user_contrib, 0)
        self.assert_alert_count(CREATE_ALERT, self.user_guest, 0)

    def test_create_no_description(self):
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

    def test_create_trailing_slash(self):
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

    def test_create_invalid_data(self):
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

    def test_create_invalid_path_assay_collection(self):
        """Test POST with assay path (should fail)"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.post_data['path'] = self.assay_path
        response = self.request_knox(
            self.url, 'POST', data=self.post_data, token=self.token_contrib
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

    def test_create_multiple(self):
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
    IrodsDataRequestMixin, TestIrodsDataRequestAPIViewBase
):
    """Tests for IrodsDataRequestUpdateAPIView"""

    def _assert_tl_count(self, count):
        """Assert timeline ProjectEvent count"""
        self.assertEqual(
            ProjectEvent.objects.filter(
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
            user=self.user_contrib,
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
            'user': self.user_contrib.pk,
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


# NOTE: For TestIrodsDataRequestDestroyAPIView, see test_views_api


class TestIrodsDataRequestAcceptAPIView(
    IrodsDataRequestMixin, TestIrodsDataRequestAPIViewBase
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
            user=self.user_contrib,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_accept(self):
        """Test IrodsDataRequestAcceptAPIView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contrib, 1)
        self.assert_irods_obj(self.obj_path, False)

    def test_accept_no_request(self):
        """Test POST to accept non-existing request"""
        url = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': self.category.sodar_uuid},
        )
        response = self.request_knox(url, 'POST')
        self.assertEqual(response.status_code, 404)

    def test_accept_delegate(self):
        """Test POST to accept request as delegate"""
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)
        response = self.request_knox(
            self.url, 'POST', token=self.get_token(self.user_delegate)
        )
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self.assert_irods_obj(self.obj_path, False)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contrib, 1)

    def test_accept_contributor(self):
        """Test POST to accept request as contributor (should fail)"""
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)
        response = self.request_knox(
            self.url, 'POST', token=self.get_token(self.user_contrib)
        )
        self.assertEqual(response.status_code, 403)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACTIVE)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_accept_lock_failure(self):
        """Test POST toa ccept request with project lock failure"""
        self.assert_irods_obj(self.obj_path)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 400)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_FAILED)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

    def test_accept_already_accepted(self):
        """Test accepting already accepted request (should fail)"""
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACTIVE)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACCEPTED)


class TestIrodsDataRequestRejectAPIView(
    IrodsDataRequestMixin, TestIrodsDataRequestAPIViewBase
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
            user=self.user_contrib,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_reject(self):
        """Test IrodsDataRequestRejectAPIView POST"""
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contrib, 0)
        response = self.request_knox(self.url, 'POST')
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_REJECTED)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_delegate(self):
        """Test POST to reject request as delegate"""
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contrib, 0)
        response = self.request_knox(
            self.url, 'POST', token=self.get_token(self.user_delegate)
        )
        self.assertEqual(response.status_code, 200)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_REJECTED)
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_contributor(self):
        """Test POST to reject request as contributor"""
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contrib, 0)
        response = self.request_knox(self.url, 'POST', token=self.token_contrib)
        self.assertEqual(response.status_code, 403)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, IRODS_REQUEST_STATUS_ACTIVE)
        self.assert_irods_obj(self.obj_path)
        self.assert_alert_count(REJECT_ALERT, self.user, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self.assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

    def test_reject_no_request(self):
        """Test POST to reject non-existing request"""
        url = reverse(
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': self.category.sodar_uuid},
        )
        response = self.request_knox(url, 'POST')
        self.assertEqual(response.status_code, 404)


class TestSampleDataFileExistsAPIView(TestSampleSheetAPITaskflowBase):
    """Tests for SampleDataFileExistsAPIView"""

    def setUp(self):
        super().setUp()
        self.make_irods_colls(self.investigation)

    def test_get_no_file(self):
        """Test GET with no file uploaded"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': IRODS_FILE_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], False)

    def test_get_file(self):
        """Test GET with uploaded file"""
        coll_path = self.irods_backend.get_sample_path(self.project) + '/'
        self.irods.data_objects.put(
            IRODS_FILE_PATH, coll_path, **{REG_CHKSUM_KW: ''}
        )
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': IRODS_FILE_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], True)

    def test_get_file_sub_coll(self):
        """Test GET with file in a sub collection"""
        coll_path = self.irods_backend.get_sample_path(self.project) + '/sub'
        self.irods.collections.create(coll_path)
        self.irods.data_objects.put(
            IRODS_FILE_PATH, coll_path + '/', **{REG_CHKSUM_KW: ''}
        )
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': IRODS_FILE_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], True)

    def test_get_no_checksum(self):
        """Test GET with no checksum (should fail)"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': ''})
        self.assertEqual(response.status_code, 400)

    def test_get_invalid_checksum(self):
        """Test GET with invalid checksum (should fail)"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': 'Invalid MD5!'})
        self.assertEqual(response.status_code, 400)


class TestProjectIrodsFileListAPIView(TestSampleSheetAPITaskflowBase):
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

    def test_get_no_collection(self):
        """Test ProjectIrodsFileListAPIView GET without collection"""
        url = reverse(
            'samplesheets:api_file_list',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user):
            response = self.client.get(url)
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
        url = reverse(
            'samplesheets:api_file_list',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['irods_data'], [])

    def test_get_collection_with_files(self):
        """Test GET with files"""
        # Set up iRODS collections
        self.make_irods_colls(self.investigation)
        coll_path = self.irods_backend.get_sample_path(self.project) + '/'
        self.irods.data_objects.put(
            IRODS_FILE_PATH, coll_path, **{REG_CHKSUM_KW: ''}
        )
        url = reverse(
            'samplesheets:api_file_list',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 1)
        self.assertEqual(
            response.data['irods_data'][0]['name'], IRODS_FILE_NAME
        )
        self.assertEqual(response.data['irods_data'][0]['type'], 'obj')
