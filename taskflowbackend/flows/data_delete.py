from config import settings

from .base_flow import BaseLinearFlow
from tasks import irods_tasks


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT
TASKFLOW_SAMPLE_DIR = settings.TASKFLOW_SAMPLE_COLL
TASKFLOW_LANDING_ZONE_DIR = settings.TASKFLOW_LANDING_ZONE_COLL


class Flow(BaseLinearFlow):
    """Flow for deleting data objects in iRODS"""

    def validate(self):
        self.required_fields = ['paths']
        self.supported_modes = ['async', 'sync']
        return super().validate()

    def build(self, force_fail=False):

        ##############
        # iRODS Tasks
        ##############

        for path in self.flow_data['paths']:
            if self.irods.data_objects.exists(path):
                self.add_task(
                    irods_tasks.RemoveDataObjectTask(
                        name=f'Remove data object ({path})',
                        irods=self.irods,
                        inject={'path': path},
                    )
                )
            else:
                self.add_task(
                    irods_tasks.RemoveCollectionTask(
                        name=f'Remove collection ({path})',
                        irods=self.irods,
                        inject={'path': path},
                    )
                )
