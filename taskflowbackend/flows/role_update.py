from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import sodar_tasks, irods_tasks


class Flow(BaseLinearFlow):
    """Flow for updating an user's role in project"""

    def validate(self):
        self.required_fields = ['username', 'user_uuid', 'role_pk']
        return super().validate()

    def build(self, force_fail=False):
        project_group = self.irods_backend.get_project_group_name(self.project)

        self.add_task(
            irods_tasks.CreateUserTask(
                name='Create user in irods',
                irods=self.irods,
                inject={
                    'user_name': self.flow_data['username'],
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
                    'user_name': self.flow_data['username'],
                },
            )
        )
        self.add_task(
            sodar_tasks.SetRoleTask(
                name='Set user role',
                sodar_api=self.sodar_api,
                project_uuid=self.project_uuid,
                inject={
                    'user_uuid': self.flow_data['user_uuid'],
                    'role_pk': self.flow_data['role_pk'],
                },
            )
        )
