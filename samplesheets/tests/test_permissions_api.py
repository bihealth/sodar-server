"""Tests for REST API View permissions in the samplesheets app"""

from django.test import override_settings
from django.urls import reverse

from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_models import RemoteSiteMixin, RemoteProjectMixin
from projectroles.tests.test_permissions import TestProjectPermissionBase
from projectroles.tests.test_permissions_api import TestProjectAPIPermissionBase

from samplesheets.models import Investigation
from samplesheets.tests.test_io import SampleSheetIOMixin
from samplesheets.tests.test_permissions import (
    SHEET_PATH,
    REMOTE_SITE_NAME,
    REMOTE_SITE_URL,
    REMOTE_SITE_SECRET,
    INVALID_SECRET,
)


class TestInvestigationRetrieveAPIView(
    SampleSheetIOMixin,
    RemoteSiteMixin,
    RemoteProjectMixin,
    TestProjectAPIPermissionBase,
):
    """Tests for InvestigationRetrieveAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test get() in InvestigationRetrieveAPIView"""
        url = reverse(
            'samplesheets:api_investigation_retrieve',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
        ]
        self.assert_response_api(url, good_users, 200)
        self.assert_response_api(url, self.user_no_roles, 403)
        self.assert_response_api(url, self.anonymous, 401)
        # Test public project
        self.project.set_public()
        self.assert_response_api(url, self.user_no_roles, 200)
        self.assert_response_api(url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test get() with anonymous guest access"""
        url = reverse(
            'samplesheets:api_investigation_retrieve',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response_api(url, self.anonymous, 200)


class TestSampleSheetImportAPIView(
    SampleSheetIOMixin,
    RemoteSiteMixin,
    RemoteProjectMixin,
    TestProjectAPIPermissionBase,
):
    """Tests for SampleSheetImportAPIView permissions"""

    def setUp(self):
        super().setUp()

        self.zip_file = open(SHEET_PATH, 'rb')
        self.post_data = {'file': self.zip_file}

    def tearDown(self):
        self.zip_file.close()
        super().tearDown()

    def test_post(self):
        """Test post() in SampleSheetImportAPIView"""
        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [
            self.guest_as.user,
            self.user_no_roles,
        ]

        def _cleanup():
            self.zip_file.seek(0)
            Investigation.objects.filter(project=self.project).delete()

        self.assert_response_api(
            url,
            good_users,
            status_code=200,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=_cleanup,
        )
        self.assert_response_api(
            url,
            bad_users,
            status_code=403,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=_cleanup,
        )
        self.assert_response_api(
            url,
            self.anonymous,
            status_code=401,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=_cleanup,
        )
        self.project.set_public()
        self.assert_response_api(
            url,
            bad_users,
            status_code=403,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=_cleanup,
        )
        self.assert_response_api(
            url,
            self.anonymous,
            status_code=401,
            method='POST',
            format='multipart',
            data=self.post_data,
            cleanup_method=_cleanup,
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test post() with anonymous guest access"""
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


class TestSampleSheetISAExportAPIView(
    SampleSheetIOMixin,
    RemoteSiteMixin,
    RemoteProjectMixin,
    TestProjectAPIPermissionBase,
):
    """Tests for SampleSheetISAExportAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test get() in SampleSheetISAExportAPIView"""
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
        ]
        bad_users = [self.guest_as.user, self.user_no_roles]
        self.assert_response_api(url, good_users, 200)
        self.assert_response_api(url, bad_users, 403)
        self.assert_response_api(url, self.anonymous, 401)
        self.project.set_public()
        self.assert_response_api(url, bad_users, 403)
        self.assert_response_api(url, self.anonymous, 401)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test get() with anonymous guest access"""
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.project.set_public()
        self.assert_response_api(url, self.anonymous, 401)


class TestSampleDataFileExistsAPIView(TestProjectAPIPermissionBase):
    """Tests for SampleDataFileExistsAPIView permissions"""

    @override_settings(ENABLE_IRODS=False)
    def test_get(self):
        """Test get() in SampleDataFileExistsAPIView"""
        url = reverse('samplesheets:api_file_exists')
        request_data = {'checksum': ''}
        good_users = [
            self.superuser,
            self.owner_as.user,
            self.delegate_as.user,
            self.contributor_as.user,
            self.guest_as.user,
            self.user_no_roles,
        ]
        # No iRODS so good users get 500 -> still ok for auth :)
        self.assert_response_api(url, good_users, 500, data=request_data)
        self.assert_response_api(url, self.anonymous, 401, data=request_data)


class TestRemoteSheetGetAPIView(
    SampleSheetIOMixin,
    RemoteSiteMixin,
    RemoteProjectMixin,
    TestProjectPermissionBase,
):
    """Tests for RemoteSheetGetAPIView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # No user
        self.anonymous = None

        # Create remote site
        self.target_site = self._make_site(
            name=REMOTE_SITE_NAME,
            url=REMOTE_SITE_URL,
            mode=SODAR_CONSTANTS['SITE_MODE_TARGET'],
            description='',
            secret=REMOTE_SITE_SECRET,
        )

    def test_view(self):
        """Test RemoteSheetGetAPIView with correct access"""

        # Create remote project
        self._make_remote_project(
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

    def test_view_invalid_access(self):
        """Test RemoteSheetGetAPIView with invalid access level"""

        # Create remote project
        self._make_remote_project(
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

    def test_view_no_access(self):
        """Test RemoteSheetGetAPIView with no remote access rights"""

        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, self.anonymous, 401)

    def test_view_invalid_secret(self):
        """Test RemoteSheetGetAPIView with invalid remote site secret"""

        # Create remote project
        self._make_remote_project(
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
