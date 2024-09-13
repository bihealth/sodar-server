from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for updating an user's role in project"""

    def validate(self):
        self.required_fields = ['user_name']
        self.require_lock = False  # Project lock not required for this flow
        return super().validate()

    def build(self, force_fail=False):
        project_group = self.irods_backend.get_user_group_name(self.project)

        self.add_task(
            irods_tasks.CreateUserTask(
                name='Create user in irods',
                irods=self.irods,
                inject={
                    'user_name': self.flow_data['user_name'],
                    'user_type': 'rodsuser',
                },
            )
        )
        self.add_task(
            irods_tasks.AddUserToGroupTask(
                name='Add user to project user group',
                irods=self.irods,
                inject={
                    'group_name': project_group,
                    'user_name': self.flow_data['user_name'],
                },
            )
        )
