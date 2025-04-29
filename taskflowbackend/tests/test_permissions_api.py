"""Tests for taskflowbackend REST API view permissions"""

from django.test import override_settings
from django.urls import reverse

from taskflowbackend.tests.base import TaskflowAPIPermissionTestBase
from taskflowbackend.views_api import (
    TASKFLOW_API_DEFAULT_VERSION,
    TASKFLOW_API_MEDIA_TYPE,
)


class TestProjectLockStatusAPIView(TaskflowAPIPermissionTestBase):
    """Tests for ProjectLockStatusAPIView permissions"""

    api_version = TASKFLOW_API_DEFAULT_VERSION
    media_type = TASKFLOW_API_MEDIA_TYPE

    def setUp(self):
        super().setUp()
        self.good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest_cat,
            self.user_guest,
        ]
        self.bad_users = [self.user_finder_cat, self.user_no_roles]
        self.url = reverse(
            'taskflowbackend:api_lock_status',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test TestProjectLockStatusAPIView GET"""
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
        self.assert_response_api(self.url, self.good_users, 200)
        self.assert_response_api(self.url, self.bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response_api(self.url, self.good_users, 200)
        self.assert_response_api(self.url, self.bad_users, 403)
        self.assert_response_api(self.url, self.anonymous, 401)
