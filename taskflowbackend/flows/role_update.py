from .base_flow import BaseLinearFlow
from apis.irods_utils import get_project_group_name
from tasks import sodar_tasks, irods_tasks


class Flow(BaseLinearFlow):
    """Flow for updating an user's role in project"""

    def validate(self):
        self.required_fields = ['username', 'user_uuid', 'role_pk']
        return super().validate()

    def build(self, force_fail=False):

        ########
        # Setup
        ########

        project_group = get_project_group_name(self.project_uuid)

        ##############
        # iRODS Tasks
        ##############

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

        ##############
        # SODAR Tasks
        ##############

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
