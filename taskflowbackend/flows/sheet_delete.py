from django.conf import settings

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import sodar_tasks, irods_tasks


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT
TASKFLOW_SAMPLE_COLL = settings.TASKFLOW_SAMPLE_COLL
TASKFLOW_LANDING_ZONE_COLL = settings.TASKFLOW_LANDING_ZONE_COLL


class Flow(BaseLinearFlow):
    """Flow for deleting the project sample sheet in iRODS"""

    def validate(self):
        self.required_fields = []
        return super().validate()

    def build(self, force_fail=False):
        project_path = self.irods_backend.get_path(self.project)
        sample_path = project_path + '/' + TASKFLOW_SAMPLE_COLL
        zone_path = project_path + '/' + TASKFLOW_LANDING_ZONE_COLL

        self.add_task(
            irods_tasks.RemoveCollectionTask(
                name='Remove sample sheet landing zones',
                irods=self.irods,
                inject={'path': zone_path},
            )
        )
        self.add_task(
            irods_tasks.RemoveCollectionTask(
                name='Remove sample sheet collection',
                irods=self.irods,
                inject={'path': sample_path},
            )
        )
        self.add_task(
            sodar_tasks.RemoveSampleSheetTask(
                name='Remove sample sheet',
                sodar_api=self.sodar_api,
                project_uuid=self.project_uuid,
                inject={},
            )
        )
