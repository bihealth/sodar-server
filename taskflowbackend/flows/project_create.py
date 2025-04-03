# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS, ROLE_RANKING

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


# SODAR constants
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']


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
        project_group = self.irods_backend.get_user_group_name(self.project)
        owner_group = self.irods_backend.get_user_group_name(
            self.project, owner=True
        )
        min_owner_rank = ROLE_RANKING[PROJECT_ROLE_DELEGATE]

        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create root collection for SODAR projects',
                irods=self.irods,
                inject={'path': self.irods_backend.get_projects_path()},
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
                    'value': (
                        str(self.project.parent.sodar_uuid)
                        if self.project.parent
                        else ''
                    ),
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
                    'irods_backend': self.irods_backend,
                },
            )
        )
        self.add_task(
            irods_tasks.CreateUserGroupTask(
                name='Create project owner group',
                irods=self.irods,
                inject={'name': owner_group},
            )
        )
        self.add_task(
            irods_tasks.CreateUserTask(
                name='Create user for project owner',
                irods=self.irods,
                inject={
                    'user_name': self.flow_data['owner'],
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
                    'user_name': self.flow_data['owner'],
                },
            )
        )
        self.add_task(
            irods_tasks.AddUserToGroupTask(
                name='Add owner user to project owner group',
                irods=self.irods,
                inject={
                    'group_name': owner_group,
                    'user_name': self.flow_data['owner'],
                },
            )
        )
        # Add inherited users
        for r in self.flow_data.get('roles_add', []):
            self.add_task(
                irods_tasks.CreateUserTask(
                    name='Create user "{}" in irods'.format(r['user_name']),
                    irods=self.irods,
                    inject={
                        'user_name': r['user_name'],
                        'user_type': 'rodsuser',
                    },
                )
            )
            self.add_task(
                irods_tasks.AddUserToGroupTask(
                    name='Add user "{}" to project user group "{}"'.format(
                        r['user_name'], project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': r['user_name'],
                    },
                )
            )
            if r.get('role_rank') and r['role_rank'] <= min_owner_rank:
                self.add_task(
                    irods_tasks.AddUserToGroupTask(
                        name='Add user "{}" to project owner group "{}"'.format(
                            r['user_name'], owner_group
                        ),
                        irods=self.irods,
                        inject={
                            'group_name': owner_group,
                            'user_name': r['user_name'],
                        },
                    )
                )
