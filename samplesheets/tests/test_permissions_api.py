"""Tests for REST API View permissions in the samplesheets app"""

import uuid

from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_models import RemoteSiteMixin, RemoteProjectMixin
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.tests.test_permissions_api import TestProjectAPIPermissionBase

from samplesheets.models import (
    Investigation,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
from samplesheets.tests.test_io import SampleSheetIOMixin
from samplesheets.tests.test_models import (
    IrodsDataRequestMixin,
    IrodsAccessTicketMixin,
)
from samplesheets.tests.test_permissions import (
    SHEET_PATH,
    REMOTE_SITE_NAME,
    REMOTE_SITE_URL,
    REMOTE_SITE_SECRET,
    INVALID_SECRET,
)


# Local constants
IRODS_FILE_PATH = '/sodarZone/path/test1.txt'
LABEL_CREATE = 'label'


class TestInvestigationRetrieveAPIView(
    SampleSheetIOMixin,
    TestProjectAPIPermissionBase,
):
    """Tests for InvestigationRetrieveAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test InvestigationRetrieveAPIView GET"""
        url = reverse(
            'samplesheets:api_investigation_retrieve',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited
            self.user_delegate_cat,  # Inherited
            self.user_contributor_cat,  # Inherited
            self.user_guest_cat,  # Inherited
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        self.assert_response_api(url, good_users, 200)
        self.assert_response_api(
            url, [self.user_finder_cat, self.user_no_roles], 403
        )
        self.assert_response_api(url, self.anonymous, 401)
        # Test public project
        self.project.set_public()
        self.assert_response_api(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response_api(url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        url = reverse(
            'samplesheets:api_investigation_retrieve',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response_api(url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:api_investigation_retrieve',
            kwargs={'project': self.project.sodar_uuid},
        )
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
        self.assert_response_api(url, good_users, 200)
        self.assert_response_api(
            url, [self.user_finder_cat, self.user_no_roles], 403
        )
        self.assert_response_api(url, self.anonymous, 401)
        # Test public project
        self.project.set_public()
        self.assert_response_api(
            url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response_api(url, self.anonymous, 401)


class TestSheetImportAPIView(SampleSheetIOMixin, TestProjectAPIPermissionBase):
    """Tests for SheetImportAPIView permissions"""

    def _cleanup_import(self):
        self.zip_file.seek(0)
        Investigation.objects.filter(project=self.project).delete()

    def setUp(self):
        super().setUp()
        self.zip_file = open(SHEET_PATH, 'rb')
        self.post_data = {'file': self.zip_file}

    def tearDown(self):
        self.zip_file.close()
        super().tearDown()

    def test_post(self):
        """Test SampleSheetImportAPIView POST"""
        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
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
            url,
            good_users,
            status_code=200,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.assert_response_api(
            url,
            bad_users,
            status_code=403,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.assert_response_api(
            url,
            self.anonymous,
            status_code=401,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.project.set_public()
        self.assert_response_api(
            url,
            bad_users,
            status_code=403,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.assert_response_api(
            url,
            self.anonymous,
            status_code=401,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response_api(
            url,
            self.anonymous,
            status_code=401,
            method='POST',
            format='multipart',
            data=self.post_data,
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
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
            url,
            good_users,
            status_code=200,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.assert_response_api(
            url,
            bad_users,
            status_code=403,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.assert_response_api(
            url,
            self.anonymous,
            status_code=401,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.project.set_public()
        self.assert_response_api(
            url,
            bad_users,
            status_code=403,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )
        self.assert_response_api(
            url,
            self.anonymous,
            status_code=401,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=self._cleanup_import,
        )


class TestSheetISAExportAPIView(
    SampleSheetIOMixin,
    TestProjectAPIPermissionBase,
):
    """Tests for SheetISAExportAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test SampleSheetISAExportAPIView GET"""
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles]
        self.assert_response_api(url, good_users, 200)
        self.assert_response_api(url, bad_users, 403)
        self.assert_response_api(url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response_api(url, bad_users, 200)
        self.assert_response_api(url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response_api(url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
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
        bad_users = [self.user_finder_cat, self.user_no_roles]
        self.assert_response_api(url, good_users, 200)
        self.assert_response_api(url, bad_users, 403)
        self.assert_response_api(url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response_api(url, bad_users, 200)
        self.assert_response_api(url, self.anonymous, 401)


class TestIrodsAccessTicketListAPIView(
    SampleSheetIOMixin, IrodsAccessTicketMixin, TestProjectAPIPermissionBase
):
    """Test permissions for IrodsAccessTicketListAPIView"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.url = (
            reverse(
                'samplesheets:api_irods_ticket_list',
                kwargs={'project': self.project.sodar_uuid},
            )
            + '?active=0'
        )
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/test/ticket1',
            user=self.user_owner,
            ticket='ticket',
            label=LABEL_CREATE,
            date_expires=(timezone.localtime() + timedelta(days=1)).isoformat(),
        )

    def test_get(self):
        """Test IrodsAccessTicketListAPIView GET"""
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


class TestIrodsAccessTicketRetrieveAPIView(
    SampleSheetIOMixin, IrodsAccessTicketMixin, TestProjectAPIPermissionBase
):
    """Test permissions for IrodsAccessTicketRetrieveAPIView"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            path='/test/ticket1',
            user=self.user_owner,
            ticket='ticket',
            label=LABEL_CREATE,
            date_expires=(timezone.localtime() + timedelta(days=1)).isoformat(),
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_retrieve',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketRetrieveAPIView GET"""
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


class TestIrodsDataRequestRetrieveAPIView(
    IrodsDataRequestMixin, TestProjectAPIPermissionBase
):
    """Tests for TestIrodsDataRequestRetrieveAPIView permissions"""

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
            'samplesheets:api_irods_request_retrieve',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
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
        # Test public project
        self.project.set_public()
        self.assert_response_api(
            self.url, [self.user_finder_cat, self.user_no_roles], 403
        )
        self.assert_response_api(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
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


class TestIrodsDataRequestListAPIView(TestProjectAPIPermissionBase):
    """Tests for TestIrodsDataRequestListAPIView permissions"""

    def setUp(self):
        super().setUp()
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
        # Test public project
        self.project.set_public()
        self.assert_response_api(
            self.url, [self.user_finder_cat, self.user_no_roles], 403
        )
        self.assert_response_api(self.url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
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


class TestIrodsDataRequestRejectAPIView(
    IrodsDataRequestMixin, TestProjectAPIPermissionBase
):
    """Test permissions for TestIrodsDataRequestRejectAPIView"""

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
            'samplesheets:api_irods_request_reject',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_reject(self):
        """Test IrodsDataRequestRejectAPIView POST"""
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
        """Test POST in IrodsDataRequestRejectAPIView with anonymous access"""
        self.assert_response_api(self.url, self.anonymous, 401, method='POST')

    def test_reject_archive(self):
        """Test POST in IrodsDataRequestUpdateAPIView with archived project"""
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


class TestIrodsDataRequestDestroyAPIView(
    SampleSheetIOMixin, IrodsDataRequestMixin, TestProjectAPIPermissionBase
):
    """Test permissions for IrodsDataRequestDestroyAPIView"""

    def _make_request(self):
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.request.sodar_uuid = self.request_uuid
        self.request.save()
        self.url = reverse(
            'samplesheets:api_irods_request_delete',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def setUp(self):
        super().setUp()
        self.request_uuid = uuid.uuid4()
        self._make_request()

    def test_delete(self):
        """Test IrodsDataRequestDestroyAPIView DELETE"""
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
            self.url,
            good_users,
            204,
            method='DELETE',
            cleanup_method=self._make_request,
        )
        self.assert_response_api(self.url, bad_users, 403, method='DELETE')
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_delete_anon(self):
        """Test DELETE with anonymous access"""
        self.project.set_public()
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')

    def test_delete_archive(self):
        """Test DELETE with archived project"""
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
            204,
            method='DELETE',
            cleanup_method=self._make_request,
        )
        self.assert_response_api(self.url, bad_users, 403, method='DELETE')
        self.assert_response_api(self.url, self.anonymous, 401, method='DELETE')


class TestRemoteSheetGetAPIView(
    SampleSheetIOMixin,
    RemoteSiteMixin,
    RemoteProjectMixin,
    TestProjectPermissionBase,
):
    """Tests for RemoteSheetGetAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # No user
        self.anonymous = None
        # Create remote site
        self.target_site = self.make_site(
            name=REMOTE_SITE_NAME,
            url=REMOTE_SITE_URL,
            mode=SODAR_CONSTANTS['SITE_MODE_TARGET'],
            description='',
            secret=REMOTE_SITE_SECRET,
        )

    def test_get(self):
        """Test RemoteSheetGetAPIView GET"""
        # Create remote project
        self.make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES'],
        )
        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, self.anonymous, 200)

    def test_get_invalid_access(self):
        """Test GET with invalid access level"""
        self.make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_VIEW_AVAIL'],
        )
        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, self.anonymous, 401)

    def test_get_no_access(self):
        """Test GET with no remote access rights"""
        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, self.anonymous, 401)

    def test_get_invalid_secret(self):
        """Test GET with invalid remote site secret"""
        self.make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_VIEW_AVAIL'],
        )
        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': INVALID_SECRET,
            },
        )
        self.assert_response(url, self.anonymous, 401)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES'],
        )
        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, self.anonymous, 200)
