"""Tests for samplesheets REST API view permissions with taskflow"""

import os

from datetime import timedelta

from irods.keywords import REG_CHKSUM_KW

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowAPIPermissionTestBase

from samplesheets.models import (
    IrodsAccessTicket,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
from samplesheets.tests.test_io import SampleSheetIOMixin
from samplesheets.tests.test_models import (
    IrodsDataRequestMixin,
    IrodsAccessTicketMixin,
)
from samplesheets.tests.test_permissions import SHEET_PATH
from samplesheets.tests.test_views_api_taskflow import (
    IRODS_FILE_PATH,
    IRODS_FILE_MD5,
)
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
    IRODS_FILE_NAME,
)


# Base Classes and Mixins ------------------------------------------------------


class IrodsDataRequestAPIViewTestBase(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIPermissionTestBase
):
    """Base class for iRODS data request API view permission tests"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up iRODS data
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.obj_path = os.path.join(self.assay_path, IRODS_FILE_NAME)
        self.md5_path = os.path.join(self.assay_path, IRODS_FILE_NAME + '.md5')
        # Create objects
        self.file_obj = self.irods.data_objects.create(self.obj_path)
        self.md5_obj = self.irods.data_objects.create(self.md5_path)


# Test Classes -----------------------------------------------------------------


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
        self.url = reverse('samplesheets:api_file_exists')

    def test_get(self):
        """Test SampleDataFileExistsAPIView GET"""
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
        self.assert_response_api(self.url, good_users, 200, data=self.post_data)
        self.assert_response_api(
            self.url, self.anonymous, 401, data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
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
        self.assert_response_api(self.url, good_users, 200, data=self.post_data)
        self.assert_response_api(
            self.url, self.anonymous, 401, data=self.post_data
        )


class TestIrodsAccessTicketAPIViewBase(
    SampleSheetIOMixin,
    IrodsAccessTicketMixin,
    SampleSheetTaskflowMixin,
    TaskflowAPIPermissionTestBase,
):
    """Tests for IrodsAccessAPIView permissions"""

    def create_ticket(self):
        """Helper function to create a ticket"""
        ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll.path + '/ticket1',
            user=self.user_owner,
            ticket='ticket',
            label='label',
            date_expires=(timezone.localtime() + timedelta(days=1)).isoformat(),
        )
        return ticket

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up iRODS data
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.coll = self.irods.collections.create(
            os.path.join(self.assay_path, 'coll')
        )


class TestIrodsAccessTicketListAPIView(TestIrodsAccessTicketAPIViewBase):
    """Test permissions for IrodsAccessTicketListAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.url = (
            reverse(
                'samplesheets:api_irods_ticket_list',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?active=0'
        )

    def test_get(self):
        """Test get() in IrodsAccessTicketListAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(self.url, good_users, 200)
        self.assert_response_api(self.url, bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test get() with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test get() with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(self.url, good_users, 200)
        self.assert_response_api(self.url, bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)


class TestIrodsAccessTicketRetrieveAPIView(TestIrodsAccessTicketAPIViewBase):
    """Test permissions for IrodsAccessTicketRetrieveAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.ticket = self.create_ticket()
        self.url = reverse(
            'samplesheets:api_irods_ticket_retrieve',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_get(self):
        """Test get() in IrodsAccessTicketRetrieveAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(self.url, good_users, 200)
        self.assert_response_api(self.url, bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test get() with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test get() with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(self.url, good_users, 200)
        self.assert_response_api(self.url, bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)


class TestIrodsAccessTicketCreateAPIView(TestIrodsAccessTicketAPIViewBase):
    """Test permissions for IrodsAccessTicketCreateAPIView"""

    def setUp(self):
        super().setUp()
        # Set up URLs
        self.url = reverse(
            'samplesheets:api_irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.path = self.coll.path
        self.label = 'label'
        self.date_expires = (
            timezone.localtime() + timedelta(days=1)
        ).isoformat()
        # Set up post data
        self.post_data = {
            'assay': self.assay.pk,
            'path': self.path,
            'label': self.label,
            'date_expires': self.date_expires,
        }

    def _delete_ticket(self):
        """Delete ticket created in setUp()"""
        access_ticket = IrodsAccessTicket.objects.all().first()
        ticket_str = access_ticket.ticket
        self.irods_backend.delete_ticket(self.irods, ticket_str)
        access_ticket.delete()

    def test_create(self):
        """Test post() in IrodsAccessTicketCreateAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(
            self.url,
            good_users,
            201,
            method='post',
            data=self.post_data,
            cleanup_method=self._delete_ticket,
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='post', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_create_anon(self):
        """Test post() with anonymous access"""
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )

    def test_create_archive(self):
        """Test post() with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(
            self.url, good_users, 201, method='post', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='post', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )


class TestIrodsAccessTicketUpdateAPIView(TestIrodsAccessTicketAPIViewBase):
    """Test permissions for IrodsAccessTicketUpdateAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket = self.create_ticket()
        # Set up URLs
        self.url = reverse(
            'samplesheets:api_irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        # Set up post data
        self.label_update = 'label_update'
        self.post_data = {'label': self.label_update}

    def test_update(self):
        """Test put() in IrodsAccessTicketUpdateAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(
            self.url, good_users, 200, method='put', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='put', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='put', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_update_anon(self):
        """Test put() with anonymous access"""
        self.assert_response_api(
            self.url, self.anonymous, 401, method='put', data=self.post_data
        )

    def test_update_archive(self):
        """Test put() with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(
            self.url, good_users, 200, method='put', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='put', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='put', data=self.post_data
        )


class TestIrodsAccessTicketDestroyAPIView(TestIrodsAccessTicketAPIViewBase):
    """Test permissions for IrodsAccessTicketDeleteAPIView"""

    def create_irods_ticket(self):
        # Create ticket in database and iRODS
        ticket_str = 'ticket'
        label = 'label'
        # Create ticket in database and iRODS
        ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll.path,
            user=self.user_owner,
            ticket=ticket_str,
            label=label,
            date_expires=timezone.localtime() + timedelta(days=1),
        )
        self.irods_backend.issue_ticket(
            self.irods,
            'read',
            self.coll.path,
            ticket_str=ticket_str,
            expiry_date=None,
        )
        return ticket

    def test_delete(self):
        """Test delete() in IrodsAccessTicketDeleteAPIView"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]

        for user in good_users:
            self.ticket = self.create_irods_ticket()
            self.url = reverse(
                'samplesheets:api_irods_ticket_delete',
                kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
            )
            self.assert_response_api(self.url, user, 204, method='delete')

        self.ticket = self.create_ticket()
        self.url = reverse(
            'samplesheets:api_irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        self.assert_response_api(self.url, bad_users, 403, method='delete')
        self.assert_response_api(self.url, self.anonymous, 401, method='delete')


class TestIrodsDataRequestListAPIView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIPermissionTestBase
):
    """Tests for IrodsDataRequestListAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)
        self.url = reverse(
            'samplesheets:api_irods_request_list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestListAPIView GET"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(self.url, good_users, 200)
        self.assert_response_api(self.url, bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(self.url, good_users, 200)
        self.assert_response_api(self.url, bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)


class TestIrodsDataRequestCreateAPIView(IrodsDataRequestAPIViewTestBase):
    """Test permissions for IrodsDataRequestCreateAPIView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:api_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {'path': self.obj_path + '/', 'description': ''}

    def test_create(self):
        """Test IrodsDataRequestCreateAPIView POST"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        bad_users = [
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(
            self.url, good_users, 201, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='POST', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_create_anon(self):
        """Test POST with anonymous access"""
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self.post_data,
        )

    def test_create_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(
            self.url, good_users, 201, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='POST', data=self.post_data
        )


class TestIrodsDataRequestUpdateAPIView(
    IrodsDataRequestMixin, IrodsDataRequestAPIViewTestBase
):
    """Test permissions for IrodsDataRequestUpdateAPIView"""

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )
        self.update_data = {'path': self.obj_path, 'description': 'Updated'}

    def test_update(self):
        """Test IrodsDataRequestUpdateAPIView POST"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,  # Request creator
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_no_roles,
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

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_update_anon(self):
        """Test POST with anonymous access"""
        self.project.set_public()
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )

    def test_update_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(
            self.url, good_users, 200, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url, bad_users, 403, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )


# NOTE: For IrodsDataRequestDestroyAPIView, see test_permissions_api


class TestIrodsDataRequestAcceptAPIView(
    IrodsDataRequestMixin, IrodsDataRequestAPIViewTestBase
):
    """Test permissions for TestIrodsDataRequestAcceptAPIView"""

    def _cleanup(self):
        self.request.status = IRODS_REQUEST_STATUS_ACTIVE
        self.request.save()

    def setUp(self):
        super().setUp()
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_accept(self):
        """Test IrodsDataRequestAcceptAPIView POST"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(
            self.url,
            good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(self.url, bad_users, 403, method='POST')
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_accept_anon(self):
        """Test POST with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    def test_accept_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        good_users = [self.superuser]
        bad_users = [
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
        self.assert_response_api(
            self.url,
            good_users,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(self.url, bad_users, 403, method='POST')
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')


# NOTE: For IrodsDataRequestRejectAPIView, see test_permissions_api
