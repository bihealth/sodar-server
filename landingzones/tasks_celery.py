"""Celery tasks for the landingzones app"""

import logging
import os

from django.conf import settings
from django.db.models import Count

from config.celery import app

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api

from landingzones.constants import STATUS_ALLOW_UPDATE, STATUS_LOCKING
from landingzones.views import ZoneMoveMixin

logger = logging.getLogger(__name__)


APP_NAME = 'landingzones'


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    if settings.LANDINGZONES_TRIGGER_ENABLE:
        sender.add_periodic_task(
            settings.LANDINGZONES_TRIGGER_MOVE_INTERVAL, trigger_zone_move
        )


@app.task
def trigger_zone_move():
    """
    Trigger landing zone validation and moving automatically if a certain file
    is located in the root of that zone.
    """
    TriggerZoneMoveTask().run()


class TriggerZoneMoveTask(ZoneMoveMixin):
    """Task for triggering landing zone validation and moving"""

    def handle_project(self, project, request, irods_backend):
        """Handle zone triggering for a single project"""
        irods = irods_backend.get_session_obj()
        for zone in project.landing_zones.filter(
            status__in=STATUS_ALLOW_UPDATE
        ):
            path = os.path.join(
                irods_backend.get_path(zone), settings.LANDINGZONES_TRIGGER_FILE
            )
            s = '{}:{} in project "{}" ({})'.format(
                zone.user.username,
                zone.title,
                zone.project.title,
                zone.project.sodar_uuid,
            )
            logger.debug(
                'Searching for trigger file "{}" for zone {}'.format(path, s)
            )
            if not irods.data_objects.exists(path):
                logger.debug('Trigger file not found for zone {}'.format(s))
                continue  # Continue looking into other zones in project
            logger.info('Trigger file found for zone {}'.format(s))
            try:
                irods.data_objects.unlink(path, force=True)
                logger.debug('Trigger file deleted')
                # Submit request to Taskflow
                self._submit_validate_move(
                    zone, validate_only=False, request=request
                )
                logger.info(
                    'Initiated landing zone validation and moving for '
                    'zone {}'.format(s)
                )
                break  # Skip the rest of the zones in project
            except Exception as ex:
                logger.error(
                    'Triggering automated moving failed in zone '
                    '{}: {}'.format(s, ex)
                )
        irods.cleanup()

    def run(self, request=None):
        try:
            irods_backend = get_backend_api('omics_irods')
        except Exception as ex:
            logger.error('Exception raised by irodsbackend: {}'.format(ex))
            return
        if not irods_backend:
            return
        # Get projects, omit those which should currently be locked by Taskflow
        # TODO: Check for lock status directly, see #2048
        projects = (
            Project.objects.filter(type='PROJECT')
            .annotate(zone_count=Count('landing_zones'))
            .exclude(zone_count=0)
            .exclude(landing_zones__status__in=STATUS_LOCKING)
        )
        for project in projects:
            self.handle_project(project, request, irods_backend)
