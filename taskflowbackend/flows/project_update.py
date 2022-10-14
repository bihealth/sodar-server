from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """Flow for updating a project: modifies project metadata and owner"""

    def validate(self):
        self.required_fields = []
        return super().validate()

    def build(self, force_fail=False):
        project_path = self.irods_backend.get_path(self.project)
        project_group = self.irods_backend.get_user_group_name(self.project)

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
                    'value': self.project.description or '',
                },
            )
        )
        self.add_task(
            irods_tasks.SetCollectionMetadataTask(
                name='Update parent metadata in project',
                irods=self.irods,
                inject={
                    'path': project_path,
                    'name': 'parent_uuid',
                    'value': str(self.project.parent.sodar_uuid)
                    if self.project.parent
                    else '',
                },
            )
        )
        # Add new inherited roles
        for user_name in self.flow_data.get('users_add', []):
            self.add_task(
                irods_tasks.CreateUserTask(
                    name='Create user "{}" in irods'.format(user_name),
                    irods=self.irods,
                    inject={'user_name': user_name, 'user_type': 'rodsuser'},
                )
            )
        for user_name in self.flow_data.get('users_add', []):
            self.add_task(
                irods_tasks.AddUserToGroupTask(
                    name='Add user "{}" to project user group "{}"'.format(
                        user_name, project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': user_name,
                    },
                )
            )
        # Delete old inherited roles
        for user_name in self.flow_data.get('users_delete', []):
            self.add_task(
                irods_tasks.RemoveUserFromGroupTask(
                    name='Remove user "{}" from project user group "{}"'.format(
                        user_name, project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': user_name,
                    },
                )
            )
