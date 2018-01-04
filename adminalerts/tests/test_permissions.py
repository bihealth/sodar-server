"""Tests for permissions in the adminalerts app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import TestPermissionBase

from .test_models import AdminAlertMixin


class TestAdminAlertPermissions(TestPermissionBase, AdminAlertMixin):
    """Tests for AdminAlert views"""

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()

        self.regular_user = self.make_user('regular_user')

        # No user
        self.anonymous = None

        # Create alert
        self.alert = self._make_alert(
            message='alert',
            user=self.superuser,
            description='description',
            active=True)

    def test_alert_create(self):
        url = reverse('alert_create')
        good_users = [
            self.superuser]
        bad_users = [
            self.anonymous,
            self.regular_user]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_alert_update(self):
        url = reverse(
            'alert_update',
            kwargs={
                'pk': self.alert.pk})
        good_users = [
            self.superuser]
        bad_users = [
            self.anonymous,
            self.regular_user]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_alert_delete(self):
        url = reverse(
            'alert_delete',
            kwargs={
                'pk': self.alert.pk})
        good_users = [
            self.superuser]
        bad_users = [
            self.anonymous,
            self.regular_user]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_alert_list(self):
        url = reverse('alert_list')
        good_users = [
            self.superuser]
        bad_users = [
            self.anonymous,
            self.regular_user]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_alert_detail(self):
        url = reverse(
            'alert_detail',
            kwargs={
                'pk': self.alert.pk})
        good_users = [
            self.superuser,
            self.regular_user]
        bad_users = [
            self.anonymous]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)
