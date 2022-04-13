from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """
    Flow for batch updating user roles in iRODS.
    NOTE: Will NOT update roles in SODAR!
    """

    def validate(self):
        self.require_lock = False  # Project lock not required for this flow
        self.required_fields = ['roles_add', 'roles_delete']
        return super().validate()

    def build(self, force_fail=False):
        # Add roles
        for username in set(
            [r['user'].username for r in self.flow_data['roles_add']]
        ):
            self.add_task(
                irods_tasks.CreateUserTask(
                    name='Create user "{}" in irods'.format(username),
                    irods=self.irods,
                    inject={'user_name': username, 'user_type': 'rodsuser'},
                )
            )
        for role_add in self.flow_data['roles_add']:
            project_group = self.irods_backend.get_user_group_name(
                role_add['project']
            )
            self.add_task(
                irods_tasks.AddUserToGroupTask(
                    name='Add user "{}" to project user group "{}"'.format(
                        role_add['user'].username, project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': role_add['user'].username,
                    },
                )
            )
        # Delete roles
        for role_delete in self.flow_data['roles_delete']:
            project_group = self.irods_backend.get_user_group_name(
                role_delete['project']
            )
            self.add_task(
                irods_tasks.RemoveUserFromGroupTask(
                    name='Remove user "{}" from project user group "{}"'.format(
                        role_delete['user'].username, project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': role_delete['user'].username,
                    },
                )
            )
