"""UI tests for the adminalerts app"""

from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.tests.test_ui import TestUIBase

from .test_models import AdminAlertMixin


class TestAlertUIBase(TestUIBase, AdminAlertMixin):

    def setUp(self):
        super(TestAlertUIBase, self).setUp()
        # Create users
        self.superuser = self._make_user('superuser', True)
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()

        self.regular_user = self._make_user('regular_user', False)

        # Create alert
        self.alert = self._make_alert(
            message='alert',
            user=self.superuser,
            description='description',
            active=True)


class TestAlertMessage(TestAlertUIBase):
    """Tests for the admin alert message"""

    def test_message(self):
        """Test visibility of alert message in home view"""
        expected = [
            (self.superuser, 1),
            (self.regular_user, 1)]
        url = reverse('home')

        self.assert_element_count(
            expected, url, 'omics-alert-top', 'class')

    def test_message_inactive(self):
        """Test visibility of an inactive alert message"""
        self.alert.active = 0
        self.alert.save()

        expected = [
            (self.superuser, 0),
            (self.regular_user, 0)]
        url = reverse('home')

        self.assert_element_count(
            expected, url, 'omics-alert-top', 'class')

    def test_message_expired(self):
        """Test visibility of an expired alert message"""
        self.alert.date_expire = timezone.now() - timezone.timedelta(days=1)
        self.alert.save()

        expected = [
            (self.superuser, 0),
            (self.regular_user, 0)]
        url = reverse('home')

        self.assert_element_count(
            expected, url, 'omics-alert-top', 'class')


class TestListView(TestAlertUIBase):
    """Tests for the admin alert list view"""

    def test_list_items(self):
        """Test existence of items in list"""
        expected = [
            (self.superuser, 1)]
        url = reverse('alert_list')

        self.assert_element_count(
            expected, url, 'omics-aa-alert-item', 'id')

    def test_list_buttons(self):
        """Test existence of buttons in list"""
        expected = [
            (self.superuser, 1)]
        url = reverse('alert_list')

        self.assert_element_count(
            expected, url, 'omics-aa-alert-buttons', 'id')
