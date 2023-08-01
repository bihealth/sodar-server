"""Tests for models in the samplesheets app"""

import os

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from samplesheets.models import (
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)

from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import (
    IrodsDataRequestMixin,
    IRODS_REQUEST_DESC,
)
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TEST_FILE_NAME = 'test.txt'
TEST_COLL_NAME = 'coll'


class TestIrodsDataRequest(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    IrodsDataRequestMixin,
    TaskflowViewTestBase,
):
    """Tests for the IrodsAccessTicket model"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner_cat,
        )

        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.obj_path = os.path.join(self.assay_path, TEST_FILE_NAME)
        self.coll_path = os.path.join(self.assay_path, TEST_COLL_NAME)
        # Create objects
        self.file_obj = self.irods.data_objects.create(self.obj_path)
        self.coll = self.irods.collections.create(self.coll_path)

        # Create request
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            path=self.obj_path,
            description=IRODS_REQUEST_DESC,
            user=self.user_owner_cat,
        )

    def test_is_data_object(self):
        """Test is_data_object()"""
        self.assertTrue(self.request.is_data_object())
        self.request.path = self.coll_path
        self.request.save()
        self.assertFalse(self.request.is_data_object())

    def test_is_collection(self):
        """Test is_collection()"""
        self.assertFalse(self.request.is_collection())
        self.request.path = self.coll_path
        self.request.save()
        self.assertTrue(self.request.is_collection())
