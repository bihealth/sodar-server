import logging

from django.contrib import auth

from config.celery import app

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_app_plugin

# Timeline dependency (Temporary HACK, see sodar_core#256)
from timeline.models import ProjectEvent


APP_NAME = 'samplesheets'

logger = logging.getLogger(__name__)
User = auth.get_user_model()


# TODO: This should be done in the SODAR Core API view called by SODAR Taskflow
@app.task(bind=True)
def update_project_cache(_self, project_uuid, user_uuid, tl_uuid=None):
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

    # TODO: Use TimelineAPI.get_event() once implemented (see sodar_core#256)
    tl_event = (
        ProjectEvent.objects.filter(sodar_uuid=tl_uuid).first()
        if tl_uuid
        else None
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
