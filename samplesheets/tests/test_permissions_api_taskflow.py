"""Tests for samplesheets REST API view permissions with taskflow"""

import os
import uuid

from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.tests.test_permissions import PermissionTestMixin

# Irodsbackend dependency
from irodsbackend.api import TICKET_MODE_READ

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
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views_api import (
    SAMPLESHEETS_API_MEDIA_TYPE,
    SAMPLESHEETS_API_DEFAULT_VERSION,
)


# Local constants
LABEL_CREATE = 'label'
LABEL_UPDATE = 'label_update'
IRODS_FILE_NAME = 'test1.txt'
IRODS_FILE_MD5 = '7265f4d211b56873a381d321f586e4a9'


# Base Classes and Mixins ------------------------------------------------------


class SheetTaskflowAPIPermissionTestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    PermissionTestMixin,
    TaskflowAPIPermissionTestBase,
):
    """Base class for samplesheets REST API view permission tests"""

    media_type = SAMPLESHEETS_API_MEDIA_TYPE
    api_version = SAMPLESHEETS_API_DEFAULT_VERSION

    def setUp(self):
        super().setUp()
        # Default users for write views
        self.good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        self.bad_users = [
            self.user_guest_cat,
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
        ]


class IrodsAccessTicketAPIViewTestBase(
    IrodsAccessTicketMixin,
    SheetTaskflowAPIPermissionTestBase,
):
    """Base class for iRODS access ticket API view permission tests"""

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


class IrodsDataRequestAPIViewTestBase(SheetTaskflowAPIPermissionTestBase):
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


class TestSampleDataFileExistsAPIView(SheetTaskflowAPIPermissionTestBase):
    """Tests for SampleDataFileExistsAPIView permissions"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Make iRODS collections
        self.make_irods_colls(self.investigation)
        # Create file
        self.coll_path = self.irods_backend.get_sample_path(self.project)
        self.coll = self.irods.collections.get(self.coll_path)
        self.make_irods_object(self.coll, IRODS_FILE_NAME)
        self.get_data = {'checksum': IRODS_FILE_MD5}
        self.url = reverse('samplesheets:api_file_exists')

    def test_get(self):
        """Test SampleDataFileExistsAPIView GET"""
        self.assert_response_api(
            self.url, self.auth_users, 200, data=self.get_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, data=self.get_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url, self.auth_users, 200, data=self.get_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, data=self.get_data
        )

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url, self.auth_users, 200, data=self.get_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, data=self.get_data
        )

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url, self.auth_users, 200, data=self.get_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, data=self.get_data
        )

    @override_settings(SHEETS_API_FILE_EXISTS_RESTRICT=True)
    def test_get_restrict(self):
        """Test GET with file exists restriction enabled"""
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_viewer,
            self.user_no_roles,
        ]
        self.assert_response_api(self.url, good_users, 200, data=self.get_data)
        self.assert_response_api(self.url, bad_users, 403, data=self.get_data)
        self.assert_response_api(
            self.url, self.anonymous, 401, data=self.get_data
        )


# NOTE: For TestIrodsAccessTicketListAPIView, see test_permissions_api
# NOTE: For TestIrodsAccessTicketRetrieveAPIView, see test_permissions_api


class TestIrodsAccessTicketCreateAPIView(IrodsAccessTicketAPIViewTestBase):
    """Test permissions for IrodsAccessTicketCreateAPIView"""

    def _delete_ticket(self):
        """Delete ticket created in test case"""
        access_ticket = IrodsAccessTicket.objects.all().first()
        ticket_str = access_ticket.ticket
        self.irods_backend.delete_ticket(self.irods, ticket_str)
        access_ticket.delete()

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:api_irods_ticket_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.path = self.coll.path
        self.date_expires = (
            timezone.localtime() + timedelta(days=1)
        ).isoformat()
        # Set up post data
        self.post_data = {
            'assay': self.assay.pk,
            'path': self.path,
            'label': LABEL_CREATE,
            'date_expires': self.date_expires,
            'allowed_hosts': [],
        }

    def test_post(self):
        """Test IrodsAccessTicketCreateAPIView POST"""
        self.assert_response_api(
            self.url,
            self.good_users,
            201,
            method='post',
            data=self.post_data,
            cleanup_method=self._delete_ticket,
        )
        self.assert_response_api(
            self.url, self.bad_users, 403, method='post', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous access"""
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='post',
            data=self.post_data,
            cleanup_method=self._delete_ticket,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='post',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='post',
            data=self.post_data,
            cleanup_method=self._delete_ticket,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='post',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url,
            self.superuser,
            201,
            method='post',
            data=self.post_data,
            cleanup_method=self._delete_ticket,
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='post',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='post', data=self.post_data
        )


class TestIrodsAccessTicketUpdateAPIView(IrodsAccessTicketAPIViewTestBase):
    """Test permissions for IrodsAccessTicketUpdateAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll.path + '/ticket1',
            user=self.user_owner,
            ticket='ticket',
            label=LABEL_CREATE,
            date_expires=(timezone.localtime() + timedelta(days=1)).isoformat(),
        )
        self.irods_backend.issue_ticket(
            irods=self.irods,
            mode=TICKET_MODE_READ,
            path=self.coll.path,
            ticket_str=self.ticket.ticket,
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_update',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )
        # Set up post data
        self.post_data = {'label': LABEL_UPDATE}

    def test_patch(self):
        """Test IrodsAccessTicketUpdateAPIView PATCH"""
        self.assert_response_api(
            self.url, self.good_users, 200, method='patch', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.bad_users, 403, method='patch', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='patch', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_patch_anon(self):
        """Test PATCH with anonymous access"""
        self.assert_response_api(
            self.url, self.anonymous, 401, method='patch', data=self.post_data
        )

    def test_patch_archive(self):
        """Test PATCH with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url, self.superuser, 200, method='patch', data=self.post_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='patch',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='patch', data=self.post_data
        )

    def test_patch_block(self):
        """Test PATCH with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url, self.superuser, 200, method='patch', data=self.post_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='patch',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='patch', data=self.post_data
        )

    def test_patch_read_only(self):
        """Test PATCH with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url, self.superuser, 200, method='patch', data=self.post_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='patch',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='patch', data=self.post_data
        )


class TestIrodsAccessTicketDestroyAPIView(IrodsAccessTicketAPIViewTestBase):
    """Test permissions for IrodsAccessTicketDeleteAPIView"""

    def _create_irods_ticket(self):
        ticket_str = 'ticket'
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path=self.coll.path,
            user=self.user_owner,
            ticket=ticket_str,
            label=LABEL_CREATE,
            date_expires=timezone.localtime() + timedelta(days=1),
        )
        self.irods_backend.issue_ticket(
            self.irods,
            'read',
            self.coll.path,
            ticket_str=ticket_str,
            date_expires=None,
        )
        self.ticket.sodar_uuid = self.request_uuid
        self.ticket.save()
        self.url = reverse(
            'samplesheets:api_irods_ticket_delete',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def setUp(self):
        super().setUp()
        self.request_uuid = uuid.uuid4()
        self._create_irods_ticket()

    def test_delete(self):
        """Test IrodsAccessTicketDeleteAPIView DELETE"""
        self.assert_response_api(
            self.url,
            self.good_users,
            204,
            method='DELETE',
            cleanup_method=self._create_irods_ticket,
        )
        self.assert_response_api(self.url, self.bad_users, 403, method='DELETE')
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_delete_anon(self):
        """Test DELETE with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')

    def test_delete_archive(self):
        """Test DELETE with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url,
            self.superuser,
            204,
            method='DELETE',
            cleanup_method=self._create_irods_ticket,
        )
        self.assert_response_api(
            self.url, self.auth_non_superusers, 403, method='DELETE'
        )
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')

    def test_delete_block(self):
        """Test DELETE with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url,
            self.superuser,
            204,
            method='DELETE',
            cleanup_method=self._create_irods_ticket,
        )
        self.assert_response_api(
            self.url, self.auth_non_superusers, 403, method='DELETE'
        )
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')

    def test_delete_read_only(self):
        """Test DELETE with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url,
            self.superuser,
            204,
            method='DELETE',
            cleanup_method=self._create_irods_ticket,
        )
        self.assert_response_api(
            self.url, self.auth_non_superusers, 403, method='DELETE'
        )
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')


class TestIrodsDataRequestListAPIView(SheetTaskflowAPIPermissionTestBase):
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
        self.assert_response_api(self.url, self.good_users, 200)
        self.assert_response_api(self.url, self.bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response_api(self.url, self.superuser, 200)
        self.assert_response_api(self.url, self.auth_non_superusers, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(self.url, self.superuser, 200)
        self.assert_response_api(self.url, self.auth_non_superusers, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(self.url, self.superuser, 200)
        self.assert_response_api(self.url, self.auth_non_superusers, 403)
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

    def test_post(self):
        """Test IrodsDataRequestCreateAPIView POST"""
        self.assert_response_api(
            self.url, self.good_users, 201, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.bad_users, 403, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='POST', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous access"""
        self.project.set_public()
        self.assert_response_api(
            self.url,
            self.anonymous,
            401,
            method='POST',
            data=self.post_data,
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url, self.superuser, 201, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='POST', data=self.post_data
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url, self.superuser, 201, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='POST', data=self.post_data
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url, self.superuser, 201, method='POST', data=self.post_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='POST',
            data=self.post_data,
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
            path=self.file_obj.path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_update',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )
        self.update_data = {'path': self.obj_path, 'description': 'Updated'}

    def test_post(self):
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
    def test_post_anon(self):
        """Test POST with anonymous access"""
        self.project.set_public()
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url, self.superuser, 200, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='PUT',
            data=self.update_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url, self.superuser, 200, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='PUT',
            data=self.update_data,
        )
        self.assert_response_api(
            self.url, self.anonymous, 401, method='PUT', data=self.update_data
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url, self.superuser, 200, method='PUT', data=self.update_data
        )
        self.assert_response_api(
            self.url,
            self.auth_non_superusers,
            403,
            method='PUT',
            data=self.update_data,
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
            path=self.file_obj.path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_accept',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_post(self):
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
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_contributor,
            self.user_guest,
            self.user_viewer,
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
    def test_post_anon(self):
        """Test POST with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url, self.auth_non_superusers, 403, method='POST'
        )
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url, self.auth_non_superusers, 403, method='POST'
        )
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(
            self.url,
            self.superuser,
            200,
            method='POST',
            cleanup_method=self._cleanup,
        )
        self.assert_response_api(
            self.url, self.auth_non_superusers, 403, method='POST'
        )
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')


# NOTE: For IrodsDataRequestRejectAPIView, see test_permissions_api


class TestProjectIrodsFileListAPIView(SheetTaskflowAPIPermissionTestBase):
    """Test permissions for ProjectIrodsFileListAPIView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up iRODS data
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.url = reverse(
            'samplesheets:api_file_list',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        self.bad_users = [
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_viewer,
            self.user_no_roles,
        ]

    def test_get(self):
        """Test ProjectIrodsFileListAPIView GET"""
        self.assert_response_api(self.url, self.good_users, 200)
        self.assert_response_api(self.url, self.bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response_api(self.url, self.bad_users, 200)
        self.assert_response_api(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public()
        self.assert_response_api(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response_api(self.url, self.good_users, 200)
        self.assert_response_api(self.url, self.bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response_api(self.url, self.bad_users, 200)
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response_api(self.url, self.superuser, 200)
        self.assert_response_api(self.url, self.auth_non_superusers, 403)
        self.assert_response_api(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response_api(self.url, self.bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(self.url, self.good_users, 200)
        self.assert_response_api(self.url, self.bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response_api(self.url, self.bad_users, 200)
        self.assert_response_api(self.url, self.anonymous, 401)
