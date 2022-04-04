from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.apis.irods_utils import get_project_group_name
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for updating a project: modifies project metadata and owner"""

    def validate(self):
        self.required_fields = ['owner', 'old_owner']
        return super().validate()

    def build(self, force_fail=False):
        project_path = self.irods_backend.get_path(self.project)
        project_group = self.irods_backend.get_project_group_name(self.project)

        self.add_task(
            irods_tasks.SetCollectionMetadataTask(
                name='Update title metadata in project',
                irods=self.irods,
                inject={
                    'path': project_path,
                    'name': 'title',
                    'value': self.project.title,
                },
            )
        )
        self.add_task(
            irods_tasks.SetCollectionMetadataTask(
                name='Update description metadata in project',
                irods=self.irods,
                inject={
                    'path': project_path,
                    'name': 'description',
                    'value': self.project('description') or '',
                },
            )
        )
        # TODO: Set public access according to public_guest_access (#71)
        if self.flow_data['owner_uuid'] != self.flow_data['old_owner_uuid']:
            self.add_task(
                irods_tasks.RemoveUserFromGroupTask(
                    name='Remove old owner "{}" from project user '
                    'group'.format(self.flow_data['owner'].username),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': self.flow_data['old_owner'].username,
                    },
                )
            )
            self.add_task(
                irods_tasks.CreateUserTask(
                    name='Create user for project owner',
                    irods=self.irods,
                    inject={
                        'user_name': self.flow_data['owner'].username,
                        'user_type': 'rodsuser',
                    },
                )
            )
            self.add_task(
                irods_tasks.AddUserToGroupTask(
                    name='Add new owner "{}" to project user group'.format(
                        self.flow_data['owner'].username
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': self.flow_data['owner'].username,
                    },
                )
            )
        # Add new inherited roles
        for username in set(
            [r['username'] for r in self.flow_data.get('roles_add', [])]
        ):
            self.add_task(
                irods_tasks.CreateUserTask(
                    name='Create user "{}" in irods'.format(username),
                    irods=self.irods,
                    inject={'user_name': username, 'user_type': 'rodsuser'},
                )
            )
        for role_add in self.flow_data.get('roles_add', []):
            # TODO: Update parameter to be project instead of UUID
            project_group = get_project_group_name(role_add['project_uuid'])
            self.add_task(
                irods_tasks.AddUserToGroupTask(
                    name='Add user "{}" to project user group "{}"'.format(
                        role_add['username'], project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': role_add['username'],
                    },
                )
            )
        # Delete old inherited roles
        for role_delete in self.flow_data.get('roles_delete', []):
            # TODO: Update parameter to be project instead of UUID
            project_group = get_project_group_name(role_delete['project_uuid'])
            self.add_task(
                irods_tasks.RemoveUserFromGroupTask(
                    name='Remove user "{}" from project user group "{}"'.format(
                        role_delete['username'], project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': role_delete['username'],
                    },
                )
            )
