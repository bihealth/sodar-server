# Samplesheets dependency
from samplesheets import tasks_taskflow as ss_tasks

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for deleting the project sample sheet in iRODS"""

    def validate(self):
        self.required_fields = []
        return super().validate()

    def build(self, force_fail=False):
        sample_path = self.irods_backend.get_sample_path(self.project)
        zone_path = self.irods_backend.get_zone_path(self.project)

        self.add_task(
            irods_tasks.RemoveCollectionTask(
                name='Remove project landing zones',
                irods=self.irods,
                inject={'path': zone_path},
            )
        )
        self.add_task(
            irods_tasks.RemoveCollectionTask(
                name='Remove sample data collection',
                irods=self.irods,
                inject={'path': sample_path},
            )
        )
        self.add_task(
            ss_tasks.RemoveSampleSheetsTask(
                name='Remove sample sheets',
                project=self.project,
                inject={},
            )
        )
