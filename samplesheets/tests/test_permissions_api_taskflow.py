"""Tests for samplesheets REST API view permissions with taskflow"""

import os

from django.test import override_settings
from django.urls import reverse

from samplesheets.models import IrodsDataRequest

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
    TEST_FILE_NAME,
)

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowAPIPermissionTestBase


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small2.zip'


class TestIrodsRequestAPIViewBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIPermissionTestBase
):
    """Helper mixin for IrodsRequestAPIView tests"""

    def setUp(self):
        super().setUp()
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


class TestIrodsRequestCreateAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for IrodsRequestCreateAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        # Set up post data
        self.post_data = {'path': self.path + '/', 'description': 'bla'}

    def test_create(self):
        """Test post() in IrodsRequestCreateAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [self.user_guest, self.user_no_roles]

        self.assert_response_api(
            self.url, good_users, 200, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='POST', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_create_anon(self):
        """Test post() in IrodsRequestCreateAPIView with anonymous access"""
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self.post_data,
        )


class TestIrodsRequestUpdateAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for IrodsRequestUpdateAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.url_create = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        # Set up post data
        self.post_data = {'path': self.path + '/', 'description': 'bla'}
        self.update_data = {'path': self.path, 'description': 'Updated'}

    def test_update(self):
        """Test post() in IrodsRequestUpdateAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.user_contributor]

        with self.login(self.superuser):
            self.client.post(self.url_create, self.post_data)
            obj = IrodsDataRequest.objects.first()

        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url, good_users, 200, method='POST', data=self.update_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='POST', data=self.update_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_update_anon(self):
        """Test post() in IrodsRequestUpdateAPIView with anonymous access"""
        self.project.set_public()
        with self.login(self.superuser):
            self.client.post(self.url_create, self.post_data)
            obj = IrodsDataRequest.objects.first()

        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self.update_data,
        )


class TestIrodsRequestDeleteAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for IrodsRequestDeleteAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.url_create = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        # Set up post data
        self.post_data = {'path': self.path + '/', 'description': 'bla'}

    def test_delete(self):
        """Test delete() in IrodsRequestDeleteAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [self.user_guest, self.user_no_roles, self.user_contributor]

        for user in good_users:
            with self.login(self.superuser):
                self.client.post(self.url_create, self.post_data)
                obj = IrodsDataRequest.objects.first()
                self.assertIsNotNone(obj)

            self.url_delete = reverse(
                'samplesheets:api_irods_request_delete',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_delete, user, 200, method='DELETE'
            )

        for user in bad_users:
            with self.login(self.superuser):
                self.client.post(self.url_create, self.post_data)
                obj = IrodsDataRequest.objects.first()
                self.assertIsNotNone(obj)

            self.url_delete = reverse(
                'samplesheets:api_irods_request_delete',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )

            self.assert_response_api(
                self.url_delete, user, 403, method='DELETE'
            )

        # Test with anonymous access
        with self.login(self.superuser):
            self.client.post(self.url_create, self.post_data)
            obj = IrodsDataRequest.objects.first()
            self.assertIsNotNone(obj)

        self.url_delete = reverse(
            'samplesheets:api_irods_request_delete',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )

        self.assert_response_api(
            self.url_delete, self.anonymous, 401, method='DELETE'
        )


class TestIrodsRequestAcceptAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for TestIrodsRequestAcceptAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.url_create = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        # Set up post data
        self.post_data = {'path': self.path + '/', 'description': 'bla'}

    def test_accept(self):
        """Test post() in IrodsRequestAcceptAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [self.user_contributor, self.user_guest, self.user_no_roles]
        with self.login(self.superuser):
            self.client.post(self.url_create, self.post_data)
            obj = IrodsDataRequest.objects.first()
            self.assertIsNotNone(obj)

        self.url_accept = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url_accept,
            good_users,
            200,
            method='POST',
            data={'confirm': True},
        )
        self.assert_response_api(
            self.url_accept,
            bad_users,
            403,
            method='POST',
            data={'confirm': True},
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_accept_anon(self):
        """Test post() in IrodsRequestAcceptAPIView with anonymous access"""
        with self.login(self.superuser):
            self.client.post(self.url_create, self.post_data)
            obj = IrodsDataRequest.objects.first()
            self.assertIsNotNone(obj)

        self.url_accept = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url_accept,
            self.anonymous,
            401,
            method='POST',
            data={'confirm': True},
        )


class TestIrodsRequestRejectAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for TestIrodsRequestRejectAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.url_create = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        # Set up post data
        self.post_data = {'path': self.path + '/', 'description': 'bla'}

    def test_reject(self):
        """Test get() in IrodsRequestRejectAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [self.user_contributor, self.user_guest, self.user_no_roles]

        with self.login(self.superuser):
            self.client.post(self.url_create, self.post_data)
            obj = IrodsDataRequest.objects.first()
            self.assertIsNotNone(obj)

        self.url_reject = reverse(
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url_reject,
            good_users,
            200,
            method='GET',
        )
        self.assert_response_api(
            self.url_reject,
            bad_users,
            403,
            method='GET',
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_accept_anon(self):
        """Test get() in IrodsRequestRejectAPIView with anonymous access"""
        with self.login(self.superuser):
            self.client.post(self.url_create, self.post_data)
            obj = IrodsDataRequest.objects.first()
            self.assertIsNotNone(obj)

        self.url_reject = reverse(
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url_reject,
            self.anonymous,
            401,
            method='GET',
        )
