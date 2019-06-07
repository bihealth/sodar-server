import logging

from django.contrib import auth

from config.celery import app

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_app_plugin, get_backend_api


APP_NAME = 'samplesheets'

logger = logging.getLogger(__name__)
User = auth.get_user_model()


@app.task(bind=True)
def update_project_cache_task(_self, project_uuid, user_uuid):
    """Update project cache asynchronously"""
    try:
        project = Project.objects.get(sodar_uuid=project_uuid)

    except Project.DoesNotExist:
        logger.error('Project not found (uuid={})'.format(project_uuid))
        return

    try:
        user = User.objects.get(sodar_uuid=user_uuid)

    except User.DoesNotExist:
        logger.error('User not found (uuid={})'.format(user_uuid))

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
    app_plugin.update_cache(project=project, user=user)

    if tl_event:
        tl_event.set_status(status_type='OK', status_desc='Update OK')

    logger.info(
        'Cache update OK for project "{}" ({})'.format(
            project.title, project.sodar_uuid
        )
    )
