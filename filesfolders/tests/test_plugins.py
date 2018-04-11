"""Plugin tests for the filesfolders app"""
import uuid

from django.urls import reverse
from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from filesfolders.urls import urlpatterns
from filesfolders.tests.test_models import FolderMixin, FileMixin,\
    HyperLinkMixin


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SECRET = '7dqq83clo2iyhg29hifbor56og6911r5'
PLUGIN_NAME = 'filesfolders'
PLUGIN_TITLE = 'Small Files'
PLUGIN_URL_ID = 'filesfolders:list'
SETTING_KEY = 'allow_public_links'


# NOTE: Setting up the filesfolders plugin is done during migration


class TestPlugins(
        TestCase, ProjectMixin, FolderMixin, FileMixin, HyperLinkMixin,
        RoleAssignmentMixin):
    """Test filesfolders plugin"""

    def setUp(self):
        # Init superuser
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]

        # Init project and owner role
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init file
        self.file_content = bytes('content'.encode('utf-8'))

        self.file = self._make_file(
            name='file.txt',
            file_name='file.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.user,
            description='',
            public_url=True,
            secret=SECRET)

        # Init folder
        self.folder = self._make_folder(
            name='folder',
            project=self.project,
            folder=None,
            owner=self.user,
            description='')

        # Init link
        self.hyperlink = self._make_hyperlink(
            name='Link',
            url='http://www.google.com/',
            project=self.project,
            folder=None,
            owner=self.user,
            description='')

    def test_plugin_retrieval(self):
        """Test retrieving ProjectAppPlugin from the database"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.get_model().name, PLUGIN_NAME)
        self.assertEqual(plugin.name, PLUGIN_NAME)
        self.assertEqual(plugin.get_model().title, PLUGIN_TITLE)
        self.assertEqual(plugin.title, PLUGIN_TITLE)
        self.assertEqual(plugin.entry_point_url_id, PLUGIN_URL_ID)

    def test_plugin_urls(self):
        """Test plugin URLs to ensure they're the same as in the app config"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        self.assertEqual(plugin.urls, urlpatterns)

    def test_get_object_link_file(self):
        """Test get_object_link() for a File object"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        url = reverse('filesfolders:file_serve', kwargs={
            'file': self.file.omics_uuid,
            'file_name': self.file.name})
        ret = plugin.get_object_link('File', self.file.omics_uuid)

        self.assertEqual(ret['url'], url)
        self.assertEqual(ret['label'], self.file.name)
        self.assertEqual(ret['blank'], True)

    def test_get_object_link_folder(self):
        """Test get_object_link() for a Folder object"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        url = reverse('filesfolders:list', kwargs={
            'folder': self.folder.omics_uuid})
        ret = plugin.get_object_link('Folder', self.folder.omics_uuid)

        self.assertEqual(ret['url'], url)
        self.assertEqual(ret['label'], self.folder.name)

    def test_get_object_link_hyperlink(self):
        """Test get_object_link() for a HyperLink object"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        ret = plugin.get_object_link('HyperLink', self.hyperlink.omics_uuid)

        self.assertEqual(ret['url'], self.hyperlink.url)
        self.assertEqual(ret['label'], self.hyperlink.name)
        self.assertEqual(ret['blank'], True)

    def test_get_taskflow_sync_data(self):
        """Test get_taskflow_sync_data()"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        self.assertEqual(plugin.get_taskflow_sync_data(), None)

    def test_get_object_link_fail(self):
        """Test get_object_link() with a non-existent object"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        self.assertEqual(plugin.get_object_link('File', uuid.uuid4()), None)
