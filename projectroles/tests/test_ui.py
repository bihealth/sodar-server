"""UI tests for the projectroles Django app"""

import socket

from django.contrib import auth
from django.test import LiveServerTestCase
from django.urls import reverse

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin,\
    ProjectInviteMixin
from projectroles.models import Role, OMICS_CONSTANTS


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


# Local constants
PROJECT_BUTTON_IDS = [
    'omics-pr-btn-project-roles',
    'omics-pr-btn-project-update',
    'omics-pr-btn-project-create',
    'omics-pr-btn-project-settings']


User = auth.get_user_model()


class LiveUserMixin:
    """Mixin for creating users to work with LiveServerTestCase"""

    @classmethod
    def _make_user(cls, user_name, superuser):
        """Make user, superuser if superuser=True"""
        kwargs = {
            'username': user_name,
            'password': 'password',
            'email': '{}@example.com'.format(user_name),
            'is_active': True}

        if superuser:
            user = User.objects.create_superuser(**kwargs)

        else:
            user = User.objects.create_user(**kwargs)

        user.save()
        return user


class TestUIBase(
        LiveServerTestCase, LiveUserMixin, ProjectMixin, RoleAssignmentMixin):
    """Base class for UI tests"""

    def setUp(self):
        socket.setdefaulttimeout(60)  # To get around Selenium hangups
        self.wait_time = 30

        # Init headless Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        self.selenium = webdriver.Chrome(chrome_options=options)

        # Prevent ElementNotVisibleException
        self.selenium.set_window_size(1100, 700)

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
        self.superuser = self._make_user('admin', True)
        self.user_owner = self._make_user('user_owner', False)
        self.user_delegate = self._make_user('user_delegate', False)
        self.user_staff = self._make_user('user_staff', False)
        self.user_contributor = self._make_user('user_contributor', False)
        self.user_guest = self._make_user('user_guest', False)
        self.user_no_roles = self._make_user('user_no_roles', False)

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

        # Top level project
        self.project_top = self._make_project(
            title='TestProjectTop',
            type=PROJECT_TYPE_PROJECT,
            parent=None)

        # Init role assignments

        # Category
        self._make_assignment(
            self.category, self.user_owner, self.role_owner)

        # Sub level project
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

        # Top level project (same roles as in self.project)
        self.as_owner = self._make_assignment(
            self.project_top, self.user_owner, self.role_owner)
        self.as_delegate = self._make_assignment(
            self.project_top, self.user_delegate, self.role_delegate)
        self.as_staff = self._make_assignment(
            self.project_top, self.user_staff, self.role_staff)
        self.as_contributor = self._make_assignment(
            self.project_top, self.user_contributor, self.role_contributor)
        self.as_guest = self._make_assignment(
            self.project_top, self.user_guest, self.role_guest)

        super(TestUIBase, self).setUp()

    def tearDown(self):
        # Shut down Selenium
        self.selenium.quit()
        super(TestUIBase, self).tearDown()

    def build_selenium_url(self, url):
        """Build absolute URL to work with Selenium"""
        return '{}{}'.format(self.live_server_url, url)

    def login_and_redirect(self, user, url):
        """Login with Selenium and wait for redirect to given url"""

        self.selenium.get(self.build_selenium_url('/'))

        # Logout (if logged in)

        try:
            signout_button = self.selenium.find_element_by_id('log-out-link')

            if signout_button:
                signout_button.click()

                # Wait for redirect
                WebDriverWait(self.selenium, self.wait_time).until(
                    ec.presence_of_element_located(
                        (By.ID, 'log-in-link')))

        except NoSuchElementException:
            pass

        # Login

        self.selenium.get(self.build_selenium_url(url))

        # Submit user data into form
        field_user = self.selenium.find_element_by_id('input-username')  # stock
        # field_user.send_keys(user.username)
        field_user.send_keys(user.username)

        field_pass = self.selenium.find_element_by_id('input-password')
        field_pass.send_keys('password')

        self.selenium.find_element_by_xpath(
            '//button[contains(., "Sign In")]').click()

        # Wait for redirect
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.ID, 'log-out-link')))

    def assert_element_exists(self, users, url, element_id, exists):
        """
        Assert existence of element on webpage based on logged user.
        :param users: User objects to test (list)
        :param url: URL to test (string)
        :param element_id: ID of element (string)
        :param exists: Whether element should or should not exist (boolean)
        """
        for user in users:
            self.login_and_redirect(user, url)

            if exists:
                self.assertIsNotNone(
                    self.selenium.find_element_by_id(element_id))

            else:
                with self.assertRaises(NoSuchElementException):
                    self.selenium.find_element_by_id(element_id)

    def assert_element_count(self, expected, url, id_substring):
        """
        Assert count of elements containing specified id based on logged user.
        :param expected: List of tuples with user (string), count (int)
        :param url: URL to test (string)
        :param id_substring: ID substring of element (string)
        """
        for e in expected:
            expected_user = e[0]    # Just to clarify code
            expected_count = e[1]

            self.login_and_redirect(expected_user, url)

            if expected_count > 0:
                self.assertEquals(
                    len(self.selenium.find_elements_by_xpath(
                        '//*[contains(@id, "{}")]'.format(id_substring))),
                    expected_count)

            else:
                with self.assertRaises(NoSuchElementException):
                    self.selenium.find_element_by_xpath(
                        '//*[contains(@id, "{}")]'.format(id_substring))

    def assert_element_set(self, expected, all_elements, url):
        """
        Assert existence of expected elements webpage based on logged user, as
        well as non-existence non-expected elements.
        :param expected: List of tuples with user (string), elements (list)
        :param all_elements: All possible elements in the set (list of strings)
        :param url: URL to test (string)
        """
        for e in expected:
            user = e[0]
            elements = e[1]

            self.login_and_redirect(user, url)

            for element in elements:
                self.assertIsNotNone(
                    self.selenium.find_element_by_id(element))

            not_expected = list(set(all_elements) ^ set(elements))

            for n in not_expected:
                with self.assertRaises(NoSuchElementException):
                    self.selenium.find_element_by_id(n)


class TestProjectList(TestUIBase):
    """Tests for the project list UI functionalities"""

    def test_button_create_toplevel(self):
        """Test top level creation button visibility according to user
        permissions"""
        expected_true = [
            self.superuser]

        expected_false = [
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user]

        url = reverse('home')

        self.assert_element_exists(
            expected_true, url, 'omics-pr-home-btn-create', True)

        self.assert_element_exists(
            expected_false, url, 'omics-pr-home-btn-create', False)


class TestProjectDetail(TestUIBase):
    """Tests for the project detail page UI functionalities"""

    def test_project_buttons(self):
        """Test visibility of top level project buttons according to user
        permissions"""
        expected = [
            (self.superuser, [
                'omics-pr-btn-project-roles',
                'omics-pr-btn-project-update',
                'omics-pr-btn-project-create',
                'omics-pr-btn-project-settings']),
            (self.as_owner.user, [
                'omics-pr-btn-project-roles',
                'omics-pr-btn-project-update',
                'omics-pr-btn-project-create',
                'omics-pr-btn-project-settings']),
            (self.as_delegate.user, [
                'omics-pr-btn-project-roles',
                'omics-pr-btn-project-update',
                'omics-pr-btn-project-settings']),
            (self.as_staff.user, [
                'omics-pr-btn-project-roles']),
            (self.as_contributor.user, [
                'omics-pr-btn-project-roles']),
            (self.as_guest.user, [
                'omics-pr-btn-project-roles'])]

        url = reverse(
            'project_detail', kwargs={'pk': self.project_top.pk})

        self.assert_element_set(expected, PROJECT_BUTTON_IDS, url)

    def test_project_buttons_category(self):
        """Test visibility of top level category buttons according to user
        permissions"""
        expected = [
            (self.superuser, [
                'omics-pr-btn-project-update',
                'omics-pr-btn-project-create']),
            (self.as_owner.user, [
                'omics-pr-btn-project-update',
                'omics-pr-btn-project-create'])]
        url = reverse(
            'project_detail', kwargs={'pk': self.category.pk})

        self.assert_element_set(expected, PROJECT_BUTTON_IDS, url)


class TestProjectRoles(TestUIBase):
    """Tests for the project roles page UI functionalities"""

    def test_list_buttons(self):
        """Test visibility of role list button group according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        expected_false = [
            self.as_contributor.user,
            self.as_guest.user]
        url = reverse('project_roles', kwargs={'pk': self.project.pk})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list', True)

        self.assert_element_exists(
            expected_false, url, 'omics-pr-btn-role-list', False)

    def test_role_list_invite_button(self):
        """Test visibility of role invite button according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        expected_false = [
            self.as_staff.user,
            self.as_contributor.user,
            self.as_guest.user]
        url = reverse('project_roles', kwargs={'pk': self.project.pk})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list-invite', True)

        self.assert_element_exists(
            expected_false, url, 'omics-pr-btn-role-list-invite', False)

    def test_role_list_add_button(self):
        """Test visibility of role invite button according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_staff.user]
        expected_false = [
            self.as_contributor.user,
            self.as_guest.user]
        url = reverse('project_roles', kwargs={'pk': self.project.pk})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list-create', True)

        self.assert_element_exists(
            expected_false, url, 'omics-pr-btn-role-list-create', False)

    def test_role_buttons(self):
        """Test visibility of role management buttons according to user
        permissions"""
        expected = [
            (self.superuser, 4),
            (self.as_owner.user, 4),
            (self.as_delegate.user, 3),
            (self.as_staff.user, 2),
            (self.as_contributor.user, 0),
            (self.as_guest.user, 0)]
        url = reverse('project_roles', kwargs={'pk': self.project.pk})
        self.assert_element_count(expected, url, 'omics-pr-btn-grp-role')


class TestProjectInviteList(TestUIBase, ProjectInviteMixin):
    """Tests for the project invite list page UI functionalities"""

    def test_list_buttons(self):
        """Test visibility of invite list button group according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        url = reverse('role_invites', kwargs={'project': self.project.pk})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list', True)

    def test_role_list_invite_button(self):
        """Test visibility of role invite button according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        url = reverse('role_invites', kwargs={'project': self.project.pk})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list-invite', True)

    def test_role_list_add_button(self):
        """Test visibility of role invite button according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        url = reverse('role_invites', kwargs={'project': self.project.pk})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list-create', True)

    def test_invite_buttons(self):
        """Test visibility of invite management buttons according to user
        permissions"""

        self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.as_owner.user,
            message='')

        expected = [
            (self.superuser, 1),
            (self.as_owner.user, 1),
            (self.as_delegate.user, 1)]
        url = reverse('role_invites', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-pr-btn-grp-invite')

# TODO: Uncomment once other apps are added
'''
class TestPlugins(TestUIBase):
    """Tests for app plugins in the UI"""

    # NOTE: Setting up the plugins is done during migration

    def test_plugin_buttons(self):
        """Test visibility of app plugin buttons"""
        expected = [(self.superuser, 4)]
        url = reverse('project_detail', kwargs={'pk': self.project.pk})
        self.assert_element_count(expected, url, 'pr_app_plugin_buttons')

    def test_plugin_cards(self):
        """Test visibility of app plugin cards"""
        expected = [(self.superuser, 4)]
        url = reverse('project_detail', kwargs={'pk': self.project.pk})
        self.assert_element_count(expected, url, 'pr_app_card')
'''
