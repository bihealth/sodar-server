"""Celery tasks for the taskflowbackend app"""
# TODO: Rename to tasks_celery.py (see issue #1400)

from config.celery import app

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api


# Celery task for async flow submitting
@app.task(bind=True)
def submit_flow_task(
    _self,
    project_uuid,
    flow_name,
    flow_data,
    targets,
    tl_uuid,
):
    irods_backend = get_backend_api('omics_irods')
    taskflow = get_backend_api('taskflow')
    timeline = get_backend_api('timeline_backend')
    project = Project.objects.get(sodar_uuid=project_uuid)
    tl_event = None
    if timeline and tl_uuid:
        tl_event = timeline.get_models()[0].objects.get(sodar_uuid=tl_uuid)
    flow = taskflow._get_flow(
        irods_backend, project, flow_name, flow_data, targets, True, tl_event
    )
    taskflow._run_flow(
        flow=flow,
        project=project,
        force_fail=False,
        async_mode=True,
        tl_event=tl_event,
    )
