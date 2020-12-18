from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import localtime

from landingzones.models import LandingZone


def get_inactive_zones(weeks=2):
    """Return list of landing zone modified old than n weeks."""
    return LandingZone.objects.filter(
        date_modified__lte=localtime() - timedelta(weeks=weeks)
    ).exclude(status__in=('DELETED', 'MOVED'))


def get_zone_str(zone):
    """Return LandingZone string output for management command"""
    return '{} ({}): {}/{}'.format(
        zone.project.sodar_uuid,
        zone.project.title,
        zone.user.username,
        zone.title,
    )


class Command(BaseCommand):
    """Command to find landingzones last modified more than two weeks ago."""

    help = 'Find landingzones last modified more than two weeks ago.'

    def handle(self, *args, **options):
        zones = get_inactive_zones()
        for zone in zones:
            self.stdout.write(get_zone_str(zone))
