import os

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks

# Landingzones dependency
from landingzones.constants import ZONE_STATUS_NOT_CREATED, ZONE_STATUS_ACTIVE
from landingzones.models import LandingZone
import landingzones.tasks_taskflow as lz_tasks


class Flow(BaseLinearFlow):
    """Flow for creating a landing zone for an assay and a user in iRODS"""

    def validate(self):
        self.require_lock = False  # Project lock not required for this flow
        self.required_fields = ['zone_uuid', 'colls', 'restrict_colls']
        self.supported_modes = ['sync', 'async']
        return super().validate()

    def build(self, force_fail=False):
        project_group = self.irods_backend.get_user_group_name(self.project)
        zone_root = self.irods_backend.get_zone_path(self.project)
        zone = LandingZone.objects.get(sodar_uuid=self.flow_data['zone_uuid'])
        user_path = os.path.join(zone_root, zone.user.username)
        zone_path = self.irods_backend.get_path(zone)
        root_access = 'read' if self.flow_data['restrict_colls'] else 'own'

        self.add_task(
            lz_tasks.RevertLandingZoneFailTask(
                name='Set landing zone status to NOT CREATED on revert',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'info_prefix': 'Failed to create landing zone',
                    'status': ZONE_STATUS_NOT_CREATED,
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
                    'irods_backend': self.irods_backend,
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
                    'irods_backend': self.irods_backend,
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
                name='Set inheritance for landing zone collection '
                '{}'.format(zone_path),
                irods=self.irods,
                inject={'path': zone_path, 'inherit': True},
            )
        )
        # Only set own access to root zone collection if not enforcing colls
        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set user {} access to landing zone root'.format(
                    root_access
                ),
                irods=self.irods,
                inject={
                    'access_name': root_access,
                    'path': zone_path,
                    'user_name': zone.user.username,
                    'irods_backend': self.irods_backend,
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
                        'irods_backend': self.irods_backend,
                    },
                )
            )
        if zone.description:
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
        # Create collections
        if self.flow_data['colls']:
            colls_full_path = [
                os.path.join(zone_path, c) for c in self.flow_data['colls']
            ]
            coll_count = len(self.flow_data['colls'])
            self.add_task(
                irods_tasks.BatchCreateCollectionsTask(
                    name='Batch create {} collection{}'.format(
                        coll_count, 's' if coll_count != 1 else ''
                    ),
                    irods=self.irods,
                    inject={'coll_paths': colls_full_path},
                )
            )
            # Enforce collection access if set
            if self.flow_data['restrict_colls']:
                self.add_task(
                    irods_tasks.BatchSetAccessTask(
                        name='Batch set user owner access to created '
                        'collections',
                        irods=self.irods,
                        inject={
                            'access_name': 'own',
                            'paths': colls_full_path,
                            'user_name': zone.user.username,
                            'irods_backend': self.irods_backend,
                        },
                    )
                )
        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to ACTIVE',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'status': ZONE_STATUS_ACTIVE,
                    'status_info': 'Available with write access for user',
                },
                force_fail=force_fail,
            )
        )
