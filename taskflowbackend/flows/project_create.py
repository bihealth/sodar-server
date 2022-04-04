from django.conf import settings

from taskflowbackend.apis.irods_utils import get_project_group_name
from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT


class Flow(BaseLinearFlow):
    """
    Flow for creating a new project. Creates related collections and user
    groups for access, also assigning membership in owner group to owner.
    """

    def validate(self):
        self.required_fields = ['owner']
        return super().validate()

    def build(self, force_fail=False):
        project_path = self.irods_backend.get_path(self.project)
        project_group = get_project_group_name(str(self.project.sodar_uuid))

        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create root collection for SODAR projects',
                irods=self.irods,
                inject={'path': PROJECT_ROOT},
            )
        )
        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create collection for project',
                irods=self.irods,
                inject={'path': project_path},
            )
        )
        self.add_task(
            irods_tasks.SetCollectionMetadataTask(
                name='Add title metadata to project',
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
                name='Add description metadata to project',
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
                name='Add parent metadata to project',
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
        self.add_task(
            irods_tasks.CreateUserGroupTask(
                name='Create project user group',
                irods=self.irods,
                inject={'name': project_group},
            )
        )
        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set project user group access',
                irods=self.irods,
                inject={
                    'access_name': 'read',
                    'path': project_path,
                    'user_name': project_group,
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
                name='Add owner user to project user group',
                irods=self.irods,
                inject={
                    'group_name': project_group,
                    'user_name': self.flow_data['owner'].username,
                },
            )
        )
        # Add inherited owners
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
