from datetime import timedelta

from django.core.management.base import BaseCommand
from django.template.defaultfilters import filesizeformat
from django.utils.timezone import localtime
from projectroles.plugins import get_backend_api

from landingzones.models import LandingZone


def get_inactive_zones(weeks=2):
    """Return list of landing zone modified old than n weeks."""
    return LandingZone.objects.filter(
        date_modified__lte=localtime() - timedelta(weeks=weeks)
    ).exclude(status__in=('DELETED', 'MOVED'))


def get_output(zones, irods_backend):
    """Return list of enriched inactive landing zones."""
    lines = []
    for zone in zones:
        path = irods_backend.get_path(zone)
        stats = irods_backend.get_object_stats(path)
        lines.append(
            ';'.join(
                [
                    str(zone.project.sodar_uuid),
                    zone.project.full_title,
                    zone.user.username,
                    path,
                    str(stats['file_count']),
                    filesizeformat(stats['total_size']).replace(u'\xa0', ' '),
                ]
            )
        )
    return lines


class Command(BaseCommand):
    """Command to find landingzones last modified more than two weeks ago."""

    help = 'Find landingzones last modified more than two weeks ago.'

    def handle(self, *args, **options):
        irods_backend = get_backend_api('omics_irods')
        zones = get_inactive_zones()
        output = get_output(zones, irods_backend)
        if output:
            self.stdout.write('\n'.join(output))
