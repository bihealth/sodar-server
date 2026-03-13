"""Taskflow task tests for the landingzones app"""

# NOTE: These do not NOT require running with taskflow and iRODS

from django.core import mail
from django.test import override_settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI

# Appalerts dependency
from appalerts.models import AppAlert

import landingzones.constants as lc
from landingzones.tasks_taskflow import SetLandingZoneStatusTask
from landingzones.tests.test_views import ViewTestBase


app_settings = AppSettingAPI()


# Local constants
APP_NAME = 'landingzones'
TASK_NAME = 'set landing zone status'


class TestSetLandingZoneStatusTask(ViewTestBase):
    """Tests for SetLandingZoneStatusTask"""

    def _get_task(self, force_fail: bool = False) -> SetLandingZoneStatusTask:
        """Initialize and return task"""
        return SetLandingZoneStatusTask(TASK_NAME, self.project, force_fail)

    def _assert_owner_alert(self, count: int, name: str = 'zone_move'):
        """Assert owner alert count"""
        self.assertEqual(
            AppAlert.objects.filter(
                app_plugin__name=APP_NAME,
                alert_name=name,
                user=self.zone.user,
                project=self.project,
            ).count(),
            count,
        )

    def _assert_member_alerts(self, count: int):
        """Assert member alert count"""
        self.assertEqual(
            AppAlert.objects.filter(
                app_plugin__name=APP_NAME,
                alert_name='zone_move_member',
                project=self.project,
            ).count(),
            count,
        )

    def _setup_member(self):
        """Set up member user"""
        self.user_contributor = self.make_user('user_contributor')
        self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )

    def setUp(self):
        super().setUp()
        self.task_kw = {
            'landing_zone': self.zone,
            'flow_name': 'landing_zone_move',
            'status': lc.ZONE_STATUS_MOVED,
            'status_info': lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_MOVED],
            'extra_data': {'file_count': 1},
        }

    def test_execute(self):
        """Test SetLandingZoneStatusTask execute()"""
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self.assertEqual(
            self.zone.status_info,
            lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_ACTIVE],
        )
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)

        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()

        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self.assertEqual(
            self.zone.status_info,
            lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_MOVED],
        )
        self._assert_owner_alert(1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').first().level,
            'SUCCESS',
        )
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Landing zone moved', mail.outbox[0].subject)

    def test_execute_member_alert(self):
        """Test execute() with member alert and email"""
        # Set up member user
        self._setup_member()

        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)

        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()

        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self.assertEqual(
            self.zone.status_info,
            lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_MOVED],
        )
        self._assert_owner_alert(1)
        self._assert_member_alerts(1)  # We should have member alert now
        self.assertEqual(len(mail.outbox), 2)  # Email for both owner and member

    @override_settings(PROJECTROLES_SEND_EMAIL=False)
    def test_execute_disable_email(self):
        """Test execute() with email disabled"""
        self._setup_member()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self._assert_owner_alert(1)
        self._assert_member_alerts(1)  # Alerts should still be raised
        self.assertEqual(len(mail.outbox), 0)

    def test_execute_disable_project_notify(self):
        """Test execute() with project member notify disabled"""
        app_settings.set(
            APP_NAME, 'member_notify_move', False, project=self.project
        )
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self._assert_owner_alert(1)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(), [self.user_owner.email])

    def test_execute_disable_owner_alert_notify(self):
        """Test execute() with owner alert notify disabled"""
        app_settings.set(
            APP_NAME,
            'notify_alert_zone_status',
            False,
            user=self.zone.user,
        )
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self._assert_owner_alert(0)  # No alert for owner
        self._assert_member_alerts(0)

    def test_execute_disable_owner_email_notify(self):
        """Test execute() with owner email notify disabled"""
        app_settings.set(
            APP_NAME,
            'notify_email_zone_status',
            False,
            user=self.zone.user,
        )
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self._assert_owner_alert(1)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)

    def test_execute_disable_member_alert_notify(self):
        """Test execute() with member alert notify disabled"""
        self._setup_member()
        app_settings.set(
            APP_NAME,
            'notify_alert_zone_status',
            False,
            user=self.user_contributor,
        )
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self._assert_owner_alert(1)
        self._assert_member_alerts(0)  # No alerts for member

    def test_execute_disable_member_email_notify(self):
        """Test execute() with member email notify disabled"""
        self._setup_member()
        app_settings.set(
            APP_NAME,
            'notify_email_zone_status',
            False,
            user=self.user_contributor,
        )
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        self._assert_owner_alert(1)
        self._assert_member_alerts(1)
        self.assertEqual(len(mail.outbox), 1)  # Email only for owner
        self.assertEqual(mail.outbox[0].recipients(), [self.user_owner.email])

    def test_execute_moved_no_files(self):
        """Test execute() with a busy status"""
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self.task_kw['extra_data'] = {'file_count': 0}
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVED)
        # No alerts or emails should be set
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)

    def test_execute_busy(self):
        """Test execute() with busy status"""
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self.task_kw['status'] = lc.ZONE_STATUS_MOVING
        self.task_kw['status_info'] = lc.DEFAULT_STATUS_INFO[
            lc.ZONE_STATUS_MOVING
        ]
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_MOVING)
        self.assertEqual(
            self.zone.status_info,
            lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_MOVING],
        )
        # No alerts or emails should be set
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)

    def test_execute_failed(self):
        """Test execute() with FAILED status"""
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self.task_kw['status'] = lc.ZONE_STATUS_FAILED
        self.task_kw['status_info'] = lc.DEFAULT_STATUS_INFO[
            lc.ZONE_STATUS_FAILED
        ]
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_FAILED)
        self.assertEqual(
            self.zone.status_info,
            lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_FAILED],
        )
        self._assert_owner_alert(1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').first().level,
            'DANGER',
        )
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 1)

    def test_execute_validate(self):
        """Test execute() in validate mode"""
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_ACTIVE)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self.task_kw['status_info'] = [
            lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_ACTIVE]
        ]
        self.task_kw['extra_data'] = {'validate_only': True}
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self.task_kw['status_info'] = [
            lc.DEFAULT_STATUS_INFO[lc.ZONE_STATUS_ACTIVE]
        ]
        self._assert_owner_alert(0)
        self._assert_owner_alert(1, name='zone_validate')
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent on validate

    def test_execute_reset(self):
        """Test execute() for zone reset"""
        self.zone.set_status('VALIDATING')
        self.assertEqual(self.zone.status, lc.ZONE_STATUS_VALIDATING)
        self._assert_owner_alert(0)
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)
        self.task_kw['flow_name'] = 'landing_zone_reset'
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self.task_kw['status_info'] = [lc.STATUS_INFO_ADMIN_RESET]
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self.task_kw['status_info'] = [lc.STATUS_INFO_ADMIN_RESET]
        self._assert_owner_alert(0)
        self._assert_owner_alert(1, name='zone_reset')
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_reset').first().level,
            'INFO',
        )
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 1)  # Reset sents email to owner
        self.assertIn('Landing zone reset', mail.outbox[0].subject)

    def test_execute_reset_disable_owner_alert_notify(self):
        """Test execute() for reset with owner email notify disabled"""
        app_settings.set(
            APP_NAME,
            'notify_alert_zone_status',
            False,
            user=self.zone.user,
        )
        self.zone.set_status('VALIDATING')
        self.task_kw['flow_name'] = 'landing_zone_reset'
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self._assert_owner_alert(0, name='zone_reset')  # No owner alert
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 1)

    def test_execute_reset_disable_owner_email_notify(self):
        """Test execute() for reset with owner email notify disabled"""
        app_settings.set(
            APP_NAME,
            'notify_email_zone_status',
            False,
            user=self.zone.user,
        )
        self.zone.set_status('VALIDATING')
        self.task_kw['flow_name'] = 'landing_zone_reset'
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self._get_task().execute(**self.task_kw)
        self.zone.refresh_from_db()
        self.task_kw['status'] = lc.ZONE_STATUS_ACTIVE
        self._assert_owner_alert(1, name='zone_reset')  # Alert should be sent
        self._assert_member_alerts(0)
        self.assertEqual(len(mail.outbox), 0)  # No email
