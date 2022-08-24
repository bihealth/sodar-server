"""UI views for the samplesheets app"""

import datetime
import io
import json
import logging
import os
import requests
import zipfile
from packaging import version

import pytz
from cubi_tk.isa_tpl import _TEMPLATES as TK_TEMPLATES

from django.conf import settings
from django.contrib import messages
from django.db.models.functions import Now
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.timezone import localtime
from django.views.generic import (
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    View,
    UpdateView,
)

from rest_framework.response import Response

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.email import send_generic_mail
from projectroles.models import (
    Project,
    SODAR_CONSTANTS,
    RoleAssignment,
)
from projectroles.plugins import get_backend_api
from projectroles.utils import build_secret
from projectroles.views import (
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
    CurrentUserFormMixin,
)

# Landingzones dependency
from landingzones.models import LandingZone

from samplesheets.forms import (
    SheetImportForm,
    SheetTemplateCreateForm,
    IrodsAccessTicketForm,
    IrodsRequestForm,
    IrodsRequestAcceptForm,
    SheetVersionEditForm,
)
from samplesheets.io import (
    SampleSheetIO,
    SampleSheetImportException,
    SampleSheetExportException,
)
from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    ISATab,
    IrodsAccessTicket,
    IrodsDataRequest,
)
from samplesheets.rendering import SampleSheetTableBuilder, EMPTY_VALUE
from samplesheets.sheet_config import SheetConfigAPI
from samplesheets.utils import (
    get_sample_colls,
    compare_inv_replace,
    get_sheets_url,
    write_excel_table,
    get_isa_field_name,
    clean_sheet_dir_name,
)


logger = logging.getLogger(__name__)
app_settings = AppSettingAPI()
conf_api = SheetConfigAPI()


# SODAR constants
SITE_MODE_TARGET = SODAR_CONSTANTS['SITE_MODE_TARGET']
REMOTE_LEVEL_READ_ROLES = SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES']

# Local constants
APP_NAME = 'samplesheets'
WARNING_STATUS_MSG = 'OK with warnings, see extra data'
TARGET_ALTAMISA_VERSION = '0.2.4'  # For warnings etc.
MISC_FILES_COLL_ID = 'misc_files'
MISC_FILES_COLL = 'MiscFiles'
TRACK_HUBS_COLL = 'TrackHubs'
RESULTS_COLL_ID = 'results_reports'
RESULTS_COLL = 'ResultsReports'
IRODS_REQ_CREATE_ALERT_NAME = 'irods_request_create'
IRODS_REQ_ACCEPT_ALERT_NAME = 'irods_request_accept'
IRODS_REQ_REJECT_ALERT_NAME = 'irods_request_reject'
SYNC_SUCCESS_MSG = 'Sample sheet sync successful'
SYNC_FAIL_DISABLED = 'Sample sheet sync disabled'
SYNC_FAIL_PREFIX = 'Sample sheet sync failed'
SYNC_FAIL_CONNECT = 'Unable to connect to URL'
SYNC_FAIL_UNSET_TOKEN = 'Remote sync token not set'
SYNC_FAIL_UNSET_URL = 'Remote sync URL not set'
SYNC_FAIL_INVALID_URL = 'Invalid API URL'
SYNC_FAIL_STATUS_CODE = 'Source API responded with status code'

EMAIL_DELETE_REQUEST_ACCEPT = r'''
Your delete request has been accepted.

Project: {project}
Path: {path}
User: {user} <{user_email}>

All data has been removed.
'''.lstrip()
EMAIL_DELETE_REQUEST_REJECT = r'''
Your delete request has been rejected.

Project: {project}
Path: {path}
User: {user} <{user_email}>

No data has been removed.
'''.lstrip()


# Mixins -----------------------------------------------------------------------


class InvestigationContextMixin(ProjectContextMixin):
    """Mixin for providing investigation for context if available"""

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        try:
            investigation = Investigation.objects.get(
                project=context['project'], active=True
            )
            context['investigation'] = investigation
        except Investigation.DoesNotExist:
            context['investigation'] = None
        return context


class SheetImportMixin:
    """Mixin for sample sheet importing/replacing helpers"""

    #: Whether configs should be regenerated on sheet replace
    replace_configs = True

    def create_timeline_event(self, project, action, tpl_name=None):
        """
        Create timeline event for sample sheet import, replace or create.

        :param project: Project object
        :param action: "import", "create" or "replace" (string)
        :param tpl_name: Optional template name (string)
        :return: ProjectEvent object
        """
        if action not in ['create', 'import', 'replace']:
            raise ValueError('Invalid action "{}"'.format(action))
        timeline = get_backend_api('timeline_backend')
        if not timeline:
            return None

        if action == 'replace':
            tl_desc = 'replace previous investigation with {investigation}'
        elif action == 'import':
            tl_desc = 'import investigation {investigation}'
        else:
            tl_desc = 'create investigation {investigation}'
            if tpl_name:
                tl_desc += ' from template "{}"'.format(tpl_name)

        return timeline.add_event(
            project=project,
            app_name=APP_NAME,
            user=self.request.user,
            event_name='sheet_{}'.format(action),
            description=tl_desc,
        )

    def handle_replace(self, investigation, old_inv, tl_event=None):
        project = investigation.project
        tb = SampleSheetTableBuilder()
        old_study_uuids = {}
        old_assay_uuids = {}
        old_study_count = old_inv.studies.count()
        old_assay_count = Assay.objects.filter(
            study__investigation=old_inv
        ).count()
        new_study_count = investigation.studies.count()
        new_assay_count = Assay.objects.filter(
            study__investigation=investigation
        ).count()

        # Ensure existing studies and assays are found in new inv
        compare_ok = compare_inv_replace(old_inv, investigation)

        try:
            if old_inv.irods_status and not compare_ok:
                raise ValueError(
                    'iRODS collections exist but studies and assays '
                    'do not match: unable to replace investigation'
                )

            # Save UUIDs
            old_inv_uuid = old_inv.sodar_uuid
            for study in old_inv.studies.all():
                old_study_uuids[study.identifier] = study.sodar_uuid
                for assay in study.assays.all():
                    old_assay_uuids[assay.get_name()] = assay.sodar_uuid

            # Set irods_status to our previous sheet's state
            investigation.irods_status = old_inv.irods_status
            investigation.save()

            # Check if we can keep existing configurations
            if (
                tb.get_headers(investigation) == tb.get_headers(old_inv)
                and compare_ok
                and old_study_count == new_study_count
                and old_assay_count == new_assay_count
            ):
                self.replace_configs = False

            # Update unfinished landing zones to point to new assays
            new_assays = {a.get_name(): a for a in investigation.get_assays()}
            for zone in LandingZone.objects.filter(project=project):
                zone.assay = new_assays[zone.assay.get_name()]
                zone.save()

            # Delete old investigation
            old_inv.delete()

        except Exception as ex:
            # Get existing investigations under project
            invs = Investigation.objects.filter(project=project).order_by('-pk')
            old_inv = None
            if invs:
                # Activate previous investigation
                if invs.count() > 1:
                    invs[1].active = True
                    invs[1].save()
                    old_inv = invs[1]
                    # Delete failed import
                    invs[0].delete()
            # Just in case, delete remaining ones from the db
            if old_inv:
                Investigation.objects.filter(project=project).exclude(
                    pk=old_inv.pk
                ).delete()
                ISATab.objects.filter(project=project).order_by(
                    '-pk'
                ).first().delete()
            self.handle_import_exception(ex, tl_event)
            return None

        # If all went well, update UUIDs
        if old_inv:
            investigation.sodar_uuid = old_inv_uuid
            investigation.save()
            for study in investigation.studies.all():
                if study.identifier in old_study_uuids:
                    study.sodar_uuid = old_study_uuids[study.identifier]
                    study.save()
                for assay in study.assays.all():
                    if assay.get_name() in old_assay_uuids:
                        assay.sodar_uuid = old_assay_uuids[assay.get_name()]
                        assay.save()

        return investigation

    def handle_import_exception(self, ex, tl_event=None, ui_mode=True):
        if isinstance(ex, SampleSheetImportException):
            ex_msg = str(ex.args[0])
            extra_data = {'warnings': ex.args[1]} if len(ex.args) > 1 else None

            if len(ex.args) > 1:
                # HACK: Report critical warnings here
                # TODO: Provide these to a proper view from Timeline
                ex_msg += '<ul>'

                def _add_crits(legend, warnings, eh):
                    for w in warnings:
                        if w['category'] == 'CriticalIsaValidationWarning':
                            eh += '<li>{}: {}</li>'.format(legend, w['message'])
                    return eh

                ex_msg = _add_crits(
                    'Investigation', ex.args[1]['investigation'], ex_msg
                )
                for k, v in ex.args[1]['studies'].items():
                    ex_msg = _add_crits(k, v, ex_msg)
                for k, v in ex.args[1]['assays'].items():
                    ex_msg = _add_crits(k, v, ex_msg)
                ex_msg += '</ul>'

            if ui_mode:
                messages.error(self.request, mark_safe(ex_msg))

        else:
            ex_msg = 'ISA-Tab import failed: {}'.format(ex)
            extra_data = None
            logger.error(ex_msg)
            if ui_mode:
                messages.error(self.request, ex_msg)

        if tl_event:
            tl_event.set_status(
                'FAILED', status_desc=ex_msg, extra_data=extra_data
            )

    def finalize_import(
        self,
        investigation,
        action,
        tl_event=None,
        isa_version=None,
        ui_mode=True,
    ):
        project = investigation.project
        success_msg = ''
        # Set current import active status to True
        investigation.active = True
        investigation.save()

        # Add investigation data in Timeline
        if tl_event:
            extra_data = (
                {'warnings': investigation.parser_warnings}
                if investigation.parser_warnings
                and not investigation.parser_warnings['all_ok']
                else None
            )
            status_desc = WARNING_STATUS_MSG if extra_data else None
            tl_event.set_status(
                'OK', status_desc=status_desc, extra_data=extra_data
            )

        if ui_mode:
            success_msg = '{}d sample sheets from {}'.format(
                action.capitalize(),
                'version {}'.format(isa_version.get_full_name())
                if action == 'restore'
                else 'ISA-Tab import',
            )
            if investigation.parser_warnings:
                success_msg += (
                    ' (<strong>Note:</strong> '
                    '<a href="#/warnings">parser warnings raised</a>)'
                )

        # Build/restore/keep sheet and display configurations
        sheet_config = None
        display_config = None
        sheet_config_valid = True

        # If replacing, delete old user display configurations
        if action == 'replace':
            if self.replace_configs:
                logger.debug('Deleting existing user display configurations..')
                app_settings.delete_setting(
                    APP_NAME, 'display_config', project=project
                )
            else:
                logger.debug('Keeping existing configurations')
                sheet_config = app_settings.get_app_setting(
                    APP_NAME, 'sheet_config', project=project
                )
                conf_api.restore_sheet_config(investigation, sheet_config)
                display_config = app_settings.get_app_setting(
                    APP_NAME, 'display_config_default', project=project
                )

        if isa_version and action == 'restore':
            logger.debug('Restoring previous edit and display configurations')
            sheet_config = isa_version.data.get('sheet_config')
            display_config = isa_version.data.get('display_config')

            try:
                conf_api.validate_sheet_config(sheet_config)
                conf_api.restore_sheet_config(investigation, sheet_config)
            except ValueError:
                sheet_config_valid = False

        if not sheet_config or not sheet_config_valid:
            logger.debug('Building new sheet configuration')
            sheet_config = conf_api.build_sheet_config(investigation)
        if not display_config:
            logger.debug('Building new display configuration')
            display_config = conf_api.build_display_config(
                investigation, sheet_config
            )

        # Save configs to isa version if we are creating the sheet
        # (or if the version is missing these configs for some reason)
        if (
            isa_version
            and action != 'restore'
            and (
                not isa_version.data.get('sheet_config')
                or not isa_version.data.get('display_config')
            )
        ):
            isa_version.data['sheet_config'] = sheet_config
            isa_version.data['display_config'] = display_config
            isa_version.save()
            logger.info('Sheet configurations added into ISA-Tab version')

        app_settings.set_app_setting(
            APP_NAME, 'sheet_config', sheet_config, project=project
        )
        app_settings.set_app_setting(
            APP_NAME,
            'display_config_default',
            display_config,
            project=project,
        )
        logger.info('Sheet configurations updated')

        # Update project cache if replacing sheets and iRODS collections exists
        if (
            action in ['replace', 'restore']
            and investigation.irods_status
            and settings.SHEETS_ENABLE_CACHE
        ):
            from samplesheets.tasks_celery import update_project_cache_task

            update_project_cache_task.delay(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(self.request.user.sodar_uuid),
                add_alert=ui_mode,
                alert_msg='Sample sheet {}d'.format(action),
            )
            if ui_mode:
                success_msg += ', initiated iRODS cache update'

        if ui_mode:
            messages.success(self.request, mark_safe(success_msg))
        logger.info('Sample sheet {} OK'.format(action))
        return investigation

    @classmethod
    def get_assays_without_plugins(cls, investigation):
        """Return list of assays with no associated plugins"""
        ret = []
        for s in investigation.studies.all():
            for a in s.assays.all():
                if not a.get_plugin():
                    ret.append(a)
        return ret

    @classmethod
    def get_assay_plugin_warning(cls, assay):
        """Return warning message for missing assay plugin"""
        return (
            'No plugin found for assay "{}": measurement_type="{}", '
            'technology_type="{}"'.format(
                assay.get_display_name(),
                get_isa_field_name(assay.measurement_type),
                get_isa_field_name(assay.technology_type),
            )
        )


class SheetISAExportMixin:
    """Mixin for exporting sample sheets in ISA-Tab format"""

    def get_isa_export(self, project, request, format='zip', version_uuid=None):
        """
        Export sample sheets as a HTTP response as ISA-Tab, either in a zipped
        archive or wrapped in a JSON structure.

        :param project: Project object
        :param request: Request object
        :param format: Export format ("zip" or "json")
        :param version_uuid: Version UUID (optional)
        :return: Response object
        :raise: ISATab.DoesNotExist if version is requested but not found
        :raise Investigation.DosNotExist if investigation is not found
        """
        timeline = get_backend_api('timeline_backend')
        tl_event = None
        sheet_io = SampleSheetIO()
        isa_version = None
        valid_formats = ['zip', 'json']

        if format not in valid_formats:
            raise ValueError(
                'Invalid format "{}". Valid formats: {}'.format(
                    format, ', '.join(valid_formats)
                )
            )

        if version_uuid:
            isa_version = ISATab.objects.get(
                project=project, sodar_uuid=version_uuid
            )
            investigation = Investigation.objects.get(
                sodar_uuid=isa_version.investigation_uuid
            )
        else:
            investigation = Investigation.objects.get(project=project)

        if not isa_version and (
            not investigation.parser_version
            or version.parse(investigation.parser_version)
            < version.parse(TARGET_ALTAMISA_VERSION)
        ):
            raise SampleSheetExportException(
                'Exporting ISA-Tabs imported using altamISA < {} is not '
                'supported. Please replace the sheets to enable export.'.format(
                    TARGET_ALTAMISA_VERSION
                ),
            )

        # Set up archive file name
        archive_name = (
            isa_version.archive_name
            if isa_version
            else investigation.archive_name
        )

        if archive_name:
            file_name = archive_name.split('.zip')[0]
        else:
            file_name = clean_sheet_dir_name(project.title)
        if isa_version:
            file_name += '_' + localtime(isa_version.date_created).strftime(
                '%Y-%m-%d_%H%M%S'
            )
            if isa_version.user:
                file_name += '_' + slugify(isa_version.user.username)
        file_name += '.zip'

        # TODO: Log anonymous export? (see #1164)
        if timeline and request.user and request.user.is_authenticated:
            if isa_version:
                tl_desc = 'export {investigation} version {isatab}'
            else:
                tl_desc = 'export {investigation} as ISA-Tab'
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=request.user,
                event_name='sheet_export',
                description=tl_desc,
                classified=True,
            )
            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title,
            )
            if isa_version:
                tl_event.add_object(
                    obj=isa_version,
                    label='isatab',
                    name=isa_version.get_full_name(),
                )

        # Initiate export
        try:
            if isa_version:
                export_data = isa_version.data
            else:
                export_data = sheet_io.export_isa(investigation)
            zip_io = None

            if format == 'zip':
                # Build Zip archive
                zip_io = io.BytesIO()
                zf = zipfile.ZipFile(
                    zip_io, mode='w', compression=zipfile.ZIP_DEFLATED
                )
                zf.writestr(
                    export_data['investigation']['path'],
                    export_data['investigation']['tsv'],
                )
                inv_dir = '/'.join(
                    export_data['investigation']['path'].split('/')[:-1]
                )
                for k, v in export_data['studies'].items():
                    zf.writestr('{}/{}'.format(inv_dir, k), v['tsv'])

                for k, v in export_data['assays'].items():
                    zf.writestr('{}/{}'.format(inv_dir, k), v['tsv'])
                zf.close()

            # Update timeline event
            if tl_event:
                export_warnings = sheet_io.get_warnings()
                extra_data = (
                    {'warnings': export_warnings}
                    if not export_warnings['all_ok']
                    else None
                )
                status_desc = WARNING_STATUS_MSG if extra_data else None
                tl_event.set_status(
                    'OK', status_desc=status_desc, extra_data=extra_data
                )

            # Set up response
            if format == 'zip' and zip_io:
                response = HttpResponse(
                    zip_io.getvalue(), content_type='application/zip'
                )
                response[
                    'Content-Disposition'
                ] = 'attachment; filename="{}"'.format(file_name)
                return response
            elif format == 'json':
                export_data['date_modified'] = str(investigation.date_modified)
                return Response(export_data, status=200)

        except Exception as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))
            raise ex


class SheetCreateImportAccessMixin:
    """Mixin for additional sheet import/create view access control"""

    def dispatch(self, *args, **kwargs):
        project = self.get_project()
        if app_settings.get_app_setting(
            APP_NAME, 'sheet_sync_enable', project=project
        ):
            messages.error(
                self.request,
                'Sheet synchronization enabled in project: import and '
                'creation not allowed.',
            )
            return redirect(reverse('home'))
        return super().dispatch(*args, **kwargs)


class IrodsCollsCreateViewMixin:
    """Mixin to be used in iRODS collections creation UI / API views"""

    def create_colls(self, investigation, request=None):
        """
        Handle iRODS collection creation via Taskflow.

        NOTE: Unlike many other Taskflow operations, this action is synchronous.

        :param investigation: Investigation object
        :param request: HTTPRequest object or None
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        project = investigation.project
        tl_event = None
        action = 'update' if investigation.irods_status else 'create'

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=request.user if request else None,
                event_name='sheet_colls_' + action,
                description=action + ' irods collection structure for '
                '{investigation}',
                status_type='SUBMIT',
            )
            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title,
            )

        flow_data = {'colls': get_sample_colls(investigation)}
        try:
            taskflow.submit(
                project=project,
                flow_name='sheet_colls_create',
                flow_data=flow_data,
            )
        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))
            raise ex
        if tl_event:
            tl_event.set_status('OK')

        if settings.SHEETS_ENABLE_CACHE:
            from samplesheets.tasks_celery import update_project_cache_task

            update_project_cache_task.delay(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(request.user.sodar_uuid) if request else None,
                add_alert=True,
                alert_msg='iRODS collection {}'.format(action),
            )

        # If public guest access and anonymous allowed, add ticket access
        if project.public_guest_access:
            irods_backend = get_backend_api('omics_irods')
            try:
                ticket = irods_backend.issue_ticket(
                    'read', irods_backend.get_sample_path(project)
                )
                app_settings.set_app_setting(
                    APP_NAME,
                    'public_access_ticket',
                    ticket.ticket,
                    project=project,
                )
            except Exception as ex:
                logger.error('Ticket issuing failed: {}'.format(ex))
                if settings.DEBUG:
                    raise ex
                return


class IrodsRequestModifyMixin:
    """iRODS data request helpers"""

    # Timeline helpers ---------------------------------------------------------

    @classmethod
    def add_tl_create(cls, irods_request):
        """
        Create timeline event for iRODS data request creation.

        :param irods_request: IrodsDataRequest object
        """
        timeline = get_backend_api('timeline_backend')
        if not timeline:
            return
        tl_event = timeline.add_event(
            project=irods_request.project,
            app_name=APP_NAME,
            user=irods_request.user,
            event_name='irods_request_create',
            description='create iRODS data request {irods_request}',
            status_type='OK',
        )
        tl_event.add_object(
            obj=irods_request,
            label='irods_request',
            name=irods_request.get_display_name(),
        )

    @classmethod
    def add_tl_delete(cls, irods_request):
        """
        Create timeline event for iRODS data request deletion.

        :param irods_request: IrodsDataRequest object
        """
        timeline = get_backend_api('timeline_backend')
        if not timeline:
            return
        tl_event = timeline.add_event(
            project=irods_request.project,
            app_name=APP_NAME,
            user=irods_request.user,
            event_name='irods_request_delete',
            description='delete iRODS data request {irods_request}',
            status_type='OK',
        )
        tl_event.add_object(
            obj=irods_request,
            label='irods_request',
            name=str(irods_request),
        )

    # App Alert Helpers --------------------------------------------------------

    @classmethod
    def add_alerts_create(cls, project, app_alerts=None):
        """
        Add app alerts for project owners/delegates on request creation. Will
        not create new alerts if the user already has a similar active alert
        in the project.

        :param project: Project object
        :param app_alerts: Appalerts API or None
        """
        if not app_alerts:
            app_alerts = get_backend_api('appalerts_backend')
        if not app_alerts:
            return

        AppAlert = app_alerts.get_model()
        # TODO: Use get_all_roles() instead
        od_users = set(
            [a.user for a in project.get_owners()]
            + [a.user for a in project.get_delegates()]
        )
        # logger.debug('od_users={}'.format(od_users))  # DEBUG
        for u in od_users:
            alert_count = AppAlert.objects.filter(
                project=project,
                user=u,
                alert_name=IRODS_REQ_CREATE_ALERT_NAME,
                active=True,
            ).count()
            if alert_count > 0:
                logger.debug('Alert exists for user: {}'.format(u.username))
                continue  # Only have one active alert per user/project
            app_alerts.add_alert(
                app_name=APP_NAME,
                alert_name=IRODS_REQ_CREATE_ALERT_NAME,
                user=u,
                message='iRODS delete requests require attention in '
                'project "{}"'.format(project.title),
                url=reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': project.sodar_uuid},
                ),
                project=project,
            )
            logger.debug(
                'Added iRODS request alert for user: {}'.format(u.username)
            )

    @classmethod
    def handle_alerts_deactivate(cls, irods_request, app_alerts=None):
        """
        Handle existing iRODS delete request project alerts on alert
        acceptance, rejection or deletion.

        :param irods_request: IrodsDataRequest object being deleted
        :param app_alerts: Appalerts API or None
        """
        if not app_alerts:
            app_alerts = get_backend_api('appalerts_backend')
        if not app_alerts:
            return
        AppAlert = app_alerts.get_model()
        req_count = (
            IrodsDataRequest.objects.filter(
                project=irods_request.project, status='ACTIVE'
            )
            .exclude(sodar_uuid=irods_request.sodar_uuid)
            .count()
        )
        if req_count == 0:
            alerts = AppAlert.objects.filter(
                alert_name=IRODS_REQ_CREATE_ALERT_NAME,
                project=irods_request.project,
                active=True,
            )
            alert_count = alerts.count()
            alerts.delete()  # Deleting as the user doesn't dismiss these
            logger.debug(
                'No active requests left for project, deleting {} '
                'owner/delegate alert{}'.format(
                    alert_count, 's' if alert_count != 1 else ''
                )
            )


class SheetRemoteSyncAPI(SheetImportMixin):
    """
    Remote sample sheet synchronization helpers.
    NOTE: Not used as a mixin because it is also called from the periodic task
    """

    def sync_sheets(self, project, user):
        """
        Synchronize sample sheets from another project or site.

        :project: Project object of target project
        :user: User performing the action
        """
        logger.debug(
            'Sync sample sheets for project "{}" ({})'.format(
                project.title, project.sodar_uuid
            )
        )

        # Check input
        url = app_settings.get_app_setting(
            APP_NAME, 'sheet_sync_url', project=project
        )
        token = app_settings.get_app_setting(
            APP_NAME, 'sheet_sync_token', project=project
        )
        if not url:
            raise ValueError(SYNC_FAIL_UNSET_URL)
        url_prefix = '/'.join(
            reverse(
                'samplesheets:api_export_json',
                kwargs={'project': project.sodar_uuid},
            ).split('/')[:-1]
        )
        if url_prefix not in url:
            raise ValueError('{}: {}'.format(SYNC_FAIL_INVALID_URL, url))
        if not token:
            raise ValueError(SYNC_FAIL_UNSET_TOKEN)

        # Get remote sheet data (source)
        try:
            response = requests.get(
                url, headers={'Authorization': 'token {}'.format(token)}
            )
        except Exception:
            raise requests.exceptions.ConnectionError(
                '{}: {}'.format(SYNC_FAIL_CONNECT, url)
            )
        if not response.status_code == 200:
            raise requests.exceptions.ConnectionError(
                'Source API responded with status code: {}'.format(
                    response.status_code
                )
            )

        try:
            source_data = response.json()
        except json.JSONDecodeError as ex:
            raise ValueError(
                'Error decoding JSON data: {}. Please check "sheet_sync_url" '
                'setting.'.format(ex)
            )

        source_date = datetime.datetime.strptime(
            source_data.pop('date_modified'),
            '%Y-%m-%d %H:%M:%S.%f+00:00',
        ).replace(tzinfo=pytz.UTC)
        old_inv = project.investigations.first()
        replace = bool(old_inv)

        if old_inv and source_date < old_inv.date_modified:
            logger.debug('No updates detected, skipping sync')
            return False

        # Import sheet data
        sheet_io = SampleSheetIO()
        investigation = sheet_io.import_isa(
            isa_data=source_data,
            project=project,
            replace=replace,
            replace_uuid=old_inv.sodar_uuid if replace else None,
        )
        # Handle replace
        if replace:
            investigation = self.handle_replace(
                investigation=investigation,
                old_inv=old_inv,
                tl_event=None,
            )

        # Activate investigation
        investigation.active = True
        investigation.save()

        # Update project cache if replacing sheets and iRODS collections exists
        if (
            replace
            and investigation.irods_status
            and settings.SHEETS_ENABLE_CACHE
        ):
            from samplesheets.tasks_celery import update_project_cache_task

            update_project_cache_task(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(user.sodar_uuid),
                add_alert=True,
                alert_msg='Remote sample sheets synchronized',
            )

        logger.info(
            'Sample sheet sync OK for project "{}" '
            '({})'.format(project.title, project.sodar_uuid)
        )
        return True


# Views ------------------------------------------------------------------------


class ProjectSheetsView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    TemplateView,
):
    """Main view for displaying sample sheets in a project"""

    permission_required = 'samplesheets.view_sheet'
    template_name = 'samplesheets/project_sheets.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        studies = Study.objects.filter(
            investigation=context['investigation']
        ).order_by('pk')

        # Provide initial context data to Vue app
        app_context = {
            'project_uuid': str(context['project'].sodar_uuid),
            'context_url': self.request.build_absolute_uri(
                reverse(
                    'samplesheets:ajax_context',
                    kwargs={'project': str(self.get_project().sodar_uuid)},
                )
            ),
        }

        if 'study' in self.kwargs:
            app_context['initial_study'] = self.kwargs['study']
        elif studies.count() > 0:
            app_context['initial_study'] = str(studies.first().sodar_uuid)
        else:
            app_context['initial_study'] = None

        context['app_context'] = json.dumps(app_context)
        context['settings_module'] = os.environ['DJANGO_SETTINGS_MODULE']
        context['EMPTY_VALUE'] = EMPTY_VALUE  # For JQuery
        return context


class SheetImportView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    CurrentUserFormMixin,
    SheetImportMixin,
    SheetCreateImportAccessMixin,
    FormView,
):
    """Sample sheet ISA-Tab import view"""

    permission_required = 'samplesheets.edit_sheet'
    model = Investigation
    form_class = SheetImportForm
    template_name = 'samplesheets/samplesheet_import_form.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        project = self.get_project()
        try:
            old_inv = Investigation.objects.get(project=project, active=True)
            context['replace_sheets'] = True
            context['irods_status'] = old_inv.irods_status
            # Check for active/ongoing zones in case of sheet replacing
            # TODO: Lock project and allow ACTIVE after taskflow integr. (#713)
            if (
                old_inv.project.landing_zones.exclude(
                    status__in=['MOVED', 'DELETED']
                ).count()
                > 0
            ):
                context['zones_exist'] = True
        except Investigation.DoesNotExist:
            pass
        return context

    def get_form_kwargs(self):
        """Pass kwargs to form"""
        kwargs = super().get_form_kwargs()
        project = self.get_project()
        if 'project' in self.kwargs:
            kwargs.update({'project': project.sodar_uuid})
        # If investigation for project already exists, set replace=True
        try:
            Investigation.objects.get(project=project, active=True)
            kwargs.update({'replace': True})
        except Investigation.DoesNotExist:
            kwargs.update({'replace': False})
        return kwargs

    def form_valid(self, form):
        project = self.get_project()
        form_kwargs = self.get_form_kwargs()
        form_action = 'replace' if form_kwargs['replace'] else 'create'
        redirect_url = get_sheets_url(project)
        tl_event = self.create_timeline_event(project, form_action)

        # Import via form
        try:
            self.object = form.save()
        except Exception as ex:
            self.handle_import_exception(ex, tl_event)
            return redirect(redirect_url)  # Return with error here

        if tl_event:
            tl_event.add_object(
                obj=self.object, label='investigation', name=self.object.title
            )

        # Handle replace
        old_inv = Investigation.objects.filter(
            project=project, active=True
        ).first()
        if form_action == 'replace' and old_inv:
            # NOTE: This function handles error/timeline reporting internally
            self.object = self.handle_replace(
                investigation=self.object, old_inv=old_inv, tl_event=tl_event
            )

        # If all went well, finalize import
        if self.object:
            isa_version = (
                ISATab.objects.filter(investigation_uuid=self.object.sodar_uuid)
                .order_by('-date_created')
                .first()
            )
            self.object = self.finalize_import(
                investigation=self.object,
                action=form_action,
                tl_event=tl_event,
                isa_version=isa_version,
            )
            # Display warnings if assay plugins are not found
            for a in self.get_assays_without_plugins(self.object):
                messages.warning(self.request, self.get_assay_plugin_warning(a))

        return redirect(redirect_url)


class SheetTemplateSelectView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    SheetCreateImportAccessMixin,
    TemplateView,
):
    """Sample sheet template selection view for template-based creation"""

    template_name = 'samplesheets/sheet_template_select.html'
    permission_required = 'samplesheets.edit_sheet'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        templates = []
        # HACK: Skip non-working templates in cubi-tk
        for t in [
            t
            for t in TK_TEMPLATES
            if t.name in settings.SHEETS_ENABLED_TEMPLATES
        ]:
            templates.append(
                {
                    'name': t.name,
                    'description': t.description[0].upper() + t.description[1:],
                }
            )
        context['sheet_templates'] = sorted(
            templates, key=lambda x: x['description']
        )
        return context

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        investigation = Investigation.objects.filter(project=project).first()
        if investigation:
            messages.error(
                request, 'Sheets already exist in project, creation not allowed'
            )
            return redirect(
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': project.sodar_uuid},
                )
            )
        return super().render_to_response(self.get_context_data())


# TODO: Prevent access if sheet sync is enabled, add tests
class SheetTemplateCreateFormView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    CurrentUserFormMixin,
    SheetImportMixin,
    SheetCreateImportAccessMixin,
    FormView,
):
    """Sample sheet ISA-Tab import view"""

    permission_required = 'samplesheets.edit_sheet'
    form_class = SheetTemplateCreateForm
    template_name = 'samplesheets/sheet_template_form.html'

    def _get_sheet_template(self):
        t_name = self.request.GET.get('sheet_tpl')
        return {t.name: t for t in TK_TEMPLATES}[t_name]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        sheet_tpl = self._get_sheet_template()
        context['description'] = (
            sheet_tpl.description[0].upper() + sheet_tpl.description[1:]
        )
        return context

    def get_form_kwargs(self):
        """Pass kwargs to form"""
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                'project': self.get_project(),
                'sheet_tpl': self._get_sheet_template(),
            }
        )
        return kwargs

    def form_valid(self, form):
        project = self.get_project()
        redirect_url = get_sheets_url(project)
        sheet_tpl = self._get_sheet_template()
        tl_event = self.create_timeline_event(
            project, 'create', tpl_name=sheet_tpl.name if sheet_tpl else None
        )

        # Create via form
        try:
            self.object = form.save()
        except Exception as ex:
            self.handle_import_exception(ex, tl_event)
            return redirect(redirect_url)  # Return with error here

        if tl_event:
            tl_event.add_object(
                obj=self.object, label='investigation', name=self.object.title
            )

        # If all went well, finalize import
        if self.object:
            isa_version = (
                ISATab.objects.filter(investigation_uuid=self.object.sodar_uuid)
                .order_by('-date_created')
                .first()
            )
            self.object = self.finalize_import(
                investigation=self.object,
                action='create',
                tl_event=tl_event,
                isa_version=isa_version,
            )

            # Display warnings if assay plugins are not found
            for a in self.get_assays_without_plugins(self.object):
                messages.warning(self.request, self.get_assay_plugin_warning(a))

        return redirect(redirect_url)

    def get(self, request, *args, **kwargs):
        redirect_url = reverse(
            'samplesheets:template_select',
            kwargs={'project': self.get_project().sodar_uuid},
        )
        t_name = self.request.GET.get('sheet_tpl')
        if not t_name:
            messages.error(request, 'Template name not provided.')
            return redirect(redirect_url)
        elif t_name not in settings.SHEETS_ENABLED_TEMPLATES:
            messages.error(
                request, 'Template "{}" is not supported.'.format(t_name)
            )
            return redirect(redirect_url)
        return super().render_to_response(self.get_context_data())


class SheetExcelExportView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Sample sheet table Excel export view"""

    permission_required = 'samplesheets.export_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return an Excel file"""
        timeline = get_backend_api('timeline_backend')
        redirect_url = get_sheets_url(self.get_project())
        assay = None
        study = None

        if 'assay' in self.kwargs:
            assay = Assay.objects.filter(
                sodar_uuid=self.kwargs['assay']
            ).first()
            study = assay.study if assay else None
        elif 'study' in self.kwargs:
            study = Study.objects.filter(
                sodar_uuid=self.kwargs['study']
            ).first()
        if not study:
            messages.error(
                self.request, 'Study not found, unable to render an Excel file'
            )
            return redirect(redirect_url)

        # Build study tables
        tb = SampleSheetTableBuilder()
        try:
            tables = tb.build_study_tables(study, ui=False)
        except Exception as ex:
            messages.error(
                self.request, 'Unable to render table for export: {}'.format(ex)
            )
            return redirect(redirect_url)

        if assay:
            table = tables['assays'][str(assay.sodar_uuid)]
            input_name = assay.file_name
            display_name = assay.get_display_name()
        else:  # Study
            table = tables['study']
            input_name = study.file_name
            display_name = study.get_display_name()

        # Set up response
        response = HttpResponse(content_type='text/tab-separated-values')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="{}.xlsx"'.format(
            input_name.split('.')[0]
        )  # TODO: TBD: Output file name?

        # Build Excel file
        write_excel_table(table, response, display_name)

        # TODO: Log anonymous export? (see #1164)
        if (
            timeline
            and self.request.user
            and self.request.user.is_authenticated
        ):
            tl_event = timeline.add_event(
                project=self.get_project(),
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_export_excel',
                description='export {{{}}} as Excel file'.format(
                    'assay' if assay else 'study'
                ),
                status_type='OK',
                classified=True,
            )
            if assay:
                tl_event.add_object(
                    obj=assay, label='assay', name=assay.get_display_name()
                )
            else:  # Study
                tl_event.add_object(
                    obj=study, label='study', name=study.get_display_name()
                )

        # Return file
        return response


class SheetISAExportView(
    SheetISAExportMixin,
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Sample sheet table ISA-Tab export view"""

    permission_required = 'samplesheets.export_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return ISA-Tab files as a ZIP archive"""
        project = self.get_project()
        version_uuid = kwargs.get('isatab')
        try:
            return self.get_isa_export(project, request, 'zip', version_uuid)
        except Exception as ex:
            if version_uuid:
                redirect_url = reverse(
                    'samplesheets:versions',
                    kwargs={'project': project.sodar_uuid},
                )
            else:
                redirect_url = get_sheets_url(project)
            messages.error(
                request,
                'Unable to export ISA-Tab{}: {}'.format(
                    ' version' if version_uuid else '', ex
                ),
            )
            return redirect(redirect_url)


class SheetDeleteView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    TemplateView,
):
    """Sample sheet deletion view"""

    permission_required = 'samplesheets.delete_sheet'
    template_name = 'samplesheets/samplesheet_confirm_delete.html'

    def get_context_data(self, *args, **kwargs):
        """Override get_context_data() to check for data objects in iRODS"""
        context = super().get_context_data(*args, **kwargs)
        irods_backend = get_backend_api('omics_irods')
        if irods_backend:
            project = self.get_project()
            try:
                context['irods_sample_stats'] = irods_backend.get_object_stats(
                    irods_backend.get_sample_path(project)
                )
            except FileNotFoundError:
                pass
        return context

    def post(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        tl_event = None
        project = Project.objects.get(sodar_uuid=kwargs['project'])
        investigation = Investigation.objects.get(project=project, active=True)
        redirect_url = get_sheets_url(project)

        # Don't allow deletion for everybody if files exist in iRODS
        # HACK for issue #424: This could also be implemented in rules..
        context = self.get_context_data(*args, **kwargs)
        file_count = (
            context['irods_sample_stats']['file_count']
            if 'irods_sample_stats' in context
            else 0
        )

        if (
            file_count > 0
            and not self.request.user.is_superuser
            and self.request.user != context['project'].get_owner().user
        ):
            messages.warning(
                self.request,
                '{} file{} for project in iRODS, deletion only allowed '
                'for project owner or superuser'.format(
                    file_count, 's' if int(file_count) != 1 else ''
                ),
            )
            return redirect(get_sheets_url(context['project']))

        # Else go forward..
        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_delete',
                description='delete investigation {investigation}',
            )
            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title,
            )

        # Don't allow deletion unless user has input the host name
        host_confirm = request.POST.get('delete_host_confirm')
        actual_host = request.get_host().split(':')[0]

        if not host_confirm or host_confirm != actual_host:
            msg = (
                'Incorrect host name for confirming sheet '
                'deletion: "{}"'.format(host_confirm)
            )
            tl_event.set_status('FAILED', msg)
            logger.error(msg + ' (correct={})'.format(actual_host))
            messages.error(
                request, 'Host name input incorrect, deletion cancelled.'
            )
            return redirect(redirect_url)

        delete_success = True

        if taskflow and investigation.irods_status:
            if tl_event:
                tl_event.set_status('SUBMIT')
            try:
                taskflow.submit(
                    project=project,
                    flow_name='sheet_delete',
                    flow_data={},
                )
            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))
                delete_success = False
                messages.error(
                    self.request,
                    'Failed to delete sample sheets: {}'.format(ex),
                )

        else:
            investigation.delete()
            tl_event.set_status('OK')

        if delete_success:
            # Delete ISA-Tab versions
            isa_versions = ISATab.objects.filter(project=project)
            v_count = isa_versions.count()
            isa_versions.delete()
            logger.debug(
                'Deleted {} ISA-Tab version{}'.format(
                    v_count, 's' if v_count != 1 else ''
                )
            )
            # Delete sheet configuration
            app_settings.set_app_setting(
                APP_NAME, 'sheet_config', {}, project=project
            )
            # Delete display configurations
            app_settings.set_app_setting(
                APP_NAME, 'display_config_default', {}, project=project
            )
            app_settings.delete_setting(
                APP_NAME, 'display_config', project=project
            )
            messages.success(self.request, 'Sample sheets deleted.')

        return redirect(redirect_url)


class SheetCacheUpdateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
    View,
):
    """Sample sheet manual cache update view"""

    permission_required = 'samplesheets.edit_sheet'

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        if settings.SHEETS_ENABLE_CACHE:
            from samplesheets.tasks_celery import update_project_cache_task

            update_project_cache_task.delay(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(request.user.sodar_uuid),
                add_alert=True,
                alert_msg='Manual cache update',
            )
            messages.warning(
                self.request,
                'Cache updating initiated. This may take some time, you will '
                'receive an alert once done. Refresh the sheet view to see '
                'the results.',
            )
        return redirect(get_sheets_url(project))


class IrodsCollsCreateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    IrodsCollsCreateViewMixin,
    TemplateView,
):
    """iRODS collection structure creation view"""

    template_name = 'samplesheets/irods_colls_confirm.html'
    permission_required = 'samplesheets.create_colls'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        investigation = context['investigation']
        if not investigation:
            return context
        context['colls'] = get_sample_colls(investigation)
        context['update_colls'] = True if investigation.irods_status else False
        return context

    def post(self, request, **kwargs):
        taskflow = get_backend_api('taskflow')
        context = self.get_context_data(**kwargs)
        project = context['project']
        investigation = context['investigation']
        action = 'update' if context['update_colls'] else 'create'
        redirect_url = get_sheets_url(project)

        # Fail if tasflow is not available
        if not taskflow:
            messages.error(
                self.request,
                'Unable to {} collections: taskflow not enabled!'.format(
                    action
                ),
            )
            return redirect(redirect_url)

        # Else go on with the creation
        try:
            self.create_colls(investigation, request)
            success_msg = (
                'Collection structure for sample data '
                '{}d in iRODS'.format(action)
            )
            if settings.SHEETS_ENABLE_CACHE:
                success_msg += ', initiated iRODS cache update'
            messages.success(self.request, success_msg)
        except taskflow.FlowSubmitException as ex:
            messages.error(self.request, str(ex))

        return redirect(redirect_url)

    def get(self, request, *args, **kwargs):
        return super().render_to_response(self.get_context_data())


class SheetVersionListView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    ListView,
):
    """Sample Sheet version list view"""

    model = ISATab
    permission_required = 'samplesheets.view_versions'
    template_name = 'samplesheets/sheet_versions.html'
    paginate_by = settings.SHEETS_VERSION_PAGINATION

    def get_queryset(self):
        return ISATab.objects.filter(
            project__sodar_uuid=self.kwargs['project']
        ).order_by('-date_created')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['current_version'] = None
        if context['investigation']:
            context['current_version'] = (
                ISATab.objects.filter(
                    project=self.get_project(),
                    investigation_uuid=context['investigation'].sodar_uuid,
                )
                .order_by('-date_created')
                .first()
            )
        return context


class SheetVersionCompareView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    SheetImportMixin,
    TemplateView,
):
    """Sample Sheet version compare view"""

    permission_required = 'samplesheets.view_versions'
    template_name = 'samplesheets/version_compare.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        source_uuid = self.request.GET.get('source')
        target_uuid = self.request.GET.get('target')
        source = ISATab.objects.filter(sodar_uuid=source_uuid).first()
        target = ISATab.objects.filter(sodar_uuid=target_uuid).first()
        context['source'] = source_uuid
        context['target'] = target_uuid
        context['source_title'] = source.date_created if source else 'N/A'
        context['target_title'] = target.date_created if target else 'N/A'
        return context


class SheetVersionCompareFileView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    SheetImportMixin,
    TemplateView,
):
    """Sample Sheet version compare file view"""

    permission_required = 'samplesheets.view_versions'
    template_name = 'samplesheets/version_compare_file.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['source'] = self.request.GET.get('source')
        context['target'] = self.request.GET.get('target')
        context['filename'] = self.request.GET.get('filename')
        context['category'] = self.request.GET.get('category')
        return context


class SheetVersionRestoreView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    SheetImportMixin,
    TemplateView,
):
    """Sample Sheet version restoring view"""

    template_name = 'samplesheets/version_confirm_restore.html'
    permission_required = 'samplesheets.manage_sheet'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        investigation = context['investigation']
        if not investigation:
            return context
        context['sheet_version'] = ISATab.objects.filter(
            sodar_uuid=self.kwargs['isatab']
        ).first()
        return context

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        tl_event = None
        project = self.get_project()
        sheet_io = SampleSheetIO(allow_critical=settings.SHEETS_ALLOW_CRITICAL)
        new_inv = None
        redirect_url = reverse(
            'samplesheets:versions', kwargs={'project': project.sodar_uuid}
        )

        old_inv = Investigation.objects.filter(
            project=project, active=True
        ).first()
        if not old_inv:
            # This shouldn't happen, but just in case
            messages.error(
                request, 'Existing sheet not found, unable to restore'
            )
            return redirect(redirect_url)

        isa_version = ISATab.objects.filter(
            sodar_uuid=self.kwargs.get('isatab')
        ).first()
        if not isa_version:
            messages.error(
                request, 'ISA-Tab version not found, unable to restore'
            )
            return redirect(redirect_url)

        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_restore',
                description='restore sheets from version {isatab}',
            )
            tl_event.add_object(
                obj=isa_version,
                label='isatab',
                name=isa_version.get_full_name(),
            )

        try:
            new_inv = sheet_io.import_isa(
                isa_data=isa_version.data,
                project=project,
                archive_name=isa_version.archive_name,
                user=request.user,
                replace=True if old_inv else False,
                replace_uuid=old_inv.sodar_uuid if old_inv else None,
                save_isa=False,  # Already exists as isa_version
            )
        except Exception as ex:
            self.handle_import_exception(ex, tl_event)

        if new_inv:
            new_inv = self.handle_replace(
                investigation=new_inv, old_inv=old_inv, tl_event=tl_event
            )
        if new_inv:
            new_inv = self.finalize_import(
                investigation=new_inv,
                action='restore',
                tl_event=tl_event,
                isa_version=isa_version,
            )
            # Edit isa_version to bump it in the list
            if 'RESTORE' not in isa_version.tags:
                isa_version.tags.append('RESTORE')
            isa_version.date_created = Now()
            isa_version.save()

        return redirect(
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': project.sodar_uuid},
            )
        )


class SheetVersionUpdateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    UpdateView,
):
    """Sample sheet version update view"""

    permission_required = 'samplesheets.manage_sheet'
    model = ISATab
    form_class = SheetVersionEditForm
    template_name = 'samplesheets/version_update.html'
    slug_url_kwarg = 'isatab'
    slug_field = 'sodar_uuid'

    def form_valid(self, form):
        obj = form.save()
        messages.success(
            self.request,
            'Description updated for sheet version "{}".'.format(
                obj.get_full_name()
            ),
        )
        return redirect(
            reverse(
                'samplesheets:versions',
                kwargs={'project': self.get_project().sodar_uuid},
            )
        )


class SheetVersionDeleteView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    DeleteView,
):
    """Sample sheet version deletion view"""

    permission_required = 'samplesheets.manage_sheet'
    template_name = 'samplesheets/version_confirm_delete.html'
    model = ISATab
    slug_url_kwarg = 'isatab'
    slug_field = 'sodar_uuid'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        investigation = context['investigation']
        if not investigation:
            return context
        context['sheet_version'] = ISATab.objects.filter(
            sodar_uuid=self.kwargs['isatab']
        ).first()
        return context

    def get_success_url(self):
        timeline = get_backend_api('timeline_backend')
        project = self.get_project()
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='version_delete',
                description='delete sample sheet version {isatab}',
                status_type='OK',
            )
            tl_event.add_object(
                obj=self.object,
                label='isatab',
                name=self.object.get_full_name(),
            )
        messages.success(
            self.request,
            'Deleted sample sheet version: {}'.format(
                self.object.get_full_name()
            ),
        )
        return reverse(
            'samplesheets:versions', kwargs={'project': project.sodar_uuid}
        )


class SheetVersionDeleteBatchView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    TemplateView,
):
    """Sample sheet version batch deletion view"""

    permission_required = 'samplesheets.manage_sheet'
    template_name = 'samplesheets/version_confirm_delete_batch.html'
    slug_url_kwarg = 'project'
    slug_field = 'sodar_uuid'

    def get_context_data(self, request, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['sheet_versions'] = ISATab.objects.filter(
            sodar_uuid__in=request.POST.getlist('version_check')
        )
        return context

    def post(self, request, **kwargs):
        context = self.get_context_data(request, **kwargs)
        # Render confirm template
        if request.POST.get('confirm'):
            return super().render_to_response(context)

        # Else go on with deletion
        project = context['project']
        version_count = context['sheet_versions'].count()

        timeline = get_backend_api('timeline_backend')
        if timeline:
            for sv in context['sheet_versions']:
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='version_delete',
                    description='delete sample sheet version {isatab}',
                    status_type='OK',
                )
                tl_event.add_object(
                    obj=sv,
                    label='isatab',
                    name=sv.get_full_name(),
                )

        context['sheet_versions'].delete()
        messages.success(
            request,
            'Deleted {} sample sheet version{}.'.format(
                version_count,
                's' if version_count != 1 else '',
            ),
        )
        return redirect(
            reverse(
                'samplesheets:versions', kwargs={'project': project.sodar_uuid}
            )
        )


class IrodsAccessTicketListView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    ListView,
):
    """Sample Sheet version list view"""

    model = IrodsAccessTicket
    permission_required = 'samplesheets.edit_sheet'
    template_name = 'samplesheets/irods_access_tickets.html'
    paginate_by = settings.SHEETS_IRODS_TICKET_PAGINATION

    def get_queryset(self):
        return self.model.objects.filter(
            project__sodar_uuid=self.kwargs['project']
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        irods_backend = get_backend_api('omics_irods')
        assays = Assay.objects.filter(
            study__investigation__project__sodar_uuid=self.kwargs['project']
        )
        context['track_hubs_available'] = bool(
            [
                track_hub
                for assay in assays
                for track_hub in irods_backend.get_child_colls_by_path(
                    irods_backend.get_path(assay) + '/' + TRACK_HUBS_COLL
                )
            ]
        )
        return context


class IrodsAccessTicketCreateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    SheetImportMixin,
    FormView,
):
    """Sample Sheet version restoring view"""

    permission_required = 'samplesheets.edit_sheet'
    template_name = 'samplesheets/irodsaccessticket_form.html'
    form_class = IrodsAccessTicketForm

    def get_initial(self):
        return {'project': self.get_project()}

    def form_valid(self, form):
        # Create iRODS ticket
        irods_backend = get_backend_api('omics_irods')
        ticket = irods_backend.issue_ticket(
            'read',
            form.cleaned_data['path'],
            ticket_str=build_secret(16),
            expiry_date=form.cleaned_data.get('date_expires'),
        )
        # Create database object
        obj = form.save(commit=False)
        obj.project = self.get_project()
        obj.assay = form.cleaned_data['assay']
        obj.study = obj.assay.study
        obj.user = self.request.user
        obj.ticket = ticket.ticket
        obj.save()
        messages.success(
            self.request,
            'iRODS access ticket "{}" created.'.format(obj.get_display_name()),
        )
        return redirect(
            reverse(
                'samplesheets:irods_tickets',
                kwargs={'project': self.kwargs['project']},
            )
        )


class IrodsAccessTicketUpdateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    UpdateView,
):
    """Sample sheet version deletion view"""

    permission_required = 'samplesheets.edit_sheet'
    model = IrodsAccessTicket
    form_class = IrodsAccessTicketForm
    template_name = 'samplesheets/irodsaccessticket_form.html'
    slug_url_kwarg = 'irodsaccessticket'
    slug_field = 'sodar_uuid'

    def get_initial(self):
        return {'project': self.get_project()}

    def form_valid(self, form):
        obj = form.save()
        messages.success(
            self.request,
            'iRODS access ticket "{}" updated.'.format(obj.get_display_name()),
        )
        return redirect(
            reverse(
                'samplesheets:irods_tickets',
                kwargs={'project': self.get_project().sodar_uuid},
            )
        )


class IrodsAccessTicketDeleteView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    DeleteView,
):
    """iRODS access ticket deletion view"""

    permission_required = 'samplesheets.delete_sheet'
    template_name = 'samplesheets/irodsaccessticket_confirm_delete.html'
    model = IrodsAccessTicket
    slug_url_kwarg = 'irodsaccessticket'
    slug_field = 'sodar_uuid'

    def get_success_url(self):
        return reverse(
            'samplesheets:irods_tickets',
            kwargs={'project': self.object.project.sodar_uuid},
        )

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        irods_backend = get_backend_api('omics_irods')
        try:
            irods_backend.delete_ticket(obj.ticket)
            messages.success(
                request,
                'iRODS access ticket "{}" deleted.'.format(
                    obj.get_display_name()
                ),
            )
        except Exception as e:
            messages.error(request, '%s. Maybe it didn\'t exist.' % e)
        return super().delete(request, *args, **kwargs)


class IrodsRequestCreateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    IrodsRequestModifyMixin,
    FormView,
):
    """View for creating an iRODS data request"""

    permission_required = 'samplesheets.edit_sheet'
    template_name = 'samplesheets/irods_request_form.html'
    form_class = IrodsRequestForm

    def form_valid(self, form):
        project = self.get_project()
        # Create database object
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.project = project
        obj.save()
        # Create timeline event
        self.add_tl_create(obj)
        # Add app alerts to owners/delegates
        self.add_alerts_create(project)
        messages.success(
            self.request,
            'iRODS data request "{}" created.'.format(obj.get_display_name()),
        )
        return redirect(
            reverse(
                'samplesheets:irods_requests',
                kwargs={'project': self.kwargs['project']},
            )
        )


class IrodsRequestUpdateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    UpdateView,
):
    """View for updating an iRODS data request"""

    permission_required = 'samplesheets.edit_sheet'
    template_name = 'samplesheets/irods_request_form.html'
    model = IrodsDataRequest
    form_class = IrodsRequestForm
    slug_url_kwarg = 'irodsdatarequest'
    slug_field = 'sodar_uuid'

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        # Create database object
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.project = self.get_project()
        obj.save()

        if timeline:
            tl_event = timeline.add_event(
                project=self.get_project(),
                app_name=APP_NAME,
                user=self.request.user,
                event_name='irods_request_update',
                description='update iRODS data request {irods_request}',
                status_type='OK',
            )
            tl_event.add_object(
                obj=obj, label='irods_request', name=obj.get_display_name()
            )

        messages.success(
            self.request,
            'iRODS data request "{}" updated.'.format(obj.get_display_name()),
        )
        return redirect(
            reverse(
                'samplesheets:irods_requests',
                kwargs={'project': self.get_project().sodar_uuid},
            )
        )


class IrodsRequestDeleteView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    IrodsRequestModifyMixin,
    DeleteView,
):
    """View for deleting an iRODS data request"""

    permission_required = 'samplesheets.delete_sheet'
    template_name = 'samplesheets/irods_request_confirm_delete.html'
    model = IrodsDataRequest
    slug_url_kwarg = 'irodsdatarequest'
    slug_field = 'sodar_uuid'

    def get_success_url(self):
        # Add timeline event
        self.add_tl_delete(self.object)
        # Handle project alerts
        self.handle_alerts_deactivate(self.object)
        messages.success(self.request, 'iRODS data request deleted.')
        return reverse(
            'samplesheets:irods_requests',
            kwargs={'project': self.object.project.sodar_uuid},
        )


class IrodsRequestAcceptView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    IrodsRequestModifyMixin,
    FormView,
):
    """View for accepting an iRODS data request"""

    permission_required = 'samplesheets.manage_sheet'
    template_name = 'samplesheets/irods_request_accept_form.html'
    form_class = IrodsRequestAcceptForm

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        obj = IrodsDataRequest.objects.filter(
            sodar_uuid=self.kwargs['irodsdatarequest']
        ).first()
        irods_backend = get_backend_api('omics_irods')
        context_data['irods_request'] = obj
        context_data['affected_objects'] = []
        context_data['affected_collections'] = []
        context_data['is_collection'] = obj.is_collection()
        if context_data['is_collection']:
            coll = irods_backend.get_coll_by_path(
                context_data['irods_request'].path
            )
            context_data[
                'affected_objects'
            ] += irods_backend.get_objs_recursively(coll)
            context_data[
                'affected_collections'
            ] += irods_backend.get_colls_recursively(coll)
        return context_data

    def form_valid(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        app_alerts = get_backend_api('appalerts_backend')
        project = self.get_project()
        tl_event = None

        try:
            obj = IrodsDataRequest.objects.get(
                sodar_uuid=self.kwargs['irodsdatarequest']
            )
        except IrodsDataRequest.DoesNotExist:
            messages.error(
                self.request,
                'iRODS data request {} doesn\' exist.'.format(
                    self.kwargs['irodsdatarequest']
                ),
            )
            return redirect(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': project.sodar_uuid},
                )
            )

        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='irods_request_accept',
                description='accept iRODS data request {irods_request}',
                status_type='OK',
            )
            tl_event.add_object(
                obj=obj, label='irods_request', name=obj.get_display_name()
            )

        flow_name = 'data_delete'
        flow_data = {'paths': [obj.path]}
        if obj.is_data_object():
            flow_data['paths'].append(obj.path + '.md5')

        try:
            taskflow.submit(
                project=project,
                flow_name=flow_name,
                flow_data=flow_data,
                tl_event=tl_event,
                async_mode=False,
            )
            obj.status = 'ACCEPTED'
            obj.save()
        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))
            obj.status = 'FAILED'
            obj.save()
            raise ex

        # Update cache
        if settings.SHEETS_ENABLE_CACHE:
            from samplesheets.tasks_celery import update_project_cache_task

            update_project_cache_task.delay(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(self.request.user.sodar_uuid),
            )

        # Prepare and send notification email
        if settings.PROJECTROLES_SEND_EMAIL:
            subject_body = 'iRODS delete request accepted'
            message_body = EMAIL_DELETE_REQUEST_ACCEPT.format(
                project=obj.project.title,
                user=obj.user.username,
                user_email=obj.user.email,
                path=obj.path,
            )
            send_generic_mail(
                subject_body, message_body, [obj.user.email], request
            )

        # Create app alert
        if app_alerts:
            app_alerts.add_alert(
                app_name=APP_NAME,
                alert_name=IRODS_REQ_ACCEPT_ALERT_NAME,
                user=obj.user,
                message='iRODS delete request accepted by {}: "{}"'.format(
                    self.request.user.username, obj.get_short_path()
                ),
                level='SUCCESS',
                url=reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': project.sodar_uuid},
                ),
                project=project,
            )
            # Handle project alerts
            self.handle_alerts_deactivate(obj, app_alerts)

        messages.success(
            self.request,
            'iRODS data request "{}" accepted.'.format(obj.get_display_name()),
        )
        return redirect(
            reverse(
                'samplesheets:irods_requests',
                kwargs={'project': project.sodar_uuid},
            )
        )


class IrodsRequestRejectView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    IrodsRequestModifyMixin,
    View,
):
    """View for rejecting an iRODS data request"""

    permission_required = 'samplesheets.manage_sheet'

    def get(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        app_alerts = get_backend_api('appalerts_backend')
        project = self.get_project()
        try:
            obj = IrodsDataRequest.objects.get(
                sodar_uuid=self.kwargs['irodsdatarequest']
            )
        except IrodsDataRequest.DoesNotExist:
            messages.error(
                self.request,
                'iRODS data request "{}" doesn\'t exist.'.format(
                    self.kwargs['irodsdatarequest']
                ),
            )
            return redirect(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': project.sodar_uuid},
                )
            )
        obj.status = 'REJECTED'
        obj.save()

        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='irods_request_reject',
                description='reject data iRODS request {irods_request}',
                status_type='OK',
            )
            tl_event.add_object(
                obj=obj, label='irods_request', name=obj.get_display_name()
            )

        messages.success(
            self.request,
            'iRODS data request "{}" rejected.'.format(obj.get_display_name()),
        )

        # Prepare and send notification email
        if settings.PROJECTROLES_SEND_EMAIL:
            subject_body = 'iRODS delete request rejected'
            message_body = EMAIL_DELETE_REQUEST_REJECT.format(
                project=obj.project.title,
                user=obj.user.username,
                user_email=obj.user.email,
                path=obj.path,
            )
            send_generic_mail(
                subject_body, message_body, [obj.user.email], request
            )

        # Create app alert
        if app_alerts:
            app_alerts.add_alert(
                app_name=APP_NAME,
                alert_name=IRODS_REQ_REJECT_ALERT_NAME,
                user=obj.user,
                message='iRODS delete request rejected by {}: "{}"'.format(
                    self.request.user.username, obj.get_short_path()
                ),
                level='WARNING',
                url=reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': project.sodar_uuid},
                ),
                project=project,
            )
            # Handle project alerts
            self.handle_alerts_deactivate(obj, app_alerts)

        return redirect(
            reverse(
                'samplesheets:irods_requests',
                kwargs={'project': project.sodar_uuid},
            )
        )


class IrodsDataRequestListView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    ListView,
):
    """View for listing iRODS data requests"""

    model = IrodsDataRequest
    permission_required = 'samplesheets.edit_sheet'
    template_name = 'samplesheets/irods_requests.html'
    paginate_by = settings.SHEETS_IRODS_REQUEST_PAGINATION

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        assign = RoleAssignment.objects.filter(
            project=self.get_project(),
            user=self.request.user,
            role__name=SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR'],
        )
        context_data['is_contributor'] = bool(assign)
        return context_data

    def get_queryset(self):
        project = self.get_project()
        queryset = self.model.objects.filter(project=project)
        # For superusers, owners and delegates,
        # display active/failed requests from all users
        if (
            self.request.user.is_superuser
            or project.is_delegate(self.request.user)
            or project.is_owner(self.request.user)
        ):
            return queryset.filter(status__in=['ACTIVE', 'FAILED'])
        # For regular users, dispaly their own requests regardless of status
        return queryset.filter(user=self.request.user)


class SheetRemoteSyncView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Sample sheet remote sync view for manual sync"""

    permission_required = 'samplesheets.edit_sheet'

    def _redirect(self):
        return redirect(
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.get_project().sodar_uuid},
            )
        )

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        timeline = get_backend_api('timeline_backend')
        tl_add = False
        tl_status_type = 'OK'
        tl_status_desc = 'Sync OK'
        sheet_sync_enable = app_settings.get_app_setting(
            APP_NAME, 'sheet_sync_enable', project=project
        )

        # Sanity check, view is not shown in UI when variable is disabled
        if not sheet_sync_enable:
            messages.error(request, SYNC_FAIL_DISABLED)
            return self._redirect()

        sync_api = SheetRemoteSyncAPI()
        try:
            ret = sync_api.sync_sheets(project, request.user)
            if ret:
                messages.success(request, SYNC_SUCCESS_MSG)
                tl_add = True
            else:
                messages.info(
                    request, 'Sample sheet sync skipped, no changes detected'
                )
        except Exception as ex:
            tl_status_type = 'FAILED'
            tl_status_desc = 'Sync failed: {}'.format(ex)
            messages.error(request, '{}: {}'.format(SYNC_FAIL_PREFIX, ex))
            tl_add = True  # Add timeline event

        if timeline and tl_add:
            sheet_sync_url = app_settings.get_app_setting(
                APP_NAME, 'sheet_sync_url', project=project
            )
            timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=request.user,
                event_name='sheet_sync_manual',
                description='sync sheets from source project (manual)',
                status_type=tl_status_type,
                status_desc=tl_status_desc,
                extra_data={'url': sheet_sync_url},
            )
        return self._redirect()
