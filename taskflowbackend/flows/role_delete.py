from .base_flow import BaseLinearFlow
from apis.irods_utils import get_project_group_name
from tasks import sodar_tasks, irods_tasks


class Flow(BaseLinearFlow):
    """Flow for removing an user's role in project"""

    def validate(self):
        self.required_fields = ['username', 'user_uuid', 'role_pk']
        return super().validate()

    def build(self, force_fail=False):

        ########
        # Setup
        ########

        existing_group = get_project_group_name(self.project_uuid)

        ##############
        # iRODS Tasks
        ##############

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

        # TODO: TBD: Also e.g. remove landing zone if created?

        ##############
        # SODAR Tasks
        ##############

        self.add_task(
            sodar_tasks.RemoveRoleTask(
                name='Remove user role',
                sodar_api=self.sodar_api,
                project_uuid=self.project_uuid,
                inject={
                    'user_uuid': self.flow_data['user_uuid'],
                    'role_pk': self.flow_data['role_pk'],
                },
            )
        )
