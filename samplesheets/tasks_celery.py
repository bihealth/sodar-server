"""Celery tasks for the samplesheets app"""

import logging

from django.conf import settings
from django.contrib import auth
from django.urls import reverse

from config.celery import app

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.constants import SODAR_CONSTANTS
from projectroles.models import Project
from projectroles.plugins import PluginAPI


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
plugin_api = PluginAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
# Local constants
APP_NAME = 'samplesheets'
CACHE_UPDATE_EVENT = 'sheet_cache_update'


@app.task(bind=True)
def update_project_cache_task(
    _self, project_uuid, user_uuid, add_alert=False, alert_msg=None
):
    """
    Update project iRODS cache asynchronously.

    :param project_uuid: Project UUID for cache item
    :param user_uuid: User UUID or None
    :param add_alert: Add app alert for action if True (bool, default=False)
    :param alert_msg: Additional message for app alert (string, optional)
    """
    try:
        project = Project.objects.get(sodar_uuid=project_uuid)
    except Project.DoesNotExist:
        logger.error('Project not found (uuid={})'.format(project_uuid))
        return
    user = User.objects.filter(sodar_uuid=user_uuid).first()

    timeline = plugin_api.get_backend_api('timeline_backend')
    tl_event = None
    if timeline:
        tl_event = timeline.add_event(
            project=project,
            app_name=APP_NAME,
            user=user,
            event_name=CACHE_UPDATE_EVENT,
            description='update cache for project sheets',
            status_type=timeline.TL_STATUS_SUBMIT,
            status_desc='Asynchronous update started',
        )

    logger.info(
        'Updating cache asynchronously for project {}'.format(
            project.get_log_title()
        )
    )
    app_plugin = plugin_api.get_app_plugin(APP_NAME)

    try:
        app_plugin.update_cache(project=project, user=user)
        if tl_event:
            tl_status_type = timeline.TL_STATUS_OK
            tl_status_desc = 'Update OK'
            tl_event.set_status(
                status_type=tl_status_type, status_desc=tl_status_desc
            )
        app_level = 'INFO'
        app_msg = 'Sample sheet iRODS cache updated'
        if alert_msg:
            app_msg += ': {}'.format(alert_msg)
        logger.info(
            'Cache update OK for project {}'.format(project.get_log_title())
        )
    except Exception as ex:
        if tl_event:
            tl_status_type = timeline.TL_STATUS_FAILED
            tl_status_desc = 'Update failed: {}'.format(ex)
            tl_event.set_status(
                status_type=tl_status_type, status_desc=tl_status_desc
            )
        app_level = 'DANGER'
        app_msg = 'Sample sheet iRODS cache update failed: {}'.format(ex)
        logger.error(
            'Cache update failed for project {}: {}'.format(
                project.get_log_title(), ex
            )
        )

    if add_alert and user:
        app_alerts = plugin_api.get_backend_api('appalerts_backend')
        if app_alerts:
            app_alerts.add_alert(
                app_name=APP_NAME,
                alert_name=CACHE_UPDATE_EVENT,
                user=user,
                message=app_msg,
                level=app_level,
                url=reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': project.sodar_uuid},
                ),
                project=project,
            )


@app.task(bind=True)
def sheet_sync_task(_self):
    """Task for synchronizing sample sheets from a source project"""
    from samplesheets.views import SheetRemoteSyncAPI

    if app_settings.get('projectroles', 'site_read_only'):
        logger.info('Site read-only mode enabled, skipping')
        return

    timeline = plugin_api.get_backend_api('timeline_backend')
    tl_add = False
    tl_status_type = timeline.TL_STATUS_OK if timeline else 'OK'
    tl_status_desc = 'Sync OK'

    for project in Project.objects.filter(type=PROJECT_TYPE_PROJECT):
        sheet_sync_enable = app_settings.get(
            APP_NAME, 'sheet_sync_enable', project=project
        )
        if not sheet_sync_enable:
            continue

        sync_api = SheetRemoteSyncAPI()
        try:
            ret = sync_api.sync_sheets(project, None)
            if ret:
                tl_add = True
        except Exception as ex:
            fail_msg = 'Sync failed: {}'.format(ex)
            logger.error(fail_msg)
            tl_add = True  # Add timeline event
            tl_status_type = timeline.TL_STATUS_FAILED if timeline else 'FAILED'
            tl_status_desc = fail_msg

        if timeline and tl_add:
            timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=None,
                event_name='sheet_sync_task',
                description='sync sheets from source project',
                status_type=tl_status_type,
                status_desc=tl_status_desc,
            )


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        settings.SHEETS_SYNC_INTERVAL * 60,
        sheet_sync_task.s(),
        name='sheet_sync_task',
    )
