import io
import json
import logging
import os
from packaging import version
import re
import zipfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.views.generic import TemplateView, FormView, DeleteView, View

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.versioning import AcceptHeaderVersioning
from knox.auth import TokenAuthentication

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, RemoteSite, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
    APIPermissionMixin,
    BaseTaskflowAPIView,
)

from samplesheets.forms import SampleSheetImportForm
from samplesheets.io import SampleSheetIO, SampleSheetImportException
from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    Protocol,
    Process,
    GenericMaterial,
    ISATab,
)
from samplesheets.rendering import SampleSheetTableBuilder, EMPTY_VALUE
from samplesheets.tasks import update_project_cache_task
from samplesheets.utils import (
    get_sample_dirs,
    compare_inv_replace,
    get_sheets_url,
    get_comments,
    write_excel_table,
    build_sheet_config,
)

# Get logger
logger = logging.getLogger(__name__)

# App settings API
app_settings = AppSettingAPI()


# SODAR constants
SITE_MODE_TARGET = SODAR_CONSTANTS['SITE_MODE_TARGET']
REMOTE_LEVEL_READ_ROLES = SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES']


# Local constants
APP_NAME = 'samplesheets'
WARNING_STATUS_MSG = 'OK with warnings, see extra data'
TARGET_ALTAMISA_VERSION = '0.2.4'  # For warnings etc.
EDIT_JSON_ATTRS = [
    'characteristics',
    'comments',
    'factor_values',
    'parameter_values',
]
EDIT_FIELD_MAP = {
    'array design ref': 'array_design_ref',
    'label': 'extract_label',
    'performer': 'performer',
}


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


class SampleSheetImportMixin:
    """Mixin for sample sheet importing/replacing helpers"""

    def handle_replace(self, investigation, old_inv, tl_event=None):
        project = investigation.project
        old_study_uuids = {}
        old_assay_uuids = {}

        try:
            # Ensure existing studies and assays are found in new inv
            if old_inv.irods_status:
                compare_inv_replace(old_inv, investigation)

            # Save UUIDs
            old_inv_uuid = old_inv.sodar_uuid

            for study in old_inv.studies.all():
                old_study_uuids[study.identifier] = study.sodar_uuid

                for assay in study.assays.all():
                    old_assay_uuids[assay.get_name()] = assay.sodar_uuid

            # Set irods_status to our previous sheet's state
            investigation.irods_status = old_inv.irods_status
            investigation.save()

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

            self.handle_import_exception(ex, tl_event)
            return None

        # If all went well..

        # Update UUIDs
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

    def handle_import_exception(self, ex, tl_event=None):
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

            messages.error(self.request, mark_safe(ex_msg))

        else:
            ex_msg = 'ISAtab import failed: {}'.format(ex)
            extra_data = None
            messages.error(self.request, ex_msg)

        if tl_event:
            tl_event.set_status(
                'FAILED', status_desc=ex_msg, extra_data=extra_data
            )

    def finalize_import(
        self, investigation, action, tl_event=None, isa_version=None
    ):
        project = investigation.project

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

        success_msg = '{}d sample sheets from {}'.format(
            action.capitalize(),
            'version {}'.format(isa_version.get_name())
            if action == 'restore'
            else 'ISAtab import',
        )

        if investigation.parser_warnings:
            success_msg += (
                ' (<strong>Note:</strong> '
                '<a href="#/warnings">parser warnings raised</a>)'
            )

        # Build sheet configuration, also save it to the related ISATab
        # NOTE: For now, this has to be done when we replace sheets, in case the
        #       columns have been altered
        # TODO: A smarter update method which detects removed/added/moved cols
        logger.debug(
            '{} sheet configuration..'.format(
                'Replacing' if action != 'create' else 'Building'
            )
        )

        if isa_version:
            sheet_config = isa_version.data.get('sheet_config')

        if not sheet_config:
            sheet_config = build_sheet_config(investigation)

            if isa_version:
                isa_version.data['sheet_config'] = sheet_config
                isa_version.save()

        app_settings.set_app_setting(
            APP_NAME, 'sheet_config', sheet_config, project=project
        )
        logger.info(
            'Sheet configuration {}'.format(
                'replaced' if action != 'create' else 'built'
            )
        )

        if isa_version:
            isa_version.data['sheet_config'] = sheet_config
            logger.info('Sheet configuration added into ISATab version')

        # Update project cache if replacing sheets and iRODS collections exists
        if (
            action in ['replace', 'restore']
            and investigation.irods_status
            and settings.SHEETS_ENABLE_CACHE
        ):
            update_project_cache_task.delay(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(self.request.user.sodar_uuid),
            )
            success_msg += ', initiated iRODS cache update'

        messages.success(self.request, mark_safe(success_msg))
        return investigation


# Regular Views ----------------------------------------------------------------


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
                    'samplesheets:api_context_get',
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


class SampleSheetImportView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    SampleSheetImportMixin,
    FormView,
):
    """Sample sheet ISATab import view"""

    permission_required = 'samplesheets.edit_sheet'
    model = Investigation
    form_class = SampleSheetImportForm
    template_name = 'samplesheets/samplesheet_import_form.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        project = self.get_project()

        try:
            old_inv = Investigation.objects.get(project=project, active=True)
            context['replace_sheets'] = True
            context['irods_status'] = old_inv.irods_status

            # Check for active zones in case of sheet replacing
            if (
                old_inv.project.landing_zones.exclude(
                    status__in=['ACTIVE', 'MOVED', 'DELETED']
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

        # TODO: Use CurrentUserFormMixin instead (see issue #660)
        kwargs.update({'current_user': self.request.user})
        return kwargs

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        project = self.get_project()
        form_kwargs = self.get_form_kwargs()
        form_action = 'replace' if form_kwargs['replace'] else 'create'
        redirect_url = get_sheets_url(project)
        tl_event = None

        if timeline:
            if form_action == 'replace':
                tl_desc = 'replace previous investigation with {investigation}'

            else:
                tl_desc = 'create investigation {investigation}'

            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_' + form_action,
                description=tl_desc,
            )

        # Try actual import
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

        return redirect(redirect_url)


class SampleSheetExcelExportView(
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

        redirect_url = get_sheets_url(self.get_project())
        if not study:
            messages.error(
                self.request, 'Study not found, unable to render an Excel file'
            )
            return redirect(redirect_url)

        # Build study tables
        tb = SampleSheetTableBuilder()

        try:
            tables = tb.build_study_tables(study)

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

        if timeline:
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


class SampleSheetISAExportView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Sample sheet table ISAtab export view"""

    permission_required = 'samplesheets.export_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return ISAtab files as a ZIP archive"""
        timeline = get_backend_api('timeline_backend')
        tl_event = None
        project = self.get_project()
        sheet_io = SampleSheetIO()

        isa_version = None
        version_uuid = kwargs.get('isatab')

        if version_uuid:
            redirect_url = reverse(
                'samplesheets:versions', kwargs={'project': project.sodar_uuid}
            )

            try:
                isa_version = ISATab.objects.get(
                    project=project, sodar_uuid=version_uuid
                )
                investigation = Investigation.objects.get(
                    sodar_uuid=isa_version.investigation_uuid
                )

            except (ISATab.DoesNotExist, Investigation.DoesNotExist):
                messages.error(
                    request, 'Unable to retrieve sample sheet version'
                )
                return redirect(redirect_url)

        else:
            redirect_url = get_sheets_url(project)

            try:
                investigation = Investigation.objects.get(project=project)

            except Investigation.DoesNotExist:
                messages.error(
                    request, 'No sample sheets available for project'
                )
                return redirect(redirect_url)

        if not isa_version and (
            not investigation.parser_version
            or version.parse(investigation.parser_version)
            < version.parse(TARGET_ALTAMISA_VERSION)
        ):
            messages.error(
                request,
                'Exporting ISAtabs imported using altamISA < {} is not '
                'supported. Please replace the sheets to enable export.'.format(
                    TARGET_ALTAMISA_VERSION
                ),
            )
            return redirect(redirect_url)

        # Set up archive file name
        archive_name = (
            isa_version.archive_name
            if isa_version
            else investigation.archive_name
        )

        if archive_name:
            file_name = archive_name.split('.zip')[0]

        else:
            file_name = re.sub(
                r'[\s]+', '_', re.sub(r'[^\w\s-]', '', project.title).strip()
            )

        if isa_version:
            file_name += '_' + isa_version.date_created.strftime(
                '%Y-%m-%d_%H%M%S'
            )

            if isa_version.user:
                file_name += '_' + slugify(isa_version.user.username)

        file_name += '.zip'

        if timeline:
            if isa_version:
                tl_desc = 'export {investigation} version {isatab}'

            else:
                tl_desc = 'export {investigation} as ISAtab'

            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
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
                    obj=isa_version, label='isatab', name=isa_version.get_name()
                )

        # Initiate export
        try:
            if isa_version:
                export_data = isa_version.data

            else:
                export_data = sheet_io.export_isa(investigation)

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
            response = HttpResponse(
                zip_io.getvalue(), content_type='application/zip'
            )
            response[
                'Content-Disposition'
            ] = 'attachment; filename="{}"'.format(file_name)
            return response

        except Exception as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            if settings.DEBUG:
                raise ex

            messages.error(request, 'Unable to export ISAtab: {}'.format(ex))
            return redirect(redirect_url)


class SampleSheetDeleteView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
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
                status_type='OK',
            )

            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title,
            )

        delete_success = True

        if taskflow and investigation.irods_status:
            if tl_event:
                tl_event.set_status('SUBMIT')

            try:
                taskflow.submit(
                    project_uuid=project.sodar_uuid,
                    flow_name='sheet_delete',
                    flow_data={},
                    request=self.request,
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

        if delete_success:
            # Delete ISATab versions
            isa_versions = ISATab.objects.filter(project=project)
            v_count = isa_versions.count()
            isa_versions.delete()
            logger.debug(
                'Deleted {} ISATab version{}'.format(
                    v_count, 's' if v_count != 1 else ''
                )
            )

            # Delete sheet configuration
            app_settings.set_app_setting(
                APP_NAME, 'sheet_config', {}, project=project
            )
            messages.success(self.request, 'Sample sheets deleted.')

        return HttpResponseRedirect(get_sheets_url(project))


class SampleSheetCacheUpdateView(
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
            update_project_cache_task.delay(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(request.user.sodar_uuid),
            )

            messages.warning(
                self.request,
                'Cache updating initiated. This may take some time, refresh '
                'sheet view after a while to see the results.',
            )
        return HttpResponseRedirect(get_sheets_url(project))


class IrodsDirsView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    TemplateView,
):
    """iRODS directory structure creation view"""

    template_name = 'samplesheets/irods_dirs_confirm.html'
    # NOTE: minimum perm, all checked files will be tested in post()
    permission_required = 'samplesheets.create_dirs'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        investigation = context['investigation']

        if not investigation:
            return context

        context['dirs'] = get_sample_dirs(investigation)
        context['update_dirs'] = True if investigation.irods_status else False
        return context

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        context = self.get_context_data(**kwargs)
        project = context['project']
        investigation = context['investigation']
        tl_event = None
        action = 'update' if context['update_dirs'] else 'create'

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_dirs_' + action,
                description=action + ' irods directory structure for '
                '{investigation}',
            )

            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title,
            )

        # Fail if tasflow is not available
        if not taskflow:
            if timeline:
                tl_event.set_status(
                    'FAILED', status_desc='Taskflow not enabled'
                )

            messages.error(
                self.request,
                'Unable to {} dirs: taskflow not enabled!'.format(action),
            )
            return redirect(get_sheets_url(project))

        # Else go on with the creation
        if tl_event:
            tl_event.set_status('SUBMIT')

        flow_data = {'dirs': context['dirs']}

        try:
            taskflow.submit(
                project_uuid=project.sodar_uuid,
                flow_name='sheet_dirs_create',
                flow_data=flow_data,
                request=self.request,
            )

            if tl_event:
                tl_event.set_status('OK')

            success_msg = (
                'Directory structure for sample data '
                '{}d in iRODS'.format(action)
            )

            if settings.SHEETS_ENABLE_CACHE:
                update_project_cache_task.delay(
                    project_uuid=str(project.sodar_uuid),
                    user_uuid=str(self.request.user.sodar_uuid),
                )
                success_msg += ', initiated iRODS cache update'

            messages.success(self.request, success_msg)

        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            messages.error(self.request, str(ex))

        return HttpResponseRedirect(get_sheets_url(project))

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        return super().render_to_response(self.get_context_data())


class SampleSheetVersionListView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    TemplateView,
):
    """Sample Sheet version list view"""

    permission_required = 'samplesheets.edit_sheet'
    template_name = 'samplesheets/sheet_versions.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['sheet_versions'] = None
        context['current_version'] = None

        if context['investigation']:
            context['sheet_versions'] = ISATab.objects.filter(
                project=self.get_project(),
                investigation_uuid=context['investigation'].sodar_uuid,
            ).order_by('-date_created')

        if context['sheet_versions']:
            context['current_version'] = context['sheet_versions'][0]

        return context


class SampleSheetVersionRestoreView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    InvestigationContextMixin,
    ProjectPermissionMixin,
    SampleSheetImportMixin,
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
                request, 'ISATab version not found, unable to restore'
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
                obj=isa_version, label='isatab', name=isa_version.get_name()
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

            isa_version.save()

        return redirect(
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': project.sodar_uuid},
            )
        )


class SampleSheetVersionDeleteView(
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
                obj=self.object, label='isatab', name=self.object.get_name()
            )

        messages.success(
            self.request,
            'Deleted sample sheet version: {}'.format(self.object.get_name()),
        )
        return reverse(
            'samplesheets:versions', kwargs={'project': project.sodar_uuid}
        )


# Ajax API Views ---------------------------------------------------------------


class SampleSheetContextGetAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """View to retrieve sample sheet context data"""

    permission_required = 'samplesheets.view_sheet'
    renderer_classes = [JSONRenderer]

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        studies = Study.objects.filter(investigation=investigation).order_by(
            'pk'
        )
        irods_backend = get_backend_api('omics_irods')

        # Can't import at module root due to circular dependency
        from .plugins import find_study_plugin, find_assay_plugin

        # General context data for Vue app
        ret_data = {
            'configuration': investigation.get_configuration()
            if investigation
            else None,
            'inv_file_name': investigation.file_name.split('/')[-1]
            if investigation
            else None,
            'irods_status': investigation.irods_status
            if investigation
            else None,
            'irods_backend_enabled': (
                True if get_backend_api('omics_irods') else False
            ),
            'parser_version': (investigation.parser_version or 'LEGACY')
            if investigation
            else None,
            'parser_warnings': True
            if investigation
            and investigation.parser_warnings
            and 'use_file_names' in investigation.parser_warnings
            else False,
            'irods_webdav_enabled': settings.IRODS_WEBDAV_ENABLED,
            'irods_webdav_url': settings.IRODS_WEBDAV_URL.rstrip('/'),
            'external_link_labels': settings.SHEETS_EXTERNAL_LINK_LABELS,
            'table_height': settings.SHEETS_TABLE_HEIGHT,
            'min_col_width': settings.SHEETS_MIN_COLUMN_WIDTH,
            'max_col_width': settings.SHEETS_MAX_COLUMN_WIDTH,
            'allow_editing': app_settings.get_app_setting(
                APP_NAME, 'allow_editing', project=project
            ),
            'alerts': [],
            'csrf_token': get_token(request),
        }

        if investigation and (
            not investigation.parser_version
            or version.parse(investigation.parser_version)
            < version.parse(TARGET_ALTAMISA_VERSION)
        ):
            ret_data['alerts'].append(
                {
                    'level': 'danger',
                    'text': 'This sample sheet has been imported with an '
                    'old altamISA version (< {}). Please replace the ISAtab '
                    'to enable all features and ensure full '
                    'functionality.'.format(TARGET_ALTAMISA_VERSION),
                }
            )

        # Study info
        ret_data['studies'] = {}

        for s in studies:
            study_plugin = find_study_plugin(investigation.get_configuration())
            ret_data['studies'][str(s.sodar_uuid)] = {
                'display_name': s.get_display_name(),
                'description': s.description,
                'comments': get_comments(s),
                'irods_path': irods_backend.get_path(s)
                if irods_backend
                else None,
                'table_url': request.build_absolute_uri(
                    reverse(
                        'samplesheets:api_study_tables_get',
                        kwargs={'study': str(s.sodar_uuid)},
                    )
                ),
                'plugin': study_plugin.title if study_plugin else None,
                'assays': {},
            }

            # Set up assay data
            for a in s.assays.all().order_by('pk'):
                assay_plugin = find_assay_plugin(
                    a.measurement_type, a.technology_type
                )
                ret_data['studies'][str(s.sodar_uuid)]['assays'][
                    str(a.sodar_uuid)
                ] = {
                    'name': a.get_name(),
                    'display_name': a.get_display_name(),
                    'irods_path': irods_backend.get_path(a)
                    if irods_backend
                    else None,
                    'display_row_links': assay_plugin.display_row_links
                    if assay_plugin
                    else True,
                    'plugin': assay_plugin.title if assay_plugin else None,
                }

        # Permissions for UI elements (will be checked on request)
        ret_data['perms'] = {
            'edit_sheet': request.user.has_perm(
                'samplesheets.edit_sheet', project
            ),
            'manage_sheet': request.user.has_perm(
                'samplesheets.manage_sheet', project
            ),
            'create_dirs': request.user.has_perm(
                'samplesheets.create_dirs', project
            ),
            'export_sheet': request.user.has_perm(
                'samplesheets.export_sheet', project
            ),
            'delete_sheet': request.user.has_perm(
                'samplesheets.delete_sheet', project
            ),
            'is_superuser': request.user.is_superuser,
        }

        # Overview data
        ret_data['investigation'] = (
            {
                'identifier': investigation.identifier,
                'title': investigation.title,
                'description': investigation.description
                if investigation.description != project.description
                else None,
                'comments': get_comments(investigation),
            }
            if investigation
            else {}
        )

        # Statistics
        ret_data['sheet_stats'] = (
            {
                'study_count': Study.objects.filter(
                    investigation=investigation
                ).count(),
                'assay_count': Assay.objects.filter(
                    study__investigation=investigation
                ).count(),
                'protocol_count': Protocol.objects.filter(
                    study__investigation=investigation
                ).count(),
                'process_count': Process.objects.filter(
                    protocol__study__investigation=investigation
                ).count(),
                'source_count': investigation.get_material_count('SOURCE'),
                'material_count': investigation.get_material_count('MATERIAL'),
                'sample_count': investigation.get_material_count('SAMPLE'),
                'data_count': investigation.get_material_count('DATA'),
            }
            if investigation
            else {}
        )

        ret_data = json.dumps(ret_data)
        return Response(ret_data, status=200)


class SampleSheetStudyTablesGetAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """View to retrieve study tables built from the sample sheet graph"""

    permission_required = 'samplesheets.view_sheet'
    renderer_classes = [JSONRenderer]

    def has_permission(self):
        """Override has_permission() to check perms depending on edit mode"""
        if bool(self.request.GET.get('edit')):
            return self.request.user.has_perm(
                'samplesheets.edit_sheet', self.get_permission_object()
            )

        return super().has_permission()

    def get(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        irods_backend = get_backend_api('omics_irods')
        cache_backend = get_backend_api('sodar_cache')
        study = Study.objects.filter(sodar_uuid=self.kwargs['study']).first()

        if not study:
            return Response(
                {
                    'render_error': 'Study not found with UUID "{}", '
                    'unable to render'.format(self.kwargs['study'])
                },
                status=404,
            )

        # Return extra edit mode data
        project = study.investigation.project
        edit = bool(request.GET.get('edit'))
        allow_editing = app_settings.get_app_setting(
            APP_NAME, 'allow_editing', project=project
        )

        if edit and not allow_editing:
            return Response(
                {
                    'render_error': 'Editing not allowed in the project, '
                    'unable to render'
                },
                status=403,
            )

        ret_data = {'study': {'display_name': study.get_display_name()}}
        tb = SampleSheetTableBuilder()

        try:
            ret_data['tables'] = tb.build_study_tables(study, edit=edit)

        except Exception as ex:
            # Raise if we are in debug mode
            if settings.DEBUG:
                raise ex

            # TODO: Log error
            ret_data['render_error'] = str(ex)
            return Response(ret_data, status=200)

        # Get iRODS content if NOT editing and collections have been created
        if not edit and study.investigation.irods_status and irods_backend:
            # Can't import at module root due to circular dependency
            from .plugins import find_study_plugin
            from .plugins import find_assay_plugin

            # Get study plugin for shortcut data
            study_plugin = find_study_plugin(
                study.investigation.get_configuration()
            )

            if study_plugin:
                shortcuts = study_plugin.get_shortcut_column(
                    study, ret_data['tables']
                )
                ret_data['tables']['study']['shortcuts'] = shortcuts

            # Get assay content if corresponding assay plugin exists
            for a_uuid, a_data in ret_data['tables']['assays'].items():
                assay = Assay.objects.filter(sodar_uuid=a_uuid).first()
                assay_path = irods_backend.get_path(assay)
                a_data['irods_paths'] = []
                assay_plugin = find_assay_plugin(
                    assay.measurement_type, assay.technology_type
                )

                if assay_plugin:
                    cache_item = cache_backend.get_cache_item(
                        name='irods/rows/{}'.format(a_uuid),
                        app_name=assay_plugin.app_name,
                        project=assay.get_project(),
                    )

                    for row in a_data['table_data']:
                        # Update assay links column
                        path = assay_plugin.get_row_path(
                            row, a_data, assay, assay_path
                        )
                        enabled = True

                        # Set initial state to disabled by cached value
                        if (
                            cache_item
                            and path in cache_item.data['paths']
                            and (
                                not cache_item.data['paths'][path]
                                or cache_item.data['paths'][path] == 0
                            )
                        ):
                            enabled = False

                        a_data['irods_paths'].append(
                            {'path': path, 'enabled': enabled}
                        )
                        # Update row links
                        assay_plugin.update_row(row, a_data, assay)

                    # Add extra table if available
                    a_data['extra_table'] = assay_plugin.get_extra_table(
                        a_data, assay
                    )

        # Get sheet configuration if editing
        if edit:
            # If the config doesn't exist yet, build it
            sheet_config = app_settings.get_app_setting(
                APP_NAME, 'sheet_config', project=project
            )

            if not sheet_config:
                logger.debug('No sheet configuration found, building..')
                sheet_config = build_sheet_config(study.investigation)
                app_settings.set_app_setting(
                    APP_NAME, 'sheet_config', sheet_config, project=project
                )
                logger.info('Sheet configuration built for investigation')

            ret_data['study_config'] = sheet_config['studies'][
                str(study.sodar_uuid)
            ]

            if timeline:
                timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=request.user,
                    event_name='sheet_edit_start',
                    description='started editing sheets',
                    status_type='OK',
                )

        return Response(ret_data, status=200)


class SampleSheetStudyLinksGetAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """View to retrieve data for shortcut links from study apps"""

    # TODO: Also do this for assay apps?
    permission_required = 'samplesheets.view_sheet'
    renderer_classes = [JSONRenderer]

    def get(self, request, *args, **kwargs):
        study = Study.objects.filter(sodar_uuid=self.kwargs['study']).first()

        # Get study plugin for shortcut data
        from .plugins import find_study_plugin

        study_plugin = find_study_plugin(
            study.investigation.get_configuration()
        )

        if not study_plugin:
            return Response(
                {'message': 'Plugin not found for study'}, status=404
            )

        ret_data = {'study': {'display_name': study.get_display_name()}}
        tb = SampleSheetTableBuilder()

        try:
            study_tables = tb.build_study_tables(study)

        except Exception as ex:
            # TODO: Log error
            ret_data['render_error'] = str(ex)
            return Response(ret_data, status=200)

        ret_data = study_plugin.get_shortcut_links(
            study, study_tables, **request.GET
        )
        return Response(ret_data, status=200)


class SampleSheetWarningsGetAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """View to retrieve parser warnings for sample sheets"""

    permission_required = 'samplesheets.view_sheet'
    renderer_classes = [JSONRenderer]

    def get(self, request, *args, **kwargs):
        investigation = Investigation.objects.filter(
            project=self.get_project()
        ).first()

        if not investigation:
            return Response(
                {'message': 'Investigation not found for project'}, status=404
            )

        return Response({'warnings': investigation.parser_warnings}, status=200)


class SampleSheetEditPostAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """View to edit sample sheet data"""

    permission_required = 'samplesheets.edit_sheet'
    renderer_classes = [JSONRenderer]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        updated_cells = request.data.get('updated_cells') or []

        for cell in updated_cells:
            logger.debug('Cell update: {}'.format(cell))
            obj = (
                eval(cell['obj_cls'])
                .objects.filter(sodar_uuid=cell['uuid'])
                .first()
            )
            # TODO: Make sure given object actually belongs in project etc.

            if not obj:
                logger.error(
                    'No {} found with UUID={}'.format(
                        cell['obj_cls'], cell['uuid']
                    )
                )
                # TODO: Return list of errors when processing in batch
                return Response(
                    {
                        'message': 'Object not found: {} ({})'.format(
                            cell['uuid'], cell['obj_cls']
                        )
                    },
                    status=500,
                )

            logger.debug(
                'Editing {} "{}" ({})'.format(
                    obj.__class__.__name__, obj.unique_name, obj.sodar_uuid
                )
            )

            # TODO: Provide the original header as one string instead
            header_type = cell['header_type']
            header_name = cell['header_name']

            # Plain fields
            if not header_type and header_name.lower() in EDIT_FIELD_MAP:
                attr_name = EDIT_FIELD_MAP[header_name.lower()]
                attr = getattr(obj, attr_name)

                if isinstance(attr, str):
                    setattr(obj, attr_name, cell['value'])

                elif isinstance(attr, dict):
                    attr['name'] = cell['value']

                    # TODO: Set accession and ontology once editing is allowed

                obj.save()
                logger.debug('Edited field: {}'.format(attr_name))

            # JSON Attributes
            elif header_type in EDIT_JSON_ATTRS:
                attr = getattr(obj, header_type)

                # TODO: Is this actually a thing nowadays?
                if isinstance(attr[header_name], str):
                    attr[header_name] = cell['value']

                elif isinstance(attr[header_name], dict):
                    # TODO: Ontology value and list support
                    attr[header_name]['value'] = cell['value']

                    # TODO: Support ontology ref in unit
                    if 'unit' not in attr[header_name] or isinstance(
                        attr[header_name]['unit'], str
                    ):
                        attr[header_name]['unit'] = cell.get('unit')

                    elif isinstance(attr[header_name]['unit'], dict):
                        attr[header_name]['unit']['name'] = cell.get('unit')

                obj.save()
                logger.debug(
                    'Edited JSON attribute: {}[{}]'.format(
                        header_type, header_name
                    )
                )

            else:
                logger.error(
                    'Editing not implemented '
                    '(header_type={}; header_name={}'.format(
                        header_type, header_name
                    )
                )
                return Response({'message': 'failed'}, status=500)

        # TODO: Log edits in timeline here, once saving in bulk

        return Response({'message': 'ok'}, status=200)


class SampleSheetEditFinishAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """View for finishing editing and saving an ISAtab copy of the current
    sample sheet"""

    permission_required = 'samplesheets.edit_sheet'
    renderer_classes = [JSONRenderer]

    def post(self, request, *args, **kwargs):
        updated = request.data.get('updated')
        log_msg = 'Finish editing: '

        if not updated:
            logger.info(log_msg + 'nothing updated')
            return Response({'message': 'ok'}, status=200)  # Nothing to do

        timeline = get_backend_api('timeline_backend')
        isa_version = None
        sheet_io = SampleSheetIO()
        project = self.get_project()
        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        export_ex = None

        try:
            isa_data = sheet_io.export_isa(investigation)

            # Save sheet config with ISATab version
            isa_data['sheet_config'] = app_settings.get_app_setting(
                APP_NAME, 'sheet_config', project=project
            )
            isa_version = sheet_io.save_isa(
                project=project,
                inv_uuid=investigation.sodar_uuid,
                isa_data=isa_data,
                tags=['EDIT'],
                user=request.user,
                archive_name=investigation.archive_name,
            )

        except Exception as ex:
            logger.error(
                log_msg + 'Unable to export sheet to ISAtab: {}'.format(ex)
            )
            export_ex = str(ex)

        if timeline:
            tl_status = 'FAILED' if export_ex else 'OK'
            tl_desc = 'finish editing sheets '

            if not updated:
                tl_desc += '(no updates)'

            elif not export_ex and isa_version:
                tl_desc += 'and save version as {isatab}'

            else:
                tl_desc += '(saving version failed)'

            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=request.user,
                event_name='sheet_edit_finish',
                description=tl_desc,
                status_type=tl_status,
                status_desc=export_ex if tl_status == 'FAILED' else None,
            )

            if not export_ex and isa_version:
                tl_event.add_object(
                    obj=isa_version, label='isatab', name=isa_version.get_name()
                )

        if not export_ex:
            logger.info(
                log_msg + 'Saved ISATab "{}"'.format(isa_version.get_name())
            )
            return Response({'message': 'ok'}, status=200)

        return Response({'message': export_ex}, status=500)


class SampleSheetManagePostAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """View to manage sample sheet configuration"""

    permission_required = 'samplesheets.manage_sheet'
    renderer_classes = [JSONRenderer]

    # TODO: Add node name for logging/timeline
    def post(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        project = self.get_project()
        fields = request.data.get('fields')
        sheet_config = app_settings.get_app_setting(
            APP_NAME, 'sheet_config', project=project
        )

        for field in fields:
            logger.debug('Field config: {}'.format(field))
            s_uuid = field['study']
            a_uuid = field['assay']
            n_idx = field['node_idx']
            f_idx = field['field_idx']
            debug_info = 'study="{}"; assay="{}"; n={}; f={})'.format(
                s_uuid, a_uuid, n_idx, f_idx
            )

            try:
                if a_uuid:
                    og_config = sheet_config['studies'][s_uuid]['assays'][
                        a_uuid
                    ]['nodes'][n_idx]['fields'][f_idx]

                else:
                    og_config = sheet_config['studies'][s_uuid]['nodes'][n_idx][
                        'fields'
                    ][f_idx]

            except Exception as ex:
                msg = 'Unable to access config field ({}): {}'.format(
                    debug_info, ex
                )
                logger.error(msg)
                return Response({'message': msg}, status=500)

            if (
                field['config']['name'] != og_config['name']
                or field['config']['type'] != og_config['type']
            ):
                msg = 'Fields do not match ({})'.format(debug_info)
                logger.error(msg)
                return Response({'message': msg}, status=500)

            # Cleanup data
            c = field['config']

            if c['format'] != 'integer':
                c.pop('range', None)
                c.pop('unit', None)
                c.pop('unit_default', None)

            elif 'range' in c and not c['range'][0] and not c['range'][1]:
                c.pop('range', None)

            if c['format'] == 'select':
                c.pop('regex', None)

            else:  # Select
                c.pop('options', None)

            if a_uuid:
                sheet_config['studies'][s_uuid]['assays'][a_uuid]['nodes'][
                    n_idx
                ]['fields'][f_idx] = c

            else:
                sheet_config['studies'][s_uuid]['nodes'][n_idx]['fields'][
                    f_idx
                ] = c

            app_settings.set_app_setting(
                APP_NAME, 'sheet_config', sheet_config, project=project
            )
            logger.info(
                'Updated field config for "{}" ({}) in {} {}'.format(
                    c['name'],
                    c['type'],
                    'assay' if a_uuid else 'study',
                    a_uuid if a_uuid else s_uuid,
                )
            )

            if timeline:
                if a_uuid:
                    tl_obj = Assay.objects.filter(sodar_uuid=a_uuid).first()

                else:
                    tl_obj = Study.objects.filter(sodar_uuid=s_uuid).first()

                tl_label = tl_obj.__class__.__name__.lower()

                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=request.user,
                    event_name='field_update',
                    description='update field configuration for "{}" '
                    'in {{{}}}'.format(c['name'].title(), tl_label),
                    status_type='OK',
                    extra_data={'config': c},
                )
                tl_event.add_object(
                    obj=tl_obj, label=tl_label, name=tl_obj.get_display_name()
                )

        return Response({'message': 'ok'}, status=200)


# General API Views ------------------------------------------------------------


# NOTE: Using a specific versioner for the query API, to be generalized..
class SourceIDAPIVersioning(AcceptHeaderVersioning):
    default_version = settings.SODAR_API_DEFAULT_VERSION
    allowed_versions = [settings.SODAR_API_DEFAULT_VERSION]
    version_param = 'version'


class SourceIDAPIRenderer(JSONRenderer):
    media_type = 'application/vnd.bihealth.sodar+json'


class SourceIDQueryAPIView(APIView):
    """Proof-of-concept source ID querying view for BeLOVE integration"""

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    versioning_class = SourceIDAPIVersioning
    renderer_classes = [SourceIDAPIRenderer]

    def get(self, *args, **kwargs):
        source_id = self.kwargs['source_id']

        source_count = GenericMaterial.objects.find(
            search_term=source_id, item_type='SOURCE'
        ).count()

        ret_data = {'id_found': True if source_count > 0 else False}
        return Response(ret_data, status=200)


# TODO: Temporary HACK, should be replaced by real solution (sodar_core#261)
class RemoteSheetGetAPIView(APIView):
    """Temporary API view for retrieving the sample sheet as JSON by a target
    site, either as rendered tables or the original ISAtab"""

    permission_classes = (AllowAny,)  # We check the secret in get()/post()

    def get(self, request, **kwargs):
        secret = kwargs['secret']
        isa = request.GET.get('isa')

        try:
            target_site = RemoteSite.objects.get(
                mode=SITE_MODE_TARGET, secret=secret
            )

        except RemoteSite.DoesNotExist:
            return Response('Remote site not found, unauthorized', status=401)

        target_project = target_site.projects.filter(
            project_uuid=kwargs['project']
        ).first()

        if (
            not target_project
            or target_project.level != REMOTE_LEVEL_READ_ROLES
        ):
            return Response(
                'No project access for remote site, unauthorized', status=401
            )

        try:
            investigation = Investigation.objects.get(
                project=target_project.get_project(), active=True
            )

        except Investigation.DoesNotExist:
            return Response(
                'No ISA investigation found for project', status=404
            )

        # All OK so far, return data
        # Rendered tables
        if not isa or int(isa) != 1:
            ret = {'studies': {}}
            tb = SampleSheetTableBuilder()

            # Build study tables
            for study in investigation.studies.all():
                try:
                    tables = tb.build_study_tables(study)

                except Exception as ex:
                    return Response(str(ex), status=500)

                ret['studies'][str(study.sodar_uuid)] = tables

        # Original ISAtab
        else:
            sheet_io = SampleSheetIO()

            try:
                ret = sheet_io.export_isa(investigation)

            except Exception as ex:
                return Response(str(ex), status=500)

        return Response(ret, status=200)


# Taskflow API Views -----------------------------------------------------------


# TODO: Integrate Taskflow API functionality with general SODAR API (see #47)


class TaskflowDirStatusGetAPIView(BaseTaskflowAPIView):
    """View for getting the sample sheet iRODS dir status"""

    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__sodar_uuid=request.data['project_uuid'], active=True
            )

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        return Response({'dir_status': investigation.irods_status}, 200)


class TaskflowDirStatusSetAPIView(BaseTaskflowAPIView):
    """View for creating or updating a role assignment based on params"""

    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__sodar_uuid=request.data['project_uuid'], active=True
            )

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        investigation.irods_status = request.data['dir_status']
        investigation.save()

        return Response('ok', status=200)


class TaskflowSheetDeleteAPIView(BaseTaskflowAPIView):
    """View for deleting the sample sheets of a project"""

    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__sodar_uuid=request.data['project_uuid'], active=True
            )

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        project = investigation.project
        investigation.delete()

        # Delete cache
        cache_backend = get_backend_api('sodar_cache')

        if cache_backend:
            cache_backend.delete_cache(APP_NAME, project)

        return Response('ok', status=200)
