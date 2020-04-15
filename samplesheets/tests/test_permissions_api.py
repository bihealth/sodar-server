"""Tests for REST API View permissions in the samplesheets app"""

from django.urls import reverse
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_models import RemoteSiteMixin, RemoteProjectMixin
from projectroles.tests.test_permissions import TestProjectPermissionBase

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
    TestProjectPermissionBase,
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
        self.assert_response(url, good_users, status_code=200)
        self.assert_response(url, [self.user_no_roles], status_code=403)
        self.assert_response(url, [self.anonymous], status_code=401)


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
        self.assert_response(url, [self.anonymous], 200)

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
        self.assert_response(url, [self.anonymous], 401)

    def test_view_no_access(self):
        """Test RemoteSheetGetAPIView with no remote access rights"""

        url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )
        self.assert_response(url, [self.anonymous], 401)

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
        self.assert_response(url, [self.anonymous], 401)
