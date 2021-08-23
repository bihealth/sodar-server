"""Taskflow API views for the landingzones app"""

import logging

from django.conf import settings
from django.contrib import auth
from django.urls import reverse

from rest_framework.response import Response

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.email import send_generic_mail
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.views_taskflow import BaseTaskflowAPIView

# Samplesheets dependency
from samplesheets.models import Assay
from samplesheets.tasks import update_project_cache_task

from landingzones.models import LandingZone


User = auth.get_user_model()
logger = logging.getLogger(__name__)
app_settings = AppSettingAPI()


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
Zone owner: {user} <{user_email}>
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
Zone owner: {user} <{user_email}>
Zone UUID: {zone_uuid}

Status message:
"{status_info}"'''.lstrip()
EMAIL_MSG_MEMBER = r'''
{user} ({user_email}) has uploaded {file_count} file{file_count_suffix}
into assay "{assay}"
under the project "{project}".

You can browse the assay metadata and related files at
the following URL:
{url}
'''.lstrip()


# TODO: Integrate Taskflow API with general SODAR API (see sodar_core#47)


class TaskflowZoneCreateAPIView(BaseTaskflowAPIView):
    def post(self, request):
        try:
            user = User.objects.get(sodar_uuid=request.data['user_uuid'])
            project = Project.objects.get(
                sodar_uuid=request.data['project_uuid']
            )
            assay = Assay.objects.get(sodar_uuid=request.data['assay_uuid'])
        except (User.DoesNotExist, Project.DoesNotExist, Assay.DoesNotExist):
            return Response('Not found', status=404)
        zone = LandingZone.objects.create(
            assay=assay,
            title=request.data['title'],
            project=project,
            user=user,
            description=request.data['description'],
        )
        return Response({'zone_uuid': zone.sodar_uuid}, status=200)


class TaskflowZoneStatusSetAPIView(BaseTaskflowAPIView):
    """API view for setting landing zone status after taskflow operation"""

    def _add_owner_alert(self, app_alerts, zone, file_count, validate_only):
        """Add app alert for zone owner"""
        if zone.status == 'MOVED':
            alert_msg = 'Successfully moved files from landing zone'
            alert_level = 'SUCCESS'
            alert_url = reverse(
                'samplesheets:project_sheets',
                kwargs={'project': zone.project.sodar_uuid},
            )
        elif validate_only and zone.status == 'ACTIVE':
            alert_msg = 'Successfully validated files in landing zone'
            alert_level = 'SUCCESS'
            alert_url = reverse(
                'landingzones:list',
                kwargs={'project': zone.project.sodar_uuid},
            )
        elif validate_only and zone.status == 'FAILED':
            alert_msg = 'Validation failed for landing zone'
            alert_level = 'DANGER'
            alert_url = reverse(
                'landingzones:list',
                kwargs={'project': zone.project.sodar_uuid},
            )
        else:  # Failed
            alert_msg = 'Failed to move files from landing zone'
            alert_level = 'DANGER'
            alert_url = reverse(
                'landingzones:list',
                kwargs={'project': zone.project.sodar_uuid},
            )
        alert_msg += ' in project "{}": {}'.format(
            zone.project.title,
            zone.title,
        )
        if zone.status == 'MOVED':
            alert_msg += ' ({} file{})'.format(
                file_count, 's' if file_count != 1 else ''
            )
        app_alerts.add_alert(
            app_name=APP_NAME,
            alert_name='zone_move',
            user=zone.user,
            level=alert_level,
            url=alert_url,
            message=alert_msg,
            project=zone.project,
        )

    def _add_member_alert(self, app_alerts, zone, user, file_count):
        """Add app alert for project member"""
        alert_msg = (
            '{} file{} uploaded by {} under assay "{}" in '
            'project "{}"'.format(
                file_count,
                's' if file_count != 1 else '',
                zone.user.username,
                zone.assay.get_display_name(),
                zone.project.title,
            )
        )
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

    def _send_owner_email(self, zone, request):
        """Send email to zone owner"""
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
            user=zone.user.username,
            user_email=zone.user.email,
            zone_uuid=str(zone.sodar_uuid),
            status_info=zone.status_info,
            url=email_url,
        )
        send_generic_mail(subject_body, message_body, [zone.user], request)

    def _send_member_email(self, zone, request, file_count):
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
            user=zone.user.get_full_name(),
            user_email=zone.user.email,
            file_count=file_count,
            file_count_suffix='s' if file_count != 1 else '',
            url=email_url,
        )
        send_generic_mail(subject_body, message_body, [zone.user], request)

    def post(self, request):
        app_alerts = get_backend_api('appalerts_backend')
        try:
            zone = LandingZone.objects.get(sodar_uuid=request.data['zone_uuid'])
        except LandingZone.DoesNotExist:
            return Response('LandingZone not found', status=404)
        try:
            zone.set_status(
                status=request.data['status'],
                status_info=request.data['status_info']
                if request.data['status_info']
                else None,
            )
        except TypeError:
            return Response('Invalid status type', status=400)

        zone.refresh_from_db()
        file_count = int(request.data.get('file_count', 0))
        validate_only = bool(int(request.data.get('validate_only', '0')))

        # Create alert and send email for zone owner
        if (
            (zone.status == 'MOVED' and file_count > 0)
            or validate_only
            or zone.status == 'FAILED'
        ):
            if app_alerts:
                self._add_owner_alert(
                    app_alerts, zone, file_count, validate_only
                )
            if settings.PROJECTROLES_SEND_EMAIL and not validate_only:
                self._send_owner_email(zone, request)

        # Create alerts and send emails to other project members if enabled
        member_notify = app_settings.get_app_setting(
            APP_NAME, 'member_notify_move', project=zone.project
        )
        if member_notify and zone.status == 'MOVED' and file_count > 0:
            members = [
                r for r in zone.project.get_all_roles() if r.user != zone.user
            ]
            for member_role in members:
                if app_alerts:
                    self._add_member_alert(
                        app_alerts=app_alerts,
                        zone=zone,
                        user=member_role.user,
                        file_count=file_count,
                    )
                if settings.PROJECTROLES_SEND_EMAIL:
                    self._send_member_email(zone, request, file_count)

        # If zone is removed by moving or deletion, call plugin function
        if request.data['status'] in ['MOVED', 'DELETED']:
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
        if request.data['status'] == 'MOVED' and settings.SHEETS_ENABLE_CACHE:
            update_project_cache_task.delay(
                project_uuid=str(zone.project.sodar_uuid),
                user_uuid=str(zone.user.sodar_uuid),
                add_alert=True,
                alert_msg='Moved landing zone "{}"'.format(zone.title),
            )

        return Response('ok', status=200)
