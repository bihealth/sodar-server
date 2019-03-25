"""Tests for permissions in the irodsbackend app"""

from unittest import skipIf

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_views_taskflow import TestTaskflowBase


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
TEST_COLL_NAME = 'test_coll'
TEST_FILE_NAME = 'test1'
NON_PROJECT_PATH = '/omicsZone/projects'
BACKENDS_ENABLED = all(
    _ in settings.ENABLED_BACKEND_PLUGINS for _ in ['omics_irods', 'taskflow']
)
BACKEND_SKIP_MSG = (
    'Required backends (taskflow, omics_irods) ' 'not enabled in settings'
)


# TODO: Move this into sodar_core, see sodar_core#147
class ViewPermissionMixin:
    def assert_response(
        self,
        url,
        users,
        status_code,
        redirect_user=None,
        redirect_anon=None,
        method='GET',
        post_data=None,
    ):
        """
        Assert a response status code for url with a list of users. Also checks
        for redirection URL where applicable.

        :param url: Target URL for the request
        :param users: Users to test
        :param status_code: Status code
        :param redirect_user: Redirect URL for signed in user (None=default)
        :param redirect_anon: Redirect URL for anonymous (None=default)
        :param method: Method for request (default='GET')
        :param post_data: Data for a POST request (optional, dict)
        """

        def make_request(url, method, post_data):
            if method == 'POST':
                return self.client.post(url, post_data)

            else:
                return self.client.get(url)

        for user in users:
            if user:  # Authenticated user
                redirect_url = (
                    redirect_user if redirect_user else reverse('home')
                )

                with self.login(user):
                    response = make_request(url, method, post_data)

            else:  # Anonymous
                redirect_url = (
                    redirect_anon
                    if redirect_anon
                    else reverse('login') + '?next=' + url
                )
                response = make_request(url, method, post_data)

            msg = 'user={}'.format(user)
            self.assertEqual(response.status_code, status_code, msg=msg)

            if status_code == 302:
                self.assertEqual(response.url, redirect_url, msg=msg)


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestIrodsbackendPermissions(ViewPermissionMixin, TestTaskflowBase):
    """Tests for irodsbackend API view permissions"""

    def setUp(self):
        super().setUp()

        # Init users
        self.superuser = self.user  # HACK
        self.anonymous = None
        self.user_owner = self.make_user('user_owner')
        self.user_delegate = self.make_user('user_delegate')
        self.user_contributor = self.make_user('user_contributor')
        self.user_guest = self.make_user('user_guest')
        self.user_no_roles = self.make_user('user_no_roles')

        # Set up project with taskflow
        self.project, self.as_owner = self._make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner,
            description='description',
        )

        # Set up assignments with taskflow
        self.as_delegate = self._make_assignment_taskflow(
            self.project, self.user_delegate, self.role_delegate
        )
        self.as_contributor = self._make_assignment_taskflow(
            self.project, self.user_contributor, self.role_contributor
        )
        self.as_guest = self._make_assignment_taskflow(
            self.project, self.user_guest, self.role_guest
        )

        # Set up irodsbackend
        self.irods_backend = get_backend_api('omics_irods')
        self.irods_session = self.irods_backend.get_session()

        # Set up test collections
        self.project_path = self.irods_backend.get_path(self.project)

    def tearDown(self):
        self.irods_session.cleanup()
        super().tearDown()

    def test_stats_get(self):
        """Test stats API view using a GET() request"""
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.project_path
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_stats_get_no_uuid(self):
        """Test stats API view using a GET() request without a project UUID"""
        url = self.irods_backend.get_url(view='stats', path=self.project_path)
        good_users = [self.superuser]
        bad_users = [
            self.anonymous,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 400)

    def test_stats_get_not_in_project(self):
        """Test stats API view using a GET() request with path not in project"""
        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=NON_PROJECT_PATH
        )
        bad_users = [
            self.anonymous,
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
        ]
        self.assert_response(url, bad_users, 400)

    def test_stats_get_no_perms(self):
        """Test stats API view using a GET() request without collection perms"""
        test_path = self.project_path + '/' + TEST_COLL_NAME
        self.irods_session.collections.create(test_path)  # NOTE: No perms given

        url = self.irods_backend.get_url(
            view='stats', project=self.project, path=test_path
        )
        good_users = [self.superuser, self.as_owner.user, self.as_delegate.user]
        bad_users = [
            self.anonymous,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_stats_post(self):
        """Test stats API view using a POST() request"""
        url = self.irods_backend.get_url(
            view='stats',
            project=self.project,
            path=self.project_path,
            method='POST',
        )
        post_data = {'paths': [self.project_path]}

        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(
            url, good_users, 200, method='POST', post_data=post_data
        )
        self.assert_response(
            url, bad_users, 403, method='POST', post_data=post_data
        )

    def test_stats_post_no_uuid(self):
        """Test stats API view using a POST() request without a project UUID"""
        url = self.irods_backend.get_url(
            view='stats', path=self.project_path, method='POST'
        )
        post_data = {'paths': [self.project_path]}

        good_users = [self.superuser]
        bad_users = [
            self.anonymous,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
        ]
        self.assert_response(
            url, good_users, 200, method='POST', post_data=post_data
        )
        self.assert_response(
            url, bad_users, 400, method='POST', post_data=post_data
        )

    def test_list_get(self):
        """Test object list API view using a GET() request"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=self.project_path, md5=0
        )
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
        ]
        bad_users = [self.anonymous, self.user_no_roles]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_list_get_no_uuid(self):
        """Test object list API view using a GET() request without a project UUID"""
        url = self.irods_backend.get_url(
            view='list', path=self.project_path, md5=0
        )
        good_users = [self.superuser]
        bad_users = [
            self.anonymous,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 400)

    def test_list_get_not_in_project(self):
        """Test object list API view using a GET() request with path not in project"""
        url = self.irods_backend.get_url(
            view='list', project=self.project, path=NON_PROJECT_PATH, md5=0
        )
        bad_users = [
            self.anonymous,
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
        ]
        self.assert_response(url, bad_users, 400)

    def test_list_get_no_perms(self):
        """Test object list API view using a GET() request without collection perms"""
        test_path = self.project_path + '/' + TEST_COLL_NAME
        self.irods_session.collections.create(test_path)  # NOTE: No perms given

        url = self.irods_backend.get_url(
            view='list', project=self.project, path=test_path, md5=0
        )
        good_users = [self.superuser, self.as_owner.user, self.as_delegate.user]
        bad_users = [
            self.anonymous,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles,
        ]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)
