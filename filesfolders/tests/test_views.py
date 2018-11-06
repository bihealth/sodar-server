"""Tests for views in the filesfolders app"""
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import RequestFactory

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.project_settings import set_project_setting

from ..models import File, Folder, HyperLink
from .test_models import FolderMixin, FileMixin, HyperLinkMixin
from ..utils import build_public_url


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'filesfolders'
SECRET = '7dqq83clo2iyhg29hifbor56og6911r5'

TEST_DATA_PATH = os.path.dirname(__file__) + '/data/'
ZIP_PATH = TEST_DATA_PATH + 'unpack_test.zip'
ZIP_PATH_NO_FILES = TEST_DATA_PATH + 'no_files.zip'


class TestViewsBase(
        ProjectMixin, RoleAssignmentMixin, FileMixin, FolderMixin,
        HyperLinkMixin, TestCase):
    """Base class for view testing"""

    def setUp(self):
        self.req_factory = RequestFactory()

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init superuser
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Init project and owner role
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Change public link setting from default
        set_project_setting(
            self.project, APP_NAME, 'allow_public_links', True)

        # Init file content
        self.file_content = bytes('content'.encode('utf-8'))
        self.file_content_alt = bytes('alt content'.encode('utf-8'))

        # Init file
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


# List View --------------------------------------------------------------


class TestListView(TestViewsBase):
    """Tests for the file list view"""

    def test_render(self):
        """Test rendering of the project root view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'filesfolders:list',
                    kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)
            self.assertIsNotNone(response.context['folders'])
            self.assertIsNotNone(response.context['files'])
            self.assertIsNotNone(response.context['links'])

    def test_render_in_folder(self):
        """Test rendering of a folder view within the project"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:list',
                kwargs={'folder': self.folder.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)
            self.assertIsNotNone(response.context['folder_breadcrumb'])
            self.assertIsNotNone(response.context['files'])
            self.assertIsNotNone(response.context['links'])

    def test_render_with_readme_txt(self):
        """Test rendering of the project list with a plaintext readme file"""

        # Init readme file
        self.readme_file = self._make_file(
            name='readme.txt',
            file_name='readme.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.user,
            description='',
            public_url=False,
            secret='xxxxxxxxx')

        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['readme_name'], 'readme.txt')
            self.assertEqual(response.context['readme_data'], self.file_content)
            self.assertEqual(response.context['readme_mime'], 'text/plain')


# File Views -------------------------------------------------------------


class TestFileCreateView(TestViewsBase):
    """Tests for the File create view"""

    def test_render(self):
        """Test rendering of the File create view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_create',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)

    def test_render_in_folder(self):
        """Test rendering of the File create view under a folder"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_create',
                kwargs={'folder': self.folder.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)
            self.assertEqual(response.context['folder'].pk, self.folder.pk)

    def test_create(self):
        """Test file creation"""

        self.assertEqual(File.objects.all().count(), 1)

        post_data = {
            'name': 'new_file.txt',
            'file': SimpleUploadedFile('new_file.txt', self.file_content),
            'folder': '',
            'description': '',
            'flag': '',
            'public_url': False}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:file_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(File.objects.all().count(), 2)

    def test_create_in_folder(self):
        """Test file creation within a folder"""
        self.assertEqual(File.objects.all().count(), 1)

        post_data = {
            'name': 'new_file.txt',
            'file': SimpleUploadedFile('new_file.txt', self.file_content),
            'folder': self.folder.sodar_uuid,
            'description': '',
            'flag': '',
            'public_url': False}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:file_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'folder': self.folder.sodar_uuid}))

        self.assertEqual(File.objects.all().count(), 2)

    def test_create_existing(self):
        """Test file create with an existing file name (should fail)"""
        self.assertEqual(File.objects.all().count(), 1)

        post_data = {
            'name': 'file.txt',
            'file': SimpleUploadedFile('file.txt', self.file_content_alt),
            'folder': '',
            'description': '',
            'flag': '',
            'public_url': False}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:file_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)

        self.assertEqual(File.objects.all().count(), 1)

    def test_unpack_archive(self):
        """Test uploading a zip file to be unpacked"""

        # Assert preconditions
        self.assertEqual(File.objects.all().count(), 1)
        self.assertEqual(Folder.objects.all().count(), 1)

        with open(ZIP_PATH, 'rb') as zip_file:
            post_data = {
                'name': 'unpack_test.zip',
                'file': zip_file,
                'folder': '',
                'description': '',
                'flag': '',
                'public_url': False,
                'unpack_archive': True}

            with self.login(self.user):
                response = self.client.post(
                    reverse(
                        'filesfolders:file_create',
                        kwargs={'project': self.project.sodar_uuid}),
                    post_data)

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse(
                    'filesfolders:list',
                    kwargs={'project': self.project.sodar_uuid}))

        # Assert postconditions
        self.assertEqual(File.objects.all().count(), 3)
        self.assertEqual(Folder.objects.all().count(), 3)

        new_file1 = File.objects.get(name='zip_test1.txt')
        new_file2 = File.objects.get(name='zip_test2.txt')
        new_folder1 = Folder.objects.get(name='dir1')
        new_folder2 = Folder.objects.get(name='dir2')

        self.assertEqual(new_file1.folder, new_folder1)
        self.assertEqual(new_file2.folder, new_folder2)
        self.assertEqual(new_folder2.folder, new_folder1)

    def test_unpack_archive_overwrite(self):
        """Test uploading a zip file with existing file (should fail)"""

        ow_folder = self._make_folder(
            name='dir1',
            project=self.project,
            folder=None,
            owner=self.user,
            description='')

        ow_file = self._make_file(
            name='zip_test1.txt',
            file_name='zip_test1.txt',
            file_content=self.file_content,
            project=self.project,
            folder=ow_folder,
            owner=self.user,
            description='',
            public_url=False,
            secret='xxxxxxxxx')

        # Assert preconditions
        self.assertEqual(File.objects.all().count(), 2)
        self.assertEqual(Folder.objects.all().count(), 2)

        with open(ZIP_PATH, 'rb') as zip_file:
            post_data = {
                'name': 'unpack_test.zip',
                'file': zip_file,
                'folder': '',
                'description': '',
                'flag': '',
                'public_url': False,
                'unpack_archive': True}

            with self.login(self.user):
                response = self.client.post(
                    reverse(
                        'filesfolders:file_create',
                        kwargs={'project': self.project.sodar_uuid}),
                    post_data)

                self.assertEqual(response.status_code, 200)

        # Assert postconditions
        self.assertEqual(File.objects.all().count(), 2)
        self.assertEqual(Folder.objects.all().count(), 2)

    def test_unpack_archive_empty(self):
        """Test uploading a zip file with an empty archive (should fail)"""

        with open(ZIP_PATH_NO_FILES, 'rb') as zip_file:
            post_data = {
                'name': 'no_files.zip',
                'file': zip_file,
                'folder': '',
                'description': '',
                'flag': '',
                'public_url': False,
                'unpack_archive': True}

            with self.login(self.user):
                response = self.client.post(
                    reverse(
                        'filesfolders:file_create',
                        kwargs={'project': self.project.sodar_uuid}),
                    post_data)

                self.assertEqual(response.status_code, 200)


class TestFileUpdateView(TestViewsBase):
    """Tests for the File update view"""

    def test_render(self):
        """Test rendering of the File update view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_update',
                kwargs={'item': self.file.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['object'].pk, self.file.pk)

    def test_update(self):
        """Test file update with different content"""
        self.assertEqual(File.objects.all().count(), 1)
        self.assertEqual(self.file.file.read(), self.file_content)

        post_data = {
            'name': 'file.txt',
            'file': SimpleUploadedFile('file.txt', self.file_content_alt),
            'folder': '',
            'description': '',
            'flag': '',
            'public_url': False}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:file_update',
                    kwargs={'item': self.file.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(File.objects.all().count(), 1)
        self.file.refresh_from_db()
        self.assertEqual(self.file.file.read(), self.file_content_alt)

    def test_update_existing(self):
        """Test file update with a file name that already exists (should fail)"""

        new_file = self._make_file(
            name='file2.txt',
            file_name='file2.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.user,
            description='',
            public_url=True,
            secret='abc123')

        self.assertEqual(File.objects.all().count(), 2)

        post_data = {
            'name': 'file2.txt',
            'file': SimpleUploadedFile('file2.txt', self.file_content_alt),
            'folder': '',
            'description': '',
            'flag': '',
            'public_url': False}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:file_update',
                    kwargs={'item': self.file.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)

        self.assertEqual(File.objects.all().count(), 2)
        self.file.refresh_from_db()
        self.assertEqual(self.file.file.read(), self.file_content)

    def test_update_folder(self):
        """Test moving file to a different folder"""
        post_data = {
            'name': 'file.txt',
            'folder': self.folder.sodar_uuid,
            'description': '',
            'flag': '',
            'public_url': False}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:file_update',
                    kwargs={'item': self.file.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'folder': self.folder.sodar_uuid}))

        self.file.refresh_from_db()
        self.assertEqual(self.file.folder, self.folder)

    def test_update_folder_existing(self):
        """Test overwriting file in a different folder (should fail)"""

        # Create file with same name in the target folder
        self._make_file(
            name='file.txt',
            file_name='file.txt',
            file_content=self.file_content_alt,
            project=self.project,
            folder=self.folder,
            owner=self.user,
            description='',
            public_url=True,
            secret='aaaaaaaaa')

        post_data = {
            'name': 'file.txt',
            'folder': self.folder.pk,
            'description': '',
            'flag': '',
            'public_url': False}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:file_update',
                    kwargs={'item': self.file.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)

        self.assertEqual(File.objects.all().count(), 2)
        self.file.refresh_from_db()
        self.assertEqual(self.file.folder, None)


class TestFileDeleteView(TestViewsBase):
    """Tests for the File delete view"""

    def test_render(self):
        """Test rendering of the File delete view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_delete',
                kwargs={'item': self.file.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['object'].pk, self.file.pk)

    def test_post(self):
        """Test deleting a File"""
        self.assertEqual(File.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(reverse(
                'filesfolders:file_delete',
                kwargs={'item': self.file.sodar_uuid}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(File.objects.all().count(), 0)


class TestFileServeView(TestViewsBase):
    """Tests for the File serving view"""

    def test_render(self):
        """Test rendering of the File serving view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_serve',
                kwargs={
                    'file': self.file.sodar_uuid,
                    'file_name': self.file.name}))
            self.assertEqual(response.status_code, 200)


class TestFileServePublicView(TestViewsBase):
    """Tests for the File public serving view"""

    def test_render(self):
        """Test rendering of the File public serving view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_serve_public',
                kwargs={
                    'secret': SECRET,
                    'file_name': self.file.name}))
            self.assertEqual(response.status_code, 200)

    def test_bad_request_setting(self):
        """Test bad request response from the public serving view if public
        linking is disabled via settings"""
        set_project_setting(
            self.project, APP_NAME, 'allow_public_links', False)

        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_serve_public',
                kwargs={
                    'secret': SECRET,
                    'file_name': self.file.name}))
            self.assertEqual(response.status_code, 400)

    def test_bad_request_file_flag(self):
        """Test bad request response from the public serving view if the file
        can not be served publicly"""
        self.file.public_url = False
        self.file.save()

        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_serve_public',
                kwargs={
                    'secret': SECRET,
                    'file_name': self.file.name}))
            self.assertEqual(response.status_code, 400)

    def test_bad_request_no_file(self):
        """Test bad request response from the public serving view if the file
        has been deleted"""

        file_name = self.file.name
        self.file.delete()

        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_serve_public',
                kwargs={
                    'secret': SECRET,
                    'file_name': file_name}))
            self.assertEqual(response.status_code, 400)


class TestFilePublicLinkView(TestViewsBase):
    """Tests for the File public link view"""

    def test_render(self):
        """Test rendering of the File public link view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_public_link',
                kwargs={'file': self.file.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context['public_url'], build_public_url(
                    self.file,
                    self.req_factory.get(
                        'file_public_link',
                        kwargs={'file': self.file.sodar_uuid})))

    def test_redirect_setting(self):
        """Test redirecting from the public link view if public linking is
        disabled via settings """
        set_project_setting(
            self.project, APP_NAME, 'allow_public_links', False)

        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_public_link',
                kwargs={'file': self.file.sodar_uuid}))
            self.assertEqual(response.status_code, 302)

    def test_redirect_no_file(self):
        """Test redirecting from the public link view if the file has been
        deleted"""
        file_uuid = self.file.sodar_uuid
        self.file.delete()

        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:file_public_link',
                kwargs={'file': file_uuid}))
            self.assertEqual(response.status_code, 302)


# Folder Views -----------------------------------------------------------


class TestFolderCreateView(TestViewsBase):
    """Tests for the File create view"""

    def test_render(self):
        """Test rendering of the Folder create view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:folder_create',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)

    def test_render_in_folder(self):
        """Test rendering of the Folder create view under a folder"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:folder_create',
                kwargs={'folder': self.folder.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)
            self.assertEqual(response.context['folder'].pk, self.folder.pk)

    def test_create(self):
        """Test folder creation"""
        self.assertEqual(Folder.objects.all().count(), 1)

        post_data = {
            'name': 'new_folder',
            'folder': '',
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:folder_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(Folder.objects.all().count(), 2)

    def test_create_in_folder(self):
        """Test folder creation within a folder"""
        self.assertEqual(Folder.objects.all().count(), 1)

        post_data = {
            'name': 'new_folder',
            'folder': self.folder.sodar_uuid,
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:folder_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'folder': self.folder.sodar_uuid}))

        self.assertEqual(Folder.objects.all().count(), 2)

    def test_create_existing(self):
        """Test folder creation with existing folder (should fail)"""
        self.assertEqual(Folder.objects.all().count(), 1)

        post_data = {
            'name': 'folder',
            'folder': '',
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:folder_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(Folder.objects.all().count(), 1)


class TestFolderUpdateView(TestViewsBase):
    """Tests for the Folder update view"""

    def test_render(self):
        """Test rendering of the Folder update view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:folder_update',
                kwargs={'item': self.folder.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['object'].pk, self.folder.pk)

    def test_update(self):
        """Test folder update"""
        self.assertEqual(Folder.objects.all().count(), 1)

        post_data = {
            'name': 'renamed_folder',
            'folder': '',
            'description': 'updated description',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:folder_update',
                    kwargs={'item': self.folder.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(Folder.objects.all().count(), 1)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, 'renamed_folder')
        self.assertEqual(self.folder.description, 'updated description')

    def test_update_existing(self):
        """Test folder update with a name that already exists (should fail)"""

        self._make_folder(
            name='folder2',
            project=self.project,
            folder=None,
            owner=self.user,
            description='')

        self.assertEqual(Folder.objects.all().count(), 2)

        post_data = {
            'name': 'folder2',
            'folder': '',
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:folder_update',
                    kwargs={'item': self.folder.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)

        self.assertEqual(Folder.objects.all().count(), 2)
        self.folder.refresh_from_db()
        self.assertEqual(self.folder.name, 'folder')


class TestFolderDeleteView(TestViewsBase):
    """Tests for the File delete view"""

    def test_render(self):
        """Test rendering of the Folder delete view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:folder_delete',
                kwargs={'item': self.folder.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['object'].pk, self.folder.pk)

    def test_post(self):
        """Test deleting a Folder"""
        self.assertEqual(Folder.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(reverse(
                'filesfolders:folder_delete',
                kwargs={'item': self.folder.sodar_uuid}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(Folder.objects.all().count(), 0)


# HyperLink Views --------------------------------------------------------


class TestHyperLinkCreateView(TestViewsBase):
    """Tests for the HyperLink create view"""

    def test_render(self):
        """Test rendering of the HyperLink create view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:hyperlink_create',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)

    def test_render_in_folder(self):
        """Test rendering of the HyperLink create view under a folder"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:hyperlink_create',
                kwargs={'folder': self.folder.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'].pk, self.project.pk)
            self.assertEqual(response.context['folder'].pk, self.folder.pk)

    def test_create(self):
        """Test hyperlink creation"""
        self.assertEqual(HyperLink.objects.all().count(), 1)

        post_data = {
            'name': 'new link',
            'url': 'http://link.com',
            'folder': '',
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:hyperlink_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(HyperLink.objects.all().count(), 2)

    def test_create_in_folder(self):
        """Test folder creation within a folder"""
        self.assertEqual(HyperLink.objects.all().count(), 1)

        post_data = {
            'name': 'new link',
            'url': 'http://link.com',
            'folder': self.folder.sodar_uuid,
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:hyperlink_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'folder': self.folder.sodar_uuid}))

        self.assertEqual(HyperLink.objects.all().count(), 2)

    def test_create_existing(self):
        """Test hyperlink creation with an existing file (should fail)"""
        self.assertEqual(HyperLink.objects.all().count(), 1)

        post_data = {
            'name': 'Link',
            'url': 'http://google.com',
            'folder': '',
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:hyperlink_create',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(HyperLink.objects.all().count(), 1)


class TestHyperLinkUpdateView(TestViewsBase):
    """Tests for the HyperLink update view"""

    def test_render(self):
        """Test rendering of the HyperLink update view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:hyperlink_update',
                kwargs={'item': self.hyperlink.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['object'].pk, self.hyperlink.pk)

    def test_update(self):
        """Test hyperlink update"""
        self.assertEqual(HyperLink.objects.all().count(), 1)

        post_data = {
            'name': 'Renamed Link',
            'url': 'http://updated.com',
            'folder': '',
            'description': 'updated description',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:hyperlink_update',
                    kwargs={'item': self.hyperlink.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(HyperLink.objects.all().count(), 1)
        self.hyperlink.refresh_from_db()
        self.assertEqual(self.hyperlink.name, 'Renamed Link')
        self.assertEqual(self.hyperlink.url, 'http://updated.com')
        self.assertEqual(self.hyperlink.description, 'updated description')

    def test_update_existing(self):
        """Test hyperlink update with a name that already exists (should fail)"""

        self._make_hyperlink(
            name='Link2',
            url='http://url2.com',
            project=self.project,
            folder=None,
            owner=self.user,
            description='')

        self.assertEqual(HyperLink.objects.all().count(), 2)

        post_data = {
            'name': 'Link2',
            'url': self.hyperlink.url,
            'folder': '',
            'description': '',
            'flag': ''}

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:hyperlink_update',
                    kwargs={'item': self.hyperlink.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)

        self.assertEqual(HyperLink.objects.all().count(), 2)
        self.hyperlink.refresh_from_db()
        self.assertEqual(self.hyperlink.name, 'Link')


class TestHyperLinkDeleteView(TestViewsBase):
    """Tests for the HyperLink delete view"""

    def test_render(self):
        """Test rendering of the File delete view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'filesfolders:hyperlink_delete',
                kwargs={'item': self.hyperlink.sodar_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['object'].pk, self.hyperlink.pk)

    def test_post(self):
        """Test deleting a HyperLink"""
        self.assertEqual(HyperLink.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(reverse(
                'filesfolders:hyperlink_delete',
                kwargs={'item': self.hyperlink.sodar_uuid}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'filesfolders:list',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(HyperLink.objects.all().count(), 0)


# Batch Editing View --------------------------------------------------------


class TestBatchEditView(TestViewsBase):
    """Tests for the batch editing view"""

    def test_render_delete(self):
        """Test rendering of the batch editing view when deleting"""
        post_data = {
            'batch-action': 'delete',
            'user-confirmed': '0'}

        post_data['batch_item_File_{}'.format(self.file.sodar_uuid)] = 1
        post_data['batch_item_Folder_{}'.format(self.folder.sodar_uuid)] = 1
        post_data['batch_item_HyperLink_{}'.format(
            self.hyperlink.sodar_uuid)] = 1

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:batch_edit',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)

    def test_render_move(self):
        """Test rendering of the batch editing view when moving"""
        post_data = {
            'batch-action': 'move',
            'user-confirmed': '0'}

        post_data['batch_item_File_{}'.format(self.file.sodar_uuid)] = 1
        post_data['batch_item_HyperLink_{}'.format(
            self.hyperlink.sodar_uuid)] = 1

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:batch_edit',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 200)

    def test_deletion(self):
        """Test batch object deletion"""

        # Assert preconditions
        self.assertEqual(File.objects.all().count(), 1)
        self.assertEqual(Folder.objects.all().count(), 1)
        self.assertEqual(HyperLink.objects.all().count(), 1)

        post_data = {
            'batch-action': 'delete',
            'user-confirmed': '1'}

        post_data['batch_item_File_{}'.format(self.file.sodar_uuid)] = 1
        post_data['batch_item_Folder_{}'.format(self.folder.sodar_uuid)] = 1
        post_data['batch_item_HyperLink_{}'.format(
            self.hyperlink.sodar_uuid)] = 1

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:batch_edit',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)

            # Assert postconditions
            self.assertEqual(File.objects.all().count(), 0)
            self.assertEqual(Folder.objects.all().count(), 0)
            self.assertEqual(HyperLink.objects.all().count(), 0)

    def test_deletion_non_empty_folder(self):
        """Test batch object deletion with a non-empty folder (should not be
        deleted)"""

        # Create new folder & file under folder
        new_folder = self._make_folder(
            'new_folder', self.project, None, self.user, '')

        new_file = self._make_file(
            name='new_file.txt',
            file_name='new_file.txt',
            file_content=self.file_content,
            project=self.project,
            folder=new_folder,  # Set new folder as parent
            owner=self.user,
            description='',
            public_url=True,
            secret='7dqq83clo2iyhg29hifbor56og6911r6')

        # Assert preconditions
        self.assertEqual(File.objects.all().count(), 2)
        self.assertEqual(Folder.objects.all().count(), 2)

        post_data = {
            'batch-action': 'delete',
            'user-confirmed': '1'}

        post_data['batch_item_File_{}'.format(self.file.sodar_uuid)] = 1
        post_data['batch_item_Folder_{}'.format(self.folder.sodar_uuid)] = 1
        post_data['batch_item_Folder_{}'.format(new_folder.sodar_uuid)] = 1

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:batch_edit',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)

            # Assert postconditions
            # The new folder and file should be left
            self.assertEqual(File.objects.all().count(), 1)
            self.assertEqual(Folder.objects.all().count(), 1)

    def test_moving(self):
        """Test batch object moving"""
        target_folder = self._make_folder(
            'target_folder', self.project, None, self.user, '')

        post_data = {
            'batch-action': 'move',
            'user-confirmed': '1',
            'target-folder': target_folder.sodar_uuid}

        post_data['batch_item_File_{}'.format(self.file.sodar_uuid)] = 1
        post_data['batch_item_Folder_{}'.format(self.folder.sodar_uuid)] = 1
        post_data['batch_item_HyperLink_{}'.format(
            self.hyperlink.sodar_uuid)] = 1

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:batch_edit',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)

            # Assert postconditions
            self.assertEqual(
                File.objects.get(pk=self.file.pk).folder.pk,
                target_folder.pk)
            self.assertEqual(
                Folder.objects.get(pk=self.folder.pk).folder.pk,
                target_folder.pk)
            self.assertEqual(
                HyperLink.objects.get(pk=self.hyperlink.pk).folder.pk,
                target_folder.pk)

    def test_moving_name_exists(self):
        """Test batch object moving with similarly name object in target
        (should not be moved)"""

        # Create new folder & file
        target_folder = self._make_folder(
            'target_folder', self.project, None, self.user, '')

        new_file = self._make_file(
            name='file.txt',    # Same name as self.file
            file_name='file.txt',
            file_content=self.file_content,
            project=self.project,
            folder=target_folder,   # New file is under target
            owner=self.user,
            description='',
            public_url=True,
            secret='7dqq83clo2iyhg29hifbor56og6911r6')

        post_data = {
            'batch-action': 'move',
            'user-confirmed': '1',
            'target-folder': target_folder.sodar_uuid}

        post_data['batch_item_File_{}'.format(self.file.sodar_uuid)] = 1
        post_data['batch_item_Folder_{}'.format(self.folder.sodar_uuid)] = 1
        post_data['batch_item_HyperLink_{}'.format(
            self.hyperlink.sodar_uuid)] = 1

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'filesfolders:batch_edit',
                    kwargs={'project': self.project.sodar_uuid}),
                post_data)

            self.assertEqual(response.status_code, 302)

            # Assert postconditions
            self.assertEqual(
                File.objects.get(pk=self.file.pk).folder,
                None)   # Not moved
            self.assertEqual(
                Folder.objects.get(pk=self.folder.pk).folder.pk,
                target_folder.pk)
            self.assertEqual(
                HyperLink.objects.get(pk=self.hyperlink.pk).folder.pk,
                target_folder.pk)
