"""Tests for views in the adminalerts app"""

from django.urls import reverse
from django.utils import timezone

from test_plus.test import TestCase

from ..models import AdminAlert
from .test_models import AdminAlertMixin


class TestViewsBase(TestCase, AdminAlertMixin):
    """Base class for view testing"""

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

        self.expiry_str = (timezone.now() + timezone.timedelta(
                days=1)).strftime('%Y-%m-%d')


class TestAdminAlertListView(TestViewsBase):
    """Tests for the alert list view"""

    def test_render(self):
        """Test rendering of the alert list view"""
        with self.login(self.superuser):
            response = self.client.get(reverse('adminalerts:list'))
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context['object_list'])
            self.assertEqual(
                response.context['object_list'][0].pk, self.alert.pk)


class TestAdminAlertDetailView(TestViewsBase):
    """Tests for the alert detail view"""

    def test_render(self):
        """Test rendering of the alert detail view"""
        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'adminalerts:detail',
                    kwargs={'uuid': self.alert.omics_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['object'], self.alert)


class TestAdminAlertCreateView(TestViewsBase):
    """Tests for the alert creation view"""

    def test_render(self):
        """Test rendering of the alert creation view"""
        with self.login(self.superuser):
            response = self.client.get(reverse('adminalerts:create'))
            self.assertEqual(response.status_code, 200)

    def test_create(self):
        """Test creating an admin alert"""

        # Assert precondition
        self.assertEqual(AdminAlert.objects.all().count(), 1)

        post_data = {
            'message': 'new alert',
            'user': self.superuser.pk,
            'description': 'description',
            'date_expire': self.expiry_str,
            'active': 1}

        with self.login(self.superuser):
            response = self.client.post(
                reverse('adminalerts:create'), post_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('adminalerts:list'))

        # Assert postcondition
        self.assertEqual(AdminAlert.objects.all().count(), 2)

    def test_create_expired(self):
        """Test creating an admin alert with and old date_expiry (should fail)"""

        # Assert precondition
        self.assertEqual(AdminAlert.objects.all().count(), 1)

        expiry_fail = (timezone.now() + timezone.timedelta(
            days=-1)).strftime('%Y-%m-%d')

        post_data = {
            'message': 'new alert',
            'user': self.superuser.pk,
            'description': 'description',
            'date_expire': expiry_fail,
            'active': 1}

        with self.login(self.superuser):
            response = self.client.post(
                reverse('adminalerts:create'), post_data)
            self.assertEqual(response.status_code, 200)

        # Assert postcondition
        self.assertEqual(AdminAlert.objects.all().count(), 1)


class TestAdminAlertUpdateView(TestViewsBase):
    """Tests for the alert update view"""

    def test_render(self):
        """Test rendering of the alert update view"""
        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'adminalerts:update',
                    kwargs={'uuid': self.alert.omics_uuid}))
            self.assertEqual(response.status_code, 200)

    def test_update(self):
        """Test updating an admin alert"""

        # Assert precondition
        self.assertEqual(AdminAlert.objects.all().count(), 1)

        post_data = {
            'message': 'updated alert',
            'user': self.superuser.pk,
            'description': 'updated description',
            'date_expire': self.expiry_str,
            'active': ''}

        with self.login(self.superuser):
            response = self.client.post(
                reverse(
                    'adminalerts:update',
                    kwargs={'uuid': self.alert.omics_uuid}),
                post_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('adminalerts:list'))

        # Assert postconditions
        self.assertEqual(AdminAlert.objects.all().count(), 1)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.message, 'updated alert')
        self.assertEqual(self.alert.description.raw, 'updated description')
        self.assertEqual(self.alert.active, False)


class TestAdminAlertDeleteView(TestViewsBase):
    """Tests for the alert deletion view"""

    def test_render(self):
        """Test rendering of the alert deletion view"""
        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'adminalerts:delete',
                    kwargs={'uuid': self.alert.omics_uuid}))
            self.assertEqual(response.status_code, 200)

    def test_delete(self):
        """Test deleting an admin alert"""

        # Assert precondition
        self.assertEqual(AdminAlert.objects.all().count(), 1)

        with self.login(self.superuser):
            response = self.client.post(
                reverse(
                    'adminalerts:delete',
                    kwargs={'uuid': self.alert.omics_uuid}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('adminalerts:list'))

        # Assert postconditions
        self.assertEqual(AdminAlert.objects.all().count(), 0)
