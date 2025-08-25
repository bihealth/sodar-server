"""Inactivezones management command"""

from datetime import timedelta
from irods.session import iRODSSession
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.template.defaultfilters import filesizeformat
from django.utils.timezone import localtime

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.plugins import PluginAPI

from landingzones.constants import ZONE_STATUS_MOVED, ZONE_STATUS_DELETED
from landingzones.models import LandingZone


logger = ManagementCommandLogger(__name__)
plugin_api = PluginAPI()


def get_inactive_zones(weeks: int = 2) -> QuerySet[LandingZone]:
    """
    Return landing zones last modified over nNweeks ago.

    :param weeks: Amount of weeks (integer, default=2)
    :return: QuerySet of LandingZone objects
    """
    return LandingZone.objects.filter(
        date_modified__lte=localtime() - timedelta(weeks=weeks)
    ).exclude(status__in=(ZONE_STATUS_MOVED, ZONE_STATUS_DELETED))


def get_output(
    zones: QuerySet[LandingZone], irods_backend: Any, irods: iRODSSession
) -> list[str]:
    """
    Return list of inactive landing zone details.

    :param zones: QuerySet of LandingZone objects
    :param irods_backend: IrodsAPI object
    :return: List of strings
    """
    lines = []
    for zone in zones:
        path = irods_backend.get_path(zone)
        if not irods.collections.exists(path):
            logger.error(
                f'No iRODS collection found for zone '
                f'"{zone.user.username}/{zone.title}" ({zone.sodar_uuid})'
            )
            continue
        try:
            stats = irods_backend.get_stats(irods, path)
            lines.append(
                ';'.join(
                    [
                        str(zone.project.sodar_uuid),
                        zone.project.full_title,
                        zone.user.username,
                        path,
                        str(stats['file_count']),
                        filesizeformat(stats['total_size']).replace(
                            u'\xa0', ' '
                        ),
                    ]
                )
            )
        except Exception as ex:
            logger.error(
                f'Exception in retrieving stats for zone '
                f'"{zone.user.username}/{zone.title}" ({zone.sodar_uuid}): {ex}'
            )
    return lines


class Command(BaseCommand):
    """Command to find landing zones last modified more than two weeks ago"""

    help = 'Returns list of landing zones last modified over two weeks ago'

    def handle(self, *args, **options):
        irods_backend = plugin_api.get_backend_api('omics_irods')
        zones = get_inactive_zones()
        with irods_backend.get_session() as irods:
            output = get_output(zones, irods_backend, irods)
        for o in output:
            logger.info(o)
