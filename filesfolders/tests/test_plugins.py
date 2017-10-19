"""Plugin tests for the filesfolders app"""

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, ProjectSetting, OMICS_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.utils import save_default_project_settings

from filesfolders.plugins import ProjectAppPlugin
from filesfolders.urls import urlpatterns
from filesfolders.tests.test_models import FolderMixin, FileMixin,\
    HyperLinkMixin


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SECRET = '7dqq83clo2iyhg29hifbor56og6911r5'
PLUGIN_NAME = 'filesfolders'
PLUGIN_TITLE = 'Small Files'
PLUGIN_URL_ID = 'project_files'
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

        # Save default settings for project
        save_default_project_settings(self.project)

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
        self.assertEquals(plugin.get_model().name, PLUGIN_NAME)
        self.assertEquals(plugin.name, PLUGIN_NAME)
        self.assertEquals(plugin.get_model().title, PLUGIN_TITLE)
        self.assertEquals(plugin.title, PLUGIN_TITLE)
        self.assertEquals(plugin.entry_point_url_id, PLUGIN_URL_ID)

    def test_plugin_urls(self):
        """Test plugin URLs to ensure they're the same as in the app config"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)
        self.assertEqual(plugin.urls, urlpatterns)

    def test_plugin_info(self):
        """Test the get_info() function in the plugin"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)

        expected = [
            ('Latest File', '{}/{} (from {} on {})'.format(
                'root',
                self.file.name,
                self.file.owner.username,
                self.file.date_modified.strftime('%Y-%m-%d'))),
            ('Maximum File Size', filesizeformat(
                settings.FILESFOLDERS_MAX_UPLOAD_SIZE))]

        self.assertEquals(plugin.get_info(self.project.pk), expected)

    def test_plugin_setting_value(self):
        """Test plugin default setting value in the database"""
        plugin = ProjectAppPluginPoint.get_plugin(PLUGIN_NAME)

        setting = ProjectSetting.objects.get(
            app_plugin=plugin.get_model(),
            project=self.project.pk,
            name=SETTING_KEY)

        expected = setting.get_value()

        self.assertEquals(
            plugin.project_settings[SETTING_KEY]['default'], expected)
