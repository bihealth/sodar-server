"""Tests for models in the samplesheets app"""

import os

from django.forms.models import model_to_dict
from django.utils.timezone import localtime

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowbackendTestBase

from samplesheets.models import (
    IRODS_DATA_REQUEST_STATUS_CHOICES,
    IrodsDataRequest,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TEST_FILE_NAME = 'test1'
TEST_COLL_NAME = 'coll1'


class TestIrodsDataRequestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Base test class for iRODS delete requests"""

    def setUp(self):
        super().setUp()

        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session()

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

        # Create iRODS collections
        self.make_irods_colls(self.investigation)

        self.assay_path = self.irods_backend.get_path(self.assay)
        self.path = os.path.join(self.assay_path, TEST_FILE_NAME)
        self.path_coll = os.path.join(self.assay_path, TEST_COLL_NAME)
        self.path_md5 = os.path.join(self.assay_path, f'{TEST_FILE_NAME}.md5')

        # Create objects
        self.file_obj = self.irods.data_objects.create(self.path)
        self.coll = self.irods.collections.create(self.path_coll)
        self.md5_obj = self.irods.data_objects.create(self.path_md5)

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

        self.action = 'delete'
        self.description = 'description'
        self.status = IRODS_DATA_REQUEST_STATUS_CHOICES[0][0]
        self.irods_data_request = self._make_irods_data_request(
            project=self.project,
            action=self.action,
            status=self.status,
            path=self.path,
            description=self.description,
            user=self.user_cat,
        )

    def tearDown(self):
        self.irods.collections.get('/sodarZone/projects').remove(force=True)

    @classmethod
    def _make_irods_data_request(
        cls,
        project,
        action,
        path,
        status,
        target_path='',
        status_info='',
        description='',
        user=None,
    ):
        """Create an iRODS access ticket object in the database"""
        values = {
            'project': project,
            'action': action,
            'path': path,
            'status': status,
            'target_path': target_path,
            'status_info': status_info,
            'user': user,
            'description': description,
        }
        obj = IrodsDataRequest(**values)
        obj.save()
        return obj


class TestIrodsDataRequest(TestIrodsDataRequestBase):
    """Tests for the IrodsAccessTicket model"""

    def test_initialization(self):
        """Test IrodsDataTicket initialization"""
        expected = {
            'id': self.irods_data_request.pk,
            'project': self.project.pk,
            'path': self.path,
            'user': self.user_cat.pk,
            'action': self.action,
            'status': self.status,
            'target_path': '',
            'status_info': '',
            'description': self.description,
            'sodar_uuid': self.irods_data_request.sodar_uuid,
        }
        self.assertDictEqual(model_to_dict(self.irods_data_request), expected)

    def test__str__(self):
        self.assertEqual(
            str(self.irods_data_request),
            '{}: {} {}'.format(
                self.project.title,
                self.action,
                self.irods_data_request.get_short_path(),
            ),
        )

    def test__repr__(self):
        self.assertEqual(
            repr(self.irods_data_request),
            'IrodsDataRequest(\'{}\', \'{}\', \'{}\', \'{}\', \'{}\')'.format(
                self.project.title,
                self.irods_data_request.get_assay_name(),
                self.action,
                self.path,
                self.user_cat.username,
            ),
        )

    def test_get_display_name(self):
        self.assertEqual(
            self.irods_data_request.get_display_name(),
            '{} {}'.format(
                self.action.capitalize(),
                self.irods_data_request.get_short_path(),
            ),
        )

    def test_get_date_created(self):
        self.assertEqual(
            self.irods_data_request.get_date_created(),
            localtime(self.irods_data_request.date_created).strftime(
                '%Y-%m-%d %H:%M'
            ),
        )

    def test_is_data_object_true(self):
        self.irods_data_request.path = self.path
        self.irods_data_request.save()
        self.assertTrue(self.irods_data_request.is_data_object())

    def test_is_data_object_false(self):
        self.irods_data_request.path = self.path_coll
        self.irods_data_request.save()
        self.assertFalse(self.irods_data_request.is_data_object())

    def test_is_collection_true(self):
        self.irods_data_request.path = self.path_coll
        self.irods_data_request.save()
        self.assertTrue(self.irods_data_request.is_collection())

    def test_is_collection_false(self):
        self.irods_data_request.path = self.path
        self.irods_data_request.save()
        self.assertFalse(self.irods_data_request.is_collection())

    def test_get_short_path(self):
        self.assertEqual(
            self.irods_data_request.get_short_path(),
            '{}/{}'.format(
                os.path.basename(self.assay_path), os.path.basename(self.path)
            ),
        )

    def test_get_assay(self):
        self.assertEqual(self.irods_data_request.get_assay(), self.assay)

    def test_get_assay_name(self):
        self.assertEqual(
            self.irods_data_request.get_assay_name(),
            self.assay.get_display_name(),
        )

    def test_get_assay_name_na(self):
        self.irods_data_request.path = '/different/path'
        self.irods_data_request.save()
        self.assertEqual(self.irods_data_request.get_assay_name(), 'N/A')
