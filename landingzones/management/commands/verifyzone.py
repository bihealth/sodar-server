"""Verifyzone management command"""

import sys

from irods.path import iRODSPath

from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.plugins import PluginAPI

import landingzones.constants as lc
from landingzones.models import LandingZone


logger = ManagementCommandLogger(__name__)
plugin_api = PluginAPI()


# Local constants
APP_NAME = 'landingzones'
MOVE_EVENT_NOT_FOUND_MSG = 'Timeline zone_move event not found'
MOVE_NOT_SUCCESSFUL_MSG = 'Zone not successfully moved'
NO_TL_EXTRA_DATA_MSG = 'Extra data not present in timeline event'


class Command(BaseCommand):
    """Command to submit landing_zone_verify taskflow on a moved zone"""

    help = 'Submit landing zone verification taskflow'

    @classmethod
    def _fail(cls, msg):
        """Fail with logged error"""
        logger.error(msg)
        sys.exit(1)

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--sync',
            dest='sync',
            action='store_true',
            default=False,
            required=False,
            help='Run in synchronous mode (only recommended in testing and '
            'development)',
        )
        parser.add_argument(
            '-z',
            '--zone',
            dest='zone',
            type=str,
            required=True,
            help='Landing zone from which files were moved',
        )

    def handle(self, *args, **options):
        sync_mode = options.get('sync', False)
        zone_uuid = options.get('zone')
        zone = LandingZone.objects.filter(sodar_uuid=zone_uuid).first()
        if not zone:
            return self._fail(f'Zone not found with UUID: {zone_uuid}')
        irods_backend = plugin_api.get_backend_api('omics_irods')
        taskflow = PluginAPI.get_backend_api('taskflow')
        timeline = plugin_api.get_backend_api('timeline_backend')
        if any([b is None for b in [irods_backend, taskflow, timeline]]):
            return self._fail('Required backends not enabled')

        # HACK: Get file list from timeline event (see issue #2327)
        TimelineEvent, TimelineEventObjectRef, _ = timeline.get_models()
        obj_ref = (
            TimelineEventObjectRef.objects.filter(
                object_uuid=zone.sodar_uuid, event__event_name='zone_move'
            )
            .order_by('-pk')
            .first()
        )
        if not obj_ref:
            return self._fail(MOVE_EVENT_NOT_FOUND_MSG)
        tl_event = obj_ref.event
        event_status = tl_event.get_status()
        if not event_status or event_status.status_type != lc.ZONE_STATUS_OK:
            return self._fail(MOVE_NOT_SUCCESSFUL_MSG)
        if 'files' not in tl_event.extra_data:
            return self._fail(NO_TL_EXTRA_DATA_MSG)
        # TODO: Check to ensure no verify tasks running in celery for same zone?

        # Set up flow data
        # HACK: landing_zone_verify expects full zone file paths
        zone_path = irods_backend.get_path(zone)
        file_paths = [
            iRODSPath(zone_path, p) for p in tl_event.extra_data['files']
        ]
        # TODO: Reduce repetition between this and SubmitZoneVerifyFlowTask
        tl_event = timeline.add_event(
            project=zone.project,
            app_name=APP_NAME,
            user=None,
            event_name='zone_verify',
            description='Verify files moved from landing zone {zone} '
            'for {user} in {assay}',
            status_type=timeline.TL_STATUS_SUBMIT,
        )
        tl_event.add_object(obj=zone, label='zone', name=zone.title)
        tl_event.add_object(
            obj=zone.user, label='user', name=zone.user.username
        )
        tl_event.add_object(
            obj=zone.assay, label='assay', name=zone.assay.get_name()
        )

        # Submit flow asynchrnonously
        logger.info(
            f'Submitting landing_zone_verify taskflow for zone "{zone.title}" '
            f'({zone.sodar_uuid}) in project {zone.project.get_log_title()}..'
        )
        try:
            flow_data = {
                'zone_uuid': str(zone.sodar_uuid),
                'file_paths': file_paths,
            }
            taskflow.submit(
                project=zone.project,
                user=None,
                flow_name='landing_zone_verify',
                flow_data=flow_data,
                async_mode=not sync_mode,
                tl_event=tl_event,
            )
            if sync_mode:
                logger.info('Verification done')
                tl_event.set_status(timeline.TL_STATUS_OK)
            else:
                logger.info('Flow submit OK, see timeline for status')
            return None
        except Exception as ex:
            return self._fail(f'Exception in submitting flow: {ex}')
