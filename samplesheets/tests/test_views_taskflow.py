"""Integration tests for views in the samplesheets Django app with taskflow"""

# NOTE: You must supply 'sodar_url': self.live_server_url in taskflow requests!

from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_taskflow import TestTaskflowBase

from unittest import skipIf

from ..models import Investigation
from ..utils import get_sample_dirs
from .test_io import SampleSheetIOMixin, SHEET_DIR


User = auth.get_user_model()


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

    def _make_irods_dirs(self, investigation, request=None):
        """
        Create iRODS directory structure for investigation
        :param investigation: Investigation object
        :param request: HTTP request object (optional, default=None)
        :raise taskflow.FlowSubmitException if submit fails
        """
        self.assertEqual(investigation.irods_status, False)

        values = {
            'project_uuid': investigation.project.sodar_uuid,
            'flow_name': 'sheet_dirs_create',
            'flow_data': {'dirs': get_sample_dirs(investigation)},
            'request': request,
        }

        if not request:
            values['sodar_url'] = self.live_server_url

        self.taskflow.submit(**values)

        investigation.refresh_from_db()
        self.assertEqual(investigation.irods_status, True)


class TestIrodsDirView(SampleSheetIOMixin, TestTaskflowBase):
    """Tests for iRODS directory structure creation view with taskflow"""

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
    def test_create_dirs(self):
        """Test directory structure creation with taskflow"""

        # Assert precondition
        self.assertEqual(self.investigation.irods_status, False)

        # Issue POST request
        values = {
            'sodar_url': self.live_server_url
        }  # HACK: Override callback URL

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:dirs',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert sample sheet dir structure state after creation
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
            'sodar_url': self.live_server_url
        }  # HACK: Override callback URL

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
        self._make_irods_dirs(self.investigation)
        irods = self.irods_backend.get_session()
        assay_path = self.irods_backend.get_path(self.assay)
        file_path = assay_path + '/' + TEST_FILE_NAME
        irods.data_objects.create(file_path)

        # Assert precondition
        self.assertEqual(irods.data_objects.exists(file_path), True)

        # Issue POST request
        values = {
            'sodar_url': self.live_server_url
        }  # HACK: Override callback URL

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
        self._make_irods_dirs(self.investigation)
        irods = self.irods_backend.get_session()
        assay_path = self.irods_backend.get_path(self.assay)
        file_path = assay_path + '/' + TEST_FILE_NAME
        irods.data_objects.create(file_path)

        # Assert precondition
        self.assertEqual(irods.data_objects.exists(file_path), True)

        # Issue POST request
        values = {
            'sodar_url': self.live_server_url
        }  # HACK: Override callback URL

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
