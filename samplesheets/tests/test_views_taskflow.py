"""Integration tests for views in the samplesheets Django app with taskflow"""

# NOTE: You must supply 'sodar_url': self.live_server_url in taskflow requests!
import os
from datetime import timedelta
import irods
from unittest import skipIf

from django.conf import settings
from django.contrib import auth
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_taskflow import TestTaskflowBase

from samplesheets.forms import ERROR_MSG_INVALID_PATH
from samplesheets.models import (
    Investigation,
    IrodsAccessTicket,
    IrodsDataRequest,
)
from samplesheets.tests.test_tasks import TestSheetSyncBase
from samplesheets.utils import get_sample_colls
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.views import TRACK_HUBS_COLL


app_settings = AppSettingAPI()
User = auth.get_user_model()


APP_NAME = 'samplesheets'


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = SODAR_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = SODAR_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = SODAR_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW'
]

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TASKFLOW_ENABLED = (
    True if 'taskflow' in settings.ENABLED_BACKEND_PLUGINS else False
)
TASKFLOW_SKIP_MSG = 'Taskflow not enabled in settings'
BACKENDS_ENABLED = all(
    _ in settings.ENABLED_BACKEND_PLUGINS for _ in ['omics_irods', 'taskflow']
)
BACKEND_SKIP_MSG = (
    'Required backends (taskflow, omics_irods) ' 'not enabled in settings'
)
TEST_FILE_NAME = 'test1'


class SampleSheetTaskflowMixin:
    """Taskflow helpers for samplesheets tests"""

    def _make_irods_colls(self, investigation, request=None):
        """
        Create iRODS collection structure for investigation.

        :param investigation: Investigation object
        :param request: HTTP request object (optional, default=None)
        :raise taskflow.FlowSubmitException if submit fails
        """
        self.assertEqual(investigation.irods_status, False)

        values = {
            'project_uuid': investigation.project.sodar_uuid,
            'flow_name': 'sheet_dirs_create',
            'flow_data': {'dirs': get_sample_colls(investigation)},
            'request': request,
        }

        if not request:
            values['sodar_url'] = self.live_server_url

        self.taskflow.submit(**values)

        investigation.refresh_from_db()
        self.assertEqual(investigation.irods_status, True)

    def _make_track_hub_coll(self, session, assay_path, name):
        """
        Create iRODS collection for a track hub under assay collection.
        """
        track_hubs_path = assay_path + '/TrackHubs'

        try:
            session.collections.get(track_hubs_path)
        except irods.exception.CollectionDoesNotExist:
            session.collections.create(track_hubs_path)

        track_hub = session.collections.create(track_hubs_path + '/' + name)
        return track_hub.path


class TestIrodsCollectionView(SampleSheetIOMixin, TestTaskflowBase):
    """Tests for iRODS collection structure creation view with taskflow"""

    def setUp(self):
        super().setUp()

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

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_create_colls(self):
        """Test collection structure creation with taskflow"""

        # Assert precondition
        self.assertEqual(self.investigation.irods_status, False)

        # Issue POST request
        values = {
            'sodar_url': self.live_server_url
        }  # HACK: Override callback URL

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:collections',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert sample sheet collection structure state after creation
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestSampleSheetDeleteView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TestTaskflowBase
):
    """Tests for sample sheet deletion with taskflow"""

    def setUp(self):
        super().setUp()

        self.irods_backend = get_backend_api('omics_irods')

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

    def test_delete(self):
        """Test sample sheet deleting with taskflow"""

        # Assert precondition
        self.assertIsNotNone(self.investigation)

        # Issue POST request
        values = {
            'delete_host_confirm': 'testserver',
            'sodar_url': self.live_server_url,
        }

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert sample sheet dir structure state after creation
        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__sodar_uuid=self.project.sodar_uuid
            )

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

    def test_delete_files_owner(self):
        """Test sample sheet deleting with files in irods as owner"""

        # Create collections and file in iRODS
        self._make_irods_colls(self.investigation)
        irods = self.irods_backend.get_session()
        assay_path = self.irods_backend.get_path(self.assay)
        file_path = assay_path + '/' + TEST_FILE_NAME
        irods.data_objects.create(file_path)

        # Assert precondition
        self.assertEqual(irods.data_objects.exists(file_path), True)

        # Issue POST request
        values = {
            'delete_host_confirm': 'testserver',
            'sodar_url': self.live_server_url,
        }

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert sample sheet dir structure state after creation
        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__sodar_uuid=self.project.sodar_uuid
            )

        # Assert file status
        self.assertEqual(irods.data_objects.exists(file_path), False)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

    def test_delete_files_contributor(self):
        """Test sample sheet deleting with files in irods as contributor"""

        # Create contributor user
        user_contributor = self.make_user('user_contributor')
        self._make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )

        # Create collections and file in iRODS
        self._make_irods_colls(self.investigation)
        irods = self.irods_backend.get_session()
        assay_path = self.irods_backend.get_path(self.assay)
        file_path = assay_path + '/' + TEST_FILE_NAME
        irods.data_objects.create(file_path)

        # Assert precondition
        self.assertEqual(irods.data_objects.exists(file_path), True)

        # Issue POST request
        values = {
            'delete_host_confirm': 'testserver',
            'sodar_url': self.live_server_url,
        }

        with self.login(user_contributor):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert sample sheet state after creation (should be there)
        self.assertIsNotNone(
            Investigation.objects.filter(
                project__sodar_uuid=self.project.sodar_uuid
            ).first()
        )

        # Assert file status (operation should fail)
        self.assertEqual(irods.data_objects.exists(file_path), True)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsAccessTicketListView(
    SampleSheetTaskflowMixin, SampleSheetIOMixin, TestTaskflowBase
):
    """Tests for the irods access ticket list view"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        self.irods_session = self.irods_backend.get_session()

        # Create iRODS track hub collections
        assay_path = self.irods_backend.get_path(self.assay)
        self._make_track_hub_coll(self.irods_session, assay_path, 'track1')
        self._make_track_hub_coll(self.irods_session, assay_path, 'track2')

        # Create iRODS track hub collections
        assay_path = self.irods_backend.get_path(self.assay)
        self.track_hub1 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track1'
        )
        self.track_hub2 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track2'
        )

    def test_render_empty(self):
        """Test rendering the irods access ticket list view"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        # Assert context data
        self.assertEqual(response.context['object_list'].count(), 0)

    def test_render(self):
        post_data = {
            'path': self.track_hub1,
            'date_expires': (timezone.localtime() + timedelta(days=1)).strftime(
                '%Y-%m-%d'
            ),
            'label': 'TestTicket',
        }

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            response = self.client.get(
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.context['object_list'].count(), 1)

        obj = response.context['object_list'].first()

        self.assertEqual(obj.get_date_expires(), post_data['date_expires'])
        self.assertEqual(obj.label, post_data['label'])
        self.assertEqual(obj.path, post_data['path'])


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsAccessTicketCreateView(
    SampleSheetTaskflowMixin, SampleSheetIOMixin, TestTaskflowBase
):
    """Tests for the irods access ticket list view"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        self.irods_session = self.irods_backend.get_session()

        # Create iRODS track hub collections
        assay_path = self.irods_backend.get_path(self.assay)
        self.track_hub1 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track1'
        )
        self.track_hub2 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track2'
        )

    def test_render(self):
        """Test rendering the irods access ticket create view"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

            self.assertEqual(response.status_code, 200)

            self.assertEqual(len(response.context['form'].fields), 3)
            self.assertIsNotNone(
                response.context['form'].fields.get('date_expires')
            )
            self.assertIsNotNone(response.context['form'].fields.get('label'))
            self.assertIsNotNone(response.context['form'].fields.get('path'))

            self.assertEqual(
                len(response.context['form'].fields['path'].widget.choices), 2
            )
            expected = [
                (
                    track_hub.path,
                    "{} / {}".format(
                        self.assay.get_display_name(), track_hub.name
                    ),
                )
                for track_hub in (
                    self.irods_backend.get_child_colls_by_path(
                        self.irods_backend.get_path(self.assay)
                        + '/'
                        + TRACK_HUBS_COLL
                    )
                )
            ]
            self.assertListEqual(
                response.context['form'].fields['path'].widget.choices, expected
            )

    def test_post(self):
        """Test posting the irods access ticket form"""

        with self.login(self.user):
            self.assertEqual(IrodsAccessTicket.objects.count(), 0)

            post_data = {
                'path': self.track_hub1,
                'date_expires': (
                    timezone.localtime() + timedelta(days=1)
                ).strftime('%Y-%m-%d'),
                'label': 'TestTicket',
            }

            response = self.client.post(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

            self.assertEqual(IrodsAccessTicket.objects.count(), 1)

            ticket = IrodsAccessTicket.objects.first()

            self.assertEqual(
                str(list(get_messages(response.wsgi_request))[0]),
                'iRODS access ticket "%s" created.' % ticket.get_display_name(),
            )

            self.assertEqual(
                ticket.get_date_expires(), post_data['date_expires']
            )
            self.assertEqual(ticket.label, post_data['label'])
            self.assertEqual(ticket.path, post_data['path'])


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsAccessTicketUpdateView(
    SampleSheetTaskflowMixin, SampleSheetIOMixin, TestTaskflowBase
):
    """Tests for the irods access ticket list view"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        self.irods_session = self.irods_backend.get_session()

        # Create iRODS track hub collections
        assay_path = self.irods_backend.get_path(self.assay)
        self.track_hub1 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track1'
        )
        self.track_hub2 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track2'
        )

    def test_render(self):
        """Test render the irods access ticket update form"""

        with self.login(self.user):
            self.assertEqual(IrodsAccessTicket.objects.count(), 0)

            post_data = {
                'path': self.track_hub1,
                'date_expires': (
                    timezone.localtime() + timedelta(days=1)
                ).strftime('%Y-%m-%d'),
                'label': 'TestTicket',
            }

            self.client.post(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsAccessTicket.objects.count(), 1)
            ticket = IrodsAccessTicket.objects.first()

            response = self.client.get(
                reverse(
                    'samplesheets:irods_ticket_update',
                    kwargs={'irodsaccessticket': str(ticket.sodar_uuid)},
                )
            )

            self.assertEqual(
                response.context['form'].initial['date_expires'],
                ticket.date_expires,
            )
            self.assertEqual(
                response.context['form'].initial['label'], ticket.label
            )
            self.assertEqual(
                response.context['form'].initial['path'], ticket.path
            )

    def test_post(self):
        """Test posting the irods access ticket update form"""

        with self.login(self.user):
            self.assertEqual(IrodsAccessTicket.objects.count(), 0)

            post_data = {
                'path': self.track_hub1,
                'date_expires': (
                    timezone.localtime() + timedelta(days=1)
                ).strftime('%Y-%m-%d'),
                'label': 'TestTicket',
            }

            self.client.post(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsAccessTicket.objects.count(), 1)

            ticket = IrodsAccessTicket.objects.first()

            update_data = {
                **post_data,
                'label': 'TestTicketAltered',
                'date_expires': '',
            }

            response = self.client.post(
                reverse(
                    'samplesheets:irods_ticket_update',
                    kwargs={'irodsaccessticket': str(ticket.sodar_uuid)},
                ),
                update_data,
            )

            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

            self.assertEqual(IrodsAccessTicket.objects.count(), 1)

            ticket = IrodsAccessTicket.objects.first()

            self.assertEqual(
                str(list(get_messages(response.wsgi_request))[1]),
                'iRODS access ticket "%s" updated.' % ticket.get_display_name(),
            )

            self.assertIsNone(ticket.get_date_expires())
            self.assertEqual(ticket.label, update_data['label'])
            self.assertEqual(ticket.path, update_data['path'])


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsAccessTicketDeleteView(
    SampleSheetTaskflowMixin, SampleSheetIOMixin, TestTaskflowBase
):
    """Tests for the irods access ticket delete view"""

    def setUp(self):
        super().setUp()

        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        self.irods_session = self.irods_backend.get_session()

        # Create iRODS track hub collections
        assay_path = self.irods_backend.get_path(self.assay)
        self.track_hub1 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track1'
        )
        self.track_hub2 = self._make_track_hub_coll(
            self.irods_session, assay_path, 'track2'
        )

    def test_delete(self):
        """Test render the irods access ticket update form"""

        with self.login(self.user):
            self.assertEqual(IrodsAccessTicket.objects.count(), 0)

            post_data = {
                'path': self.track_hub1,
                'date_expires': (
                    timezone.localtime() + timedelta(days=1)
                ).strftime('%Y-%m-%d'),
                'label': 'TestTicket',
            }

            self.client.post(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.client.post(
                reverse(
                    'samplesheets:irods_ticket_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                {**post_data, 'path': self.track_hub2},
            )

            self.assertEqual(IrodsAccessTicket.objects.count(), 2)

            ticket = IrodsAccessTicket.objects.first()

            response = self.client.delete(
                reverse(
                    'samplesheets:irods_ticket_delete',
                    kwargs={'irodsaccessticket': str(ticket.sodar_uuid)},
                ),
            )

            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

            self.assertEqual(IrodsAccessTicket.objects.count(), 1)

            self.assertEqual(
                str(list(get_messages(response.wsgi_request))[2]),
                'iRODS access ticket "%s" deleted.' % ticket.get_display_name(),
            )


class TestIrodsRequestViewsBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TestTaskflowBase,
):
    """Base test class for iRODS delete requests"""

    def setUp(self):
        super().setUp()

        self.irods_backend = get_backend_api('omics_irods')
        self.irods_session = self.irods_backend.get_session()

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

        # Create iRODS collections
        self._make_irods_colls(self.investigation)

        self.assay_path = self.irods_backend.get_path(self.assay)

        self.path = os.path.join(self.assay_path, TEST_FILE_NAME)
        self.path_md5 = os.path.join(self.assay_path, f'{TEST_FILE_NAME}.md5')

        # Create objects
        self.file_obj = self.irods_session.data_objects.create(self.path)
        self.md5_obj = self.irods_session.data_objects.create(self.path_md5)

        # Init users (owner = user_cat, superuser = user)
        self.user_delegate = self.make_user('user_delegate')
        self.user_contrib = self.make_user('user_contrib')
        self.user_contrib2 = self.make_user('user_contrib2')
        self.user_guest = self.make_user('user_guest')

        self._make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self._make_assignment_taskflow(
            self.project, self.user_contrib, self.role_contributor
        )
        self._make_assignment_taskflow(
            self.project, self.user_contrib2, self.role_contributor
        )
        self._make_assignment_taskflow(
            self.project, self.user_guest, self.role_guest
        )

    def tearDown(self):
        self.irods_session.collections.get('/omicsZone/projects').remove(
            force=True
        )


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsRequestCreateView(TestIrodsRequestViewsBase):
    """Test IrodsRequestCreateView"""

    def test_post_create(self):
        """Test creating a delete request"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.path, 'description': 'bla'}

        with self.login(self.user):
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
        # TODO: Test app alert status

    def test_post_create_trailing_slash(self):
        """Test creating a delete request with trailing slash in path"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.path + '/', 'description': 'bla'}

        with self.login(self.user):
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
        # TODO: Test app alert status

    def test_create_invalid_form_data(self):
        """Test creating a delete request with invalid form data"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': '/doesnt/exist', 'description': 'bla'}

        with self.login(self.user):
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

    def test_create_invalid_path_is_assay_collection(self):
        """Test creating a delete request with invalid form data"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.assay_path, 'description': 'bla'}

        with self.login(self.user):
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
        # TODO: Test app alert status


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsRequestUpdateView(TestIrodsRequestViewsBase):
    """Test IrodsRequestUpdateView"""

    def test_post_update(self):
        """Test POST request for updating a delete request"""
        post_data = {'path': self.path, 'description': 'Description'}
        update_data = {'path': self.path, 'description': 'Updated'}

        with self.login(self.user):
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
            f'iRODS data request "{obj.get_display_name()}" updated.',
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.path)
        self.assertEqual(obj.description, 'Updated')

    def test_post_update_invalid_form_data(self):
        """Test updating a delete request with invalid form data"""
        with self.login(self.user):
            post_data = {'path': self.path, 'description': 'Description'}
            update_data = {'path': '/doesnt/exist', 'description': 'Updated'}

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


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsRequestDeleteView(TestIrodsRequestViewsBase):
    """Test IrodsRequestUpdateView"""

    def test_get_contributor(self):
        """Test GET request for deleting a delete request"""
        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)

            obj = IrodsDataRequest.objects.first()

            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertEqual(response.status_code, 200)

    def test_post_contributor(self):
        """Test POST request for deleting a delete request"""
        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)

            obj = IrodsDataRequest.objects.first()

            response = self.client.delete(
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


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsRequestAcceptView(TestIrodsRequestViewsBase):
    """Test IrodsRequestAcceptView"""

    def test_accept_request_doesnt_exist(self):
        """Test POST request for accepting a delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_cat):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={
                        'irodsdatarequest': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
                    },
                ),
                {'confirm': True},
            )

            self.assertRedirects(response, reverse('home'))

    def test_accept(self):
        """Test POST request for accepting a delete request"""
        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)

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
                f'iRODS data request "{obj.get_display_name()}" accepted.',
            )

            obj = IrodsDataRequest.objects.first()
            self.assertEqual(obj.status, 'ACCEPTED')

    def test_accept_invalid_form_data(self):
        """Test POST request for accepting a delete request with invalid form data"""
        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)

            obj = IrodsDataRequest.objects.first()

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': False},
            )

            self.assertEqual(
                response.context['form'].errors['confirm'][0],
                'This field is required.',
            )

    def test_accept_owner(self):
        """Test POST request for accepting a delete request as owner"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)

        obj = IrodsDataRequest.objects.first()

        with self.login(self.user_cat):
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
                f'iRODS data request "{obj.get_display_name()}" accepted.',
            )

            obj = IrodsDataRequest.objects.first()
            self.assertEqual(obj.status, 'ACCEPTED')

    def test_accept_delegate(self):
        """Test POST request for accepting a delete request as delegate"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)

        obj = IrodsDataRequest.objects.first()

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
                f'iRODS data request "{obj.get_display_name()}" accepted.',
            )

            obj = IrodsDataRequest.objects.first()
            self.assertEqual(obj.status, 'ACCEPTED')

    def test_accept_contributor(self):
        """Test POST request for accepting a delete request as contributor"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

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
                    'samplesheets:irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )

            self.assertRedirects(response, reverse('home'))
            self.assertEqual(IrodsDataRequest.objects.count(), 1)


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsRequestRejectView(TestIrodsRequestViewsBase):
    """Test IrodsRequestRejectView"""

    def test_reject_request_doesnt_exist(self):
        """Test GET request for rejecting a delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_cat):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_request_reject',
                    kwargs={
                        'irodsdatarequest': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
                    },
                ),
            )

            self.assertRedirects(response, reverse('home'))

    def test_reject_admin(self):
        """Test GET request for rejecting a delete request"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
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
                f'iRODS data request "{obj.get_display_name()}" rejected.',
            )
            obj.refresh_from_db()
            self.assertEqual(obj.status, 'REJECTED')

    def test_reject_owner(self):
        """Test GET request for rejecting a delete request as owner"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)

        obj = IrodsDataRequest.objects.first()

        with self.login(self.user_cat):
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
                f'iRODS data request "{obj.get_display_name()}" rejected.',
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj.refresh_from_db()
            self.assertEqual(obj.status, 'REJECTED')

    def test_reject_delegate(self):
        """Test GET request for rejecting a delete request as delegate"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
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
                f'iRODS data request "{obj.get_display_name()}" rejected.',
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj.refresh_from_db()
            self.assertEqual(obj.status, 'REJECTED')

    def test_reject_contributor(self):
        """Test GET request for rejecting a delete request as contributor"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
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
                'User not authorized for requested action',
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsRequestListView(TestIrodsRequestViewsBase):
    """Test IrodsRequestListView"""

    def test_list(self):
        """Test GET request for listing delete requests"""

        with self.login(self.user):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
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

        with self.login(self.user):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
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

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
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

    def test_list_as_contributor2_by_contributor(
        self,
    ):
        """Test GET request for listing delete requests"""

        with self.login(self.user_contrib):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            post_data = {'path': self.path, 'description': 'bla'}

            self.client.post(
                reverse(
                    'samplesheets:irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
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

        with self.login(self.user):
            self.assertEqual(IrodsDataRequest.objects.count(), 0)

            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context['object_list']), 0)


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestSampleSheetSyncView(TestSheetSyncBase):
    """Tests for SampleSheetSyncView"""

    def test_get_sync_successful(self):
        """Test sync sheets successfully"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )

        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            'Sample sheet sync successful',
        )

        # Check if investigation was created. Extensive test of task in
        # test_tasks.py
        self.assertEqual(self.project_target.investigations.count(), 1)

    def test_get_sync_disabled(self):
        """Test sync sheets disabled"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_enable',
            False,
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )

        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            'Sample sheet sync disabled',
        )

        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_sync_wrong_token(self):
        """Test sync sheets wrong token"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_token',
            'WRONGTOKEN',
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )

        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            'Sample sheet sync failed: Source API responded with status code 401',
        )

        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_sync_token_missing(self):
        """Test sync sheets token missing"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_token',
            '',
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )

        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            'Sample sheet sync: Token not set',
        )

        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_sync_url_missing(self):
        """Test sync sheets URL missing"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_url',
            '',
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )

        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            'Sample sheet sync: URL not set',
        )

        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_sync_wrong_url(self):
        """Test sync sheets wrong URL"""
        url = 'https://alsdjfasdkjfasdgfli.com'

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_url',
            url,
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )

        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            'Sample sheet sync failed: Unable to connect to URL: {}'.format(
                url
            ),
        )

        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_sync_url_to_nonexisting_sheet(self):
        """Test sync sheets nonexisting URL"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_url',
            self.live_server_url
            + reverse(
                'samplesheets:api_export_json',
                kwargs={'project': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'},
            ),
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )

        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            'Sample sheet sync failed: Source API responded with status code '
            '403',
        )

        self.assertEqual(self.project_target.investigations.count(), 0)
