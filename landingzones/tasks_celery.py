"""Celery tasks for the landingzones app"""

import logging
import os

from typing import Any

from django.conf import settings
from django.db.models import Count
from django.http import HttpRequest

from config.celery import app

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project
from projectroles.plugins import PluginAPI

from landingzones.constants import STATUS_ALLOW_UPDATE, STATUS_LOCKING
from landingzones.views import ZoneMoveMixin


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
plugin_api = PluginAPI()


# Local constants
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

    def handle_project(
        self, project: Project, request: HttpRequest, irods_backend: Any
    ):
        """
        Handle zone triggering for a single project.

        :param project: Project object
        :param request: HttpRequest object
        :param irods_backend: IrodsAPI object
        """
        irods = irods_backend.get_session_obj()
        for zone in project.landing_zones.filter(
            status__in=STATUS_ALLOW_UPDATE
        ):
            path = os.path.join(
                irods_backend.get_path(zone), settings.LANDINGZONES_TRIGGER_FILE
            )
            s = (
                f'{zone.user.username}:{zone.title} in project '
                f'{zone.project.get_log_title()}'
            )
            logger.debug(f'Searching for trigger file "{path}" for zone {s}')
            if not irods.data_objects.exists(path):
                logger.debug(f'Trigger file not found for zone {s}')
                continue  # Continue looking into other zones in project
            logger.info(f'Trigger file found for zone {s}')
            try:
                irods.data_objects.unlink(path, force=True)
                logger.debug('Trigger file deleted')
                # Submit request to Taskflow
                self.submit_validate_move(
                    zone, validate_only=False, request=request
                )
                logger.info(
                    f'Initiated landing zone validation and moving for zone {s}'
                )
                break  # Skip the rest of the zones in project
            except Exception as ex:
                logger.error(
                    f'Triggering automated moving failed in zone {s}: {ex}'
                )
        irods.cleanup()

    def run(self, request: HttpRequest = None):
        if app_settings.get('projectroles', 'site_read_only'):
            logger.info('Site read-only mode enabled, skipping')
            return
        try:
            irods_backend = plugin_api.get_backend_api('omics_irods')
        except Exception as ex:
            logger.error(f'Exception raised by irodsbackend: {ex}')
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
