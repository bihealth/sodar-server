from django.conf import settings
from django.db import models
from django.utils import timezone

# Access Django user model
AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class AdminAlert(models.Model):
    """An un-dismissable alert from a superuser to site users. Not dependent on
    project. Will expire after a set time."""

    #: Alert message to be shown for users
    message = models.CharField(
        max_length=255,
        unique=False,
        help_text='Alert message to be shown for users')

    #: Superuser who has set the alert
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='alerts',
        help_text='Superuser who has set the alert')

    #: Full description (optional, will be shown on a separate page)
    description = models.TextField(
        unique=False,
        blank=True,
        null=True,
        help_text='Full description of alert '
                  '(optional, will be shown on a separate page)')

    #: Alert creation timestamp
    date_created = models.DateTimeField(
        auto_now_add=True,
        help_text='Alert creation timestamp')

    #: Alert expiration timestamp
    date_expire = models.DateTimeField(
        blank=False,
        null=False,
        help_text='Alert expiration timestamp')

    #: Alert status (for disabling the alert before expiration)
    active = models.BooleanField(
        default=True,
        help_text='Alert status (for disabling the alert before expiration)')

    def __str__(self):
        return '{}{}'.format(
            self.message,
            ' [ACTIVE]' if (
                self.active and self.date_expire > timezone.now()) else '')

    def __repr__(self):
        values = (self.message, self.user.username, self.active)
        return 'AdminAlert({})'.format(', '.join(repr(v) for v in values))

    def is_active(self):
        """Return True if alert is active and has not expired"""
        return True if (
            self.date_expire > timezone.now() and self.active) else False

    def is_expired(self):
        """Return True if alert has expired"""
        return True if self.date_expire < timezone.now() else False
