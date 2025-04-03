# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS, ROLE_RANKING

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


# SODAR constants
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']


class Flow(BaseLinearFlow):
    """Flow for batch updating user roles in iRODS"""

    def validate(self):
        self.require_lock = False  # Project lock not required for this flow
        self.required_fields = ['roles_add', 'roles_delete']
        return super().validate()

    def build(self, force_fail=False):
        users_add = set([r['user_name'] for r in self.flow_data['roles_add']])
        min_owner_rank = ROLE_RANKING[PROJECT_ROLE_DELEGATE]
        owner_groups_add = set(
            [
                self.irods_backend.get_user_group_name(r['project_uuid'], True)
                for r in self.flow_data['roles_add']
                if r.get('role_rank') and r['role_rank'] <= min_owner_rank
            ]
        )

        # Create missing users
        for user_name in users_add:
            self.add_task(
                irods_tasks.CreateUserTask(
                    name='Create user "{}" in irods'.format(user_name),
                    irods=self.irods,
                    inject={'user_name': user_name, 'user_type': 'rodsuser'},
                )
            )
        # Create missing owner groups
        for owner_group in owner_groups_add:
            self.add_task(
                irods_tasks.CreateUserGroupTask(
                    name='Create owner group "{}" in irods'.format(owner_group),
                    irods=self.irods,
                    inject={'name': owner_group},
                )
            )

        # Add/update roles
        for role_add in self.flow_data['roles_add']:
            project_group = self.irods_backend.get_user_group_name(
                role_add['project_uuid']
            )
            owner_group = self.irods_backend.get_user_group_name(
                role_add['project_uuid'], owner=True
            )
            self.add_task(
                irods_tasks.AddUserToGroupTask(
                    name='Add user "{}" to project user group "{}"'.format(
                        role_add['user_name'], project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': role_add['user_name'],
                    },
                )
            )
            # If role is delegate or owner, add to owner group
            if (
                role_add.get('role_rank')
                and role_add['role_rank'] <= min_owner_rank
            ):
                self.add_task(
                    irods_tasks.AddUserToGroupTask(
                        name='Add user "{}" to project owner group "{}"'.format(
                            role_add['user_name'], owner_group
                        ),
                        irods=self.irods,
                        inject={
                            'group_name': owner_group,
                            'user_name': role_add['user_name'],
                        },
                    )
                )
            # Else remove from owner group (in case of update)
            else:
                self.add_task(
                    irods_tasks.RemoveUserFromGroupTask(
                        name='Remove user "{}" from project owner group '
                        '"{}"'.format(role_add['user_name'], owner_group),
                        irods=self.irods,
                        inject={
                            'group_name': owner_group,
                            'user_name': role_add['user_name'],
                        },
                    )
                )

        # Delete roles
        for role_delete in self.flow_data['roles_delete']:
            project_group = self.irods_backend.get_user_group_name(
                role_delete['project_uuid']
            )
            self.add_task(
                irods_tasks.RemoveUserFromGroupTask(
                    name='Remove user "{}" from project user group "{}"'.format(
                        role_delete['user_name'], project_group
                    ),
                    irods=self.irods,
                    inject={
                        'group_name': project_group,
                        'user_name': role_delete['user_name'],
                    },
                )
            )
            # If role is delegate, owner or None, remove from owner group
            if (
                not role_delete.get('role_rank')
                or role_delete['role_rank'] <= min_owner_rank
            ):
                owner_group = self.irods_backend.get_user_group_name(
                    role_delete['project_uuid'], owner=True
                )
                self.add_task(
                    irods_tasks.RemoveUserFromGroupTask(
                        name='Remove user "{}" from project owner group '
                        '"{}"'.format(role_delete['user_name'], owner_group),
                        irods=self.irods,
                        inject={
                            'group_name': owner_group,
                            'user_name': role_delete['user_name'],
                        },
                    )
                )
