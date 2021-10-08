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
from projectroles.plugins import get_backend_api, get_app_plugin


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
User = auth.get_user_model()


PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
APP_NAME = 'samplesheets'


@app.task(bind=True)
def update_project_cache_task(
    _self, project_uuid, user_uuid, add_alert=False, alert_msg=None
):
    """
    Update project cache asynchronously.

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

    timeline = get_backend_api('timeline_backend')
    tl_event = None
    if timeline:
        tl_event = timeline.add_event(
            project=project,
            app_name=APP_NAME,
            user=user,
            event_name='sheet_cache_update',
            description='update cache for project sheets',
            status_type='SUBMIT',
            status_desc='Asynchronous update started',
        )

    logger.info(
        'Updating cache asynchronously for project "{}" ({})'.format(
            project.title, project.sodar_uuid
        )
    )
    app_plugin = get_app_plugin(APP_NAME)

    try:
        app_plugin.update_cache(project=project, user=user)
        tl_status_type = 'OK'
        tl_status_desc = 'Update OK'
        app_level = 'INFO'
        app_msg = 'Sample sheet iRODS cache updated'
        if alert_msg:
            app_msg += ': {}'.format(alert_msg)
        logger.info(
            'Cache update OK for project "{}" ({})'.format(
                project.title, project.sodar_uuid
            )
        )
    except Exception as ex:
        tl_status_type = 'FAILED'
        tl_status_desc = 'Update failed: {}'.format(ex)
        app_level = 'DANGER'
        app_msg = 'Sample sheet iRODS cache update failed: {}'.format(ex)
        logger.error(
            'Cache update failed for project "{}" ({}): {}'.format(
                project.title, project.sodar_uuid, ex
            )
        )

    if tl_event:
        tl_event.set_status(
            status_type=tl_status_type, status_desc=tl_status_desc
        )
    if add_alert and user:
        app_alerts = get_backend_api('appalerts_backend')
        if app_alerts:
            app_alerts.add_alert(
                app_name=APP_NAME,
                alert_name='sheet_cache_update',
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
def sheet_sync_task(_self, username):
    """Task for synchronizing sample sheets from a source project"""
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.error('User not found (username={})'.format(username))
        return False

    timeline = get_backend_api('timeline_backend')
    tl_add = False
    tl_status_type = 'OK'
    tl_status_desc = 'Sync OK'

    for project in Project.objects.filter(type=PROJECT_TYPE_PROJECT):
        sheet_sync_enable = app_settings.get_app_setting(
            APP_NAME, 'sheet_sync_enable', project=project
        )
        if not sheet_sync_enable:
            continue
        sheet_sync_url = app_settings.get_app_setting(
            APP_NAME, 'sheet_sync_url', project=project
        )
        sheet_sync_token = app_settings.get_app_setting(
            APP_NAME, 'sheet_sync_token', project=project
        )

        from samplesheets.views import SheetRemoteSyncAPI

        sync = SheetRemoteSyncAPI()
        try:
            ret = sync.run(project, sheet_sync_url, sheet_sync_token, user)
            if ret:
                tl_add = True
        except Exception as ex:
            fail_msg = 'Sync failed: {}'.format(ex)
            logger.error(fail_msg)
            tl_add = True  # Add timeline event
            tl_status_type = 'FAILED'
            tl_status_desc = fail_msg

        if timeline and tl_add:
            timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=user,
                event_name='sheet_sync_task',
                description='sync sheets from source project',
                status_type=tl_status_type,
                status_desc=tl_status_desc,
            )


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        settings.SHEETS_SYNC_INTERVAL * 60,
        sheet_sync_task.s(settings.PROJECTROLES_DEFAULT_ADMIN),
        name='sheet_sync_task',
    )
