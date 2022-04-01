from config import settings

from .base_flow import BaseLinearFlow
from apis.irods_utils import (
    get_landing_zone_root,
    get_landing_zone_path,
    get_project_group_name,
)
from tasks import sodar_tasks, irods_tasks


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT


class Flow(BaseLinearFlow):
    """Flow for creating a landing zone for an assay and a user in iRODS"""

    def validate(self):
        self.require_lock = False  # Project lock not required for this flow
        self.supported_modes = ['sync', 'async']
        self.required_fields = [
            'zone_title',
            'zone_uuid',
            'user_name',
            'user_uuid',
            'assay_path',
            'colls',
        ]
        return super().validate()

    def build(self, force_fail=False):

        ########
        # Setup
        ########

        project_group = get_project_group_name(self.project_uuid)
        zone_root = get_landing_zone_root(self.project_uuid)
        user_path = zone_root + '/' + self.flow_data['user_name']
        zone_path = get_landing_zone_path(
            project_uuid=self.project_uuid,
            user_name=self.flow_data['user_name'],
            assay_path=self.flow_data['assay_path'],
            zone_title=self.flow_data['zone_title'],
            zone_config=self.flow_data['zone_config'],
        )

        ##############
        # SODAR Tasks
        ##############

        self.add_task(
            sodar_tasks.RevertLandingZoneFailTask(
                name='Set landing zone status to NOT CREATED on revert',
                sodar_api=self.sodar_api,
                project_uuid=self.project_uuid,
                inject={
                    'zone_uuid': self.flow_data['zone_uuid'],
                    'flow_name': self.flow_name,
                    'info_prefix': 'Failed to create landing zone',
                    'status': 'NOT CREATED',
                },
            )
        )

        ##############
        # iRODS Tasks
        ##############

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
                    'user_name': self.flow_data['user_name'],
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
                    'user_name': self.flow_data['user_name'],
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
                    'user_name': self.flow_data['user_name'],
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
                        'value': self.flow_data['description'],
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

        ##############
        # SODAR Tasks
        ##############

        # NOTE: Not using zone_uuid here because taskflow doesn't know it yet
        self.add_task(
            sodar_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to ACTIVE',
                sodar_api=self.sodar_api,
                project_uuid=self.project_uuid,
                inject={
                    'zone_uuid': self.flow_data['zone_uuid'],
                    'flow_name': self.flow_name,
                    'user_uuid': self.flow_data['user_uuid'],
                    'status': 'ACTIVE',
                    'status_info': 'Available with write access for user',
                },
            )
        )
