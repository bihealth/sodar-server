from django.conf import settings

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks, sodar_tasks


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT


class Flow(BaseLinearFlow):
    """Flow for deleting a landing zone from a project and a user in iRODS"""

    def validate(self):
        self.require_lock = False  # Project lock not required for this flow
        self.supported_modes = ['sync', 'async']
        self.required_fields = ['landing_zone']
        return super().validate()

    def build(self, force_fail=False):
        zone = self.flow_data['landing_zone']
        zone_path = self.irods_backend.get_path(zone)
        zone_uuid = str(zone.sodar_uuid)

        # If async, set up task to set landing zone status to failed
        if self.request_mode == 'async':
            self.add_task(
                sodar_tasks.RevertLandingZoneFailTask(
                    name='Set landing zone status to FAILED on revert',
                    project_uuid=self.project_uuid,
                    inject={
                        'zone_uuid': zone_uuid,
                        'flow_name': self.flow_name,
                        'info_prefix': 'Failed to delete landing zone',
                    },
                )
            )
        # Set zone status to DELETING
        self.add_task(
            sodar_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to DELETING',
                project_uuid=self.project_uuid,
                inject={
                    'zone_uuid': zone_uuid,
                    'status': 'DELETING',
                    'status_info': 'Deleting landing zone',
                    'flow_name': self.flow_name,
                },
            )
        )
        self.add_task(
            irods_tasks.RemoveCollectionTask(
                name='Remove the landing zone collection',
                irods=self.irods,
                inject={'path': zone_path},
            )
        )
        # Set zone status to DELETING
        self.add_task(
            sodar_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to DELETED',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'status': 'DELETED',
                    'status_info': 'Landing zone deleted',
                },
            )
        )
