"""Integration tests for views in the samplesheets Django app with taskflow"""

# NOTE: You must supply 'omics_url': self.live_server_url in taskflow requests!

from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse

# Projectroles dependency
from projectroles.models import OMICS_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_taskflow import TestTaskflowBase

from unittest import skipIf

from ..models import Investigation
from ..utils import get_sample_dirs
from .test_io import SampleSheetIOMixin, SHEET_DIR


User = auth.get_user_model()


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TASKFLOW_ENABLED = True if \
    'taskflow' in settings.ENABLED_BACKEND_PLUGINS else False
TASKFLOW_SKIP_MSG = 'Taskflow not enabled in settings'


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
            'project_uuid': investigation.project.omics_uuid,
            'flow_name': 'sheet_dirs_create',
            'flow_data': {'dirs': get_sample_dirs(investigation)},
            'request': request}

        if not request:
            values['omics_url'] = self.live_server_url

        self.taskflow.submit(**values)

        investigation.refresh_from_db()
        self.assertEqual(investigation.irods_status, True)


class TestIrodsDirView(
        TestTaskflowBase, SampleSheetIOMixin):
    """Tests for iRODS directory structure creation view with taskflow"""

    def setUp(self):
        super(TestIrodsDirView, self).setUp()

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

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_create_dirs(self):
        """Test directory structure creation with taskflow"""

        # Assert precondition
        self.assertEqual(self.investigation.irods_status, False)

        # Issue POST request
        values = {
            'omics_url': self.live_server_url}  # HACK: Override callback URL

        with self.login(self.user):
            response = self.client.post(reverse(
                    'samplesheets:dirs',
                    kwargs={'project': self.project.omics_uuid}),
                values)

        # Assert sample sheet dir structure state after creation
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.omics_uuid}))


class TestSampleSheetDeleteView(
        TestTaskflowBase, SampleSheetIOMixin):
    """Tests for sample sheet deletion with taskflow"""

    def setUp(self):
        super(TestSampleSheetDeleteView, self).setUp()

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

    @skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
    def test_delete(self):
        """Test sample sheet deleting with taskflow"""

        # Assert precondition
        self.assertIsNotNone(self.investigation)

        # Issue POST request
        values = {
            'omics_url': self.live_server_url}  # HACK: Override callback URL

        with self.login(self.user):
            response = self.client.post(reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.omics_uuid}),
                values)

        # Assert sample sheet dir structure state after creation
        with self.assertRaises(Investigation.DoesNotExist):
            Investigation.objects.get(
                project__omics_uuid=self.project.omics_uuid)

        # Assert redirect
        with self.login(self.user):
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.omics_uuid}))
