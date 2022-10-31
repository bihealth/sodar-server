"""Celery tasks for the landingzones app"""
import logging

from django.conf import settings
from django.db.models import Count

from config.celery import app

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api

from landingzones.models import STATUS_ALLOW_UPDATE, STATUS_LOCKING
from landingzones.views import ZoneMoveMixin

logger = logging.getLogger(__name__)


APP_NAME = 'landingzones'


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    if settings.LANDINGZONES_TRIGGER_ENABLE:
        sender.add_periodic_task(
            settings.LANDINGZONES_TRIGGER_MOVE_INVERVAL, trigger_zone_move
        )


@app.task
def trigger_zone_move():
    """
    Trigger landing zone validation and moving automatically if a certain file
    is located in the root of that zone.
    """
    TriggerZoneMoveTask().run()


class TriggerZoneMoveTask(ZoneMoveMixin):
    def run(self, request=None):
        try:
            irods_backend = get_backend_api('omics_irods')
        except Exception as ex:
            logger.error('Exception raised by irodsbackend: {}'.format(ex))
            return
        if not irods_backend:
            return

        irods = irods_backend.get_session()

        # Get projects, omit those which should currently be locked by Taskflow
        # TODO: Once we integrate Taskflow, check for lock status directly
        projects = (
            Project.objects.filter(type='PROJECT')
            .annotate(zone_count=Count('landing_zones'))
            .exclude(zone_count=0)
            .exclude(landing_zones__status__in=STATUS_LOCKING)
        )

        for project in projects:
            for zone in project.landing_zones.filter(
                status__in=STATUS_ALLOW_UPDATE
            ):
                trigger_path = (
                    irods_backend.get_path(zone)
                    + '/'
                    + settings.LANDINGZONES_TRIGGER_FILE
                )
                z_log = '{}:{} in project "{}" ({})'.format(
                    zone.user.username,
                    zone.title,
                    zone.project.title,
                    zone.project.sodar_uuid,
                )
                logger.debug(
                    'Searching for trigger file "{}" for zone {}'.format(
                        trigger_path, z_log
                    )
                )

                if irods.data_objects.exists(trigger_path):
                    logger.info('Trigger file found for zone {}'.format(z_log))
                    try:
                        irods.data_objects.unlink(trigger_path, force=True)
                        logger.debug('Trigger file deleted')

                        # Submit request to Taskflow
                        self._submit_validate_move(
                            zone, validate_only=False, request=request
                        )
                        logger.info(
                            'Initiated landing zone validation and moving for '
                            'zone {}'.format(z_log)
                        )
                        break  # Skip the rest of the zones in this project
                    except Exception as ex:
                        logger.error(
                            'Triggering automated moving failed in zone '
                            '{}: {}'.format(z_log, ex)
                        )
                else:
                    logger.debug(
                        'Trigger file not found for zone {}'.format(z_log)
                    )

        irods.cleanup()
