"""Resetzone management command"""

import sys

from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger

from landingzones.models import LandingZone
from landingzones.views import ZoneResetMixin


logger = ManagementCommandLogger(__name__)


class Command(ZoneResetMixin, BaseCommand):
    """Command to return list of busy landing zones"""

    help = 'Reset landing zone state'

    def add_arguments(self, parser):
        parser.add_argument(
            '-z',
            '--zone',
            dest='zone',
            type=str,
            required=True,
            help='UUID of landing zone to reset',
        )

    def handle(self, *args, **options):
        zone_uuid = options.get('zone')
        zone = LandingZone.objects.filter(sodar_uuid=zone_uuid).first()
        if not zone:
            logger.error(f'Zone not found with UUID: {zone_uuid}')
            sys.exit(1)
        try:
            self.reset_zone(zone)
        except Exception as ex:
            logger.error(f'Exception in reset_zone(): {ex}')
            sys.exit(1)
