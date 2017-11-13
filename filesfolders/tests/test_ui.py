"""UI tests for the filesfolders app"""

from urllib.parse import urlencode

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_ui import TestUIBase
from projectroles.models import ProjectSetting, OMICS_CONSTANTS
from projectroles.project_settings import set_project_setting
from projectroles.utils import build_secret

from .test_models import FolderMixin, FileMixin, HyperLinkMixin


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'filesfolders'


class TestListView(TestUIBase, FolderMixin, FileMixin, HyperLinkMixin):
    """Tests for filesfolders main file list view UI"""

    def setUp(self):
        super(TestListView, self).setUp()

        set_project_setting(
            self.project, APP_NAME, 'allow_public_links', True)

        self.file_content = bytes('content'.encode('utf-8'))
        self.secret_file_owner = build_secret()
        self.secret_file_contributor = build_secret()

        # Init folders

        # Folder created by project owner
        self.folder_owner = self._make_folder(
            name='folder_owner',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='')

        # File created by project contributor
        self.folder_contributor = self._make_folder(
            name='folder_contributor',
            project=self.project,
            folder=None,
            owner=self.user_contributor,
            description='')

        # Init files

        # File uploaded by project owner
        self.file_owner = self._make_file(
            name='file_owner.txt',
            file_name='file_owner.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='',
            public_url=True,    # NOTE: Public URL OK
            secret=self.secret_file_owner)

        # File uploaded by project contributor
        self.file_contributor = self._make_file(
            name='file_contributor.txt',
            file_name='file_contributor.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.user_contributor,
            description='',
            public_url=False,   # NOTE: No public URL
            secret=self.secret_file_contributor)

        # Init hyperlinks

        # HyperLink added by project owner
        self.hyperlink_owner = self._make_hyperlink(
            name='Owner link',
            url='https://www.bihealth.org/',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='')

        # HyperLink added by project contributor
        self.hyperlink_contrib = self._make_hyperlink(
            name='Contributor link',
            url='http://www.google.com/',
            project=self.project,
            folder=None,
            owner=self.user_contributor,
            description='')

    def test_buttons_list(self):
        """Test file/folder list-wide button visibility according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user]
        expected_false = [
            self.as_guest.user]
        url = reverse('project_files', kwargs={'project': self.project.pk})

        self.assert_element_exists(
            expected_true, url, 'omics-ff-buttons-list', True)

        self.assert_element_exists(
            expected_false, url, 'omics-ff-buttons-list', False)

    def test_buttons_file(self):
        """Test file action buttons visibility according to user permissions"""
        expected = [
            (self.superuser, 2),
            (self.as_owner.user, 2),
            (self.as_delegate.user, 2),
            (self.as_staff.user, 2),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 0)]
        url = reverse('project_files', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-ff-file-buttons')

    def test_buttons_folder(self):
        """Test folder action buttons visibility according to user
        permissions"""
        expected = [
            (self.superuser, 2),
            (self.as_owner.user, 2),
            (self.as_delegate.user, 2),
            (self.as_staff.user, 2),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 0)]
        url = reverse('project_files', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-ff-folder-buttons')

    def test_buttons_hyperlink(self):
        """Test hyperlink action buttons visibility according to user
        permissions"""
        expected = [
            (self.superuser, 2),
            (self.as_owner.user, 2),
            (self.as_delegate.user, 2),
            (self.as_staff.user, 2),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 0)]
        url = reverse('project_files', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-ff-hyperlink-buttons')

    def test_file_checkboxes(self):
        """Test batch file editing checkbox visibility according to user
        permissions"""
        expected = [
            (self.superuser, 6),
            (self.as_owner.user, 6),
            (self.as_delegate.user, 6),
            (self.as_staff.user, 6),
            (self.as_contributor.user, 3),
            (self.as_guest.user, 0)]
        url = reverse('project_files', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-ff-file-checkbox')

    def test_public_link(self):
        """Test public link visibility according to user
        permissions"""
        expected = [
            (self.superuser, 1),
            (self.as_owner.user, 1),
            (self.as_delegate.user, 1),
            (self.as_staff.user, 1),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 0)]
        url = reverse('project_files', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-ff-link-public')

    def test_public_link_disable(self):
        """Test public link visibility if allow_public_links is set to False"""
        setting = ProjectSetting.objects.get(
            project=self.project.pk,
            app_plugin__name=APP_NAME,
            name='allow_public_links')
        setting.value = 0
        setting.save()

        expected = [
            (self.superuser, 0),
            (self.as_owner.user, 0),
            (self.as_delegate.user, 0),
            (self.as_staff.user, 0),
            (self.as_contributor.user, 0),
            (self.as_guest.user, 0)]
        url = reverse('project_files', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-ff-link-public')


class TestSearch(TestUIBase, FolderMixin, FileMixin, HyperLinkMixin):
    """Tests for the project search UI functionalities"""

    def setUp(self):
        super(TestSearch, self).setUp()

        self.file_content = bytes('content'.encode('utf-8'))
        self.secret_file_owner = build_secret()
        self.secret_file_contributor = build_secret()

        # Init folders

        # Folder created by project owner
        self.folder_owner = self._make_folder(
            name='folder_owner',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='description')

        # File created by project contributor
        self.folder_contributor = self._make_folder(
            name='folder_contributor',
            project=self.project,
            folder=None,
            owner=self.user_contributor,
            description='description')

        # Init files

        # File uploaded by project owner
        self.file_owner = self._make_file(
            name='file_owner.txt',
            file_name='file_owner.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='description',
            public_url=True,    # NOTE: Public URL OK
            secret=self.secret_file_owner)

        # File uploaded by project contributor
        self.file_contributor = self._make_file(
            name='file_contributor.txt',
            file_name='file_contributor.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.user_contributor,
            description='description',
            public_url=False,   # NOTE: No public URL
            secret=self.secret_file_contributor)

        # Init hyperlinks

        # HyperLink added by project owner
        self.hyperlink_owner = self._make_hyperlink(
            name='Owner link',
            url='https://www.bihealth.org/',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='description')

        # HyperLink added by project contributor
        self.hyperlink_contrib = self._make_hyperlink(
            name='Contributor link',
            url='http://www.google.com/',
            project=self.project,
            folder=None,
            owner=self.user_contributor,
            description='description')

    def test_search_results(self):
        """Test search items visibility according to user permissions"""
        expected = [
            (self.superuser, 4),
            (self.as_owner.user, 4),
            (self.as_delegate.user, 4),
            (self.as_contributor.user, 4),
            (self.as_staff.user, 4),
            (self.as_guest.user, 4),
            (self.user_no_roles, 0)]
        url = reverse('project_search') + '?' + urlencode({'s': 'description'})
        self.assert_element_count(expected, url, 'omics-ff-search-item')

    def test_search_type_file(self):
        """Test search items visibility with 'file' type"""
        expected = [
            (self.superuser, 2),
            (self.as_owner.user, 2),
            (self.as_delegate.user, 2),
            (self.as_contributor.user, 2),
            (self.as_staff.user, 2),
            (self.as_guest.user, 2),
            (self.user_no_roles, 0)]
        url = reverse('project_search') + '?' + urlencode({
            's': 'file type:file'})
        self.assert_element_count(expected, url, 'omics-ff-search-item')

    def test_search_type_link(self):
        """Test search items visibility with 'link' as type"""
        expected = [
            (self.superuser, 2),
            (self.as_owner.user, 2),
            (self.as_delegate.user, 2),
            (self.as_contributor.user, 2),
            (self.as_staff.user, 2),
            (self.as_guest.user, 2),
            (self.user_no_roles, 0)]
        url = reverse('project_search') + '?' + urlencode({
            's': 'link type:link'})
        self.assert_element_count(expected, url, 'omics-ff-search-item')

    def test_search_type_nonexisting(self):
        """Test search items visibility with a nonexisting type"""
        expected = [
            (self.superuser, 0),
            (self.as_owner.user, 0),
            (self.as_delegate.user, 0),
            (self.as_contributor.user, 0),
            (self.as_staff.user, 0),
            (self.as_guest.user, 0),
            (self.user_no_roles, 0)]
        url = reverse('project_search') + '?' + urlencode({
            's': 'test type:Jaix1au'})
        self.assert_element_count(expected, url, 'omics-ff-search-item')
