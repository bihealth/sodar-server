"""Tests for permissions in the filesfolders app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.models import ProjectSetting, OMICS_CONSTANTS
from projectroles.project_settings import set_project_setting
from projectroles.tests.test_permissions import TestProjectPermissionBase

from filesfolders.tests.test_models import FileMixin, FolderMixin,\
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
APP_NAME = 'filesfolders'
SECRET = '7dqq83clo2iyhg29hifbor56og6911r5'


class TestFolderPermissions(TestProjectPermissionBase, FolderMixin):
    """Tests for Folder views"""

    def setUp(self):
        super(TestFolderPermissions, self).setUp()

        self.folder = self._make_folder(
            name='folder',
            project=self.project,
            folder=None,
            owner=self.as_owner.user,   # Project owner is the owner of folder
            description='')

    def test_folder_create(self):
        url = reverse(
            'filesfolders:folder_create',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user]
        bad_users = [
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_folder_update(self):
        url = reverse(
            'filesfolders:folder_update',
            kwargs={'item': self.folder.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the folder
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_folder_delete(self):
        url = reverse(
            'filesfolders:folder_delete',
            kwargs={'item': self.folder.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the folder
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)


class TestFilePermissions(TestProjectPermissionBase, FileMixin):
    """Tests for File views"""

    def setUp(self):
        super(TestFilePermissions, self).setUp()

        set_project_setting(
            self.project, APP_NAME, 'allow_public_links', True)

        self.file_content = bytes('content'.encode('utf-8'))

        # Init file
        self.file = self._make_file(
            name='file.txt',
            file_name='file.txt',
            file_content=self.file_content,
            project=self.project,
            folder=None,
            owner=self.as_owner.user,     # Project owner is the file owner
            description='',
            public_url=True,
            secret=SECRET)

    def test_file_create(self):
        url = reverse(
            'filesfolders:file_create',
            kwargs={
                'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user]
        bad_users = [
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_file_update(self):
        url = reverse(
            'filesfolders:file_update',
            kwargs={'item': self.file.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the file
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_file_delete(self):
        url = reverse(
            'filesfolders:file_delete',
            kwargs={'item': self.file.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the file
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_file_public_link(self):
        """Test generation and viewing of a public URL to a file"""
        url = reverse(
            'filesfolders:file_public_link',
            kwargs={'file': self.file.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user]
        bad_users = [
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_file_serve(self):
        """Test file serving for authenticated users"""
        url = reverse(
            'filesfolders:file_serve',
            kwargs={
                'file': self.file.omics_uuid,
                'file_name': self.file.name})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user]
        bad_users = [
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_file_serve_public(self):
        """Test public file serving"""
        url = reverse(
            'filesfolders:file_serve_public',
            kwargs={
                'secret': SECRET,
                'file_name': self.file.name})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)

    def test_file_serve_public_disabled(self):
        """Test public file serving if not allowed in project, should fail"""
        set_project_setting(
            self.project, APP_NAME, 'allow_public_links', False)
        url = reverse(
            'filesfolders:file_serve_public',
            kwargs={
                'secret': SECRET,
                'file_name': self.file.name})
        bad_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]

        for user in bad_users:
            with self.login(user):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)

        # Anonymous
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)


class TestHyperLinkPermissions(TestProjectPermissionBase, HyperLinkMixin):
    """Tests for HyperLink views"""

    def setUp(self):
        super(TestHyperLinkPermissions, self).setUp()

        # Init link
        self.hyperlink = self._make_hyperlink(
            name='Link',
            url='http://www.google.com/',
            project=self.project,
            folder=None,
            owner=self.user_owner,
            description='')

    def test_hyperlink_create(self):
        url = reverse(
            'filesfolders:hyperlink_create',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user]
        bad_users = [
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_hyperlink_update(self):
        url = reverse(
            'filesfolders:hyperlink_update',
            kwargs={'item': self.hyperlink.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the link
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_hyperlink_delete(self):
        url = reverse(
            'filesfolders:hyperlink_delete',
            kwargs={'item': self.hyperlink.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.as_contributor.user,   # NOTE: not the owner of the link
            self.anonymous,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)


class TestBatchPermissions(TestProjectPermissionBase, FolderMixin):
    """Tests for batch editing views"""

    def setUp(self):
        super(TestBatchPermissions, self).setUp()

        self.folder = self._make_folder(
            name='folder',
            project=self.project,
            folder=None,
            owner=self.as_owner.user,   # Project owner is the owner of folder
            description='')

    def test_batch_edit(self):
        """Test access to batch editing confirmation"""
        url = reverse(
            'filesfolders:batch_edit',
            kwargs={'project': self.project.omics_uuid})

        # NOTE: Contributor is OK as checks for object perms happen after POST
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user]
        bad_users = [
            # self.anonymous,
            self.as_guest.user,
            self.user_no_roles]

        post_data = {
            'batch-action': 'delete',
            'user-confirmed': '0',
            'batch_item_Folder_{}'.format(self.folder.omics_uuid): '1'}

        for user in good_users:
            with self.login(user):
                response = self.client.post(url, post_data)
                self.assertEqual(response.status_code, 200)

        for user in bad_users:
            with self.login(user):
                response = self.client.post(url, post_data)
                self.assertEqual(response.status_code, 302)
