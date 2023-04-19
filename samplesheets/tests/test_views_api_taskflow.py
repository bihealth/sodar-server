"""
Tests for REST API views in the samplesheets app with SODAR Taskflow enabled
"""

import json
import os

from irods.keywords import REG_CHKSUM_KW

from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Taskflowbackend dependency
from taskflowbackend.tests.base import (
    TaskflowAPIViewTestBase,
)

# Samplesheets dependencies
from samplesheets.views_api import IRODS_ERROR_MSG

from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_TSV_DIR = SHEET_DIR + 'i_small2/'
SHEET_PATH = SHEET_DIR + 'i_small2.zip'
SHEET_PATH_EDITED = SHEET_DIR + 'i_small2_edited.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2_alt.zip'
IRODS_FILE_PATH = os.path.dirname(__file__) + '/irods/test1.txt'
IRODS_FILE_NAME = 'test1.txt'
IRODS_FILE_MD5 = '0b26e313ed4a7ca6904b0e9369e5b957'


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


class TestInvestigationRetrieveAPIView(TestSampleSheetAPITaskflowBase):
    """Tests for InvestigationRetrieveAPIView"""

    def test_get(self):
        """Test get() in InvestigationRetrieveAPIView"""
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
        """Test post() in IrodsCollsCreateAPIView"""
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
        """Test post() with already created collections (should fail)"""
        # Set up iRODS collections
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.investigation.irods_status, True)
        url = reverse(
            'samplesheets:api_irods_colls_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url, method='POST')
        self.assertEqual(response.status_code, 400)


class TestSampleDataFileExistsAPIView(TestSampleSheetAPITaskflowBase):
    """Tests for SampleDataFileExistsAPIView"""

    def setUp(self):
        super().setUp()
        self.make_irods_colls(self.investigation)

    def test_get(self):
        """Test getting file existence info with no file uploaded"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': IRODS_FILE_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], False)

    def test_get_file(self):
        """Test getting file existence info with an uploaded file"""
        coll_path = self.irods_backend.get_sample_path(self.project) + '/'
        self.irods.data_objects.put(
            IRODS_FILE_PATH, coll_path, **{REG_CHKSUM_KW: ''}
        )
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': IRODS_FILE_MD5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], True)

    def test_get_file_sub_coll(self):
        """Test getting file existence info in a sub collection"""
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
        """Test getting file existence info with no checksum (should fail)"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': ''})
        self.assertEqual(response.status_code, 400)

    def test_get_invalid_checksum(self):
        """Test getting file existence info with an invalid checksum (should fail)"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': 'Notvalid MD5!'})
        self.assertEqual(response.status_code, 400)


class TestProjectIrodsFileListAPIView(
    TestSampleSheetAPITaskflowBase,
):
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
        """Test GET request in ProjectIrodsFileListAPIView without collection"""
        url = reverse(
            'samplesheets:api_file_list',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data['detail'],
            '{} {}'.format(
                IRODS_ERROR_MSG,
                'iRODS collection not found',
            ),
        )

    def test_get_empty_collection(self):
        """Test GET request in ProjectIrodsFileListAPIView"""
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
        """Test GET request in ProjectIrodsFileListAPIView"""
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
