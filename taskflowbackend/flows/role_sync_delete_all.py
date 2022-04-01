from .base_flow import BaseLinearFlow
from apis.irods_utils import get_project_group_name
from tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for removing all users EXCEPT the owner from a project"""

    def validate(self):
        self.required_fields = ['owner_username']
        return super().validate()

    def build(self, force_fail=False):

        ########
        # Setup
        ########

        group_name = get_project_group_name(self.project_uuid)
        irods_group = self.irods.user_groups.get(name=group_name)

        ##############
        # iRODS Tasks
        ##############

        for user in [
            user
            for user in irods_group.members
            if user.name != self.flow_data['owner_username']
        ]:
            self.add_task(
                irods_tasks.RemoveUserFromGroupTask(
                    name='Remove user {} from group {}'.format(
                        user.name, group_name
                    ),
                    irods=self.irods,
                    inject={'group_name': group_name, 'user_name': user.name},
                )
            )
