"""View tests in the samplesheets Django app with taskflow"""

import irods
import os

from datetime import timedelta
from irods.models import TicketQuery
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.contrib.messages import get_messages
from django.forms.models import model_to_dict
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Appalerts dependency
from appalerts.models import AppAlert

# Timeline dependency
from timeline.models import ProjectEvent

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowbackendTestBase

from samplesheets.forms import ERROR_MSG_INVALID_PATH
from samplesheets.models import (
    Investigation,
    IrodsAccessTicket,
    IrodsDataRequest,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import IrodsAccessTicketMixin
from samplesheets.utils import get_sample_colls
from samplesheets.views import (
    IRODS_REQ_ACCEPT_ALERT as ACCEPT_ALERT,
    IRODS_REQ_CREATE_ALERT as CREATE_ALERT,
    IRODS_REQ_REJECT_ALERT as REJECT_ALERT,
    IRODS_NO_REQ_MSG,
)


app_settings = AppSettingAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TEST_FILE_NAME = 'test1'
TEST_FILE_NAME2 = 'test2'
DUMMY_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
PUBLIC_USER_NAME = 'user_no_roles'
PUBLIC_USER_PASS = 'password'
SOURCE_ID = '0815'
SAMPLE_ID = '0815-N1'
INVALID_REDIS_URL = 'redis://127.0.0.1:6666/0'
TICKET_LABEL = 'TestTicket'
TICKET_LABEL_UPDATED = 'TestTicketUpdated'
TICKET_STR = 'q657xxx3i2x2b8vj'


class SampleSheetTaskflowMixin:
    """Taskflow helpers for samplesheets tests"""

    def make_irods_colls(self, investigation, ticket_str=None, request=None):
        """
        Create iRODS collection structure for investigation.

        :param investigation: Investigation object
        :param ticket_str: Access ticket string or None
        :param request: HTTP request object (optional, default=None)
        :raise taskflow.FlowSubmitException if submit fails
        """
        self.assertEqual(investigation.irods_status, False)
        project = investigation.project
        values = {
            'project': project,
            'flow_name': 'sheet_colls_create',
            'flow_data': {
                'colls': get_sample_colls(investigation),
                'ticket_str': ticket_str,
            },
        }
        self.taskflow.submit(**values)
        investigation.refresh_from_db()
        self.assertEqual(investigation.irods_status, True)

    def make_track_hub_coll(self, session, assay_path, name):
        """
        Create iRODS collection for a track hub under assay collection.

        :param session: iRODS session object
        :param assay_path: Full assay path (string)
        :param name: Track hub collection name (string)
        :return: Path to track hub (string)
        """
        track_hubs_path = assay_path + '/TrackHubs'
        try:
            session.collections.get(track_hubs_path)
        except irods.exception.CollectionDoesNotExist:
            session.collections.create(track_hubs_path)
        track_hub = session.collections.create(track_hubs_path + '/' + name)
        return track_hub.path


class SampleSheetPublicAccessMixin:
    """Helpers for sample sheet public access modification with taskflow"""

    def set_public_access(self, access):
        """
        Set project public access by issuing a project update POST request.

        :param access: Bool
        """
        with self.login(self.user):
            response = self.client.patch(
                reverse(
                    'projectroles:api_project_update',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                format='json',
                data={'public_guest_access': access},
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.public_guest_access, access)


class IrodsAccessTicketViewTestMixin:
    """Helpers for iRODS access ticket view tests"""

    def get_irods_ticket(self, sodar_ticket):
        """
        Query for iRODS ticket.

        :param sodar_ticket: IrodsAccessTicket object
        :return: dict
        """
        try:
            return (
                self.irods.query(TicketQuery.Ticket, TicketQuery.Collection)
                .filter(TicketQuery.Ticket.string == sodar_ticket.ticket)
                .one()
            )
        except irods.exception.NoResultFound:
            return None

    @classmethod
    def get_tl_event_count(cls, action):
        """
        Return iRODS ticket timeline event count.

        :param action: "create", "update" or "delete" (string)
        :return: Integer
        """
        return ProjectEvent.objects.filter(
            event_name='irods_ticket_' + action
        ).count()

    @classmethod
    def get_app_alert_count(cls, action):
        """
        Return iRODS ticket app alert count.

        :param action: "create", "update" or "delete" (string)
        :return: Integer
        """
        return AppAlert.objects.filter(
            alert_name='irods_ticket_' + action
        ).count()


class TestIrodsCollsCreateView(
    SampleSheetIOMixin, SampleSheetPublicAccessMixin, TaskflowbackendTestBase
):
    """Tests for iRODS collection structure creation view with taskflow"""

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

    def test_create_colls(self):
        """Test collection structure creation with taskflow"""
        self.assertEqual(self.investigation.irods_status, False)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:collections',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        # Assert sample sheet collection structure state after creation
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)
        # Assert iRODS collection status
        self.assert_irods_coll(self.irods_backend.get_sample_path(self.project))
        self.assert_irods_coll(self.study)
        self.assert_irods_coll(self.assay)
        # Assert app setting status (should be unset)
        self.assertEqual(
            app_settings.get(
                APP_NAME, 'public_access_ticket', project=self.project
            ),
            '',
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_create_colls_anon(self):
        """Test collection structure creation with anonymous project access"""
        self.set_public_access(True)
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(
            app_settings.get(
                APP_NAME, 'public_access_ticket', project=self.project
            ),
            '',
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:collections',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)
        self.assert_irods_coll(self.irods_backend.get_sample_path(self.project))
        self.assert_irods_coll(self.study)
        self.assert_irods_coll(self.assay)
        # Assert app setting status (should be set)
        self.assertNotEqual(
            app_settings.get(
                APP_NAME, 'public_access_ticket', project=self.project
            ),
            '',
        )


class TestSheetDeleteView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowbackendTestBase
):
    """Tests for sample sheet deletion with taskflow"""

    def _setup_files(self):
        """Setup file(s) in iRODS"""
        self.make_irods_colls(self.investigation)
        self.assert_irods_coll(self.irods_backend.get_sample_path(self.project))
        self.assert_irods_coll(self.study)
        self.assert_irods_coll(self.assay)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.file_path = self.assay_path + '/' + TEST_FILE_NAME
        self.irods.data_objects.create(self.file_path)
        self.assertEqual(self.irods.data_objects.exists(self.file_path), True)

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods')
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

    def test_render_no_files_owner(self):
        """Test rendering without files as owner"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.context['irods_file_count'], 0)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_render_no_files_contributor(self):
        """Test rendering without files as contributor"""
        # Create contributor user
        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        with self.login(user_contributor):
            response = self.client.get(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.context['irods_file_count'], 0)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_render_files_owner(self):
        """Test rendering with files as owner"""
        self._setup_files()
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.context['irods_file_count'], 1)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_render_files_contributor(self):
        """Test rendering with files as contributor"""
        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        self._setup_files()
        with self.login(user_contributor):
            response = self.client.get(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.context['can_delete_sheets'], False)

    def test_delete(self):
        """Test sample sheet deleting with taskflow"""
        self.assertIsNotNone(self.investigation)
        values = {'delete_host_confirm': 'testserver'}
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        # Assert investigation status
        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__sodar_uuid=self.project.sodar_uuid
            )

    def test_delete_files_owner(self):
        """Test sheet deleting with files as owner"""
        self._setup_files()
        values = {'delete_host_confirm': 'testserver'}
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__sodar_uuid=self.project.sodar_uuid
            )
        # Assert file status
        self.assertEqual(self.irods.data_objects.exists(self.file_path), False)
        # Assert collection status
        self.assert_irods_coll(
            self.irods_backend.get_sample_path(self.project), expected=False
        )
        self.assert_irods_coll(self.study, expected=False)
        self.assert_irods_coll(self.assay, expected=False)

    def test_delete_files_owner_inherited(self):
        """Test sheet deleting with files as inherited owner"""
        self._setup_files()
        values = {'delete_host_confirm': 'testserver'}
        with self.login(self.user_owner_cat):
            self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__sodar_uuid=self.project.sodar_uuid
            )
        self.assertEqual(self.irods.data_objects.exists(self.file_path), False)
        self.assert_irods_coll(
            self.irods_backend.get_sample_path(self.project), expected=False
        )
        self.assert_irods_coll(self.study, expected=False)
        self.assert_irods_coll(self.assay, expected=False)

    def test_delete_files_delegate(self):
        """Test sheet deleting with files as delegate"""
        # Create and assign delegate user
        user_delegate = self.make_user('user_delegate')
        self.make_assignment_taskflow(
            self.project, user_delegate, self.role_delegate
        )
        self._setup_files()

        values = {'delete_host_confirm': 'testserver'}
        with self.login(user_delegate):
            self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__sodar_uuid=self.project.sodar_uuid
            )
        self.assertEqual(self.irods.data_objects.exists(self.file_path), False)
        self.assert_irods_coll(
            self.irods_backend.get_sample_path(self.project), expected=False
        )
        self.assert_irods_coll(self.study, expected=False)
        self.assert_irods_coll(self.assay, expected=False)

    def test_delete_files_contributor(self):
        """Test sheet deleting with files as contributor (should fail)"""
        # Create contributor user
        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        self._setup_files()

        values = {'delete_host_confirm': 'testserver'}
        with self.login(user_contributor):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        # Assert investigation state after creation (should be there)
        self.assertIsNotNone(
            Investigation.objects.filter(
                project__sodar_uuid=self.project.sodar_uuid
            ).first()
        )
        # Assert collection and file status (operation should fail)
        self.assert_irods_coll(self.irods_backend.get_sample_path(self.project))
        self.assert_irods_coll(self.study)
        self.assert_irods_coll(self.assay)
        self.assertEqual(self.irods.data_objects.exists(self.file_path), True)


class TestIrodsAccessTicketListView(
    SampleSheetTaskflowMixin,
    SampleSheetIOMixin,
    IrodsAccessTicketMixin,
    TaskflowbackendTestBase,
):
    """Tests for the iRODS access ticket list view"""

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

        # Create collection under assay
        assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(assay_path, 'coll')
        )

    def test_render_empty(self):
        """Test rendering empty ticket list"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 0)

    def test_render(self):
        """Test rendering ticket list with created ticket"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path=self.coll.path,
            label=TICKET_LABEL,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.context['object_list'].count(), 1)
        obj = response.context['object_list'].first()
        self.assertEqual(obj.label, TICKET_LABEL)
        self.assertEqual(obj.path, self.coll.path)


class TestIrodsAccessTicketCreateView(
    SampleSheetTaskflowMixin,
    SampleSheetIOMixin,
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    TaskflowbackendTestBase,
):
    """Tests for iRODS access ticket create view"""

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

        # Create collection under assay
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(self.assay_path, 'coll')
        )

        self.date_expires = (timezone.localtime() + timedelta(days=1)).strftime(
            '%Y-%m-%d'
        )
        self.url = reverse(
            'samplesheets:irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.user.set_password('password')

    def test_render(self):
        """Test rendering the iRODS access ticket create view"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['form'].fields), 3)
        self.assertIsNotNone(response.context['form'].fields.get('path'))
        self.assertIsNotNone(response.context['form'].fields.get('label'))
        self.assertIsNotNone(
            response.context['form'].fields.get('date_expires')
        )

    def test_post(self):
        """Test POST to create iRODS access ticket"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

        post_data = {
            'path': self.coll.path,
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        expected = {
            'id': ticket.pk,
            'study': self.study.pk,
            'assay': self.assay.pk,
            'ticket': ticket.ticket,
            'path': self.coll.path,
            'label': TICKET_LABEL,
            'user': self.user.pk,
            'date_expires': ticket.date_expires,
            'sodar_uuid': ticket.sodar_uuid,
        }
        self.assertEqual(model_to_dict(ticket), expected)

        # Assert ticket state in iRODS
        irods_ticket = self.get_irods_ticket(ticket)
        self.assertEqual(irods_ticket[TicketQuery.Ticket.type], 'read')
        self.assertIsNotNone(irods_ticket[TicketQuery.Ticket.expiry_ts])
        self.assertEqual(
            irods_ticket[TicketQuery.Collection.name], self.coll.path
        )

        self.assertEqual(self.get_tl_event_count('create'), 1)
        # As creator is owner, only inherited owner receives an alert
        self.assertEqual(self.get_app_alert_count('create'), 1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='irods_ticket_create')
            .first()
            .user,
            self.user_owner_cat,
        )

    def test_post_contributor(self):
        """Test POST as contributor"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )

        post_data = {
            'path': self.coll.path,
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(user_contributor):
            self.client.post(self.url, post_data)

        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertIsNotNone(self.get_irods_ticket(ticket))

        self.assertEqual(self.get_tl_event_count('create'), 1)
        # Both owners should receive alert
        self.assertEqual(self.get_app_alert_count('create'), 2)
        self.assertListEqual(
            [
                a.user
                for a in AppAlert.objects.filter(
                    alert_name='irods_ticket_create'
                )
            ],
            [self.user, self.user_owner_cat],
        )

    def test_post_no_expiry(self):
        """Test POST with no expiry date"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': self.coll.path,
            'date_expires': '',
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        ticket = IrodsAccessTicket.objects.first()
        self.assertEqual(ticket.get_date_expires(), None)
        irods_ticket = self.get_irods_ticket(ticket)
        self.assertIsNone(irods_ticket[TicketQuery.Ticket.expiry_ts])

    def test_post_invalid_path(self):
        """Test POST with invalid iRODS path (should fail)"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)
        post_data = {
            'path': self.coll.path + '/..',
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertEqual(self.get_tl_event_count('create'), 0)
        self.assertEqual(self.get_app_alert_count('create'), 0)

    def test_post_expired(self):
        """Test POST with expired date (should fail)"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': self.coll.path,
            'date_expires': (timezone.localtime() - timedelta(days=1)).strftime(
                '%Y-%m-%d'
            ),
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)

    def test_post_assay_root(self):
        """Test POST with assay root path"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': self.assay_path,
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)

    def test_post_study_path(self):
        """Test POST with study path (should fail)"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': self.irods_backend.get_path(self.study),
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)

    def test_post_non_existing_path(self):
        """Test POST with non-existing path (should fail)"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': os.path.join(self.assay_path, 'NOT-A-REAL-COLLECTION'),
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)

    def test_post_object_path(self):
        """Test POST with path to data object (should fail)"""
        obj = self.make_irods_object(self.coll, 'test.txt')
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': obj.path,
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)

    def test_post_existing_ticket(self):
        """Test POST with prior ticket for the same path (should fail)"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path=self.coll.path,
            label='OldTicket',
            user=self.user,
        )
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        post_data = {
            'path': self.coll.path,
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)

    def test_post_wrong_project(self):
        """Test POST with assay path in wrong project"""
        alt_project, _ = self.make_project_taskflow(
            'AltProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': self.assay_path,  # Path is still for self.project
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': alt_project.sodar_uuid},
                ),
                post_data,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)


class TestIrodsAccessTicketUpdateView(
    SampleSheetTaskflowMixin,
    SampleSheetIOMixin,
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    TaskflowbackendTestBase,
):
    """Tests for the iRODS access ticket update view"""

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
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)

        # Create collection under assay
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(self.assay_path, 'coll')
        )
        # Create ticket
        self.date_expires = timezone.localtime() + timedelta(days=1)
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll.path,
            user=self.user,
            ticket=TICKET_STR,
            label=TICKET_LABEL,
            date_expires=self.date_expires,
        )
        self.url = reverse(
            'samplesheets:irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_render(self):
        """Test rendering iRODS access ticket update form"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user):
            response = self.client.get(self.url)
        form_data = response.context['form']
        self.assertEqual(form_data.initial['date_expires'], self.date_expires)
        self.assertEqual(form_data.initial['label'], self.ticket.label)
        self.assertEqual(form_data.initial['path'], self.ticket.path)

    def test_post(self):
        """Test POST to update iRODS access ticket"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

        update_data = {'label': TICKET_LABEL_UPDATED, 'date_expires': ''}
        with self.login(self.user):
            response = self.client.post(self.url, update_data)
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.get_date_expires(), None)
        self.assertEqual(self.ticket.label, update_data['label'])
        self.assertEqual(self.ticket.path, self.coll.path)  # Path not updated
        self.assertEqual(self.get_tl_event_count('update'), 1)
        self.assertEqual(self.get_app_alert_count('update'), 1)


class TestIrodsAccessTicketDeleteView(
    SampleSheetTaskflowMixin,
    SampleSheetIOMixin,
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    TaskflowbackendTestBase,
):
    """Tests for the iRODS access ticket delete view"""

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
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Create collection under assay
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(self.assay_path, 'coll')
        )
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
            expiry_date=None,
        )

    def test_render(self):
        """Test rendering iRODS access ticket delete view"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_ticket_delete',
                    kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
                ),
            )
        self.assertEqual(response.status_code, 200)

    def test_delete(self):
        """Test deleting iRODS access ticket"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertIsNotNone(self.get_irods_ticket(self.ticket))
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_ticket_delete',
                    kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        self.assertIsNone(self.get_irods_ticket(self.ticket))
        self.assertEqual(self.get_tl_event_count('delete'), 1)
        self.assertEqual(self.get_app_alert_count('delete'), 1)


class TestIrodsRequestViewsBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Base test class for iRODS delete requests"""

    def _assert_alert_count(self, alert_name, user, count, project=None):
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

        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Set up iRODS data
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.path = os.path.join(self.assay_path, TEST_FILE_NAME)
        self.path_md5 = os.path.join(self.assay_path, f'{TEST_FILE_NAME}.md5')
        # Second file
        self.path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        self.path2_md5 = os.path.join(self.assay_path, f'{TEST_FILE_NAME2}.md5')
        # Create objects
        self.file_obj = self.irods.data_objects.create(self.path)
        self.md5_obj = self.irods.data_objects.create(self.path_md5)
        self.file_obj2 = self.irods.data_objects.create(self.path2)
        self.md5_obj2 = self.irods.data_objects.create(self.path2_md5)

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

        # Get appalerts API and model
        self.app_alerts = get_backend_api('appalerts_backend')
        self.app_alert_model = self.app_alerts.get_model()

        # Set default POST data
        self.post_data = {'path': self.path, 'description': 'bla'}
        self.post_data2 = {'path': self.path2, 'description': 'bla2'}
        # self.post_data_md5 = {'path': self.path_md5, 'description': 'bla_md5'}

    def tearDown(self):
        self.irods.collections.get('/sodarZone/projects').remove(force=True)
        super().tearDown()


class TestIrodsRequestCreateView(TestIrodsRequestViewsBase):
    """Test IrodsRequestCreateView"""

    def test_create(self):
        """Test creating a delete request"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

        with self.login(self.user_contrib):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        obj = IrodsDataRequest.objects.first()
        self.assertEqual(
            list(get_messages(response.wsgi_request))[0].message,
            'iRODS data request "{}" created.'.format(obj.get_display_name()),
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.path)
        self.assertEqual(obj.description, 'bla')
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    def test_create_trailing_slash(self):
        """Test creating a delete request with trailing slash in path"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.path + '/', 'description': 'bla'}

        with self.login(self.user_contrib):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        obj = IrodsDataRequest.objects.first()
        self.assertEqual(
            list(get_messages(response.wsgi_request))[0].message,
            f'iRODS data request "{obj.get_display_name()}" created.',
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.path)
        self.assertEqual(obj.description, 'bla')

    def test_create_invalid_form_data(self):
        """Test creating a delete request with invalid form data"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        post_data = {'path': '/doesnt/exist', 'description': 'bla'}

        with self.login(self.user_contrib):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )
            self.assertEqual(
                response.context['form'].errors['path'][0],
                ERROR_MSG_INVALID_PATH,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

    def test_create_invalid_path_assay_collection(self):
        """Test creating a delete request with assay path (should fail)"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.assay_path, 'description': 'bla'}

        with self.login(self.user_contrib):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

        self.assertEqual(
            response.context['form'].errors['path'][0],
            ERROR_MSG_INVALID_PATH,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

    def test_create_multiple(self):
        """Test creating multiple_requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.post_data['path'] = path2
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


class TestIrodsRequestUpdateView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestUpdateView"""

    def test_update(self):
        """Test POST request for updating a delete request"""
        post_data = {'path': self.path, 'description': 'Description'}
        update_data = {'path': self.path, 'description': 'Updated'}

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_update',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                update_data,
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        obj = IrodsDataRequest.objects.first()
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request "{}" updated.'.format(obj.get_display_name()),
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.path)
        self.assertEqual(obj.description, 'Updated')

    def test_post_update_invalid_form_data(self):
        """Test updating a delete request with invalid form data"""
        post_data = {'path': self.path, 'description': 'Description'}
        update_data = {'path': '/doesnt/exist', 'description': 'Updated'}

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_update',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                update_data,
            )
            self.assertEqual(
                response.context['form'].errors['path'][0],
                ERROR_MSG_INVALID_PATH,
            )


class TestIrodsRequestDeleteView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestUpdateView"""

    def test_get_contributor(self):
        """Test GET request for deleting a request"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    def test_delete_contributor(self):
        """Test POST request for deleting a request"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request deleted.',
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

    def test_delete_one_of_multiple(self):
        """Test deleting one of multiple requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.post_data['path'] = path2
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 2)
            obj = IrodsDataRequest.objects.first()
            # NOTE: Still should only have one request for both
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

            self.client.post(
                reverse(
                    'samplesheets:irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        # NOTE: After deleting just one the requests, alerts remain
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


class TestIrodsRequestAcceptView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestAcceptView"""

    def test_render(self):
        """Test rendering IrodsRequestAcceptView"""
        self.assert_irods_obj(self.path)
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
        self.assertEqual(response.context['irods_request_data'][0], obj)

    def test_render_coll(self):
        """Test rendering IrodsRequestAcceptView with a collection request"""
        coll_path = os.path.join(self.assay_path, 'request_coll')
        self.irods.collections.create(coll_path)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.post_data['path'] = coll_path

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
        self.assertEqual(response.context['irods_request_data'][0], obj)

    def test_accept(self):
        """Test accepting a delete request"""
        self.assert_irods_obj(self.path)
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
            self.assertEqual(
                list(get_messages(response.wsgi_request))[-1].message,
                'iRODS data request "{}" accepted.'.format(
                    obj.get_display_name()
                ),
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACCEPTED')
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_irods_obj(self.path, False)

    def test_accept_no_request(self):
        """Test accepting a delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        with self.login(self.user_owner_cat):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': DUMMY_UUID},
                ),
                {'confirm': True},
            )
        self.assertEqual(response.status_code, 404)

    def test_accept_invalid_form_data(self):
        """Test accepting a delete request with invalid form data"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': False},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context['form'].errors['confirm'][0],
                'This field is required.',
            )

        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_irods_obj(self.path)

    def test_accept_owner(self):
        """Test accepting a delete request as owner"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

        with self.login(self.user_owner_cat):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
            self.assertEqual(
                list(get_messages(response.wsgi_request))[-1].message,
                'iRODS data request "{}" accepted.'.format(
                    obj.get_display_name()
                ),
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACCEPTED')
        self.assert_irods_obj(self.path, False)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 1)

    def test_accept_delegate(self):
        """Test accepting a delete request as delegate"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

        with self.login(self.user_delegate):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
            self.assertEqual(
                list(get_messages(response.wsgi_request))[-1].message,
                'iRODS data request "{}" accepted.'.format(
                    obj.get_display_name()
                ),
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACCEPTED')
        self.assert_irods_obj(self.path, False)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 1)

    def test_accept_contributor(self):
        """Test accepting a delete request as contributor"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()
            self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
            self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
            self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertRedirects(response, reverse('home'))

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assert_irods_obj(self.path)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

    def test_accept_one_of_multiple(self):
        """Test accepting one of multiple requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.post_data['path'] = path2
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(
            IrodsDataRequest.objects.filter(status='ACTIVE').count(), 2
        )
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )

        self.assertEqual(
            IrodsDataRequest.objects.filter(status='ACTIVE').count(), 1
        )
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_accept_lock_failure(self):
        """Test accepting a delete request with project lock failure"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'FAILED')
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self.assert_irods_obj(self.path, True)


class TestIrodsRequestAcceptBatchView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestAcceptBatchView"""

    def test_render(self):
        """Test rendering IrodsRequestAcceptBatchView"""
        self.assert_irods_obj(self.path)
        self.assert_irods_obj(self.path_md5)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data2,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 2)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {
                    # 'irodsdatarequests': ','.join(
                    'irods_requests': ','.join(
                        [
                            str(irods_request.sodar_uuid)
                            for irods_request in IrodsDataRequest.objects.all()
                        ]
                    ),
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['affected_object_paths'],
            sorted(
                set(
                    [
                        irods_request.path
                        for irods_request in IrodsDataRequest.objects.all()
                    ]
                )
            ),
        )
        self.assertEqual(len(response.context['irods_request_data']), 2)
        self.assertEqual(
            response.context['irods_request_data'][0],
            IrodsDataRequest.objects.first(),
        )
        self.assertEqual(
            response.context['irods_request_data'][1],
            IrodsDataRequest.objects.last(),
        )

    def test_render_coll(self):
        """Test rendering IrodsRequestAcceptBatchView for a collection"""
        coll_path = os.path.join(self.assay_path, 'request_coll')
        self.irods.collections.create(coll_path)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.post_data['path'] = coll_path

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {
                    # 'irodsdatarequests': ','.join(
                    'irods_requests': ','.join(
                        [
                            str(irods_request.sodar_uuid)
                            for irods_request in IrodsDataRequest.objects.all()
                        ]
                    ),
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['irods_request_data'][0],
            IrodsDataRequest.objects.first(),
        )
        self.assertEqual(
            response.context['affected_object_paths'][0],
            coll_path,
        )

    def test_accept(self):
        """Test accepting a delete request"""
        self.assert_irods_obj(self.path)
        self.assert_irods_obj(self.path2)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data2,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 2)

        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {
                    # 'irodsdatarequests': ','.join(
                    'irods_requests': ','.join(
                        [
                            str(irods_request.sodar_uuid)
                            for irods_request in IrodsDataRequest.objects.all()
                        ]
                    )
                    + ',',  # Add trailing comma to test for correct splitting
                    'confirm': True,
                },
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(len(list(get_messages(response.wsgi_request))), 2)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request "{}" accepted.'.format(
                IrodsDataRequest.objects.first().get_display_name()
            ),
        )
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-2].message,
            'iRODS data request "{}" accepted.'.format(
                IrodsDataRequest.objects.last().get_display_name()
            ),
        )
        obj = IrodsDataRequest.objects.first()
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACCEPTED')
        obj2 = IrodsDataRequest.objects.last()
        obj2.refresh_from_db()
        self.assertEqual(obj2.status, 'ACCEPTED')
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_irods_obj(self.path, False)
        self.assert_irods_obj(self.path2, False)

    def test_accept_no_request(self):
        """Test accepting a delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        with self.login(self.user_owner_cat):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {
                    # 'irodsdatarequests': DUMMY_UUID + ',',
                    'irods_requests': DUMMY_UUID + ',',
                    'confirm': True,
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            IRODS_NO_REQ_MSG,
        )

    def test_accept_invalid_form_data(self):
        """Test accepting a delete request with invalid form data"""
        self.assert_irods_obj(self.path)
        self.assert_irods_obj(self.path2)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data2,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 2)

        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {
                    # 'irodsdatarequests': ','.join(
                    'irods_requests': ','.join(
                        [
                            str(irods_request.sodar_uuid)
                            for irods_request in IrodsDataRequest.objects.all()
                        ]
                    )
                    + ',',  # Add trailing comma to test for correct splitting
                    'confirm': False,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['confirm'][0],
            'This field is required.',
        )
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_irods_obj(self.path)
        self.assert_irods_obj(self.path2)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_accept_lock_failure(self):
        """Test accepting a delete request with redis lock failure"""
        self.assert_irods_obj(self.path)
        self.assert_irods_obj(self.path2)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data2,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 2)

        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {
                    # 'irodsdatarequests': ','.join(
                    'irods_requests': ','.join(
                        [
                            str(irods_request.sodar_uuid)
                            for irods_request in IrodsDataRequest.objects.all()
                        ]
                    )
                    + ',',  # Add trailing comma to test for correct splitting
                    'confirm': True,
                },
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        obj = IrodsDataRequest.objects.first()
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'FAILED')
        obj2 = IrodsDataRequest.objects.last()
        obj2.refresh_from_db()
        self.assertEqual(obj2.status, 'FAILED')
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self.assert_irods_obj(self.path)
        self.assert_irods_obj(self.path2)


class TestIrodsRequestRejectView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestRejectView"""

    def test_reject_admin(self):
        """Test rejecting delete request as admin"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request "{}" rejected.'.format(obj.get_display_name()),
        )
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'REJECTED')
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_owner(self):
        """Test rejecting delete request as owner"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user_owner_cat):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request "{}" rejected.'.format(obj.get_display_name()),
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'REJECTED')
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_delegate(self):
        """Test rejecting delete request as delegate"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user_delegate):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request "{}" rejected.'.format(obj.get_display_name()),
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'REJECTED')
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_contributor(self):
        """Test rejecting delete request as contributor"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()

            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertRedirects(response, reverse('home'))

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'User not authorized for requested action.',
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

    def test_reject_one_of_multiple(self):
        """Test rejecting one of multiple requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.post_data['path'] = path2
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(
            IrodsDataRequest.objects.filter(status='ACTIVE').count(), 2
        )
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

        with self.login(self.user):
            self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                )
            )

        self.assertEqual(
            IrodsDataRequest.objects.filter(status='ACTIVE').count(), 1
        )
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_no_request(self):
        """Test rejecting delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_owner_cat):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': DUMMY_UUID},
                ),
            )
        self.assertEqual(response.status_code, 404)


class TestIrodsRequestRejectBatchView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestRejectBatchView"""

    def test_reject(self):
        """Test rejecting delete request"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data2,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 2)

            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_reject_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {
                    # 'irodsdatarequests': ','.join(
                    'irods_requests': ','.join(
                        [
                            str(irods_request.sodar_uuid)
                            for irods_request in IrodsDataRequest.objects.all()
                        ]
                    )
                    + ','
                },
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request "{}" rejected.'.format(
                IrodsDataRequest.objects.first().get_display_name()
            ),
        )
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-2].message,
            'iRODS data request "{}" rejected.'.format(
                IrodsDataRequest.objects.last().get_display_name()
            ),
        )
        obj = IrodsDataRequest.objects.first()
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'REJECTED')
        obj2 = IrodsDataRequest.objects.last()
        obj2.refresh_from_db()
        self.assertEqual(obj2.status, 'REJECTED')
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

    def test_reject_no_request(self):
        """Test rejecting delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        with self.login(self.user_owner_cat):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_reject_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                # {'irodsdatarequests': DUMMY_UUID + ','},
                {'irods_requests': DUMMY_UUID + ','},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            IRODS_NO_REQ_MSG,
        )


class TestIrodsRequestListView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestListView"""

    def test_list(self):
        """Test GET request for listing delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)

            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)
        self.assertEqual(response.context['object_list'][0].path, self.path)

    def test_list_as_admin_by_contributor(self):
        """Test GET request for listing delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_list_as_owner_by_contributor(self):
        """Test GET request for listing delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)
        self.assertEqual(response.context['object_list'][0].path, self.path)

    def test_list_as_contributor2_by_contributor(self):
        """Test GET request for listing delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib2):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_list_empty(self):
        """Test GET request for empty list of delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)


class TestSampleDataPublicAccess(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    SampleSheetPublicAccessMixin,
    TaskflowbackendTestBase,
):
    """Tests for granting/revoking public guest access for projects"""

    def setUp(self):
        super().setUp()
        # Create user in iRODS
        self.user_no_roles = self.make_user(PUBLIC_USER_NAME)
        try:
            self.irods.users.create(
                user_name=PUBLIC_USER_NAME,
                user_type='rodsuser',
                user_zone=self.irods.zone,
            )
        except irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
            pass  # In case a previous test failed before cleanup
        self.irods.users.modify(PUBLIC_USER_NAME, 'password', PUBLIC_USER_PASS)
        self.user_home_path = '/{}/home/{}'.format(
            settings.IRODS_ZONE, PUBLIC_USER_NAME
        )
        self.assertTrue(self.irods.collections.exists(self.user_home_path))
        self.user_session = get_backend_api(
            'omics_irods',
            user_name=PUBLIC_USER_NAME,
            user_pass=PUBLIC_USER_PASS,
        ).get_session_obj()

        # Make publicly accessible project
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
            public_guest_access=True,
        )

        # Import investigation and create collections
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.make_irods_colls(self.investigation)
        self.project_path = self.irods_backend.get_path(self.project)
        self.sample_path = self.irods_backend.get_sample_path(self.project)

        # Create test file
        self.file_path = self.sample_path + '/' + TEST_FILE_NAME
        self.irods.data_objects.create(self.file_path)

    def tearDown(self):
        # self.irods.collections.remove(self.user_home_path)
        self.irods.users.remove(user_name=PUBLIC_USER_NAME)
        self.user_session.cleanup()
        super().tearDown()

    def test_public_access(self):
        """Test public access for project"""
        obj = self.user_session.data_objects.get(self.file_path)
        self.assertIsNotNone(obj)
        # Ensure no access to project root
        with self.assertRaises(irods.exception.CollectionDoesNotExist):
            self.user_session.data_objects.get(self.project_path)

    def test_public_access_disable(self):
        """Test public access with disabled access"""
        self.set_public_access(False)
        obj = self.irods.data_objects.get(self.file_path)  # Test with owner
        self.assertIsNotNone(obj)
        with self.assertRaises(irods.exception.CollectionDoesNotExist):
            self.user_session.data_objects.get(self.file_path)

    def test_public_access_reenable(self):
        """Test public access with disabled and re-enabled access"""
        self.set_public_access(False)
        self.set_public_access(True)
        obj = self.irods.data_objects.get(self.file_path)  # Test with owner
        self.assertIsNotNone(obj)
        obj = self.user_session.data_objects.get(self.file_path)
        self.assertIsNotNone(obj)
        # Ensure no access to project root
        with self.assertRaises(irods.exception.CollectionDoesNotExist):
            self.user_session.data_objects.get(self.project_path)

    def test_public_access_nested(self):
        """Test public access for nested collection"""
        new_coll_path = self.sample_path + '/new_coll'
        coll = self.irods.collections.create(new_coll_path)  # Test with owner
        self.assertIsNotNone(coll)
        coll = self.user_session.collections.get(new_coll_path)
        self.assertIsNotNone(coll)

    def test_public_access_nested_disable(self):
        """Test public access for nested collection with disabled access"""
        self.set_public_access(False)
        new_coll_path = self.sample_path + '/new_coll'
        coll = self.irods.collections.create(new_coll_path)  # Test with owner
        self.assertIsNotNone(coll)
        with self.assertRaises(irods.exception.CollectionDoesNotExist):
            self.user_session.collections.get(new_coll_path)


class TestProjectSearchView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowbackendTestBase
):
    """Tests for project search with sample sheet items"""

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

        # Set up sample collections
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)

        # Create test file
        self.file_name = '{}_test.txt'.format(SAMPLE_ID)
        self.file_path = self.assay_path + '/' + self.file_name
        self.irods.data_objects.create(self.file_path)

    def test_search(self):
        """Test search without keyword limiting"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': SAMPLE_ID})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(len(data['results']['materials']['items']), 1)
        self.assertEqual(
            data['results']['materials']['items'][0]['name'], SAMPLE_ID
        )
        self.assertEqual(len(data['results']['files']['items']), 1)
        self.assertEqual(
            data['results']['files']['items'][0]['name'], self.file_name
        )

    def test_search_limit_source(self):
        """Test search with source type limit"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': '{} type:source'.format(SOURCE_ID)})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(len(data['results']['materials']['items']), 1)
        self.assertEqual(
            data['results']['materials']['items'][0]['name'], SOURCE_ID
        )

    def test_search_limit_sample(self):
        """Test search with sample type limit"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': '{} type:sample'.format(SAMPLE_ID)})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(len(data['results']['materials']['items']), 1)
        self.assertEqual(
            data['results']['materials']['items'][0]['name'], SAMPLE_ID
        )

    def test_search_limit_file(self):
        """Test search with file type limit"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': '{} type:file'.format(SAMPLE_ID)})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(len(data['results']['files']['items']), 1)
        self.assertEqual(
            data['results']['files']['items'][0]['name'], self.file_name
        )
