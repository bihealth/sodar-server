import json
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, FormView, View

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.versioning import AcceptHeaderVersioning
from knox.auth import TokenAuthentication

# Projectroles dependency
from projectroles.models import Project, RemoteSite, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
    APIPermissionMixin,
    BaseTaskflowAPIView,
)

from .forms import SampleSheetImportForm
from .models import (
    Investigation,
    Study,
    Assay,
    Protocol,
    Process,
    GenericMaterial,
)
from .rendering import SampleSheetTableBuilder, EMPTY_VALUE
from .tasks import update_project_cache_task
from .utils import (
    get_sample_dirs,
    compare_inv_replace,
    get_sheets_url,
    write_csv_table,
)


# SODAR constants
SITE_MODE_TARGET = SODAR_CONSTANTS['SITE_MODE_TARGET']
REMOTE_LEVEL_READ_ROLES = SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES']


# Local constants
APP_NAME = 'samplesheets'


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


class ProjectSheetsView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    TemplateView,
):
    """Main view for displaying sample sheets in a project"""

    # Projectroles dependency
    permission_required = 'samplesheets.view_sheet'
    template_name = 'samplesheets/project_sheets.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        studies = Study.objects.filter(
            investigation=context['investigation']
        ).order_by('title')

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
    FormView,
):
    """Sample sheet JSON import view"""

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
        timeline = get_backend_api('timeline_backend')
        project = self.get_project()
        form_kwargs = self.get_form_kwargs()
        form_action = 'replace' if form_kwargs['replace'] else 'create'

        old_inv_found = False
        old_inv_uuid = None
        old_study_uuids = {}
        old_assay_uuids = {}
        redirect_url = get_sheets_url(project)

        try:
            self.object = form.save()
            old_inv = None

            # Check for existing investigation
            try:
                old_inv = Investigation.objects.get(
                    project=project, active=True
                )
                old_inv_found = True
            except Investigation.DoesNotExist:
                pass  # This is fine

            if old_inv:
                # Ensure existing studies and assays are found in new inv
                if old_inv.irods_status:
                    compare_inv_replace(old_inv, self.object)

                # Save UUIDs
                old_inv_uuid = old_inv.sodar_uuid

                for study in old_inv.studies.all():
                    old_study_uuids[study.identifier] = study.sodar_uuid

                    for assay in study.assays.all():
                        old_assay_uuids[assay.get_name()] = assay.sodar_uuid

                # Set irods_status to our previous sheet's state
                self.object.irods_status = old_inv.irods_status
                self.object.save()

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

            if settings.DEBUG:
                raise ex

            messages.error(self.request, str(ex))
            return redirect(redirect_url)  # NOTE: Return here with failure

        # If all went well..

        # Update UUIDs
        if old_inv_found:
            self.object.sodar_uuid = old_inv_uuid
            self.object.save()

            for study in self.object.studies.all():
                if study.identifier in old_study_uuids:
                    study.sodar_uuid = old_study_uuids[study.identifier]
                    study.save()

                for assay in study.assays.all():
                    if assay.get_name() in old_assay_uuids:
                        assay.sodar_uuid = old_assay_uuids[assay.get_name()]
                        assay.save()

        # Set current import active status to True
        self.object.active = True
        self.object.save()

        # Add event in Timeline
        if timeline:
            if form_action == 'replace':
                desc = 'replace previous investigation with '

            else:
                desc = 'create investigation '

            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_' + form_action,
                description=desc + ' {investigation}',
                status_type='OK',
            )

            tl_event.add_object(
                obj=self.object, label='investigation', name=self.object.title
            )

        success_msg = '{}d sample sheets from ISAtab import'.format(
            form_action.capitalize()
        )

        # Update project cache if replacing sheets
        if form_action == 'replace' and settings.SHEETS_ENABLE_CACHE:
            update_project_cache_task.delay(
                project_uuid=str(project.sodar_uuid),
                user_uuid=str(self.request.user.sodar_uuid),
            )
            success_msg += ', initiated iRODS cache update'

        messages.success(self.request, success_msg)
        return redirect(redirect_url)


class SampleSheetTableExportView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Sample sheet table TSV export view"""

    permission_required = 'samplesheets.export_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return TSV file"""

        # Get the input study (we need study to build assay tables too)
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
                self.request, 'Study not found, unable to render TSV'
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

        if 'assay' in self.kwargs:
            table = tables['assays'][str(assay.sodar_uuid)]
            input_name = assay.file_name

        else:  # Study
            table = tables['study']
            input_name = study.file_name

        # Set up response
        response = HttpResponse(content_type='text/tab-separated-values')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="{}.tsv"'.format(
            input_name.split('.')[0]
        )  # TODO: TBD: Output file name?

        # Build TSV
        write_csv_table(table, response)

        # Return file
        return response


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

        else:
            investigation.delete()

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
    """iRODS directory structure creation confirm view"""

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
            messages.success(
                self.request,
                'Directory structure for sample data {}d in iRODS'.format(
                    action
                ),
            )

            if tl_event:
                tl_event.set_status('OK')

        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            messages.error(self.request, str(ex))

        return HttpResponseRedirect(get_sheets_url(project))

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        return super().render_to_response(self.get_context_data())


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
            'title'
        )
        irods_backend = get_backend_api('omics_irods')

        # Can't import at module root due to circular dependency
        from .plugins import find_study_plugin, find_assay_plugin

        # General context data for Vue app
        ret_data = {
            'configuration': investigation.get_configuration()
            if investigation
            else None,
            'irods_status': investigation.irods_status
            if investigation
            else None,
            'irods_backend_enabled': (
                True if get_backend_api('omics_irods') else False
            ),
            'irods_webdav_enabled': settings.IRODS_WEBDAV_ENABLED,
            'irods_webdav_url': settings.IRODS_WEBDAV_URL.rstrip('/'),
            'external_link_labels': settings.SHEETS_EXTERNAL_LINK_LABELS,
            'table_height': settings.SHEETS_TABLE_HEIGHT,
            'min_col_width': settings.SHEETS_MIN_COLUMN_WIDTH,
            'max_col_width': settings.SHEETS_MAX_COLUMN_WIDTH,
        }

        # Study info
        ret_data['studies'] = {}

        for s in studies:
            study_plugin = find_study_plugin(investigation.get_configuration())
            ret_data['studies'][str(s.sodar_uuid)] = {
                'display_name': s.get_display_name(),
                'description': s.description,
                'comments': s.comments,
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
            for a in s.assays.all().order_by('file_name'):
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
                'comments': investigation.comments,
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

    def get(self, request, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')
        cache_backend = get_backend_api('sodar_cache')

        study = Study.objects.filter(sodar_uuid=self.kwargs['study']).first()

        ret_data = {'study': {'display_name': study.get_display_name()}}
        tb = SampleSheetTableBuilder()

        try:
            ret_data['table_data'] = tb.build_study_tables(study)

        except Exception as ex:
            # TODO: Log error
            ret_data['render_error'] = str(ex)
            return Response(ret_data, status=200)

        if study.investigation.irods_status and irods_backend:
            # Can't import at module root due to circular dependency
            from .plugins import find_study_plugin
            from .plugins import find_assay_plugin

            # Get study plugin for shortcut data
            study_plugin = find_study_plugin(
                study.investigation.get_configuration()
            )

            if study_plugin:
                shortcuts = study_plugin.get_shortcut_column(
                    study, ret_data['table_data']
                )
                ret_data['table_data']['study']['shortcuts'] = shortcuts

            # Get assay content if corresponding assay plugin exists
            for a_uuid, a_data in ret_data['table_data']['assays'].items():
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
    """Temporary API view for retrieving sample sheet tables as JSON by a target
    site"""

    permission_classes = (AllowAny,)  # We check the secret in get()/post()

    def get(self, request, *args, **kwargs):
        secret = kwargs['secret']

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
        ret = {'studies': {}}
        tb = SampleSheetTableBuilder()

        # Build study tables
        for study in investigation.studies.all():
            try:
                tables = tb.build_study_tables(study)

            except Exception:
                continue  # TODO: TBD: How to inform the requester of a failure?

            ret['studies'][str(study.sodar_uuid)] = tables

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
