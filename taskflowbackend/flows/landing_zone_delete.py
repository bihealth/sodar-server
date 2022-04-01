from config import settings

from .base_flow import BaseLinearFlow
from apis.irods_utils import get_landing_zone_path
from tasks import sodar_tasks, irods_tasks


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT


class Flow(BaseLinearFlow):
    """Flow for deleting a landing zone from a project and a user in iRODS"""

    def validate(self):
        self.require_lock = False  # Project lock not required for this flow
        self.supported_modes = ['sync', 'async']
        self.required_fields = [
            'zone_title',
            'zone_uuid',
            'assay_path',
            'user_name',
        ]
        return super().validate()

    def build(self, force_fail=False):

        ########
        # Setup
        ########

        zone_path = get_landing_zone_path(
            project_uuid=self.project_uuid,
            user_name=self.flow_data['user_name'],
            assay_path=self.flow_data['assay_path'],
            zone_title=self.flow_data['zone_title'],
            zone_config=self.flow_data['zone_config'],
        )

        ########
        # Tasks
        ########

        # If async, set up task to set landing zone status to failed
        if self.request_mode == 'async':
            self.add_task(
                sodar_tasks.RevertLandingZoneFailTask(
                    name='Set landing zone status to FAILED on revert',
                    sodar_api=self.sodar_api,
                    project_uuid=self.project_uuid,
                    inject={
                        'zone_uuid': self.flow_data['zone_uuid'],
                        'flow_name': self.flow_name,
                        'info_prefix': 'Failed to delete landing zone',
                    },
                )
            )

        # Set zone status to DELETING
        self.add_task(
            sodar_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to DELETING',
                sodar_api=self.sodar_api,
                project_uuid=self.project_uuid,
                inject={
                    'zone_uuid': self.flow_data['zone_uuid'],
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

        ##############
        # SODAR Tasks
        ##############

        # Set zone status to DELETING
        self.add_task(
            sodar_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to DELETED',
                sodar_api=self.sodar_api,
                project_uuid=self.project_uuid,
                inject={
                    'zone_uuid': self.flow_data['zone_uuid'],
                    'flow_name': self.flow_name,
                    'status': 'DELETED',
                    'status_info': 'Landing zone deleted',
                },
            )
        )
