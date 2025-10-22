from irods.path import iRODSPath

from django.conf import settings

# Landingzones dependency
from landingzones.models import LandingZone

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


SAMPLE_COLL = settings.IRODS_SAMPLE_COLL


class Flow(BaseLinearFlow):
    """
    Flow for verifying files moved from landing zone into the project sample
    data collection.
    """

    def validate(self) -> bool:
        self.require_lock = False
        self.supported_modes = ['sync', 'async']
        self.required_fields = ['zone_uuid', 'file_paths']
        return super().validate()

    def build(self, force_fail: bool = False):
        zone = LandingZone.objects.get(sodar_uuid=self.flow_data['zone_uuid'])
        zone_path = self.irods_backend.get_path(zone)
        assay_path = self.irods_backend.get_path(zone.assay)
        # Convert file paths from zone to assay
        file_paths = [
            iRODSPath(assay_path, p.split(zone_path + '/')[1])
            for p in self.flow_data['file_paths']
        ]
        file_count = len(file_paths)

        self.add_task(
            irods_tasks.BatchCalculateChecksumTask(
                name='Batch calculate all file checksums in iRODS',
                irods=self.irods,
                inject={
                    'landing_zone': None,  # No zone to update
                    'file_paths': file_paths,
                    'force': True,  # Force recalculating of all checksums
                },
            )
        )

        self.add_task(
            irods_tasks.BatchVerifySampleChecksumsTask(
                name=f'Batch validate checksums of {file_count} data objects',
                irods=self.irods,
                inject={
                    'file_paths': file_paths,
                    'assay': zone.assay,
                    'user': self.user,
                    'irods_backend': self.irods_backend,
                },
            )
        )
