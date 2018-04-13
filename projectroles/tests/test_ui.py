"""UI tests for the projectroles app"""

import socket
from urllib.parse import urlencode

from django.contrib import auth
from django.test import LiveServerTestCase
from django.urls import reverse

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.plugins import get_active_plugins
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin,\
    ProjectInviteMixin


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


# Local constants
PROJECT_LINK_IDS = [
    'omics-pr-link-project-roles',
    'omics-pr-link-project-update',
    'omics-pr-link-project-create',
    'omics-pr-link-project-star']


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
        options.add_argument('no-sandbox')  # For Gitlab-CI compatibility
        self.selenium = webdriver.Chrome(chrome_options=options)

        # Prevent ElementNotVisibleException
        self.selenium.set_window_size(1400, 1000)

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init users
        self.superuser = self._make_user('admin', True)
        self.user_owner = self._make_user('user_owner', False)
        self.user_delegate = self._make_user('user_delegate', False)
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

        # Init role assignments

        # Category
        self._make_assignment(
            self.category, self.user_owner, self.role_owner)

        # Sub level project
        self.as_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner)
        self.as_delegate = self._make_assignment(
            self.project, self.user_delegate, self.role_delegate)
        self.as_contributor = self._make_assignment(
            self.project, self.user_contributor, self.role_contributor)
        self.as_guest = self._make_assignment(
            self.project, self.user_guest, self.role_guest)

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

        ########################
        # Logout (if logged in)
        ########################

        try:
            user_button = self.selenium.find_element_by_id(
                'omics-navbar-user-dropdown')

            user_button.click()

            # Wait for element to be visible
            WebDriverWait(self.selenium, self.wait_time).until(
                ec.presence_of_element_located(
                    (By.ID, 'omics-navbar-link-logout')))

            try:
                signout_button = self.selenium.find_element_by_id(
                    'omics-navbar-link-logout')
                signout_button.click()

                # Wait for redirect
                WebDriverWait(self.selenium, self.wait_time).until(
                    ec.presence_of_element_located(
                        (By.ID, 'omics-form-signin')))

            except NoSuchElementException:
                pass

        except NoSuchElementException:
            pass

        ########
        # Login
        ########

        self.selenium.get(self.build_selenium_url(url))

        # Submit user data into form
        field_user = self.selenium.find_element_by_id('omics-signin-username')
        # field_user.send_keys(user.username)
        field_user.send_keys(user.username)

        field_pass = self.selenium.find_element_by_id('omics-signin-password')
        field_pass.send_keys('password')

        self.selenium.find_element_by_xpath(
            '//button[contains(., "Sign In")]').click()

        # Wait for redirect
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located(
                (By.ID, 'omics-navbar-user-dropdown')))

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

    def assert_element_count(
            self, expected, url, search_string, attribute='id'):
        """
        Assert count of elements containing specified id or class based on
        the logged user.
        :param expected: List of tuples with user (string), count (int)
        :param url: URL to test (string)
        :param search_string: ID substring of element (string)
        :param attribute: Attribute to search for (string, default=id)
        """
        for e in expected:
            expected_user = e[0]    # Just to clarify code
            expected_count = e[1]

            self.login_and_redirect(expected_user, url)

            if expected_count > 0:
                self.assertEqual(
                    len(self.selenium.find_elements_by_xpath(
                        '//*[contains(@{}, "{}")]'.format(
                            attribute, search_string))),
                    expected_count,
                    'expected_user={}'.format(expected_user))

            else:
                with self.assertRaises(NoSuchElementException):
                    self.selenium.find_element_by_xpath(
                        '//*[contains(@{}, "{}")]'.format(
                            attribute, search_string))

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

    def assert_element_active(self, user, element_id, all_elements, url):
        """
        Assert the "active" status of an element based on logged user as well
        as unset status of other elements.
        :param user: User for logging in
        :param element_id: ID of element to test (string)
        :param all_elements: All possible elements in the set (list of strings)
        :param url: URL to test (string)
        """
        self.login_and_redirect(user, url)

        # Wait for element to be present (sometimes this is too slow)
        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, element_id)))

        element = self.selenium.find_element_by_id(element_id)

        self.assertIsNotNone(element)
        self.assertIn('active', element.get_attribute('class'))

        not_expected = [e for e in all_elements if e != element_id]
        # print(not_expected)     # DEBUG

        for n in not_expected:
            element = self.selenium.find_element_by_id(n)
            self.assertIsNotNone(element)
            self.assertNotIn('active', element.get_attribute('class'))


class TestBaseTemplate(TestUIBase):
    """Tests for the base project template"""

    def test_admin_link(self):
        """Test admin site link visibility according to user permissions"""
        expected_true = [
            self.superuser]

        expected_false = [
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user,
            self.user_no_roles]

        url = reverse('home')

        self.assert_element_exists(
            expected_true, url, 'omics-navbar-admin-link', True)

        self.assert_element_exists(
            expected_false, url, 'omics-navbar-admin-link', False)


class TestProjectList(TestUIBase):
    """Tests for the project list UI functionalities"""

    def test_link_create_toplevel(self):
        """Test project creation link visibility according to user
        permissions"""
        expected_true = [
            self.superuser]

        expected_false = [
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user]

        url = reverse('home')

        self.assert_element_exists(
            expected_true, url, 'omics-pr-home-link-create', True)

        self.assert_element_exists(
            expected_false, url, 'omics-pr-home-link-create', False)


class TestProjectDetail(TestUIBase):
    """Tests for the project detail page UI functionalities"""

    def test_project_links(self):
        """Test visibility of project links according to user
        permissions"""
        expected = [
            (self.superuser, [
                'omics-pr-link-project-roles',
                'omics-pr-link-project-update',
                'omics-pr-link-project-star']),
            (self.as_owner.user, [
                'omics-pr-link-project-roles',
                'omics-pr-link-project-update',
                'omics-pr-link-project-star']),
            (self.as_delegate.user, [
                'omics-pr-link-project-roles',
                'omics-pr-link-project-update',
                'omics-pr-link-project-star']),
            (self.as_contributor.user, [
                'omics-pr-link-project-roles',
                'omics-pr-link-project-star']),
            (self.as_guest.user, [
                'omics-pr-link-project-roles',
                'omics-pr-link-project-star'])]

        url = reverse(
            'projectroles:detail', kwargs={'project': self.project.omics_uuid})

        self.assert_element_set(expected, PROJECT_LINK_IDS, url)

    def test_project_links_category(self):
        """Test visibility of top level category links according to user
        permissions"""

        # Add user with rights only for the subproject
        sub_user = self._make_user('sub_user', False)
        self._make_assignment(
            self.project, sub_user, self.role_contributor)

        expected = [
            (self.superuser, [
                'omics-pr-link-project-update',
                'omics-pr-link-project-create',
                'omics-pr-link-project-star']),
            (self.as_owner.user, [
                'omics-pr-link-project-update',
                'omics-pr-link-project-create',
                'omics-pr-link-project-star']),
            (sub_user, [
                'omics-pr-link-project-star'])]
        url = reverse(
            'projectroles:detail',
            kwargs={'project': self.category.omics_uuid})

        self.assert_element_set(expected, PROJECT_LINK_IDS, url)


class TestProjectRoles(TestUIBase):
    """Tests for the project roles page UI functionalities"""

    def test_list_buttons(self):
        """Test visibility of role list button group according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        expected_false = [
            self.as_contributor.user,
            self.as_guest.user]
        url = reverse(
            'projectroles:roles',
            kwargs={'project': self.project.omics_uuid})

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
            self.as_contributor.user,
            self.as_guest.user]
        url = reverse(
            'projectroles:roles',
            kwargs={'project': self.project.omics_uuid})

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
            self.as_delegate.user]
        expected_false = [
            self.as_contributor.user,
            self.as_guest.user]
        url = reverse(
            'projectroles:roles',
            kwargs={'project': self.project.omics_uuid})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list-create', True)

        self.assert_element_exists(
            expected_false, url, 'omics-pr-btn-role-list-create', False)

    def test_role_buttons(self):
        """Test visibility of role management buttons according to user
        permissions"""
        expected = [
            (self.superuser, 3),
            (self.as_owner.user, 3),
            (self.as_delegate.user, 2),
            (self.as_contributor.user, 0),
            (self.as_guest.user, 0)]
        url = reverse(
            'projectroles:roles',
            kwargs={'project': self.project.omics_uuid})
        self.assert_element_count(expected, url, 'omics-pr-btn-grp-role')

    def test_role_preview(self):
        """Test visibility of role preview popup"""
        url = reverse(
            'projectroles:role_create',
            kwargs={'project': self.project.omics_uuid})
        self.login_and_redirect(self.as_owner.user, url)

        button = self.selenium.find_element_by_id('omics-pr-email-preview-link')
        button.click()

        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'omics-popup-content')))

        self.assertIsNotNone(
            self.selenium.find_element_by_id('omics-popup-content'))

    def test_invite_preview(self):
        """Test visibility of invite preview popup"""
        url = reverse(
            'projectroles:invite_create',
            kwargs={'project': self.project.omics_uuid})
        self.login_and_redirect(self.as_owner.user, url)

        button = self.selenium.find_element_by_id(
            'omics-pr-invite-preview-link')
        button.click()

        WebDriverWait(self.selenium, self.wait_time).until(
            ec.presence_of_element_located((By.ID, 'omics-popup-content')))

        self.assertIsNotNone(
            self.selenium.find_element_by_id('omics-popup-content'))


class TestProjectInviteList(TestUIBase, ProjectInviteMixin):
    """Tests for the project invite list page UI functionalities"""

    def test_list_buttons(self):
        """Test visibility of invite list button group according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        url = reverse(
            'projectroles:invites',
            kwargs={'project': self.project.omics_uuid})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list', True)

    def test_role_list_invite_button(self):
        """Test visibility of role invite button according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        url = reverse(
            'projectroles:invites',
            kwargs={'project': self.project.omics_uuid})

        self.assert_element_exists(
            expected_true, url, 'omics-pr-btn-role-list-invite', True)

    def test_role_list_add_button(self):
        """Test visibility of role invite button according to user
        permissions"""
        expected_true = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        url = reverse(
            'projectroles:invites',
            kwargs={'project': self.project.omics_uuid})

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
        url = reverse(
            'projectroles:invites',
            kwargs={'project': self.project.omics_uuid})
        self.assert_element_count(expected, url, 'omics-pr-btn-grp-invite')


class TestPlugins(TestUIBase):
    """Tests for app plugins in the UI"""

    # NOTE: Setting up the plugins is done during migration
    def setUp(self):
        super(TestPlugins, self).setUp()
        self.plugin_count = len(get_active_plugins())

    def test_plugin_links(self):
        """Test visibility of app plugin links"""
        expected = [(self.superuser, self.plugin_count)]
        url = reverse(
            'projectroles:detail',
            kwargs={'project': self.project.omics_uuid})
        self.assert_element_count(expected, url, 'omics-pr-link-app-plugin')

    def test_plugin_cards(self):
        """Test visibility of app plugin cards"""
        expected = [(self.superuser, self.plugin_count)]
        url = reverse(
            'projectroles:detail',
            kwargs={'project': self.project.omics_uuid})
        self.assert_element_count(expected, url, 'omics-pr-app-item')


class TestProjectSidebar(TestUIBase, ProjectInviteMixin):
    """Tests for the project sidebar"""

    def setUp(self):
        super(TestProjectSidebar, self).setUp()

        self.sidebar_ids = [
            'omics-pr-nav-project-detail',
            'omics-pr-nav-project-roles',
            'omics-pr-nav-project-update']

        # Add app plugin navs
        for p in get_active_plugins():
            self.sidebar_ids.append('omics-pr-nav-app-plugin-{}'.format(p.name))

    def test_render_detail(self):
        """Test visibility of sidebar in the project_detail view"""
        url = reverse(
            'projectroles:detail',
            kwargs={'project': self.project.omics_uuid})

        self.assert_element_exists(
            [self.superuser], url, 'omics-pr-sidebar', True)

    def test_render_home(self):
        """Test visibility of sidebar in the home view"""
        url = reverse('home')

        self.assert_element_exists(
            [self.superuser], url, 'omics-pr-sidebar', True)

    def test_app_links(self):
        """Test visibility of app links"""
        url = reverse(
            'projectroles:detail',
            kwargs={'project': self.project.omics_uuid})
        expected = [(self.superuser, len(get_active_plugins()))]

        self.assert_element_count(
            expected, url, 'omics-pr-nav-app-plugin')

    def test_link_active_detail(self):
        """Test active status of link on the project_detail page"""
        url = reverse(
            'projectroles:detail',
            kwargs={'project': self.project.omics_uuid})

        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-detail',
            self.sidebar_ids, url)

    def test_link_active_role_list(self):
        """Test active status of link on the project roles page"""
        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:roles',
                kwargs={'project': self.project.omics_uuid}))

    def test_link_active_role_create(self):
        """Test active status of link on the role creation page"""
        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:role_create',
                kwargs={'project': self.project.omics_uuid}))

    def test_link_active_role_update(self):
        """Test active status of link on the role update page"""
        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:role_update',
                kwargs={'roleassignment': self.as_contributor.omics_uuid}))

    def test_link_active_role_delete(self):
        """Test active status of link on the role deletion page"""
        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:role_delete',
                kwargs={'roleassignment': self.as_contributor.omics_uuid}))

    def test_link_active_role_invites(self):
        """Test active status of link on the invites page"""
        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:invites',
                kwargs={'project': self.project.omics_uuid}))

    def test_link_active_role_invite_create(self):
        """Test active status of link on the invite create page"""
        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:invite_create',
                kwargs={'project': self.project.omics_uuid}))

    def test_link_active_role_invite_resend(self):
        """Test active status of link on the invite resend page"""
        invite = self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.as_owner.user,
            message='')

        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:invite_resend',
                kwargs={'projectinvite': invite.omics_uuid}))

    def test_link_active_role_invite_revoke(self):
        """Test active status of link on the invite revoke page"""
        invite = self._make_invite(
            email='test@example.com',
            project=self.project,
            role=self.role_contributor,
            issuer=self.as_owner.user,
            message='')

        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-roles', self.sidebar_ids,
            reverse(
                'projectroles:invite_revoke',
                kwargs={'projectinvite': invite.omics_uuid}))

    def test_link_active_update(self):
        """Test active status of link on the project_update page"""
        url = reverse(
            'projectroles:update',
            kwargs={'project': self.project.omics_uuid})

        self.assert_element_active(
            self.superuser, 'omics-pr-nav-project-update',
            self.sidebar_ids, url)


class TestProjectSearch(TestUIBase):
    """Tests for the project search UI functionalities"""

    def test_search_results(self):
        """Test project search items visibility according to user permissions"""
        expected = [
            (self.superuser, 1),
            (self.as_owner.user, 1),
            (self.as_delegate.user, 1),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 1),
            (self.user_no_roles, 0)]
        url = reverse('projectroles:search') + '?' + urlencode({'s': 'test'})
        self.assert_element_count(expected, url, 'omics-pr-project-search-item')

    def test_search_type_project(self):
        """Test project search items visibility with 'project' type"""
        expected = [
            (self.superuser, 1),
            (self.as_owner.user, 1),
            (self.as_delegate.user, 1),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 1),
            (self.user_no_roles, 0)]
        url = reverse('projectroles:search') + '?' + urlencode(
            {'s': 'test type:project'})
        self.assert_element_count(expected, url, 'omics-pr-project-search-item')

    def test_search_type_nonexisting(self):
        """Test project search items visibility with a nonexisting type"""
        expected = [
            (self.superuser, 0),
            (self.as_owner.user, 0),
            (self.as_delegate.user, 0),
            (self.as_contributor.user, 0),
            (self.as_guest.user, 0),
            (self.user_no_roles, 0)]
        url = reverse('projectroles:search') + '?' + urlencode(
            {'s': 'test type:Jaix1au'})
        self.assert_element_count(expected, url, 'omics-pr-project-search-item')
