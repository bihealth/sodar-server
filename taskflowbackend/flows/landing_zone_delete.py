from landingzones.constants import ZONE_STATUS_DELETING, ZONE_STATUS_DELETED
from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks, sodar_tasks

# Landingzones dependency
import landingzones.tasks_taskflow as lz_tasks
from landingzones.models import LandingZone


class Flow(BaseLinearFlow):
    """Flow for deleting a landing zone from a project and a user in iRODS"""

    def validate(self) -> bool:
        self.require_lock = False  # Project lock not required for this flow
        self.supported_modes = ['sync', 'async']
        self.required_fields = ['zone_uuid']
        return super().validate()

    def build(self, force_fail: bool = False):
        # Setup
        zone = LandingZone.objects.get(sodar_uuid=self.flow_data['zone_uuid'])
        zone_path = self.irods_backend.get_path(zone)
        zone_files = []
        zone_stats = {}
        if self.tl_event:  # Get file list for timeline event extra data
            zone_objs = self.irods_backend.get_objects(
                self.irods,
                zone_path,
                include_checksum=False,
                include_colls=False,
            )
            zone_files = [o['path'][len(zone_path) + 1 :] for o in zone_objs]
            zone_stats = self.irods_backend.get_stats(self.irods, zone_path)

        # If async, set up task to set landing zone status to failed
        if self.request_mode == 'async':
            self.add_task(
                lz_tasks.RevertLandingZoneFailTask(
                    name='Set landing zone status to FAILED on revert',
                    project=self.project,
                    inject={
                        'landing_zone': zone,
                        'flow_name': self.flow_name,
                        'info_prefix': 'Failed to delete landing zone',
                    },
                )
            )
        # Set zone status to DELETING
        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to DELETING',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'status': ZONE_STATUS_DELETING,
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
        # Set zone status to DELETED
        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to DELETED',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'status': ZONE_STATUS_DELETED,
                    'status_info': 'Landing zone deleted',
                },
            )
        )
        # Add timeline extra data
        if self.tl_event:
            self.add_task(
                sodar_tasks.TimelineEventExtraDataUpdateTask(
                    name='Update timeline event extra data with file list',
                    project=self.project,
                    inject={
                        'tl_event': self.tl_event,
                        'extra_data': {
                            'files': zone_files,
                            'total_size': zone_stats.get('total_size'),
                        },
                    },
                )
            )
