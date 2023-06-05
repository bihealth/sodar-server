"""Tests for samplesheets REST API view permissions with taskflow"""

import os

from irods.keywords import REG_CHKSUM_KW

from django.test import override_settings
from django.urls import reverse

from samplesheets.models import IrodsDataRequest

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowAPIPermissionTestBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin
from samplesheets.tests.test_permissions import SHEET_PATH
from samplesheets.tests.test_views_api_taskflow import (
    IRODS_FILE_PATH,
    IRODS_FILE_MD5,
)
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
    TEST_FILE_NAME,
)


class TestSampleDataFileExistsAPIView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIPermissionTestBase
):
    """Tests for SampleDataFileExistsAPIView permissions"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Make iRODS collections
        self.make_irods_colls(self.investigation)
        # Upload file
        coll_path = self.irods_backend.get_sample_path(self.project) + '/'
        self.irods.data_objects.put(
            IRODS_FILE_PATH, coll_path, **{REG_CHKSUM_KW: ''}
        )
        self.post_data = {'checksum': IRODS_FILE_MD5}

    def test_get(self):
        """Test get() in SampleDataFileExistsAPIView"""
        url = reverse('samplesheets:api_file_exists')
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(url, good_users, 200, data=self.post_data)
        self.assert_response_api(url, self.anonymous, 401, data=self.post_data)

    def test_get_archive(self):
        """Test get() with archived project"""
        self.project.set_archive()
        url = reverse('samplesheets:api_file_exists')
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(url, good_users, 200, data=self.post_data)
        self.assert_response_api(url, self.anonymous, 401, data=self.post_data)


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

    def create_request(self):
        """Helper function to create a request"""
        url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        # Set up post data
        post_data = {'path': self.path + '/', 'description': 'bla'}
        with self.login(self.superuser):
            self.client.post(url, post_data)
            obj = IrodsDataRequest.objects.first()
        return obj


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
            self.user_delegate_cat,
            self.user_delegate,
            self.user_contributor_cat,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]

        self.assert_response_api(
            self.url, good_users, 200, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='POST', data=self.post_data
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

    def test_create_archived(self):
        """Test post() in IrodsRequestCreateAPIView with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]

        self.assert_response_api(
            self.url, good_users, 200, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='POST', data=self.post_data
        )


class TestIrodsRequestUpdateAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for IrodsRequestUpdateAPIView"""

    def setUp(self):
        super().setUp()
        self.update_data = {'path': self.path, 'description': 'Updated'}

    def test_update(self):
        """Test post() in IrodsRequestUpdateAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]

        obj = self.create_request()
        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url, good_users, 200, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_update_anon(self):
        """Test post() in IrodsRequestUpdateAPIView with anonymous access"""
        self.project.set_public()
        obj = self.create_request()
        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )

    def test_update_archived(self):
        """Test post() in IrodsRequestUpdateAPIView with archived project"""
        self.project.set_archive()
        obj = self.create_request()
        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]
        self.assert_response_api(
            self.url, good_users, 200, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )


class TestIrodsRequestDeleteAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for IrodsRequestDeleteAPIView"""

    def test_delete(self):
        """Test delete() in IrodsRequestDeleteAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]

        for user in good_users:
            obj = self.create_request()
            self.url_delete = reverse(
                'samplesheets:api_irods_request_delete',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_delete, user, 200, method='DELETE'
            )

        for user in bad_users:
            obj = self.create_request()
            self.url_delete = reverse(
                'samplesheets:api_irods_request_delete',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_delete, user, 403, method='DELETE'
            )

        # Test with anonymous access
        with self.login(self.superuser):
            obj = self.create_request()
            self.url_delete = reverse(
                'samplesheets:api_irods_request_delete',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_delete, self.anonymous, 401, method='DELETE'
            )


class TestIrodsRequestAcceptAPIView(TestIrodsRequestAPIViewBase):
    """Test permissions for TestIrodsRequestAcceptAPIView"""

    def test_accept(self):
        """Test post() in IrodsRequestAcceptAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]
        for user in good_users:
            obj = self.create_request()
            self.url_accept = reverse(
                'samplesheets:api_irods_request_accept',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_accept,
                user,
                200,
                method='POST',
                data={'confirm': True},
            )

        for user in bad_users:
            obj = self.create_request()
            self.url_accept = reverse(
                'samplesheets:api_irods_request_accept',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_accept,
                user,
                403,
                method='POST',
                data={'confirm': True},
            )

        obj = self.create_request()
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

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_accept_anon(self):
        """Test post() in IrodsRequestAcceptAPIView with anonymous access"""
        obj = self.create_request()
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

    def test_accept_archived(self):
        """Test post() in IrodsRequestUpdateAPIView with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]
        for user in good_users:
            obj = self.create_request()
            self.url_accept = reverse(
                'samplesheets:api_irods_request_accept',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_accept,
                user,
                200,
                method='POST',
                data={'confirm': True},
            )

        for user in bad_users:
            obj = self.create_request()
            self.url_accept = reverse(
                'samplesheets:api_irods_request_accept',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_accept,
                user,
                403,
                method='POST',
                data={'confirm': True},
            )

        obj = self.create_request()
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

    def test_reject(self):
        """Test get() in IrodsRequestRejectAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited owner
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]
        for user in good_users:
            obj = self.create_request()
            self.url_reject = reverse(
                'samplesheets:api_irods_request_reject',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_reject,
                user,
                200,
                method='GET',
            )

        for user in bad_users:
            obj = self.create_request()
            self.url_reject = reverse(
                'samplesheets:api_irods_request_reject',
                kwargs={'irodsdatarequest': obj.sodar_uuid},
            )
            self.assert_response_api(
                self.url_reject,
                user,
                403,
                method='GET',
            )

        obj = self.create_request()
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

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_accept_anon(self):
        """Test get() in IrodsRequestRejectAPIView with anonymous access"""
        obj = self.create_request()
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

    def test_reject_archived(self):
        """Test post() in IrodsRequestUpdateAPIView with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
            self.user_owner_cat,
            self.user_owner,
            self.user_delegate_cat,
            self.user_delegate,
            self.user_contributor_cat,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
            self.user_no_roles,
            self.user_finder_cat,
        ]
        obj = self.create_request()
        self.url_reject = reverse(
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': obj.sodar_uuid},
        )
        self.assert_response_api(self.url_reject, good_users, 200, method='GET')
        self.assert_response_api(self.url_reject, bad_users, 403, method='GET')
        self.assert_response_api(
            self.url_reject, self.anonymous, 401, method='GET'
        )
