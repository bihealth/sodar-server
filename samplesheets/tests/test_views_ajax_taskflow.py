from unittest.case import skipIf

from django.conf import settings
from django.urls import reverse

from samplesheets.models import IrodsDataRequest
from samplesheets.tests.test_views import (
    IRODS_BACKEND_ENABLED,
    IRODS_BACKEND_SKIP_MSG,
)
from samplesheets.tests.test_views_taskflow import TestIrodsRequestViewsBase


# Local constants
IRODS_NON_PROJECT_PATH = (
    '/' + settings.IRODS_ZONE + '/home/' + settings.IRODS_USER
)
IRODS_FAIL_COLL = 'xeiJ1Vie'


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsRequestCreateAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestCreateAjaxView"""

    def test_create_request(self):
        """Test creating a delete request on an existing data object"""

        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], 'ACTIVE')

    def test_create_request_exists_same_user(self):
        """Test creating delete request on data object where a request already exists"""
        with self.login(self.user_contrib):
            self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_create_request_exists_as_admin_by_contributor(
        self,
    ):
        """Test creating delete request on data object where a request already exists"""
        with self.login(self.user_contrib):
            self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_create_request_exists_as_contributor_by_contributor2(
        self,
    ):
        """Test creating delete request on data object where a request already exists"""
        with self.login(self.user_contrib):
            self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib2):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsRequestDeleteAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestDeleteAjaxView"""

    def test_delete_request(self):
        """Test GET request for deleting an existing delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(self.user_contrib):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)

    def test_delete_request_as_admin_by_contributor(self):
        """Test GET request for deleting an existing delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)

    def test_delete_request_as_contributor_by_contributor2(
        self,
    ):
        """Test GET request for deleting an existing delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(self.user_contrib2):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Assert response
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data['detail'], 'User not allowed to delete request'
        )

    def test_delete_request_doesnt_exists(self):
        """Test GET request for deleting a delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        # Delete request
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        # Assert response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['detail'], 'Request not found')


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsObjectListAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsObjectListAjaxView"""

    def test_get_coll_obj_with_delete_request(self):
        """Test GET request for listing a collection in iRODS with a data object with a delete request"""
        # Create request
        with self.login(self.user_contrib):
            self.client.get(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.path
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                )
                + '?path='
                + self.assay_path
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
                )
                + '?path='
                + self.assay_path
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
                )
                + '?path='
                + self.assay_path
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
                )
                + '?path='
                + fail_path
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
                )
                + '?path='
                + IRODS_NON_PROJECT_PATH
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
                )
                + '?path='
                + self.assay_path
            )

            self.assertEqual(response.status_code, 403)
