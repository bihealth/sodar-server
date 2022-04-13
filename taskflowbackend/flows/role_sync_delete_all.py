from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for removing all users EXCEPT the owner from a project"""

    def validate(self):
        self.required_fields = ['owner_username']
        return super().validate()

    def build(self, force_fail=False):
        group_name = self.irods_backend.get_user_group_name(self.project)
        irods_group = self.irods.user_groups.get(name=group_name)

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
