"""Setzonepaths management command"""

import sys

from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.plugins import PluginAPI

from landingzones.constants import STATUS_FINISHED
from landingzones.models import LandingZone


logger = ManagementCommandLogger(__name__)
plugin_api = PluginAPI()


class Command(BaseCommand):
    """
    Command for setting missing irods_path field values for existing
    active landing zones.
    """

    help = 'Set missing iRODS paths for active landing zones'

    def add_arguments(self, parser):
        parser.add_argument(
            '-c',
            '--check',
            action='store_true',
            help='Log paths to be updated with no database changes',
        )

    def handle(self, *args, **options):
        irods_backend = plugin_api.get_backend_api('omics_irods')
        if not irods_backend:
            logger.error('iRODS backend not enabled')
            sys.exit(1)
        check = options.get('check')

        zones = LandingZone.objects.exclude(
            status__in=STATUS_FINISHED
        ).order_by('project__full_title', 'pk')
        log_pl = 's' if zones.count() != 1 else ''
        logger.debug(f'{zones.count()} active zone{log_pl} found')
        ok_count = 0
        for zone in zones:
            if zone.irods_path:
                continue  # Skip zones with existing names
            try:
                path = irods_backend.get_path(zone)
                logger.info(
                    f'{zone.project.get_log_title()}: {zone.title}: {path}'
                )
                if not check:
                    zone.irods_path = path
                    zone.save()
                ok_count += 1
            except Exception as ex:
                logger.error(
                    f'Exception for zone "{zone.title}" ({zone.sodar_uuid}): '
                    f'{ex}'
                )
        log_pl = 's' if ok_count != 1 else ''
        log_check = 'to be ' if check else ''
        logger.info(f'{ok_count} zone path{log_pl} {log_check}updated')
