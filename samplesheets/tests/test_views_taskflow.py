"""Tests for UI views in the samplesheets app with taskflow"""

import os
import uuid

from datetime import timedelta
from irods.exception import CollectionDoesNotExist, NoResultFound
from irods.models import TicketQuery
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.contrib.messages import get_messages
from django.core import mail
from django.forms.models import model_to_dict
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.views import NO_AUTH_MSG

# Appalerts dependency
from appalerts.models import AppAlert

# Timeline dependency
from timeline.models import TimelineEvent

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from samplesheets.forms import ERROR_MSG_INVALID_PATH
from samplesheets.models import (
    Investigation,
    IrodsAccessTicket,
    IrodsDataRequest,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
    IRODS_REQUEST_STATUS_FAILED,
    IRODS_REQUEST_STATUS_ACCEPTED,
    IRODS_REQUEST_STATUS_REJECTED,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import (
    IrodsAccessTicketMixin,
    IrodsDataRequestMixin,
    IRODS_REQUEST_DESC,
)
from samplesheets.utils import get_sample_colls
from samplesheets.views import (
    IRODS_REQUEST_EVENT_ACCEPT as EVENT_ACCEPT,
    IRODS_REQUEST_EVENT_CREATE as EVENT_CREATE,
    IRODS_REQUEST_EVENT_DELETE as EVENT_DELETE,
    IRODS_REQUEST_EVENT_REJECT as EVENT_REJECT,
    IRODS_REQUEST_EVENT_UPDATE as EVENT_UPDATE,
    NO_REQUEST_MSG,
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
DUMMY_UUID = str(uuid.uuid4())
SHEET_PATH = SHEET_DIR + 'i_small.zip'
IRODS_FILE_NAME = 'test1.txt'
IRODS_FILE_NAME2 = 'test2.txt'
PUBLIC_USER_NAME = 'user_no_roles'
PUBLIC_USER_PASS = 'password'
SOURCE_ID = '0815'
SAMPLE_ID = '0815-N1'
INVALID_REDIS_URL = 'redis://127.0.0.1:6666/0'
TICKET_LABEL = 'TestTicket'
TICKET_LABEL_UPDATED = 'TestTicketUpdated'
TICKET_STR = 'q657xxx3i2x2b8vj'
IRODS_REQUEST_DESC_UPDATE = 'Updated'
SHEET_SYNC_URL = 'https://sodar.instance/samplesheets/sync/' + DUMMY_UUID
SHEET_SYNC_URL_INVALID = 'https://some.sodar/not-valid-url'
SHEET_SYNC_TOKEN = 'dohdai4EZie0xooF'


# Base Classes and Mixins ------------------------------------------------------


class SampleSheetTaskflowMixin:
    """Taskflow helpers for samplesheets tests"""

    def make_irods_colls(self, investigation, ticket_str=None):
        """
        Create iRODS collection structure for investigation.

        :param investigation: Investigation object
        :param ticket_str: Access ticket string or None
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
        except CollectionDoesNotExist:
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
        except NoResultFound:
            return None

    @classmethod
    def get_tl_event_count(cls, action):
        """
        Return iRODS ticket timeline event count.

        :param action: "create", "update" or "delete" (string)
        :return: Integer
        """
        return TimelineEvent.objects.filter(
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


class IrodsDataRequestViewTestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Base test class for iRODS delete requests"""

    # TODO: Retrieve this from a common base/helper class instead of redef
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

    # TODO: Move this into SODAR Core (see bihealth/sodar-core#1243)
    def _assert_tl_count(self, event_name, count, **kwargs):
        """
        Assert expected timeline event count.

        :param event_name: Event name (string)
        :param user: SODARUser object
        :param count: Integer
        :param kwargs: Extra kwargs for query (dict, optional)
        """
        timeline = get_backend_api('timeline_backend')
        TimelineEvent, _ = timeline.get_models()
        self.assertEqual(
            TimelineEvent.objects.filter(
                event_name=event_name, **kwargs
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
        self.obj_path = os.path.join(self.assay_path, IRODS_FILE_NAME)
        self.obj_path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.file_obj = self.irods.data_objects.create(self.obj_path)
        self.file_obj2 = self.irods.data_objects.create(self.obj_path2)
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
        # Get appalerts API and model
        self.app_alerts = get_backend_api('appalerts_backend')
        self.app_alert_model = self.app_alerts.get_model()
        # Set default POST data
        self.post_data = {
            'path': self.obj_path,
            'description': IRODS_REQUEST_DESC,
        }
        self.post_data2 = {
            'path': self.obj_path2,
            'description': IRODS_REQUEST_DESC,
        }


# Tests ------------------------------------------------------------------------


class TestIrodsCollsCreateView(
    SampleSheetIOMixin, SampleSheetPublicAccessMixin, TaskflowViewTestBase
):
    """Tests for IrodsCollsCreateView with taskflow"""

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
        # Set up test helpers
        self.url = reverse(
            'samplesheets:collections',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.url_redirect = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsCollsCreateView POST"""
        self.assertEqual(self.investigation.irods_status, False)
        with self.login(self.user):
            response = self.client.post(self.url)
            self.assertRedirects(response, self.url_redirect)
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
    def test_post_anon(self):
        """Test POST with anonymous access enabled"""
        self.set_public_access(True)
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(
            app_settings.get(
                APP_NAME, 'public_access_ticket', project=self.project
            ),
            '',
        )
        with self.login(self.user):
            response = self.client.post(self.url)
            self.assertRedirects(response, self.url_redirect)
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
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowViewTestBase
):
    """Tests for SheetDeleteView with taskflow"""

    def _setup_files(self):
        """Setup file(s) in iRODS"""
        self.make_irods_colls(self.investigation)
        self.assert_irods_coll(self.irods_backend.get_sample_path(self.project))
        self.assert_irods_coll(self.study)
        self.assert_irods_coll(self.assay)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.file_path = self.assay_path + '/' + IRODS_FILE_NAME
        self.irods.data_objects.create(self.file_path)
        self.assertEqual(self.irods.data_objects.exists(self.file_path), True)

    def _assert_tl_event_count(self, count):
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='sheet_delete').count(),
            count,
        )

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods')
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
        self.timeline = get_backend_api('timeline_backend')
        self.url = reverse(
            'samplesheets:delete',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {'delete_host_confirm': 'testserver'}

    def test_get_no_files_owner(self):
        """Test SheetDeleteView GET without files as owner"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.context['irods_file_count'], 0)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_get_no_files_contributor(self):
        """Test GET without files as contributor"""
        # Create contributor user
        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        with self.login(user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.context['irods_file_count'], 0)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_get_files_owner(self):
        """Test GET with files as owner"""
        self._setup_files()
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.context['irods_file_count'], 1)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_get_files_contributor(self):
        """Test GET with files as contributor"""
        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        self._setup_files()
        with self.login(user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.context['can_delete_sheets'], False)

    def test_post(self):
        """Test POST with no iRODS collections or files"""
        self.assertIsNotNone(self.investigation)
        self._assert_tl_event_count(0)
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
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
        # Assert timeline event status
        self._assert_tl_event_count(1)
        tl_event = TimelineEvent.objects.get(event_name='sheet_delete')
        self.assertEqual(
            tl_event.get_status().status_type, self.timeline.TL_STATUS_OK
        )

    def test_post_colls(self):
        """Test POST with collections created"""
        self.make_irods_colls(self.investigation)
        self.assert_irods_coll(
            self.irods_backend.get_sample_path(self.project), expected=True
        )
        self._assert_tl_event_count(0)
        with self.login(self.user):
            self.client.post(self.url, self.post_data)
        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__sodar_uuid=self.project.sodar_uuid
            )
        self.assert_irods_coll(
            self.irods_backend.get_sample_path(self.project), expected=False
        )
        self._assert_tl_event_count(1)
        tl_event = TimelineEvent.objects.get(event_name='sheet_delete')
        self.assertEqual(
            tl_event.get_status().status_type, self.timeline.TL_STATUS_OK
        )

    def test_post_files_owner(self):
        """Test sheet deleting with files as owner"""
        self._setup_files()
        with self.login(self.user):
            self.client.post(self.url, self.post_data)
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

    def test_post_files_owner_inherited(self):
        """Test sheet deleting with files as inherited owner"""
        self._setup_files()
        with self.login(self.user_owner_cat):
            self.client.post(self.url, self.post_data)
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

    def test_post_files_delegate(self):
        """Test sheet deleting with files as delegate"""
        # Create and assign delegate user
        user_delegate = self.make_user('user_delegate')
        self.make_assignment_taskflow(
            self.project, user_delegate, self.role_delegate
        )
        self._setup_files()
        with self.login(user_delegate):
            self.client.post(self.url, self.post_data)
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

    def test_post_files_contributor(self):
        """Test sheet deleting with files as contributor (should fail)"""
        # Create contributor user
        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        self._setup_files()
        with self.login(user_contributor):
            response = self.client.post(self.url, self.post_data)
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
    TaskflowViewTestBase,
):
    """Tests for IrodsAccessTicketListView with taskflow"""

    def setUp(self):
        super().setUp()
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
        assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(assay_path, 'coll')
        )
        self.url = reverse(
            'samplesheets:irods_tickets',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketListView GET"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path=self.coll.path,
            label=TICKET_LABEL,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.context['object_list'].count(), 1)
        obj = response.context['object_list'].first()
        self.assertEqual(obj.label, TICKET_LABEL)
        self.assertEqual(obj.path, self.coll.path)

    def test_get_empty(self):
        """Test GET with empty ticket list"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 0)


class TestIrodsAccessTicketCreateView(
    SampleSheetTaskflowMixin,
    SampleSheetIOMixin,
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    TaskflowViewTestBase,
):
    """Tests for IrodsAccessTicketCreateView with taskflow"""

    def setUp(self):
        super().setUp()
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

    def test_get(self):
        """Test IrodsAccessTicketCreateView GET"""
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
        """Test POST"""
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
        alerts = AppAlert.objects.filter(
            alert_name='irods_ticket_create'
        ).order_by('user__username')
        self.assertEqual(
            [a.user for a in alerts],
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
        """Test POST with assay root path (should fail)"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)
        post_data = {
            'path': self.assay_path,
            'date_expires': self.date_expires,
            'label': TICKET_LABEL,
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IrodsAccessTicket.objects.count(), 0)

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
    TaskflowViewTestBase,
):
    """Tests for IrodsAccessTicketUpdateView with taskflow"""

    def setUp(self):
        super().setUp()
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

    def test_get(self):
        """Test IrodsAccessTicketUpdateView GET"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user):
            response = self.client.get(self.url)
        form_data = response.context['form']
        self.assertEqual(form_data.initial['date_expires'], self.date_expires)
        self.assertEqual(form_data.initial['label'], self.ticket.label)
        self.assertEqual(form_data.initial['path'], self.ticket.path)

    def test_post(self):
        """Test POST"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertEqual(self.get_tl_event_count('update'), 0)
        self.assertEqual(self.get_app_alert_count('update'), 0)

        post_data = {'label': TICKET_LABEL_UPDATED, 'date_expires': ''}
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
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.get_date_expires(), None)
        self.assertEqual(self.ticket.label, post_data['label'])
        self.assertEqual(self.ticket.path, self.coll.path)  # Path not updated
        self.assertEqual(self.get_tl_event_count('update'), 1)
        self.assertEqual(self.get_app_alert_count('update'), 1)


class TestIrodsAccessTicketDeleteView(
    SampleSheetTaskflowMixin,
    SampleSheetIOMixin,
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    TaskflowViewTestBase,
):
    """Tests for IrodsAccessTicketDeleteView with taskflow"""

    def setUp(self):
        super().setUp()
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
        self.url = reverse(
            'samplesheets:irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketDeleteView GET"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        """Test POST"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        self.assertIsNotNone(self.get_irods_ticket(self.ticket))
        self.assertEqual(self.get_tl_event_count('delete'), 0)
        self.assertEqual(self.get_app_alert_count('delete'), 0)
        with self.login(self.user):
            response = self.client.post(self.url)
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


class TestIrodsDataRequestCreateView(IrodsDataRequestViewTestBase):
    """Tests for IrodsDataRequestCreateView with taskflow"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsDataRequestCreateView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_tl_count(EVENT_CREATE, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 0)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 0)

        with self.login(self.user_contributor):
            response = self.client.post(self.url, self.post_data)
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
        self.assertEqual(obj.path, self.obj_path)
        self.assertEqual(obj.description, IRODS_REQUEST_DESC)
        self._assert_tl_count(EVENT_CREATE, 1)
        self.assertEqual(
            TimelineEvent.objects.get(event_name=EVENT_CREATE).extra_data,
            {
                'action': IRODS_REQUEST_ACTION_DELETE,
                'path': obj.path,
                'description': obj.description,
            },
        )
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)

    def test_post_trailing_slash(self):
        """Test POST with trailing slash in path"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {
            'path': self.obj_path + '/',
            'description': IRODS_REQUEST_DESC,
        }
        with self.login(self.user_contributor):
            response = self.client.post(self.url, post_data)
        obj = IrodsDataRequest.objects.first()
        self.assertEqual(
            list(get_messages(response.wsgi_request))[0].message,
            f'iRODS data request "{obj.get_display_name()}" created.',
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.obj_path)
        self.assertEqual(obj.description, IRODS_REQUEST_DESC)

    def test_post_invalid_data(self):
        """Test POST with invalid form data"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_tl_count(EVENT_CREATE, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 0)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 0)
        post_data = {'path': '/doesnt/exist', 'description': IRODS_REQUEST_DESC}
        with self.login(self.user_contributor):
            response = self.client.post(self.url, post_data)
        self.assertEqual(
            response.context['form'].errors['path'][0],
            ERROR_MSG_INVALID_PATH,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_tl_count(EVENT_CREATE, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 0)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 0)

    def test_post_assay_path(self):
        """Test POST with assay path (should fail)"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.assay_path, 'description': IRODS_REQUEST_DESC}
        with self.login(self.user_contributor):
            response = self.client.post(self.url, post_data)
        self.assertEqual(
            response.context['form'].errors['path'][0],
            ERROR_MSG_INVALID_PATH,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

    def test_create_multiple(self):
        """Test POST with multiple requests for same path"""
        path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.irods.data_objects.create(path2)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_tl_count(EVENT_CREATE, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 0)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 0)
        with self.login(self.user_contributor):
            self.client.post(self.url, self.post_data)
            self.post_data['path'] = path2
            self.client.post(self.url, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self._assert_tl_count(EVENT_CREATE, 2)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)


class TestIrodsDataRequestUpdateView(
    IrodsDataRequestMixin, IrodsDataRequestViewTestBase
):
    """Tests for IrodsDataRequestUpdateView with taskflow"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
            description=IRODS_REQUEST_DESC,
        )
        self.url = reverse(
            'samplesheets:irods_request_update',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsDataRequestUpdateView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_tl_count(EVENT_UPDATE, 0)

        post_data = {
            'path': self.obj_path,
            'description': IRODS_REQUEST_DESC_UPDATE,
        }
        with self.login(self.user_contributor):
            response = self.client.post(self.url, post_data)
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            'iRODS data request "{}" updated.'.format(
                self.request.get_display_name()
            ),
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.request.refresh_from_db()
        self.assertEqual(self.request.path, self.obj_path)
        self.assertEqual(self.request.description, IRODS_REQUEST_DESC_UPDATE)
        self._assert_tl_count(EVENT_UPDATE, 1)
        self.assertEqual(
            TimelineEvent.objects.get(event_name=EVENT_UPDATE).extra_data,
            {
                'action': IRODS_REQUEST_ACTION_DELETE,
                'path': self.request.path,
                'description': self.request.description,
            },
        )

    def test_post_superuser(self):
        """Test POST as superuser"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_tl_count(EVENT_UPDATE, 0)

        post_data = {
            'path': self.obj_path,
            'description': IRODS_REQUEST_DESC_UPDATE,
        }
        with self.login(self.user):
            self.client.post(self.url, post_data)

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.request.refresh_from_db()
        self.assertEqual(self.request.path, self.obj_path)
        self.assertEqual(self.request.description, IRODS_REQUEST_DESC_UPDATE)
        # Assert user is not updated when superuser updates the request
        self.assertEqual(self.request.user, self.user_contributor)
        self._assert_tl_count(EVENT_UPDATE, 1)

    def test_post_invalid_form_data(self):
        """Test POST with invalid form data"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_tl_count(EVENT_UPDATE, 0)

        post_data = {
            'path': '/sodarZone/path/does/not/exist',
            'description': IRODS_REQUEST_DESC_UPDATE,
        }
        with self.login(self.user_contributor):
            response = self.client.post(self.url, post_data)

        self.assertEqual(
            response.context['form'].errors['path'][0],
            ERROR_MSG_INVALID_PATH,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.request.refresh_from_db()
        self.assertEqual(self.request.path, self.obj_path)
        self.assertEqual(self.request.description, IRODS_REQUEST_DESC)
        self._assert_tl_count(EVENT_UPDATE, 0)


class TestIrodsDataRequestDeleteView(
    IrodsDataRequestMixin, IrodsDataRequestViewTestBase
):
    """Tests for IrodsDataRequestDeleteView"""

    def setUp(self):
        super().setUp()
        self.url_create = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsDataRequestDeleteView POST"""
        # NOTE: We use post() to ensure alerts are created
        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assert_irods_obj(self.obj_path)
        self._assert_tl_count(EVENT_DELETE, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user_contributor):
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
        self.assert_irods_obj(self.obj_path)
        self._assert_tl_count(EVENT_DELETE, 1)
        self.assertEqual(
            TimelineEvent.objects.get(event_name=EVENT_DELETE).extra_data, {}
        )
        # Create alerts should be deleted
        self._assert_alert_count(EVENT_CREATE, self.user, 0)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 0)

    def test_post_one_of_multiple(self):
        """Test POST for one of multiple requests"""
        self._assert_tl_count(EVENT_DELETE, 0)
        obj_path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.irods.data_objects.create(obj_path2)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
            self.post_data['path'] = obj_path2
            self.client.post(self.url_create, self.post_data)

            self.assertEqual(IrodsDataRequest.objects.count(), 2)
            self.assert_irods_obj(self.obj_path)
            self.assert_irods_obj(obj_path2)
            # NOTE: Still should only have one request for both
            self._assert_alert_count(EVENT_CREATE, self.user, 1)
            self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
            obj = IrodsDataRequest.objects.filter(path=obj_path2).first()
            self.client.post(
                reverse(
                    'samplesheets:irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(obj_path2)
        self._assert_tl_count(EVENT_DELETE, 1)
        # NOTE: After deleting just one the requests, alerts remain
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)


class TestIrodsDataRequestAcceptView(
    IrodsDataRequestMixin, IrodsDataRequestViewTestBase
):
    """Tests for IrodsDataRequestAcceptView with taskflow"""

    def setUp(self):
        super().setUp()
        self.timeline = get_backend_api('timeline_backend')
        self.url_create = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestAcceptView GET"""
        self.assert_irods_obj(self.obj_path)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
        self.assertEqual(response.context['request_objects'][0], obj)

    def test_get_coll(self):
        """Test GET with collection request"""
        coll_path = os.path.join(self.assay_path, 'request_coll')
        self.irods.collections.create(coll_path)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=coll_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
        self.assertEqual(response.context['request_objects'][0], obj)

    def test_post(self):
        """Test POST to accept delete request"""
        self.assert_irods_obj(self.obj_path)
        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_tl_count(EVENT_ACCEPT, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        mail_count = len(mail.outbox)

        obj = IrodsDataRequest.objects.first()
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
            'iRODS data request "{}" accepted.'.format(obj.get_display_name()),
        )
        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self._assert_tl_count(EVENT_ACCEPT, 1)
        self._assert_alert_count(EVENT_CREATE, self.user, 0)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self.assert_irods_obj(self.obj_path, False)
        tl_event = TimelineEvent.objects.filter(event_name=EVENT_ACCEPT).first()
        self.assertEqual(tl_event.status_changes.count(), 2)
        self.assertEqual(
            tl_event.get_status().status_type, self.timeline.TL_STATUS_OK
        )
        self.assertEqual(len(mail.outbox), mail_count + 1)
        self.assertEqual(
            mail.outbox[-1].recipients(), [self.user_contributor.email]
        )

    def test_post_no_request(self):
        """Test POST with non-existing delete request"""
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

    def test_post_invalid_data(self):
        """Test POST with invalid form data"""
        self.assert_irods_obj(self.obj_path)
        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_tl_count(EVENT_ACCEPT, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)

        obj = IrodsDataRequest.objects.first()
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
        self._assert_tl_count(EVENT_ACCEPT, 0)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self.assert_irods_obj(self.obj_path)

    def test_post_as_owner(self):
        """Test POST as owner"""
        self.assert_irods_obj(self.obj_path)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 0)

        with self.login(self.user_owner_cat):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self.assert_irods_obj(self.obj_path, False)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 1)

    def test_post_delegate(self):
        """Test POST as delegate"""
        self.assert_irods_obj(self.obj_path)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 0)

        with self.login(self.user_delegate):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self.assert_irods_obj(self.obj_path, False)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 1)

    def test_post_contributor(self):
        """Test POST as contributor"""
        self.assert_irods_obj(self.obj_path)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 0)

        with self.login(self.user_contributor):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertRedirects(response, reverse('home'))

        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACTIVE)
        self.assert_irods_obj(self.obj_path)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 0)

    def test_post_one_of_multiple(self):
        """Test POST for one of multiple requests"""
        obj_path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.irods.data_objects.create(obj_path2)
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(obj_path2)
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        request2 = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=obj_path2,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.assertEqual(
            IrodsDataRequest.objects.filter(
                status=IRODS_REQUEST_STATUS_ACTIVE
            ).count(),
            2,
        )
        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': request2.sodar_uuid},
                ),
                {'confirm': True},
            )

        self.assertEqual(
            IrodsDataRequest.objects.filter(
                status=IRODS_REQUEST_STATUS_ACTIVE
            ).count(),
            1,
        )
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(obj_path2, False)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_post_lock_failure(self):
        """Test POST with project lock failure"""
        self.assert_irods_obj(self.obj_path)
        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)

        obj = IrodsDataRequest.objects.first()
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
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_FAILED)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self.assert_irods_obj(self.obj_path, True)
        tl_event = TimelineEvent.objects.filter(event_name=EVENT_ACCEPT).first()
        self.assertEqual(tl_event.status_changes.count(), 2)
        self.assertEqual(
            tl_event.get_status().status_type, self.timeline.TL_STATUS_FAILED
        )

    def test_post_collection(self):
        """Test POST with multiple objects in collection"""
        coll_path = os.path.join(self.assay_path, 'request_coll')
        obj_path2 = os.path.join(coll_path, IRODS_FILE_NAME)
        self.irods.collections.create(coll_path)
        self.irods.data_objects.create(obj_path2)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assert_irods_obj(obj_path2)

        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=coll_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 0)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_contributor, 1)
        self.assertEqual(self.irods.collections.exists(coll_path), False)
        self.assert_irods_obj(obj_path2, False)

    def test_post_disable_email_notify(self):
        """Test POST wth disabled email notifications"""
        app_settings.set(
            APP_NAME,
            'notify_email_irods_request',
            False,
            user=self.user_contributor,
        )
        self.assert_irods_obj(self.obj_path)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        mail_count = len(mail.outbox)
        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self.assert_irods_obj(self.obj_path, False)
        self.assertEqual(len(mail.outbox), mail_count)  # No new mail


class TestIrodsDataRequestAcceptBatchView(
    IrodsDataRequestMixin, IrodsDataRequestViewTestBase
):
    """Tests for IrodsDataRequestAcceptBatchView with taskflow"""

    @classmethod
    def _get_request_uuids(cls):
        return ','.join(
            [str(r.sodar_uuid) for r in IrodsDataRequest.objects.all()]
        )

    def setUp(self):
        super().setUp()
        self.url_create = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.url_accept = reverse(
            'samplesheets:irods_request_accept_batch',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.url_list = reverse(
            'samplesheets:irods_requests',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestAcceptBatchView GET"""
        self.assert_irods_obj(self.obj_path)
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path2,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 2)

        with self.login(self.user):
            response = self.client.post(
                self.url_accept, {'irods_requests': self._get_request_uuids()}
            )
        self.assertEqual(response.status_code, 200)
        paths = [r.path for r in IrodsDataRequest.objects.all()]
        self.assertEqual(
            response.context['affected_object_paths'], sorted(set(paths))
        )
        self.assertEqual(len(response.context['request_objects']), 2)
        self.assertEqual(
            response.context['request_objects'][0],
            IrodsDataRequest.objects.first(),
        )
        self.assertEqual(
            response.context['request_objects'][1],
            IrodsDataRequest.objects.last(),
        )

    def test_get_coll(self):
        """Test GET with collection"""
        coll_path = os.path.join(self.assay_path, 'request_coll')
        self.irods.collections.create(coll_path)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=coll_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user):
            response = self.client.post(
                self.url_accept,
                {'irods_requests': self._get_request_uuids()},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['request_objects'][0],
            IrodsDataRequest.objects.first(),
        )
        self.assertEqual(
            response.context['affected_object_paths'][0], coll_path
        )

    def test_post(self):
        """Test POST to accept delete requests"""
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(self.obj_path2)

        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
            self.client.post(
                self.url_create,
                self.post_data2,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                self.url_accept,
                {
                    'irods_requests': self._get_request_uuids()
                    + ',',  # Add trailing comma to test for correct splitting
                    'confirm': True,
                },
            )
            self.assertRedirects(response, self.url_list)
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
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACCEPTED)
        obj2 = IrodsDataRequest.objects.last()
        obj2.refresh_from_db()
        self.assertEqual(obj2.status, IRODS_REQUEST_STATUS_ACCEPTED)
        self._assert_alert_count(EVENT_CREATE, self.user, 0)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self.assert_irods_obj(self.obj_path, False)
        self.assert_irods_obj(self.obj_path2, False)

    def test_post_no_request(self):
        """Test POST with non-existing delete request"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        with self.login(self.user_owner_cat):
            response = self.client.post(
                self.url_accept,
                {
                    'irods_requests': DUMMY_UUID + ',',
                    'confirm': True,
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            NO_REQUEST_MSG,
        )

    def test_post_invalid_data(self):
        """Test POST with invalid form data"""
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(self.obj_path2)

        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.client.post(self.url_create, self.post_data2)
            self.assertEqual(IrodsDataRequest.objects.count(), 2)

        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                self.url_accept,
                {
                    'irods_requests': self._get_request_uuids()
                    + ',',  # Add trailing comma to test for correct splitting
                    'confirm': False,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['confirm'][0],
            'This field is required.',
        )
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(self.obj_path2)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_post_lock_failure(self):
        """Test POST with project lock failure"""
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(self.obj_path2)

        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.client.post(self.url_create, self.post_data2)
            self.assertEqual(IrodsDataRequest.objects.count(), 2)

        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_ACCEPT, self.user, 0)
        self._assert_alert_count(EVENT_ACCEPT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                self.url_accept,
                {
                    'irods_requests': self._get_request_uuids()
                    + ',',  # Add trailing comma to test for correct splitting
                    'confirm': True,
                },
            )
            self.assertRedirects(response, self.url_list)
        obj = IrodsDataRequest.objects.first()
        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_FAILED)
        obj2 = IrodsDataRequest.objects.last()
        obj2.refresh_from_db()
        self.assertEqual(obj2.status, IRODS_REQUEST_STATUS_FAILED)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(self.obj_path2)


class TestIrodsDataRequestRejectView(
    IrodsDataRequestMixin, IrodsDataRequestViewTestBase
):
    """Tests for IrodsDataRequestRejectView"""

    def setUp(self):
        super().setUp()
        self.url_create = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get_superuser(self):
        """Test IrodsDataRequestRejectView GET as superuser"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assert_irods_obj(self.obj_path)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 0)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        mail_count = len(mail.outbox)

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
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_REJECTED)
        self.assert_irods_obj(self.obj_path)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 1)
        self.assertEqual(len(mail.outbox), mail_count + 1)
        self.assertEqual(
            mail.outbox[-1].recipients(), [self.user_contributor.email]
        )

    def test_get_owner(self):
        """Test GET as owner"""
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )

        with self.login(self.user_owner_cat):
            self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_REJECTED)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 1)

    def test_get_delegate(self):
        """Test GET as delegate"""
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )

        with self.login(self.user_delegate):
            self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )

        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_REJECTED)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 1)

    def test_get_contributor(self):
        """Test GET as contributor"""
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )

        with self.login(self.user_contributor):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertRedirects(response, reverse('home'))

        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message, NO_AUTH_MSG
        )
        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_ACTIVE)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 0)

    def test_get_one_of_multiple(self):
        """Test GET with one of multiple requests"""
        obj_path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.irods.data_objects.create(obj_path2)
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(obj_path2)
        with self.login(self.user_contributor):
            self.client.post(self.url_create, self.post_data)
            self.post_data['path'] = obj_path2
            self.client.post(self.url_create, self.post_data)
        self.assertEqual(
            IrodsDataRequest.objects.filter(
                status=IRODS_REQUEST_STATUS_ACTIVE
            ).count(),
            2,
        )
        obj = IrodsDataRequest.objects.filter(path=obj_path2).first()
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)

        with self.login(self.user):
            self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                )
            )

        self.assertEqual(
            IrodsDataRequest.objects.filter(
                status=IRODS_REQUEST_STATUS_ACTIVE
            ).count(),
            1,
        )
        self.assert_irods_obj(self.obj_path)
        self.assert_irods_obj(obj_path2)
        self._assert_alert_count(EVENT_CREATE, self.user, 1)
        self._assert_alert_count(EVENT_CREATE, self.user_delegate, 1)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 1)

    def test_get_no_request(self):
        """Test GET with non-existing delete request"""
        with self.login(self.user_owner_cat):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': DUMMY_UUID},
                ),
            )
        self.assertEqual(response.status_code, 404)

    def test_get_disable_email_notify(self):
        """Test GET with disabled email notifications"""
        app_settings.set(
            APP_NAME,
            'notify_email_irods_request',
            False,
            user=self.user_contributor,
        )
        self.assert_irods_obj(self.obj_path)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        mail_count = len(mail.outbox)
        with self.login(self.user):
            self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
        obj.refresh_from_db()
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_REJECTED)
        self.assert_irods_obj(self.obj_path)
        self.assertEqual(len(mail.outbox), mail_count)


class TestIrodsDataRequestRejectBatchView(
    IrodsDataRequestMixin, IrodsDataRequestViewTestBase
):
    """Tests for IrodsDataRequestRejectBatchView with taskflow"""

    def setUp(self):
        super().setUp()
        self.url_create = reverse(
            'samplesheets:irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.url_reject = reverse(
            'samplesheets:irods_request_reject_batch',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsDataRequestRejectBatchView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 0)
        with self.login(self.user):
            self.client.post(self.url_create, self.post_data)
            self.client.post(self.url_create, self.post_data2)
            response = self.client.post(
                self.url_reject,
                {
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
        self.assertEqual(obj.status, IRODS_REQUEST_STATUS_REJECTED)
        obj2 = IrodsDataRequest.objects.last()
        obj2.refresh_from_db()
        self.assertEqual(obj2.status, IRODS_REQUEST_STATUS_REJECTED)
        self._assert_alert_count(EVENT_REJECT, self.user, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_delegate, 0)
        self._assert_alert_count(EVENT_REJECT, self.user_contributor, 0)

    def test_post_no_request(self):
        """Test POST with non-existing request"""
        with self.login(self.user_owner_cat):
            response = self.client.post(
                self.url_reject,
                {'irods_requests': DUMMY_UUID + ','},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[-1].message,
            NO_REQUEST_MSG,
        )


class TestSampleDataPublicAccess(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    SampleSheetPublicAccessMixin,
    TaskflowViewTestBase,
):
    """Tests for granting/revoking public guest access for projects"""

    def setUp(self):
        super().setUp()
        # Create user in iRODS
        self.user_no_roles = self.make_user(PUBLIC_USER_NAME)
        self.irods.users.create(
            user_name=PUBLIC_USER_NAME,
            user_type='rodsuser',
            user_zone=self.irods.zone,
        )
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
        self.file_path = self.sample_path + '/' + IRODS_FILE_NAME
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
        with self.assertRaises(CollectionDoesNotExist):
            self.user_session.data_objects.get(self.project_path)

    def test_public_access_disable(self):
        """Test public access with disabled access"""
        self.set_public_access(False)
        obj = self.irods.data_objects.get(self.file_path)  # Test with owner
        self.assertIsNotNone(obj)
        with self.assertRaises(CollectionDoesNotExist):
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
        with self.assertRaises(CollectionDoesNotExist):
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
        with self.assertRaises(CollectionDoesNotExist):
            self.user_session.collections.get(new_coll_path)


class TestProjectSearchView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowViewTestBase
):
    """Tests for ProjectSearchView with taskflow and sample sheet items"""

    def setUp(self):
        super().setUp()
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
        self.assay_path = self.irods_backend.get_path(self.assay)
        # Create test file
        self.file_name = '{}_test.txt'.format(SAMPLE_ID)
        self.file_path = self.assay_path + '/' + self.file_name
        self.irods.data_objects.create(self.file_path)

    def test_get(self):
        """Test ProjectSearchView GET without keyword limiting"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': SAMPLE_ID})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(len(data['results']['materials'].items), 1)
        self.assertEqual(
            data['results']['materials'].items[0]['name'], SAMPLE_ID
        )
        self.assertEqual(len(data['results']['files'].items), 1)
        self.assertEqual(
            data['results']['files'].items[0]['name'], self.file_name
        )

    def test_get_limit_source(self):
        """Test GET with source type limit"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': '{} type:source'.format(SOURCE_ID)})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(len(data['results']['materials'].items), 1)
        self.assertEqual(
            data['results']['materials'].items[0]['name'], SOURCE_ID
        )

    def test_get_limit_sample(self):
        """Test GET with sample type limit"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': '{} type:sample'.format(SAMPLE_ID)})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(len(data['results']['materials'].items), 1)
        self.assertEqual(
            data['results']['materials'].items[0]['name'], SAMPLE_ID
        )

    def test_get_limit_file(self):
        """Test GET with file type limit"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': '{} type:file'.format(SAMPLE_ID)})
            )
        self.assertEqual(response.status_code, 200)
        data = response.context['app_results'][0]
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(len(data['results']['files'].items), 1)
        self.assertEqual(
            data['results']['files'].items[0]['name'], self.file_name
        )


class TestProjectUpdateView(TaskflowViewTestBase):
    """Tests for ProjectUpdateView with taskflow and samplesheets app settings"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.values = model_to_dict(self.project)
        self.values['parent'] = self.category.sodar_uuid
        self.values['owner'] = self.user.sodar_uuid
        self.values.update(
            app_settings.get_all(project=self.project, post_safe=True)
        )
        self.url = reverse(
            'projectroles:update',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post_sync_default(self):
        """Test POST with default sheet sync values"""
        self.values['description'] = 'updated description'
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            app_settings.get(
                APP_NAME, 'sheet_sync_enable', project=self.project
            )
        )
        self.assertEqual(
            app_settings.get(APP_NAME, 'sheet_sync_url', project=self.project),
            '',
        )
        self.assertEqual(
            app_settings.get(
                APP_NAME, 'sheet_sync_token', project=self.project
            ),
            '',
        )

    def test_post_sync_enable(self):
        """Test POST with enabled sync and correct url/token"""
        self.values['description'] = 'updated description'
        self.assertFalse(
            app_settings.get(
                APP_NAME, 'sheet_sync_enable', project=self.project
            )
        )
        self.assertEqual(
            app_settings.get(APP_NAME, 'sheet_sync_url', project=self.project),
            '',
        )
        self.assertEqual(
            app_settings.get(
                APP_NAME, 'sheet_sync_token', project=self.project
            ),
            '',
        )

        self.values['settings.samplesheets.sheet_sync_enable'] = True
        self.values['settings.samplesheets.sheet_sync_url'] = SHEET_SYNC_URL
        self.values['settings.samplesheets.sheet_sync_token'] = SHEET_SYNC_TOKEN
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
            self.assertRedirects(
                response,
                reverse(
                    'projectroles:detail',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.description, 'updated description')
        self.assertTrue(
            app_settings.get(
                APP_NAME, 'sheet_sync_enable', project=self.project
            )
        )
        self.assertEqual(
            app_settings.get(APP_NAME, 'sheet_sync_url', project=self.project),
            SHEET_SYNC_URL,
        )
        self.assertEqual(
            app_settings.get(
                APP_NAME, 'sheet_sync_token', project=self.project
            ),
            SHEET_SYNC_TOKEN,
        )

    def test_post_sync_no_url_or_token(self):
        """Test POST with enabled sync and no URL or token"""
        self.values['settings.samplesheets.sheet_sync_enable'] = True
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
        self.assertEqual(response.status_code, 200)

    def test_post_sync_no_token(self):
        """Test POST with enabled sync and no token"""
        self.values['settings.samplesheets.sheet_sync_enable'] = True
        self.values['settings.samplesheets.sheet_sync_url'] = SHEET_SYNC_URL
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
        self.assertEqual(response.status_code, 200)

    def test_post_sync_no_url(self):
        """Test POST with enabled sync and no URL or token"""
        self.values['settings.samplesheets.sheet_sync_enable'] = True
        self.values['settings.samplesheets.sheet_sync_token'] = SHEET_SYNC_TOKEN
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
        self.assertEqual(response.status_code, 200)

    def test_post_sync_invalid_url(self):
        """Test POST with enabled sync and no token"""
        self.values['settings.samplesheets.sheet_sync_enable'] = True
        self.values['settings.samplesheets.sheet_sync_url'] = (
            SHEET_SYNC_URL_INVALID
        )
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
        self.assertEqual(response.status_code, 200)

    def test_post_sync_disabled(self):
        """Test POST with disabled sync and valid input"""
        self.values['settings.samplesheets.sheet_sync_enable'] = False
        self.values['settings.samplesheets.sheet_sync_url'] = SHEET_SYNC_URL
        self.values['settings.samplesheets.sheet_sync_token'] = SHEET_SYNC_TOKEN
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
        self.assertEqual(response.status_code, 302)

    def test_post_sync_disabled_invalid_url(self):
        """Test POST with disabled sync and invalid input"""
        self.values['settings.samplesheets.sheet_sync_enable'] = False
        self.values['settings.samplesheets.sheet_sync_url'] = (
            SHEET_SYNC_URL_INVALID
        )
        with self.login(self.user):
            response = self.client.post(self.url, self.values)
        self.assertEqual(response.status_code, 200)
