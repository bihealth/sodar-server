"""Tests for models in the filesfolders app"""
import base64

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict

from test_plus.test import TestCase

from ..models import File, FileData, Folder, HyperLink

# Projectroles dependency
from projectroles.models import OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin


# Omics constants
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']

PROJECT_NAME = 'Test Project'
SECRET = '7dqq83clo2iyhg29hifbor56og6911r5'


class FolderMixin:
    """Helper mixin for Folder creation"""
    @classmethod
    def _make_folder(cls, name, project, folder, owner, description):
        values = {
            'name': name,
            'project': project,
            'folder': folder,
            'owner': owner,
            'description': description}
        result = Folder(**values)
        result.save()
        return result


class TestFolder(TestCase, FolderMixin, ProjectMixin):
    """Tests for model.Folder"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Make project
        self.project = self._make_project(
            PROJECT_NAME, PROJECT_TYPE_PROJECT, None)

        # Make folder
        self.folder = self._make_folder(
            name='folder',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='')

    def test_initialization(self):
        expected = {
            'id': self.folder.pk,
            'name': 'folder',
            'project': self.project.pk,
            'folder': None,
            'owner': self.user_owner.pk,
            'description': '',
            'omics_uuid': self.folder.omics_uuid}
        self.assertEqual(model_to_dict(self.folder), expected)

    def test__str__(self):
        expected = '{}: root/folder'.format(PROJECT_NAME)
        self.assertEquals(str(self.folder), expected)

    def test__repr__(self):
        expected = "Folder('{}', 'folder', '/')".format(PROJECT_NAME)
        self.assertEquals(repr(self.folder), expected)

    def test_create_subfolder(self):
        """Test subfolder creation"""
        subfolder = self._make_folder(
            name='subfolder',
            project=self.project,
            folder=self.folder,
            owner=self.user_owner,
            description='')
        expected = {
            'id': subfolder.pk,
            'name': 'subfolder',
            'project': self.project.pk,
            'folder': self.folder.pk,
            'owner': self.user_owner.pk,
            'description': '',
            'omics_uuid': subfolder.omics_uuid}
        self.assertEquals(model_to_dict(subfolder), expected)


class FileMixin:
    """Helper mixin for File creation"""
    @classmethod
    def _make_file(
            cls, name, file_name, file_content, project, folder,
            owner, description, public_url, secret):
        values = {
            'name': name,
            'file': SimpleUploadedFile(file_name, file_content),
            'project': project,
            'folder': folder,
            'owner': owner,
            'description': description,
            'public_url': public_url,
            'secret': secret}
        result = File(**values)
        result.save()
        return result


class TestFile(TestCase, FileMixin, FolderMixin, ProjectMixin):
    """Tests for model.File"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Make project
        self.project = self._make_project(
            PROJECT_NAME, PROJECT_TYPE_PROJECT, None)

        # Make folder
        self.folder = self._make_folder(
            name='folder',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='')

        self.file_content = bytes('content'.encode('utf-8'))

        # Make file
        self.file = self._make_file(
            name='file.txt',
            file_name='file.txt',
            file_content=self.file_content,
            project=self.project,
            folder=self.folder,
            owner=self.user_owner,
            description='',
            public_url=True,
            secret=SECRET)

    def test_initialization(self):
        expected = {
            'id': self.file.pk,
            'name': 'file.txt',
            'file': self.file.file,
            'project': self.project.pk,
            'folder': self.folder.pk,
            'owner': self.user_owner.pk,
            'description': '',
            'public_url': True,
            'secret': SECRET,
            'omics_uuid': self.file.omics_uuid}
        self.assertEquals(model_to_dict(self.file), expected)

    def test__str__(self):
        expected = '{}: root/{}/{}'.format(
            PROJECT_NAME,
            self.folder.name,
            self.file.name)
        self.assertEquals(str(self.file), expected)

    def test__repr__(self):
        expected = "File('{}', '{}', {})".format(
            PROJECT_NAME,
            self.file.name,
            self.folder.__repr__())
        self.assertEquals(repr(self.file), expected)

    def test_file_access(self):
        """Ensure file can be accessed in database after creation"""
        file_data = FileData.objects.get(file_name=self.file.file.name)

        expected = {
            'id': file_data.pk,
            'file_name': 'filesfolders.FileData/bytes/file_name/'
                         'content_type/file.txt',
            'content_type': 'text/plain',
            'bytes': base64.b64encode(self.file_content).decode('utf-8')}

        self.assertEquals(model_to_dict(file_data), expected)

    def test_file_deletion(self):
        """Ensure file is removed from database after deletion"""

        # Assert precondition
        self.assertEquals(FileData.objects.all().count(), 1)

        self.file.delete()

        # Assert postcondition
        self.assertEquals(FileData.objects.all().count(), 0)


class HyperLinkMixin:
    """Helper mixin for HyperLink creation"""
    @classmethod
    def _make_hyperlink(cls, name, url, project, folder, owner, description):
        values = {
            'name': name,
            'url': url,
            'project': project,
            'folder': folder,
            'owner': owner,
            'description': description}
        result = HyperLink(**values)
        result.save()
        return result


class TestHyperLink(
        TestCase, FileMixin, FolderMixin, ProjectMixin, HyperLinkMixin):
    """Tests for model.File"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Make project
        self.project = self._make_project(
            PROJECT_NAME, PROJECT_TYPE_PROJECT, None)

        # Make folder
        self.folder = self._make_folder(
            name='folder',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='')

        # Make hyperlink
        self.hyperlink = self._make_hyperlink(
            name='Link',
            url='http://www.google.com/',
            project=self.project,
            folder=self.folder,
            owner=self.user_owner,
            description='')

    def test_initialization(self):
        expected = {
            'id': self.hyperlink.pk,
            'name': 'Link',
            'url': 'http://www.google.com/',
            'project': self.project.pk,
            'folder': self.folder.pk,
            'owner': self.user_owner.pk,
            'description': '',
            'omics_uuid': self.hyperlink.omics_uuid}
        self.assertEquals(model_to_dict(self.hyperlink), expected)

    def test__str__(self):
        expected = '{}: {} / {}'.format(
            PROJECT_NAME,
            self.folder.name,
            self.hyperlink.name)
        self.assertEquals(str(self.hyperlink), expected)

    def test__repr__(self):
        expected = "HyperLink('{}', '{}', {})".format(
            PROJECT_NAME,
            self.hyperlink.name,
            self.folder.__repr__())
        self.assertEquals(repr(self.hyperlink), expected)
