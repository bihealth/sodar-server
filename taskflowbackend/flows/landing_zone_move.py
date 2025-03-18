from django.conf import settings

# Landingzones dependency
from landingzones.constants import (
    ZONE_STATUS_MOVED,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_MOVING,
)
import landingzones.tasks_taskflow as lz_tasks
from landingzones.models import LandingZone

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


SAMPLE_COLL = settings.IRODS_SAMPLE_COLL
ZONE_INFO_CHECK = 'Checking availability and file types of {count} file{plural}'
ZONE_INFO_CALC = 'Calculating missing checksums in iRODS'
ZONE_INFO_VALIDATE = 'Validating {count} file{plural}'
ZONE_INFO_READ_ONLY = ', write access disabled'


class Flow(BaseLinearFlow):
    """
    Flow for validating and moving files from a landing zone to the
    sample data collection in iRODS.
    """

    def validate(self):
        self.supported_modes = ['sync', 'async']
        self.required_fields = ['zone_uuid']
        return super().validate()

    def build(self, force_fail=False):
        validate_only = self.flow_data.get('validate_only', False)
        zone = LandingZone.objects.get(sodar_uuid=self.flow_data['zone_uuid'])
        project_group = self.irods_backend.get_user_group_name(self.project)
        sample_path = self.irods_backend.get_path(zone.assay)
        zone_path = self.irods_backend.get_path(zone)
        admin_name = self.irods.username
        file_name_prohibit = self.flow_data.get('file_name_prohibit')

        # HACK: Set zone status in the Django site
        zone.set_status(
            ZONE_STATUS_PREPARING,
            'Preparing transaction for validation{}'.format(
                ' and moving' if not validate_only else ''
            ),
        )

        # Get landing zone data object and collection paths from iRODS
        zone_all = self.irods_backend.get_objects(
            self.irods, zone_path, include_md5=True, include_colls=True
        )
        zone_objects = [o['path'] for o in zone_all if o['type'] == 'obj']
        zone_objects_nomd5 = [
            p for p in zone_objects if p[p.rfind('.') + 1 :].lower() != 'md5'
        ]
        zone_objects_md5 = [
            p for p in zone_objects if p not in zone_objects_nomd5
        ]
        file_count = len(zone_objects_nomd5)
        file_count_msg_plural = 's' if file_count != 1 else ''

        # Get all collections with root path
        zone_all_colls = [zone_path]
        zone_all_colls += [o['path'] for o in zone_all if o['type'] == 'coll']
        # Get list of collections containing files (ignore empty colls)
        zone_object_colls = list(set([p[: p.rfind('/')] for p in zone_objects]))
        # Convert paths to collections inside sample collection
        zone_path_len = len(zone_path.split('/'))
        sample_colls = [
            sample_path + '/' + '/'.join(p.split('/')[zone_path_len:])
            for p in zone_object_colls
            if len(p.split('/')) > zone_path_len
        ]

        # print('sample_path: {}'.format(sample_path))                # DEBUG
        # print('zone_objects: {}'.format(zone_objects))              # DEBUG
        # print('zone_objects_nomd5: {}'.format(zone_objects_nomd5))  # DEBUG
        # print('zone_all_colls: {}'.format(zone_all_colls))          # DEBUG
        # print('zone_object_colls: {}'.format(zone_object_colls))    # DEBUG
        # print('sample_colls: {}'.format(sample_colls))              # DEBUG

        # Set up task to set landing zone status to failed
        self.add_task(
            lz_tasks.RevertLandingZoneFailTask(
                name='Set landing zone status to FAILED on revert',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'flow_name': self.flow_name,
                    'info_prefix': 'Failed to {} landing zone files'.format(
                        'validate' if validate_only else 'move'
                    ),
                    'extra_data': {'validate_only': int(validate_only)},
                },
            )
        )

        if not validate_only:
            self.add_task(
                irods_tasks.SetInheritanceTask(
                    name='Set inheritance for landing zone collection '
                    '{}'.format(zone_path),
                    irods=self.irods,
                    inject={'path': zone_path, 'inherit': True},
                )
            )
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Set admin "{}" owner access for zone coll {}'.format(
                        admin_name, zone_path
                    ),
                    irods=self.irods,
                    inject={
                        'access_name': 'own',
                        'path': zone_path,
                        'user_name': admin_name,
                        'irods_backend': self.irods_backend,
                    },
                )
            )
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Set user "{}" read access for zone collection '
                    '{}'.format(zone.user.username, zone_path),
                    irods=self.irods,
                    inject={
                        'access_name': 'read',
                        'path': zone_path,
                        'user_name': zone.user.username,
                        'irods_backend': self.irods_backend,
                    },
                )
            )
            # Workaround for sodar#297
            # If script user is set, set read access
            if self.flow_data.get('script_user'):
                self.add_task(
                    irods_tasks.SetAccessTask(
                        name='Set script user "{}" read access to landing '
                        'zone'.format(self.flow_data['script_user']),
                        irods=self.irods,
                        inject={
                            'access_name': 'read',
                            'path': zone_path,
                            'user_name': self.flow_data['script_user'],
                            'irods_backend': self.irods_backend,
                        },
                    )
                )

        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to VALIDATING (check)',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'status': ZONE_STATUS_VALIDATING,
                    'status_info': ZONE_INFO_CHECK.format(
                        count=file_count, plural=file_count_msg_plural
                    )
                    + (ZONE_INFO_READ_ONLY if not validate_only else ''),
                    'flow_name': self.flow_name,
                },
            )
        )
        if file_name_prohibit:
            self.add_task(
                irods_tasks.BatchCheckFileSuffixTask(
                    name='Batch check file types for zone data objects',
                    irods=self.irods,
                    inject={
                        'file_paths': zone_objects_nomd5,
                        'suffixes': file_name_prohibit,
                        'zone_path': zone_path,
                    },
                )
            )
        self.add_task(
            irods_tasks.BatchCheckFileExistTask(
                name='Batch check file and MD5 checksum file existence for '
                'zone data objects',
                irods=self.irods,
                inject={
                    'file_paths': zone_objects_nomd5,
                    'md5_paths': zone_objects_md5,
                    'zone_path': zone_path,
                },
            )
        )

        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to VALIDATING (calculate)',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'status': ZONE_STATUS_VALIDATING,
                    'status_info': ZONE_INFO_CALC
                    + (ZONE_INFO_READ_ONLY if not validate_only else ''),
                    'flow_name': self.flow_name,
                },
            )
        )
        self.add_task(
            irods_tasks.BatchCalculateChecksumTask(
                name='Batch calculate missing checksums in iRODS',
                irods=self.irods,
                inject={
                    'landing_zone': zone,
                    'file_paths': zone_objects_nomd5,
                    'force': False,
                },
            )
        )
        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to VALIDATING (compare)',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'status': ZONE_STATUS_VALIDATING,
                    'status_info': ZONE_INFO_VALIDATE.format(
                        count=file_count, plural=file_count_msg_plural
                    )
                    + (ZONE_INFO_READ_ONLY if not validate_only else ''),
                    'flow_name': self.flow_name,
                },
            )
        )
        self.add_task(
            irods_tasks.BatchValidateChecksumsTask(
                name='Batch validate MD5 checksums of {} data objects'.format(
                    file_count
                ),
                irods=self.irods,
                inject={
                    'landing_zone': zone,
                    'paths': zone_objects_nomd5,
                    'zone_path': zone_path,
                },
            )
        )

        # Return at this point if validate_only
        if validate_only:
            self.add_task(
                lz_tasks.SetLandingZoneStatusTask(
                    name='Set landing zone status to ACTIVE',
                    project=self.project,
                    inject={
                        'landing_zone': zone,
                        'status': ZONE_STATUS_ACTIVE,
                        'status_info': 'Successfully validated '
                        '{} file{}'.format(
                            file_count,
                            's' if file_count != 1 else '',
                        ),
                        'flow_name': self.flow_name,
                        'extra_data': {'validate_only': int(validate_only)},
                    },
                )
            )
            return

        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to MOVING',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'status': ZONE_STATUS_MOVING,
                    'status_info': 'Validation OK, '
                    'moving {} files into {}'.format(file_count, SAMPLE_COLL),
                    'flow_name': self.flow_name,
                },
            )
        )
        if sample_colls:
            self.add_task(
                irods_tasks.BatchCreateCollectionsTask(
                    name='Create collections in {}'.format(SAMPLE_COLL),
                    irods=self.irods,
                    inject={'paths': sample_colls},
                )
            )
        self.add_task(
            irods_tasks.BatchMoveDataObjectsTask(
                name='Move {} files and set project group '
                'read access'.format(len(zone_objects)),
                irods=self.irods,
                inject={
                    'landing_zone': zone,
                    'src_root': zone_path,
                    'dest_root': sample_path,
                    'src_paths': zone_objects,
                    'access_name': 'read',
                    'user_name': project_group,
                    'irods_backend': self.irods_backend,
                },
            )
        )
        self.add_task(
            irods_tasks.SetAccessTask(
                name='Remove user "{}" access from sample collection {}'.format(
                    zone.user.username, sample_path
                ),
                irods=self.irods,
                inject={
                    'access_name': 'null',
                    'path': sample_path,
                    'user_name': zone.user.username,
                    'irods_backend': self.irods_backend,
                },
            )
        )
        # If script user is set, remove access
        if self.flow_data.get('script_user'):
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Remove script user "{}" access to sample path '
                    'zone'.format(self.flow_data['script_user']),
                    irods=self.irods,
                    inject={
                        'access_name': 'null',
                        'path': sample_path,
                        'user_name': self.flow_data['script_user'],
                        'irods_backend': self.irods_backend,
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
        self.add_task(
            lz_tasks.SetLandingZoneStatusTask(
                name='Set landing zone status to MOVED',
                project=self.project,
                inject={
                    'landing_zone': zone,
                    'status': ZONE_STATUS_MOVED,
                    'status_info': 'Successfully moved {} file{}, landing zone '
                    'removed'.format(
                        file_count, 's' if file_count != 1 else ''
                    ),
                    'flow_name': self.flow_name,
                    'extra_data': {'file_count': file_count},
                },
                force_fail=force_fail,
            )
        )
