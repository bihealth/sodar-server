"""Busyzones management command"""

from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger

from landingzones.models import LandingZone, STATUS_BUSY


logger = ManagementCommandLogger(__name__)


class Command(BaseCommand):
    """Command to return list of busy landing zones"""

    help = 'Returns list of currently busy landing zones'

    def handle(self, *args, **options):
        zones = LandingZone.objects.filter(status__in=STATUS_BUSY)
        output = []
        for zone in zones:
            logger.info(
                ';'.join(
                    [
                        str(zone.project.sodar_uuid),
                        zone.project.full_title,
                        zone.user.username,
                        zone.title,
                        zone.status,
                        str(zone.sodar_uuid),
                    ]
                )
            )
        if output:
            logger.info(output)
