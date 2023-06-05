"""
Tests for REST API views in the samplesheets app with SODAR Taskflow enabled
"""

import json
import os

from irods.keywords import REG_CHKSUM_KW

from django.urls import reverse
from django.test import override_settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Taskflowbackend dependency
from taskflowbackend.tests.base import (
    TaskflowAPIViewTestBase,
)

# Samplesheets dependencies
from samplesheets.models import IrodsDataRequest
from samplesheets.views import (
    IRODS_REQ_CREATE_ALERT as CREATE_ALERT,
    IRODS_REQ_ACCEPT_ALERT as ACCEPT_ALERT,
    IRODS_REQ_REJECT_ALERT as REJECT_ALERT,
)
from samplesheets.views_api import IRODS_QUERY_ERROR_MSG

from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
    TEST_FILE_NAME,
    INVALID_REDIS_URL,
)

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


class TestIrodsRequestAPIViewBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIViewTestBase
):
    """Base samplesheets API view test class for iRODS delete requests"""

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
        # Create objects
        self.file_obj = self.irods.data_objects.create(self.path)
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

        # Get appalerts API and model
        self.app_alerts = get_backend_api('appalerts_backend')
        self.app_alert_model = self.app_alerts.get_model()

        # Set default POST data
        self.post_data = {'path': self.path, 'description': 'bla'}

    def tearDown(self):
        self.irods.collections.get('/sodarZone/projects').remove(force=True)
        super().tearDown()


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


class TestIrodsRequestCreateAPIView(TestIrodsRequestAPIViewBase):
    """Tests for IrodsRequestCreateAPIView"""

    def test_create(self):
        """Test post() in IrodsRequestCreateAPIView"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user_contrib):
            response = self.client.post(url, self.post_data)
            self.assertEqual(response.status_code, 200)

        obj = IrodsDataRequest.objects.first()
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.path)
        self.assertEqual(obj.description, 'bla')
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_contrib, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_guest, 0)

    def test_create_trailing_slash(self):
        """Test creating a request with a trailing slash in path"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.path + '/', 'description': 'bla'}
        url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )

        with self.login(self.user_contrib):
            response = self.client.post(url, post_data)
            self.assertEqual(response.status_code, 200)

        obj = IrodsDataRequest.objects.first()
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(obj.path, self.path + '/')
        self.assertEqual(obj.description, 'bla')

    def test_create_invalid_data(self):
        """Test creating a request with invalid data"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        post_data = {'path': '/doesnt/exist', 'description': 'bla'}
        url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user_contrib):
            response = self.client.post(url, post_data)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

    def test_create_invalid_path_assay_collection(self):
        """Test creating a request with assay path (should fail)"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        post_data = {'path': self.assay_path, 'description': 'bla'}
        url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user_contrib):
            response = self.client.post(url, post_data)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

    def test_create_multiple(self):
        """Test creating multiple requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2')
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user_contrib):
            response = self.client.post(url, self.post_data)
            self.assertEqual(response.status_code, 200)
            self.post_data['path'] = path2
            response = self.client.post(url, self.post_data)
            self.assertEqual(response.status_code, 200)

        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


class TestIrodsRequestUpdateAPIView(TestIrodsRequestAPIViewBase):
    """Tests for IrodsRequestUpdateAPIView"""

    def test_update(self):
        """Test updating a request"""
        update_data = {'path': self.path, 'description': 'Updated'}

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()
            response = self.client.put(
                reverse(
                    'samplesheets:api_irods_request_update',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                update_data,
            )
            self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self.assertEqual(obj.description, 'Updated')
        self.assertEqual(obj.path, self.path)

    def test_update_invalid_data(self):
        """Test updating a request with invalid data"""
        update_data = {'path': '/doesnt/exist', 'description': 'Updated'}

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()
            response = self.client.put(
                reverse(
                    'samplesheets:api_irods_request_update',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                update_data,
            )
            self.assertEqual(response.status_code, 400)

        obj.refresh_from_db()
        self.assertEqual(obj.description, 'bla')
        self.assertEqual(obj.path, self.path)


class TestIrodsRequestDeleteAPIView(TestIrodsRequestAPIViewBase):
    """Tests for IrodsRequestDeleteAPIView"""

    def test_delete(self):
        """Test deleting a request"""
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
            obj = IrodsDataRequest.objects.first()

            response = self.client.delete(
                reverse(
                    'samplesheets:api_irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

    def test_delete_one_of_multiple(self):
        """Test deleting one of multiple requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2')
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.post_data['path'] = path2
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.assertEqual(IrodsDataRequest.objects.count(), 2)
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
            obj = IrodsDataRequest.objects.first()
            # NOTE: Still should only have one request for both
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

            response = self.client.delete(
                reverse(
                    'samplesheets:api_irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


class TestIrodsRequestAcceptAPIView(TestIrodsRequestAPIViewBase):
    """Tests for IrodsRequestAcceptAPIView"""

    def test_accept(self):
        """Test accepting a request"""
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
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
                    'samplesheets:api_irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACCEPTED')
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_irods_obj(self.path, False)

    def test_accept_no_request(self):
        """Test accepting a non-existing request"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:api_irods_request_accept',
                    kwargs={'irodsdatarequest': self.category.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertEqual(response.status_code, 404)

    def test_accept_invalid_data(self):
        """Test accepting a request with invalid data"""
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
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
                    'samplesheets:api_irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': False},
            )
            self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self.assert_irods_obj(self.path, False)

    def test_accept_delegate(self):
        """Test accepting a request as delegate"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
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
                    'samplesheets:api_irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACCEPTED')
        self.assert_irods_obj(self.path, False)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 1)

    def test_accept_contributor(self):
        """Test accepting a request as contributor"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

        with self.login(self.user_contrib):
            response = self.client.post(
                reverse(
                    'samplesheets:api_irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertEqual(response.status_code, 403)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACTIVE')
        self.assert_irods_obj(self.path, True)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)

    def test_accept_one_of_multiple(self):
        """Test accepting one of multiple requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2')
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
            self.post_data['path'] = path2
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:api_irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACCEPTED')
        self.assertEqual(
            IrodsDataRequest.objects.filter(status='ACTIVE').count(), 1
        )
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_accept_lock_failure(self):
        """Test accepting a request with project lock failure"""
        self.assert_irods_obj(self.path)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
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
                    'samplesheets:api_irods_request_accept',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
                {'confirm': True},
            )
            self.assertEqual(response.status_code, 500)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'FAILED')
        self.assert_irods_obj(self.path, True)
        self._assert_alert_count(ACCEPT_ALERT, self.user, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(ACCEPT_ALERT, self.user_contrib, 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self.assert_irods_obj(self.path, True)


class TestIrodsRequestRejectAPIView(TestIrodsRequestAPIViewBase):
    """Tests for IrodsRequestRejectAPIView"""

    def test_reject_admin(self):
        """Test rejecting a request as admin"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'REJECTED')
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_delegate(self):
        """Test rejecting a request as delegate"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        obj = IrodsDataRequest.objects.first()

        with self.login(self.user_delegate):
            response = self.client.get(
                reverse(
                    'samplesheets:api_irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertEqual(response.status_code, 200)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'REJECTED')
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_contributor(self):
        """Test rejecting a request as contributor"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            obj = IrodsDataRequest.objects.first()

            response = self.client.get(
                reverse(
                    'samplesheets:api_irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertEqual(response.status_code, 403)

        obj.refresh_from_db()
        self.assertEqual(obj.status, 'ACTIVE')
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 0)

    def test_reject_one_of_multiple(self):
        """Test rejecting one of multipe requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2')
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME + '_2.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.post_data['path'] = path2
            self.client.post(
                reverse(
                    'samplesheets:api_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 2)
        obj = IrodsDataRequest.objects.first()
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_irods_request_reject',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                ),
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(
            IrodsDataRequest.objects.filter(status='ACTIVE').count(), 1
        )
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'REJECTED')
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        self._assert_alert_count(REJECT_ALERT, self.user, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_delegate, 0)
        self._assert_alert_count(REJECT_ALERT, self.user_contrib, 1)

    def test_reject_no_request(self):
        """Test rejecting request, that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_irods_request_reject',
                    kwargs={'irodsdatarequest': self.category.sodar_uuid},
                ),
            )
            self.assertEqual(response.status_code, 404)


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
            '{}: {}'.format(
                IRODS_QUERY_ERROR_MSG, 'iRODS collection not found'
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
