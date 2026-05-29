from irods.exception import GroupDoesNotExist

# Landingzones dependency
import landingzones.tasks_taskflow as lz_tasks
from landingzones.constants import ZONE_STATUS_ACTIVE, STATUS_INFO_ADMIN_RESET
from landingzones.models import LandingZone

from taskflowbackend.constants import (
    IRODS_ACCESS_DELETE_OBJ,
    IRODS_ACCESS_READ_OBJ,
)
from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


class Flow(BaseLinearFlow):
    """
    Flow for resetting landing zone status to ACTIVE with write access for zone
    owner and project owner group.
    """

    def validate(self) -> bool:
        self.require_lock = False
        self.supported_modes = ['sync', 'async']
        self.required_fields = ['zone_uuid', 'restrict_colls']
        return super().validate()

    def build(self, force_fail: bool = False):
        zone = LandingZone.objects.get(sodar_uuid=self.flow_data['zone_uuid'])
        zone_path = self.irods_backend.get_path(zone)
        owner_group = self.irods_backend.get_group_name(self.project, True)
        try:  # Support for legacy zones
            self.irods.groups.get(owner_group)
            owner_group_exists = True
        except GroupDoesNotExist:
            owner_group_exists = False
        root_access = (
            IRODS_ACCESS_READ_OBJ
            if self.flow_data['restrict_colls']
            else IRODS_ACCESS_DELETE_OBJ
        )
        zone_coll = self.irods.collections.get(zone_path)
        colls_full_path = [c.path for c in zone_coll.subcollections]

        # Set collection inheritance
        self.add_task(
            irods_tasks.SetInheritanceTask(
                name=f'Set inheritance for landing zone collection {zone_path}',
                irods=self.irods,
                inject={'path': zone_path, 'inherit': True},
            )
        )
        # Set user access to zone collection
        # Only set delete access to root level zone coll if not enforcing colls
        self.add_task(
            irods_tasks.SetAccessTask(
                name=f'Set user {root_access} access to landing zone root',
                irods=self.irods,
                inject={
                    'access_name': root_access,
                    'path': zone_path,
                    'user_name': zone.user.username,
                    'irods_backend': self.irods_backend,
                },
            )
        )
        # Set project owner group access to zone collection
        if owner_group_exists:  # Support for legacy zones
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Set project owner group access to landing zone root',
                    irods=self.irods,
                    inject={
                        'access_name': root_access,
                        'path': zone_path,
                        'user_name': owner_group,
                        'irods_backend': self.irods_backend,
                    },
                )
            )
        # If script user is set, add write access
        # NOTE: This will intentionally fail if user has not been created!
        if self.flow_data.get('script_user'):
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Set script user "{}" delete_object access to landing '
                    'zone'.format(self.flow_data['script_user']),
                    irods=self.irods,
                    inject={
                        'access_name': IRODS_ACCESS_DELETE_OBJ,
                        'path': zone_path,
                        'user_name': self.flow_data['script_user'],
                        'irods_backend': self.irods_backend,
                    },
                )
            )
        # Enforce collection access if set
        if self.flow_data['restrict_colls']:
            self.add_task(
                irods_tasks.BatchSetAccessTask(
                    name='Batch set user delete_object access to created '
                    'collections',
                    irods=self.irods,
                    inject={
                        'access_name': IRODS_ACCESS_DELETE_OBJ,
                        'paths': colls_full_path,
                        'user_name': zone.user.username,
                        'irods_backend': self.irods_backend,
                    },
                )
            )
            self.add_task(
                irods_tasks.BatchSetAccessTask(
                    name='Batch set owner group delete_object access to '
                    'created collections',
                    irods=self.irods,
                    inject={
                        'access_name': IRODS_ACCESS_DELETE_OBJ,
                        'paths': colls_full_path,
                        'user_name': owner_group,
                        'irods_backend': self.irods_backend,
                    },
                )
            )
        # Finally, set zone status to active
        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to ACTIVE',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'status': ZONE_STATUS_ACTIVE,
                    'status_info': STATUS_INFO_ADMIN_RESET,
                },
                force_fail=force_fail,
            )
        )
