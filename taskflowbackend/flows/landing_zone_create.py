from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import sodar_tasks, irods_tasks


class Flow(BaseLinearFlow):
    """Flow for creating a landing zone for an assay and a user in iRODS"""

    def validate(self):
        self.require_lock = False  # Project lock not required for this flow
        self.supported_modes = ['sync', 'async']
        self.required_fields = ['landing_zone', 'colls']
        return super().validate()

    def build(self, force_fail=False):
        project_group = self.irods_backend.get_project_group_name(self.project)
        zone_root = self.irods_backend.get_zone_path(self.project)
        zone = self.flow_data['landing_zone']
        user_path = zone_root + '/' + zone.user.username
        zone_path = self.irods_backend.get_path(zone)

        self.add_task(
            sodar_tasks.RevertLandingZoneFailTask(
                name='Set landing zone status to NOT CREATED on revert',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'info_prefix': 'Failed to create landing zone',
                    'status': 'NOT CREATED',
                },
            )
        )
        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create collection for project landing zones',
                irods=self.irods,
                inject={'path': zone_root},
            )
        )
        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set project group read access for project landing zones '
                'root collection',
                irods=self.irods,
                inject={
                    'access_name': 'read',
                    'path': zone_root,
                    'user_name': project_group,
                    'recursive': False,
                },
            )
        )
        self.add_task(
            irods_tasks.CreateUserTask(
                name='Create user if it does not exist',
                irods=self.irods,
                inject={
                    'user_name': zone.user.username,
                    'user_type': 'rodsuser',
                },
            )
        )
        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create collection for user landing zones in project',
                irods=self.irods,
                inject={'path': user_path},
            )
        )
        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set user read access to user collection inside project '
                'landing zones',
                irods=self.irods,
                inject={
                    'access_name': 'read',
                    'path': user_path,
                    'user_name': zone.user.username,
                    'recursive': False,
                },
            )
        )
        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create collection for landing zone',
                irods=self.irods,
                inject={'path': zone_path},
            )
        )
        self.add_task(
            irods_tasks.SetInheritanceTask(
                name='Set inheritance for landing zone collection {}'.format(
                    zone_path
                ),
                irods=self.irods,
                inject={'path': zone_path, 'inherit': True},
            )
        )
        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set user owner access to landing zone',
                irods=self.irods,
                inject={
                    'access_name': 'own',
                    'path': zone_path,
                    'user_name': zone.user.username,
                },
            )
        )
        # If script user is set, add write access
        # NOTE: This will intentionally fail if user has not been created!
        if self.flow_data.get('script_user'):
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Set script user "{}" write access to landing '
                    'zone'.format(self.flow_data['script_user']),
                    irods=self.irods,
                    inject={
                        'access_name': 'write',
                        'path': zone_path,
                        'user_name': self.flow_data['script_user'],
                    },
                )
            )
        if (
            'description' in self.flow_data
            and self.flow_data['description'] != ''
        ):
            self.add_task(
                irods_tasks.SetCollectionMetadataTask(
                    name='Add description metadata to landing zone collection',
                    irods=self.irods,
                    inject={
                        'path': zone_path,
                        'name': 'description',
                        'value': zone.description,
                    },
                )
            )
        for d in self.flow_data['colls']:
            coll_path = zone_path + '/' + d
            self.add_task(
                irods_tasks.CreateCollectionTask(
                    name='Create collection {}'.format(coll_path),
                    irods=self.irods,
                    inject={'path': coll_path},
                )
            )
        self.add_task(
            sodar_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to ACTIVE',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'status': 'ACTIVE',
                    'status_info': 'Available with write access for user',
                },
            )
        )
