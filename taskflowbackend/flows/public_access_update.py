from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


PUBLIC_GROUP = 'public'


class Flow(BaseLinearFlow):
    """Flow for granting or revoking public access in a collection"""

    def validate(self):
        self.required_fields = ['path', 'access']
        return super().validate()

    def build(self, force_fail=False):
        access_name = 'read' if self.flow_data['access'] else 'null'

        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set collection user group access',
                irods=self.irods,
                inject={
                    'access_name': access_name,
                    'path': self.flow_data['path'],
                    'user_name': PUBLIC_GROUP,
                },
                force_fail=force_fail,
            )
        )
