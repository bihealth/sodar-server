from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for removing an user's role in project"""

    def validate(self):
        self.required_fields = ['username']
        return super().validate()

    def build(self, force_fail=False):
        existing_group = self.irods_backend.get_user_group_name(self.project)

        self.add_task(
            irods_tasks.RemoveUserFromGroupTask(
                name='Remove user from existing group',
                irods=self.irods,
                inject={
                    'group_name': existing_group,
                    'user_name': self.flow_data['username'],
                },
            )
        )
