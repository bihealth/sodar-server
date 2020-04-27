"""
Tests for REST API views in the samplesheets app with SODAR Taskflow enabled
"""

from unittest.case import skipIf

from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_api_taskflow import TestTaskflowAPIBase

from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.tests.test_views import (
    IRODS_BACKEND_ENABLED,
    IRODS_BACKEND_SKIP_MSG,
)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']


# Local constants
SHEET_TSV_DIR = SHEET_DIR + 'i_small2/'
SHEET_PATH = SHEET_DIR + 'i_small2.zip'
SHEET_PATH_EDITED = SHEET_DIR + 'i_small2_edited.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2_alt.zip'


class TestSampleSheetAPITaskflowBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TestTaskflowAPIBase
):
    """Base samplesheets API view test class with Taskflow enabled"""

    def setUp(self):
        super().setUp()

        # Get iRODS backend for session access
        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        # self.irods_session = self.irods_backend.get_session()

        # Init project
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


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsCollsCreateAPIView(TestSampleSheetAPITaskflowBase):
    """Tests for IrodsCollsCreateAPIView"""

    def test_post(self):
        """Test post() in IrodsCollsCreateAPIView"""

        # Assert preconditions
        self.assertEqual(self.investigation.irods_status, False)

        url = reverse(
            'samplesheets:api_irods_colls_create',
            kwargs={'project': self.project.sodar_uuid},
        )

        response = self.request_knox(url, method='POST', data=self.request_data)

        self.assertEqual(response.status_code, 200)
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)

    def test_post_created(self):
        """Test post() with already created collections (should fail)"""

        # Set up iRODS collections
        self._make_irods_colls(self.investigation)

        # Assert preconditions
        self.assertEqual(self.investigation.irods_status, True)

        url = reverse(
            'samplesheets:api_irods_colls_create',
            kwargs={'project': self.project.sodar_uuid},
        )

        response = self.request_knox(url, method='POST', data=self.request_data)

        self.assertEqual(response.status_code, 400)
