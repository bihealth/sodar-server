"""Tests for TaskflowAPI"""

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

from taskflowbackend.api import TaskflowAPI
from taskflowbackend.tests.base import TaskflowViewTestBase


taskflow = TaskflowAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']


class TestTaskflowAPILocking(TaskflowViewTestBase):
    """Tests for project locking features in TaskflowAPI"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )

    def test_is_locked_false(self):
        """Test is_locked() with non-locked project"""
        self.assertEqual(taskflow.is_locked(self.project), False)

    def test_is_locked_true(self):
        """Test is_locked() with locked project"""
        self.lock_project(self.project)
        self.assertEqual(taskflow.is_locked(self.project), True)
