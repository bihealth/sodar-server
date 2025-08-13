"""Celery tasks for the taskflowbackend app"""

from config.celery import app

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import PluginAPI


plugin_api = PluginAPI()


# Celery task for async flow submitting
@app.task(bind=True)
def submit_flow_task(
    _self,
    project_uuid,
    flow_name,
    flow_data,
    tl_uuid,
):
    irods_backend = plugin_api.get_backend_api('omics_irods')
    taskflow = plugin_api.get_backend_api('taskflow')
    timeline = plugin_api.get_backend_api('timeline_backend')
    project = Project.objects.get(sodar_uuid=project_uuid)
    tl_event = None
    if timeline and tl_uuid:
        tl_event = timeline.get_models()[0].objects.get(sodar_uuid=tl_uuid)
    flow = taskflow.get_flow(
        irods_backend, project, flow_name, flow_data, True, tl_event
    )
    taskflow.run_flow(
        flow=flow,
        project=project,
        force_fail=False,
        async_mode=True,
        tl_event=tl_event,
    )
