import os
from unittest.case import skipIf

from django.conf import settings
from django.urls import reverse

from samplesheets.models import IrodsDataRequest
from samplesheets.tests.test_views import (
    IRODS_BACKEND_ENABLED,
    IRODS_BACKEND_SKIP_MSG,
)
from samplesheets.tests.test_views_taskflow import (
    TestIrodsRequestViewsBase,
    TEST_FILE_NAME2,
)


# Local constants
IRODS_NON_PROJECT_PATH = (
    '/' + settings.IRODS_ZONE + '/home/' + settings.IRODS_USER
)
IRODS_FAIL_COLL = 'xeiJ1Vie'


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsRequestCreateAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestCreateAjaxView"""

    def test_create_request(self):
        """Test creating a delete request on a data object"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assertEqual(self._get_create_alert_count(self.user), 0)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], 'ACTIVE')
        self.assertEqual(self._get_create_alert_count(self.user), 1)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 1)

    def test_create_exists_same_user(self):
        """Test creating delete request if request for same user exists"""

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(self._get_create_alert_count(self.user), 1)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 1)

        with self.login(self.user_contrib):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )
        self.assertEqual(self._get_create_alert_count(self.user), 1)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 1)

    def test_create_exists_as_admin_by_contributor(self):
        """Test creating request as admin if request from contributor exists"""
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_create_exists_as_contributor_by_contributor2(self):
        """Test creating request as contributor if request by contributor2 exists"""
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib2):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_create_multiple(self):
        """Test creating multiple delete requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
        self.irods_session.data_objects.create(path2)
        self.irods_session.data_objects.create(path2_md5)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assertEqual(self._get_create_alert_count(self.user), 0)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 0)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': path2},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self.assertEqual(self._get_create_alert_count(self.user), 1)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 1)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsRequestDeleteAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestDeleteAjaxView"""

    def test_delete_request(self):
        """Test GET request for deleting an existing delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(self._get_create_alert_count(self.user), 1)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 1)

        # Delete request
        with self.login(self.user_contrib):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)
        self.assertEqual(self._get_create_alert_count(self.user), 0)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 0)

    def test_delete_request_as_admin_by_contributor(self):
        """Test deleting an existing delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)

    def test_delete_request_as_contributor_by_contributor2(self):
        """Test GET request for deleting an existing delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(self.user_contrib2):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Assert response
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data['detail'], 'User not allowed to delete request'
        )

    def test_delete_request_doesnt_exist(self):
        """Test deleting a delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        # Delete request
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        # Assert response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['detail'], 'Request not found')

    def test_delete_one_of_multiple(self):
        """Test deleting one of multiple requests"""
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
        self.irods_session.data_objects.create(path2)
        self.irods_session.data_objects.create(path2_md5)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assertEqual(self._get_create_alert_count(self.user), 0)
        self.assertEqual(self._get_create_alert_count(self.user_delegate), 0)

        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': path2},
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 2)
            self.assertEqual(self._get_create_alert_count(self.user), 1)
            self.assertEqual(
                self._get_create_alert_count(self.user_delegate), 1
            )

            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self.assertEqual(self._get_create_alert_count(self.user), 1)
            self.assertEqual(
                self._get_create_alert_count(self.user_delegate), 1
            )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsObjectListAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsObjectListAjaxView"""

    def test_get_coll_obj_with_delete_request(self):
        """Test listing collection with data object with delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data_objects'][0]['name'], 'test1')
        self.assertEqual(response.json()['data_objects'][0]['path'], self.path)
        self.assertEqual(
            response.json()['data_objects'][0]['irods_request_status'],
            'ACTIVE',
        )

    def test_get_empty_coll(self):
        """Test GET request for listing an empty collection in iRODS"""

        self.irods_session.data_objects.get(self.path).unlink(force=True)
        self.irods_session.data_objects.get(self.path_md5).unlink(force=True)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['data_objects']), 0)

    def test_get_coll_obj(self):
        """Test GET request for listing a collection with a data object"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['data_objects']), 1)

            list_obj = response.data['data_objects'][0]
            self.assertNotIn('md5_file', list_obj)
            self.assertEqual(self.file_obj.name, list_obj['name'])
            self.assertEqual(self.file_obj.path, list_obj['path'])
            self.assertEqual(self.file_obj.size, 0)

    def test_get_coll_not_found(self):
        """Test GET request for listing a collection which doesn't exist"""
        fail_path = self.assay_path + '/' + IRODS_FAIL_COLL
        self.assertEqual(
            self.irods_session.collections.exists(fail_path), False
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': fail_path},
            )

            self.assertEqual(response.status_code, 404)

    def test_get_coll_not_in_project(self):
        """Test GET request for listing a collection not belonging to project"""
        self.assertEqual(
            self.irods_session.collections.exists(IRODS_NON_PROJECT_PATH), True
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': IRODS_NON_PROJECT_PATH},
            )

            self.assertEqual(response.status_code, 400)

    def test_get_no_access(self):
        """Test GET request for listing with no acces for the iRODS folder"""
        new_user = self.make_user('new_user')
        self._make_assignment(
            self.project, new_user, self.role_contributor
        )  # No taskflow

        with self.login(new_user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )

            self.assertEqual(response.status_code, 403)
