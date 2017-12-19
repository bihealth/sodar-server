"""Tests for permissions in the projectroles Django app"""

from urllib.parse import urlencode

from django.core.urlresolvers import reverse

from test_plus.test import TestCase

from ..models import Role, OMICS_CONSTANTS
from .test_models import ProjectMixin, RoleAssignmentMixin, \
    ProjectInviteMixin


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


class TestPermissionBase(
        TestCase, ProjectMixin, RoleAssignmentMixin, ProjectInviteMixin):
    """Base class for testing permissions"""

    def setUp(self):
        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_staff = Role.objects.get_or_create(
            name=PROJECT_ROLE_STAFF)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init users

        # Superuser
        self.superuser = self.make_user('superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        # No user
        self.anonymous = None

        # Users with role assignments
        self.user_owner = self.make_user('user_owner')
        self.user_delegate = self.make_user('user_delegate')
        self.user_staff = self.make_user('user_staff')
        self.user_contributor = self.make_user('user_contributor')
        self.user_guest = self.make_user('user_guest')

        # User without role assignments
        self.user_no_roles = self.make_user('user_no_roles')

        # Init projects

        # Top level category
        self.category = self._make_project(
            title='TestCategoryTop',
            type=PROJECT_TYPE_CATEGORY,
            parent=None)

        # Subproject under category
        self.project = self._make_project(
            title='TestProjectSub',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category)

        # Init role assignments

        self._make_assignment(
            self.category, self.user_owner, self.role_owner)
        self.as_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner)
        self.as_delegate = self._make_assignment(
            self.project, self.user_delegate, self.role_delegate)
        self.as_staff = self._make_assignment(
            self.project, self.user_staff, self.role_staff)
        self.as_contributor = self._make_assignment(
            self.project, self.user_contributor, self.role_contributor)
        self.as_guest = self._make_assignment(
            self.project, self.user_guest, self.role_guest)

    # TODO: Remove and use assert_response() instead
    def assert_render200_ok(self, url, users):
        """
        Assert successful HTTP request for url with a list of users.
        :param url: Target URL for the request
        :param users: Users to test
        """
        for user in users:
            # Authenticated user
            if user:
                with self.login(user):
                    response = self.client.get(url)

                    self.assertEqual(
                        response.status_code, 200, 'user={}'.format(user))

            # Anonymous
            else:
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code, 200, 'user={}'.format(user))

    # TODO: Remove and use assert_response() instead
    def assert_redirect(
            self, url, users, redirect_user=None, redirect_anon=None,
            method='GET'):
        """
        Assert redirection to an appropriate page if user is not authorized
        :param url: Target URL for the request
        :param users: Users to test
        :param redirect_user: Redirect URL for signed in user (None=default)
        :param redirect_anon: Redirect URL for anonymous (None=default)
        :param method: Method for URL (default = 'GET')
        """
        def make_request(url, method):
            if method == 'POST':
                return self.client.post(url)

            else:
                return self.client.get(url)

        for user in users:
            if user:    # Authenticated user
                redirect_url = redirect_user if redirect_user else \
                    reverse('home')

                with self.login(user):
                    response = make_request(url, method)

            else:   # Anonymous
                redirect_url = redirect_anon if redirect_anon else \
                    reverse('account_login') + '?next=' + url

                response = make_request(url, method)

            msg = 'user={}'.format(user)
            self.assertEqual(response.status_code, 302, msg=msg)
            self.assertEqual(response.url, redirect_url, msg=msg)

    def assert_response(
            self, url, users, status_code, redirect_user=None,
            redirect_anon=None, method='GET'):
        """
        Assert a response status code for url with a list of users. Also checks
        for redirection URL where applicable.
        :param url: Target URL for the request
        :param users: Users to test
        :param status_code: Status code
        :param redirect_user: Redirect URL for signed in user (None=default)
        :param redirect_anon: Redirect URL for anonymous (None=default)
        :param method: Method for request (default='GET')
        """
        def make_request(url, method):
            if method == 'POST':
                return self.client.post(url)

            else:
                return self.client.get(url)

        for user in users:
            if user:    # Authenticated user
                redirect_url = redirect_user if redirect_user else \
                    reverse('home')

                with self.login(user):
                    response = make_request(url, method)

            else:   # Anonymous
                redirect_url = redirect_anon if redirect_anon else \
                    reverse('account_login') + '?next=' + url

                response = make_request(url, method)

            msg = 'user={}'.format(user)
            self.assertEqual(response.status_code, status_code, msg=msg)

            if status_code == 302:
                self.assertEqual(response.url, redirect_url, msg=msg)


class TestBaseViews(TestPermissionBase):
    """Tests for base views"""

    def test_home(self):
        url = reverse('home')
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        bad_users = [
            self.anonymous]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_project_search(self):
        url = reverse('project_search') + '?' + urlencode({'s': 'test'})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        bad_users = [
            self.anonymous]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(reverse('home'), bad_users)

    def test_login(self):
        url = reverse('account_login')
        good_users = [
            self.anonymous,
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]

        self.assert_render200_ok(url, good_users)

    def test_logout(self):
        url = reverse('account_logout')
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_redirect(
            url,
            good_users,
            redirect_user='/login/',
            redirect_anon='/login/')

    def test_about(self):
        url = reverse('about')
        good_users = [
            self.anonymous,
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)

    def test_admin(self):
        url = '/admin/'
        good_users = [
            self.superuser]
        bad_users = [
            self.anonymous,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(
            url, bad_users,
            redirect_user='/admin/login/?next=/admin/',
            redirect_anon='/admin/login/?next=/admin/')


class TestProjectViews(TestPermissionBase):
    """Tests for Project views"""

    def test_category_details(self):
        """Test access to category details"""
        url = reverse('project_detail', kwargs={'pk': self.category.pk})

        # Add user with access to project below category: should still be able
        # to view the category
        new_user = self.make_user('new_user')
        self._make_assignment(
            self.project, new_user, self.role_contributor)

        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            new_user]
        bad_users = [
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_project_details(self):
        """Test access to project details"""
        url = reverse('project_detail', kwargs={'pk': self.project.pk})
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

    def test_update(self):
        """Test access to project updating"""
        url = reverse('project_update', kwargs={'pk': self.project.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.anonymous,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_create_top(self):
        """Test access to top level project creation"""
        url = reverse('project_create')
        good_users = [
            self.superuser]
        bad_users = [
            self.anonymous,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_create_sub(self):
        """Test access to subproject creation"""
        url = reverse('project_create', kwargs={'project': self.category.pk})
        good_users = [
            self.superuser,
            self.as_owner.user]
        bad_users = [
            self.anonymous,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_roles(self):
        """Test access to role list"""
        url = reverse('project_roles', kwargs={'pk': self.project.pk})
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

    def test_role_create(self):
        """Test access to role creation"""
        url = reverse(
            'role_create',
            kwargs={
                'project': self.project.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.anonymous,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_role_update(self):
        """Test access to role updating"""
        url = reverse(
            'role_update',
            kwargs={
                'project': self.project.pk,
                'pk': self.as_contributor.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.anonymous,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_role_delete(self):
        """Test access to role deletion"""
        url = reverse(
            'role_delete',
            kwargs={
                'project': self.project.pk,
                'pk': self.as_contributor.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        bad_users = [
            self.anonymous,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_role_update_owner(self):
        """Test access to owner role update: not allowed, should fail"""
        url = reverse(
            'role_update',
            kwargs={
                'project': self.project.pk,
                'pk': self.as_owner.pk})
        bad_users = [
            self.anonymous,
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_redirect(url, bad_users)

    def test_role_delete_owner(self):
        """Test access to owner role deletion: not allowed, should fail"""
        url = reverse(
            'role_delete',
            kwargs={
                'project': self.project.pk,
                'pk': self.as_owner.pk})
        bad_users = [
            self.anonymous,
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_redirect(url, bad_users)

    def test_role_update_delegate(self):
        """Test access to delegate role update"""
        url = reverse(
            'role_update',
            kwargs={
                'project': self.project.pk,
                'pk': self.as_delegate.pk})
        good_users = [
            self.superuser,
            self.as_owner.user]
        bad_users = [
            self.anonymous,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_role_delete_delegate(self):
        """Test access to role deletion for delegate"""
        url = reverse(
            'role_delete',
            kwargs={
                'project': self.project.pk,
                'pk': self.as_delegate.pk})
        good_users = [
            self.superuser,
            self.as_owner.user]
        bad_users = [
            self.anonymous,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_role_import(self):
        """Test access to role importing"""
        url = reverse(
            'role_import',
            kwargs={
                'project': self.project.pk})
        good_users = [
            self.superuser,
            self.as_owner.user]
        bad_users = [
            self.anonymous,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)


    def test_role_invite_create(self):
        """Test access to role invite creation"""
        url = reverse(
            'role_invite_create',
            kwargs={
                'project': self.project.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.anonymous,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_role_invite_list(self):
        """Test access to role invite list"""
        url = reverse(
            'role_invites',
            kwargs={
                'project': self.project.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.anonymous,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_role_invite_resend(self):
        """Test access to role invite resending"""

        # Init invite
        invite = self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.user_owner,
            message='')

        url = reverse(
            'role_invite_resend',
            kwargs={
                'project': self.project.pk,
                'pk': invite.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.anonymous,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_redirect(
            url,
            good_users,
            redirect_user=reverse(
                'role_invites',
                kwargs={'project': self.project.pk}))
        self.assert_redirect(url, bad_users)

    def test_role_invite_revoke(self):
        """Test access to role invite revoking"""

        # Init invite
        invite = self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.user_owner,
            message='')

        url = reverse(
            'role_invite_revoke',
            kwargs={
                'project': self.project.pk,
                'pk': invite.pk})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.anonymous,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_starring_api(self):
        """Test access to project starring API view"""
        url = reverse('project_star', kwargs={'pk': self.project.pk})
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
        self.assert_response(url, good_users, 200, method='POST')
        self.assert_response(url, bad_users, 403, method='POST')
