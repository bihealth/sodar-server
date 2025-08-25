"""Taskflow tasks for the landingzones app"""

import logging

from typing import Any, Optional

from django.conf import settings
from django.contrib import auth
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.email import send_generic_mail, get_email_user
from projectroles.models import SODARUser
from projectroles.plugins import PluginAPI

# Samplesheets dependency
from samplesheets.tasks_celery import update_project_cache_task

# Taskflowbackend dependency
from taskflowbackend.tasks.sodar_tasks import SODARBaseTask

from landingzones.constants import (
    STATUS_BUSY,
    STATUS_FINISHED,
    ZONE_STATUS_FAILED,
    ZONE_STATUS_NOT_CREATED,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_DELETED,
)
from landingzones.models import LandingZone


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
plugin_api = PluginAPI()
User = auth.get_user_model()


# Local constants
APP_NAME = 'landingzones'

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
        cls,
        app_alerts: Any,
        zone: LandingZone,
        flow_name: str,
        file_count: int,
        validate_only: bool,
    ):
        """
        Add app alert for zone owner for finished actions.

        :param app_alerts: AppAlertAPI object
        :param zone: LandingZone object
        :param flow_name: String
        :param file_count: Integer
        :param validate_only: Boolean
        """
        alert_level = (
            'DANGER'
            if zone.status in [ZONE_STATUS_FAILED, ZONE_STATUS_NOT_CREATED]
            else 'SUCCESS'
        )
        alert_url = reverse(
            'landingzones:list',
            kwargs={'project': zone.project.sodar_uuid},
        )

        if zone.status == ZONE_STATUS_MOVED:
            alert_msg = 'Successfully moved {} file{} from landing zone'.format(
                file_count, 's' if file_count != 1 else ''
            )
            alert_url = reverse(
                'samplesheets:project_sheets',
                kwargs={'project': zone.project.sodar_uuid},
            )
        elif validate_only and zone.status == ZONE_STATUS_ACTIVE:
            alert_msg = 'Successfully validated files in landing zone'
        elif validate_only and zone.status == ZONE_STATUS_FAILED:
            alert_msg = 'Validation failed for landing zone'
        elif (
            flow_name == 'landing_zone_move'
            and zone.status == ZONE_STATUS_FAILED
        ):
            alert_msg = 'Failed to move files from landing zone'
        elif zone.status == ZONE_STATUS_DELETED:
            alert_msg = 'Deleted landing zone'
        elif (
            flow_name == 'landing_zone_delete'
            and zone.status == ZONE_STATUS_FAILED
        ):
            alert_msg = 'Failed to delete landing zone'
        else:
            logger.error(
                f'Unknown input for _add_owner_alert(): flow_name={flow_name}; '
                f'status={zone.status}'
            )
            return

        alert_msg += f': {zone.title}'
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
    def _add_member_move_alert(
        cls,
        app_alerts: Any,
        zone: LandingZone,
        user: SODARUser,
        file_count: int,
    ):
        """
        Add app alert for project member.

        :param app_alerts: AppAlertAPI object
        :param zone: LandingZone object
        :param user: SODARUser object
        :param file_count: Integer
        """
        alert_msg = '{} file{} uploaded by {}.'.format(
            file_count,
            's' if file_count != 1 else '',
            zone.user.username,
        )
        if zone.user_message:
            alert_msg += f': {zone.user_message}'
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
    def _send_owner_move_email(cls, zone: LandingZone):
        """
        Send email to zone owner on zone move/validate.

        :param zone: LandingZone object
        """
        server_host = settings.SODAR_API_DEFAULT_HOST.geturl()
        subject_body = (
            f'Landing zone {zone.status.lower()}: {zone.project.title} / '
            f'{zone.title}'
        )
        if zone.status == ZONE_STATUS_MOVED:
            message_body = EMAIL_MSG_MOVED
            email_url = server_host + zone.assay.get_url()
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
    def _send_member_move_email(
        cls, member: SODARUser, zone: LandingZone, file_count: int
    ):
        """
        Send member email on landing zone move.

        :param member: SODARUser object
        :param zone: LandingZone object
        :param file_count: Integer
        """
        server_host = settings.SODAR_API_DEFAULT_HOST.geturl()
        subject_body = (
            f'Files uploaded in project "{zone.project.title}" by '
            f'{zone.user.get_full_name()}'
        )
        message_body = EMAIL_MSG_MEMBER
        email_url = server_host + zone.assay.get_url()
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
    def set_status(
        cls,
        zone: LandingZone,
        flow_name: str,
        status: str,
        status_info: str,
        extra_data: Optional[dict] = None,
    ):
        """
        Set landing zone status. Notify users by alerts and emails if
        applicable.

        :param zone: LandingZone object
        :param flow_name: Name of flow (string)
        :param status: Zone status (string)
        :param status_info: Detailed zone status info (string)
        :param extra_data: Optional extra data (dict)
        """
        app_alerts = plugin_api.get_backend_api('appalerts_backend')
        # Refresh in case sheets have been replaced (see issue #1839)
        zone.refresh_from_db()
        zone.set_status(
            status=status,
            status_info=status_info if status_info else None,
        )

        if not extra_data:
            extra_data = {}
        file_count = extra_data.get('file_count', 0)
        validate_only = extra_data.get('validate_only', False)

        # Create alert and send email for zone owner for finished actions
        # NOTE: Create is excluded as this should be virtually instantaneous
        if (
            zone.status not in STATUS_BUSY
            and flow_name != 'landing_zone_create'
            and (file_count > 0 or zone.status != ZONE_STATUS_MOVED)
        ):
            if app_alerts and zone.user.is_active:
                try:
                    cls._add_owner_alert(
                        app_alerts,
                        zone,
                        flow_name,
                        file_count,
                        validate_only,
                    )
                except Exception as ex:  # NOTE: We won't fail/revert here
                    logger.error(f'Exception in _add_owner_alert(): {ex}')
            # NOTE: We only send email on move
            if (
                settings.PROJECTROLES_SEND_EMAIL
                and flow_name == 'landing_zone_move'
                and not validate_only
                and zone.user.is_active
                and app_settings.get(
                    APP_NAME, 'notify_email_zone_status', user=zone.user
                )
            ):
                try:
                    cls._send_owner_move_email(zone)
                except Exception as ex:  # NOTE: We won't fail/revert here
                    logger.error(f'Exception in _send_owner_move_email(): {ex}')

        # Create alerts and send emails to other project members on move
        member_notify = app_settings.get(
            APP_NAME, 'member_notify_move', project=zone.project
        )
        if (
            member_notify
            and zone.status == ZONE_STATUS_MOVED
            and file_count > 0
        ):
            members = [
                a.user
                for a in zone.project.get_roles()
                if a.user != zone.user and a.user.is_active
            ]
            for member in list(set(members)):
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
                            f'Exception in _add_member_move_alert(): {ex}'
                        )
                if settings.PROJECTROLES_SEND_EMAIL:
                    try:
                        cls._send_member_move_email(member, zone, file_count)
                    except Exception as ex:  # NOTE: We won't fail/revert here
                        logger.error(
                            f'Exception in _send_member_move_email(): {ex}'
                        )

        # If zone is removed by moving or deletion, call plugin function
        # TODO: TBD: Move into separate task?
        if status in [ZONE_STATUS_MOVED, ZONE_STATUS_DELETED]:
            from .plugins import get_zone_config_plugin  # See issue #269

            config_plugin = get_zone_config_plugin(zone)
            if config_plugin:
                try:
                    config_plugin.cleanup_zone(zone)
                except Exception as ex:
                    logger.error(
                        f'Unable to cleanup zone "{zone.title}" with plugin '
                        f'"{config_plugin.name}": {ex}'
                    )

        # Update cache
        # TODO: TBD: Move into separate task?
        if status == ZONE_STATUS_MOVED and settings.SHEETS_ENABLE_CACHE:
            try:
                update_project_cache_task.delay(
                    project_uuid=str(zone.project.sodar_uuid),
                    user_uuid=str(zone.user.sodar_uuid),
                    add_alert=True,
                    alert_msg=f'Moved landing zone "{zone.title}".',
                )
            except Exception as ex:
                logger.error(f'Unable to run project cache update task: {ex}')


class SetLandingZoneStatusTask(BaseLandingZoneStatusTask):
    """Set LandingZone status"""

    def execute(
        self,
        landing_zone: LandingZone,
        flow_name: str,
        status: str,
        status_info: str,
        extra_data: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        # Prevent setting status if already finished (see #1909)
        landing_zone.refresh_from_db()
        if landing_zone.status not in STATUS_FINISHED:
            self.set_status(
                landing_zone, flow_name, status, status_info, extra_data
            )
            self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(
        self,
        landing_zone: LandingZone,
        flow_name: str,
        status: str,
        status_info: str,
        extra_data: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        pass  # Disabled, call RevertLandingZoneStatusTask to revert


class RevertLandingZoneFailTask(BaseLandingZoneStatusTask):
    """Set LandingZone status in case of failure"""

    def execute(
        self,
        landing_zone: LandingZone,
        flow_name: str,
        info_prefix: str,
        status: str = ZONE_STATUS_FAILED,
        extra_data: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        super().execute(*args, **kwargs)

    def revert(
        self,
        landing_zone: LandingZone,
        flow_name: str,
        info_prefix: str,
        status: str = ZONE_STATUS_FAILED,
        extra_data: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        status_info = info_prefix
        for k, v in kwargs['flow_failures'].items():
            status_info += ': '
            status_info += str(v.exception) if v.exception else 'unknown error'
        self.set_status(
            landing_zone, flow_name, status, status_info, extra_data
        )
