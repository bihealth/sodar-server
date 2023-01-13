"""Taskflow tasks for the landingzones app"""

import logging

from django.conf import settings
from django.contrib import auth
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.email import send_generic_mail, get_email_user
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.tasks_celery import update_project_cache_task

# Taskflowbackend dependency
from taskflowbackend.tasks.sodar_tasks import SODARBaseTask

from landingzones.models import STATUS_BUSY


User = auth.get_user_model()
logger = logging.getLogger(__name__)
app_settings = AppSettingAPI()


# Local constants
APP_NAME = 'landingzones'
STATUS_INFO_LEN = 1024
STATUS_TRUNCATE_MSG = '... <TRUNCATED>'

EMAIL_MSG_MOVED = r'''
Data was successfully validated and moved into the project
sample data repository from your landing zone.

You can browse the assay metadata and related files at
the following URL:
{url}

Project: {project}
Assay: {assay}
Landing zone: {zone}
Zone owner: {user}
Zone UUID: {zone_uuid}

Status message:
"{status_info}"'''.lstrip()

EMAIL_MSG_FAILED = r'''
Validating and moving data from your landing zone into the
project sample data repository has failed. Please verify your
data and request for support if the problem persists.

Manage your landing zone at the following URL:
{url}

Project: {project}
Assay: {assay}
Landing zone: {zone}
Zone owner: {user}
Zone UUID: {zone_uuid}

Status message:
"{status_info}"
'''.lstrip()

EMAIL_MSG_MEMBER = r'''
{user} has uploaded {file_count} file{file_count_suffix}
into assay "{assay}"
under the project "{project}".

Message from zone owner:
{user_message}

You can browse the assay metadata and related files at
the following URL:
{url}
'''.lstrip()


class BaseLandingZoneStatusTask(SODARBaseTask):
    """Base task class for landing zone status updates"""

    @classmethod
    def _add_owner_alert(
        cls, app_alerts, zone, flow_name, file_count, validate_only
    ):
        """Add app alert for zone owner for finished actions"""
        alert_level = (
            'DANGER' if zone.status in ['FAILED', 'NOT CREATED'] else 'SUCCESS'
        )
        alert_url = reverse(
            'landingzones:list',
            kwargs={'project': zone.project.sodar_uuid},
        )

        if zone.status == 'MOVED':
            alert_msg = 'Successfully moved {} file{} from landing zone'.format(
                file_count, 's' if file_count != 1 else ''
            )
            alert_url = reverse(
                'samplesheets:project_sheets',
                kwargs={'project': zone.project.sodar_uuid},
            )
        elif validate_only and zone.status == 'ACTIVE':
            alert_msg = 'Successfully validated files in landing zone'
        elif validate_only and zone.status == 'FAILED':
            alert_msg = 'Validation failed for landing zone'
        elif flow_name == 'landing_zone_move' and zone.status == 'FAILED':
            alert_msg = 'Failed to move files from landing zone'
        elif zone.status == 'DELETED':
            alert_msg = 'Deleted landing zone'
        elif flow_name == 'landing_zone_delete' and zone.status == 'FAILED':
            alert_msg = 'Failed to delete landing zone'
        else:
            logger.error(
                'Unknown input for _add_owner_alert(): flow_name={}; '
                'status={}'.format(flow_name, zone.status)
            )
            return

        alert_msg += ': {}'.format(zone.title)
        if validate_only:
            alert_name = 'validate'
        elif flow_name == 'landing_zone_delete':
            alert_name = 'delete'
        else:
            alert_name = 'move'
        app_alerts.add_alert(
            app_name=APP_NAME,
            alert_name='zone_' + alert_name,
            user=zone.user,
            level=alert_level,
            url=alert_url,
            message=alert_msg,
            project=zone.project,
        )

    @classmethod
    def _add_member_move_alert(cls, app_alerts, zone, user, file_count):
        """Add app alert for project member"""
        alert_msg = '{} file{} uploaded by {}.'.format(
            file_count,
            's' if file_count != 1 else '',
            zone.user.username,
        )
        if zone.user_message:
            alert_msg += ': {}'.format(zone.user_message)
        app_alerts.add_alert(
            app_name=APP_NAME,
            alert_name='zone_move_member',
            user=user,
            level='INFO',
            url=reverse(
                'samplesheets:project_sheets',
                kwargs={'project': zone.project.sodar_uuid},
            ),
            message=alert_msg,
            project=zone.project,
        )

    @classmethod
    def _send_owner_move_email(cls, zone):
        """Send email to zone owner on zone move/validate"""
        server_host = settings.SODAR_API_DEFAULT_HOST.geturl()
        subject_body = 'Landing zone {}: {} / {}'.format(
            zone.status.lower(),
            zone.project.title,
            zone.title,
        )
        if zone.status == 'MOVED':
            message_body = EMAIL_MSG_MOVED
            email_url = (
                server_host
                + reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': zone.project.sodar_uuid},
                )
                + '#/assay/'
                + str(zone.assay.sodar_uuid)
            )
        else:  # FAILED
            message_body = EMAIL_MSG_FAILED
            email_url = (
                server_host
                + reverse(
                    'landingzones:list',
                    kwargs={'project': zone.project.sodar_uuid},
                )
                + '#'
                + str(zone.sodar_uuid)
            )
        message_body = message_body.format(
            zone=zone.title,
            project=zone.project.title,
            assay=zone.assay.get_display_name(),
            user=get_email_user(zone.user),
            zone_uuid=str(zone.sodar_uuid),
            status_info=zone.status_info,
            url=email_url,
        )
        send_generic_mail(subject_body, message_body, [zone.user])

    @classmethod
    def _send_member_move_email(cls, member, zone, file_count):
        """Send member email on landing zone move"""
        server_host = settings.SODAR_API_DEFAULT_HOST.geturl()
        subject_body = 'Files uploaded in project "{}" by {}'.format(
            zone.project.title,
            zone.user.get_full_name(),
        )
        message_body = EMAIL_MSG_MEMBER
        email_url = (
            server_host
            + reverse(
                'samplesheets:project_sheets',
                kwargs={'project': zone.project.sodar_uuid},
            )
            + '#/assay/'
            + str(zone.assay.sodar_uuid)
        )
        message_body = message_body.format(
            project=zone.project.title,
            assay=zone.assay.get_display_name(),
            user=get_email_user(zone.user),
            file_count=file_count,
            file_count_suffix='s' if file_count != 1 else '',
            user_message=zone.user_message or 'N/A',
            url=email_url,
        )
        send_generic_mail(subject_body, message_body, [member])

    @classmethod
    def set_status(cls, zone, flow_name, status, status_info, extra_data=None):
        """
        Set landing zone status. Notify users by alerts and emails if
        applicable.

        :param zone: LandingZone object
        :param flow_name: Name of flow (string)
        :param status: Zone status (string)
        :param status_info: Detailed zone status info (string)
        :param extra_data: Optional extra data (dict)
        """
        app_alerts = get_backend_api('appalerts_backend')

        # Truncate status info (fix for #1307)
        if len(status_info) >= STATUS_INFO_LEN - len(STATUS_TRUNCATE_MSG):
            status_info = (
                status_info[: STATUS_INFO_LEN - len(STATUS_TRUNCATE_MSG)]
                + STATUS_TRUNCATE_MSG
            )
        zone.set_status(
            status=status,
            status_info=status_info if status_info else None,
        )
        zone.refresh_from_db()

        if not extra_data:
            extra_data = {}
        file_count = extra_data.get('file_count', 0)
        validate_only = extra_data.get('validate_only', False)

        # Create alert and send email for zone owner for finished actions
        # NOTE: Create is excluded as this should be virtually instantaneous
        if (
            zone.status not in STATUS_BUSY
            and flow_name != 'landing_zone_create'
            and (file_count > 0 or zone.status != 'MOVED')
        ):
            if app_alerts:
                try:
                    cls._add_owner_alert(
                        app_alerts,
                        zone,
                        flow_name,
                        file_count,
                        validate_only,
                    )
                except Exception as ex:  # NOTE: We won't fail/revert here
                    logger.error(
                        'Exception in _add_owner_alert(): {}'.format(ex)
                    )
            # NOTE: We only send email on move
            if (
                settings.PROJECTROLES_SEND_EMAIL
                and flow_name == 'landing_zone_move'
                and not validate_only
            ):
                try:
                    cls._send_owner_move_email(zone)
                except Exception as ex:  # NOTE: We won't fail/revert here
                    logger.error(
                        'Exception in _send_owner_move_email(): {}'.format(ex)
                    )

        # Create alerts and send emails to other project members on move
        member_notify = app_settings.get(
            APP_NAME, 'member_notify_move', project=zone.project
        )
        if member_notify and zone.status == 'MOVED' and file_count > 0:
            members = list(
                set(
                    [
                        r.user
                        for r in zone.project.get_all_roles()
                        if r.user != zone.user
                    ]
                )
            )
            for member in members:
                if app_alerts:
                    try:
                        cls._add_member_move_alert(
                            app_alerts=app_alerts,
                            zone=zone,
                            user=member,
                            file_count=file_count,
                        )
                    except Exception as ex:
                        logger.error(
                            'Exception in _add_member_move_alert(): {}'.format(
                                ex
                            )
                        )
                if settings.PROJECTROLES_SEND_EMAIL:
                    try:
                        cls._send_member_move_email(member, zone, file_count)
                    except Exception as ex:  # NOTE: We won't fail/revert here
                        logger.error(
                            'Exception in _send_member_move_email(): {}'.format(
                                ex
                            )
                        )

        # If zone is removed by moving or deletion, call plugin function
        # TODO: TBD: Move into separate task?
        if status in ['MOVED', 'DELETED']:
            from .plugins import get_zone_config_plugin  # See issue #269

            config_plugin = get_zone_config_plugin(zone)
            if config_plugin:
                try:
                    config_plugin.cleanup_zone(zone)
                except Exception as ex:
                    logger.error(
                        'Unable to cleanup zone "{}" with plugin '
                        '"{}": {}'.format(zone.title, config_plugin.name, ex)
                    )

        # Update cache
        # TODO: TBD: Move into separate task?
        if status == 'MOVED' and settings.SHEETS_ENABLE_CACHE:
            try:
                update_project_cache_task.delay(
                    project_uuid=str(zone.project.sodar_uuid),
                    user_uuid=str(zone.user.sodar_uuid),
                    add_alert=True,
                    alert_msg='Moved landing zone "{}".'.format(zone.title),
                )
            except Exception as ex:
                logger.error(
                    'Unable to run project cache update task: {}'.format(ex)
                )


class SetLandingZoneStatusTask(BaseLandingZoneStatusTask):
    """Set LandingZone status"""

    def execute(
        self,
        landing_zone,
        flow_name,
        status,
        status_info,
        extra_data=None,
        *args,
        **kwargs
    ):
        self.set_status(
            landing_zone, flow_name, status, status_info, extra_data
        )
        self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(
        self,
        landing_zone,
        flow_name,
        status,
        status_info,
        extra_data=None,
        *args,
        **kwargs
    ):
        pass  # Disabled, call RevertLandingZoneStatusTask to revert


class RevertLandingZoneFailTask(BaseLandingZoneStatusTask):
    """Set LandingZone status in case of failure"""

    def execute(
        self,
        landing_zone,
        flow_name,
        info_prefix,
        status='FAILED',
        extra_data=None,
        *args,
        **kwargs
    ):
        super().execute(*args, **kwargs)

    def revert(
        self,
        landing_zone,
        flow_name,
        info_prefix,
        status='FAILED',
        extra_data=None,
        *args,
        **kwargs
    ):
        status_info = info_prefix
        for k, v in kwargs['flow_failures'].items():
            status_info += ': '
            status_info += str(v.exception) if v.exception else 'unknown error'
        self.set_status(
            landing_zone, flow_name, status, status_info, extra_data
        )
