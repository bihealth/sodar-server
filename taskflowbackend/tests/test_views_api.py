"""Tests for REST API views in the taskflowbackend app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

from taskflowbackend.tests.base import TaskflowAPIViewTestBase
from taskflowbackend.views_api import (
    TASKFLOW_API_DEFAULT_VERSION,
    TASKFLOW_API_MEDIA_TYPE,
    CATEGORY_EX_MSG,
)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']


class TestProjectLockStatusAPIView(TaskflowAPIViewTestBase):
    """Tests for ProjectLockStatusAPIView"""

    api_version = TASKFLOW_API_DEFAULT_VERSION
    media_type = TASKFLOW_API_MEDIA_TYPE

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.url = reverse(
            'taskflowbackend:api_lock_status',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test ProjectLockStatusAPIView GET"""
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'is_locked': False})

    def test_get_locked(self):
        """Test GET with locked project"""
        self.lock_project(self.project)
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'is_locked': True})

    def test_get_category(self):
        """Test GET with category (should fail)"""
        url = reverse(
            'taskflowbackend:api_lock_status',
            kwargs={'project': self.category.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], CATEGORY_EX_MSG)
