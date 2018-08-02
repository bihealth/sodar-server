"""Tests for models in the adminalerts app"""

from django.forms.models import model_to_dict
from django.utils import timezone

from test_plus.test import TestCase

from ..models import AdminAlert


class AdminAlertMixin:
    """Helper mixin for AdminAlert creation"""

    @classmethod
    def _make_alert(
            cls, message, user, description, active=True, date_expire_days=1):
        """Make and save n AdminAlert"""
        values = {
            'message': message,
            'user': user,
            'description': description,
            'date_expire': timezone.now() + timezone.timedelta(
                days=date_expire_days),
            'active': active}
        alert = AdminAlert(**values)
        alert.save()
        return alert


class TestAdminAlert(TestCase, AdminAlertMixin):
    """Tests for AdminAlert model"""

    def setUp(self):

        # Create superuser
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True

        # Create alert
        self.alert = self._make_alert(
            message='alert',
            user=self.superuser,
            description='description',
            active=True)

    def test_initialization(self):
        expected = {
            'id': self.alert.pk,
            'message': 'alert',
            'user': self.superuser.pk,
            # 'description': 'description',
            'date_expire': self.alert.date_expire,
            'active': True,
            'omics_uuid': self.alert.omics_uuid}
        model_dict = model_to_dict(self.alert)
        # HACK: Can't compare markupfields like this. Better solution?
        model_dict.pop('description', None)
        self.assertEqual(model_dict, expected)

    def test__str__(self):
        expected = 'alert [ACTIVE]'
        self.assertEqual(str(self.alert), expected)

    def test__repr__(self):
        expected = "AdminAlert('alert', 'superuser', True)"
        self.assertEqual(repr(self.alert), expected)
