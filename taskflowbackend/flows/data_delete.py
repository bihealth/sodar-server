from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for deleting data objects in iRODS"""

    def validate(self):
        self.required_fields = ['paths']
        self.supported_modes = ['async', 'sync']
        return super().validate()

    def build(self, force_fail=False):
        for path in self.flow_data['paths']:
            if self.irods.data_objects.exists(path):
                self.add_task(
                    irods_tasks.RemoveDataObjectTask(
                        name='Remove data object: {}'.format(path),
                        irods=self.irods,
                        inject={'path': path},
                    )
                )
            else:
                self.add_task(
                    irods_tasks.RemoveCollectionTask(
                        name='Remove collection: {}'.format(path),
                        irods=self.irods,
                        inject={'path': path},
                    )
                )
