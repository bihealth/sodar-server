# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS, ROLE_RANKING

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


# SODAR constants
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']


class Flow(BaseLinearFlow):
    """Flow for updating a project. Modifies project metadata and users."""

    def validate(self):
        self.required_fields = []
        self.require_lock = False  # Project lock not required for this flow
        return super().validate()

    def build(self, force_fail=False):
        project_path = self.irods_backend.get_path(self.project)
        project_group = self.irods_backend.get_group_name(self.project)
        owner_group = self.irods_backend.get_group_name(self.project, True)
        min_owner_rank = ROLE_RANKING[PROJECT_ROLE_DELEGATE]

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
                    'value': (
                        str(self.project.parent.sodar_uuid)
                        if self.project.parent
                        else ''
                    ),
                },
            )
        )
        # Add new inherited roles
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
        for r in self.flow_data.get('roles_add', []):
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
        # Delete old inherited roles
        for r in self.flow_data.get('roles_delete', []):
            self.add_task(
                irods_tasks.RemoveUserFromGroupTask(
                    name='Remove user "{}" from project user group "{}"'.format(
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
                    irods_tasks.RemoveUserFromGroupTask(
                        name='Remove user "{}" from project owner group '
                        '"{}"'.format(r['user_name'], owner_group),
                        irods=self.irods,
                        inject={
                            'group_name': owner_group,
                            'user_name': r['user_name'],
                        },
                    )
                )
