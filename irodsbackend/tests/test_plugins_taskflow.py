"""Tests for plugins in the irodsbackend app with Taskflow enabled"""

import os

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import BackendPluginPoint

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowbackendTestBase


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
TEST_COLL = 'test'
TEST_FILE = 'test.txt'


class TestGetStatistics(TaskflowbackendTestBase):
    """Tests for get_statistics()"""

    def setUp(self):
        super().setUp()
        self.plugin = BackendPluginPoint.get_plugin('omics_irods')
        # Make project with owner in Taskflow
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
            public_guest_access=False,
        )
        # Set up test collection
        self.test_path = os.path.join(
            self.irods_backend.get_path(self.project), TEST_COLL
        )
        self.test_coll = self.irods.collections.create(self.test_path)
        # Set up rods user trash collection if not there
        self.trash_path = os.path.join(
            self.irods_backend.get_trash_path(), 'home', settings.IRODS_USER
        )
        if not self.irods.collections.exists(self.trash_path):
            self.irods.collections.create(self.trash_path)
        self.trash_coll = self.irods.collections.get(self.trash_path)

    def test_no_files(self):
        """Test get_statistics() with no files"""
        stats = self.plugin.get_statistics()
        # NOTE: filesizeformat() returns non-breakable whitespaces
        self.assertEqual(stats['irods_data_size']['value'], '0\xa0bytes')
        self.assertEqual(stats['irods_trash_size']['value'], '0\xa0bytes')

    def test_project_file(self):
        """Test get_statistics() with file under project collection"""
        self.make_irods_object(self.test_coll, TEST_FILE)
        stats = self.plugin.get_statistics()
        self.assertEqual(stats['irods_data_size']['value'], '1.0\xa0KB')
        self.assertEqual(stats['irods_trash_size']['value'], '0\xa0bytes')

    def test_trash_file(self):
        """Test get_statistics() with file under trash collection"""
        self.make_irods_object(self.trash_coll, TEST_FILE)
        stats = self.plugin.get_statistics()
        self.assertEqual(stats['irods_data_size']['value'], '0\xa0bytes')
        self.assertEqual(stats['irods_trash_size']['value'], '1.0\xa0KB')
