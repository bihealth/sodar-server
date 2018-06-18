import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, FormView, View

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin, ProjectPermissionMixin, APIPermissionMixin, \
    HTTPRefererMixin

from .forms import SampleSheetImportForm
from .models import Investigation, Study, Assay, Protocol, Process, \
    GenericMaterial
from .rendering import SampleSheetTableBuilder, EMPTY_VALUE
from .utils import get_sample_dirs, compare_inv_replace


APP_NAME = 'samplesheets'


class InvestigationContextMixin(ProjectContextMixin):
    """Mixin for providing investigation for context if available"""
    def get_context_data(self, *args, **kwargs):
        context = super(InvestigationContextMixin, self).get_context_data(
            *args, **kwargs)

        try:
            investigation = Investigation.objects.get(
                project=context['project'], active=True)
            context['investigation'] = investigation

        except Investigation.DoesNotExist:
            context['investigation'] = None

        return context


class ProjectSheetsView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        InvestigationContextMixin, TemplateView):
    """Main view for displaying sample sheets in a project"""

    # Projectroles dependency
    permission_required = 'samplesheets.view_sheet'
    template_name = 'samplesheets/project_sheets.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectSheetsView, self).get_context_data(
            *args, **kwargs)
        project = context['project']

        if 'investigation' in context and context['investigation']:
            try:
                if 'study' in self.kwargs and self.kwargs['study']:
                    study = Study.objects.get(
                        omics_uuid=self.kwargs['study'])
                else:
                    study = Study.objects.filter(
                        investigation=context['investigation']).first()

                context['study'] = study
                tb = SampleSheetTableBuilder()

                try:
                    context['table_data'] = tb.build_study_tables(study)

                except Exception as ex:
                    # TODO: Log error
                    context['render_error'] = str(ex)

                # iRODS backend
                context['irods_backend'] = get_backend_api('omics_irods')

                # iRODS WebDAV
                if settings.IRODS_WEBDAV_ENABLED:
                    context['irods_webdav_enabled'] = True
                    context['irods_webdav_url'] = \
                        settings.IRODS_WEBDAV_URL.rstrip('/')

                # TODO: TBD: Get from irodsbackend instead?
                context['irods_base_dir'] = \
                    '/omicsZone/projects/{}/{}/{}'.format(
                        str(project.omics_uuid)[:2],
                        project.omics_uuid,
                        settings.IRODS_SAMPLE_DIR)

            except Study.DoesNotExist:
                pass    # TODO: Show error message if study not found?

        context['EMPTY_VALUE'] = EMPTY_VALUE    # For JQuery
        return context


class ProjectSheetsOverviewView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, TemplateView):
    """Main view for displaying information about project sheets"""

    # Projectroles dependency
    permission_required = 'samplesheets.view_sheet'
    template_name = 'samplesheets/overview.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectSheetsOverviewView, self).get_context_data(
            *args, **kwargs)

        # Investigation
        investigation = None

        try:
            investigation = Investigation.objects.get(
                project=context['project'], active=True)
            context['investigation'] = investigation

        except Investigation.DoesNotExist:
            context['investigation'] = None
            return context

        def get_material_count(item_type):
            return GenericMaterial.objects.filter(
                Q(item_type=item_type),
                Q(study__investigation=investigation) |
                Q(assay__study__investigation=investigation)).count()

        # Statistics
        context['sheet_stats'] = {
            'study_count': Study.objects.filter(
                investigation=investigation).count(),
            'assay_count': Assay.objects.filter(
                study__investigation=investigation).count(),
            'protocol_count': Protocol.objects.filter(
                study__investigation=investigation).count(),
            'process_count': Process.objects.filter(
                protocol__study__investigation=investigation).count(),
            'source_count': get_material_count('SOURCE'),
            'material_count': get_material_count('MATERIAL'),
            'sample_count': get_material_count('SAMPLE'),
            'data_count': get_material_count('DATA')}

        return context


class SampleSheetImportView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, FormView):
    """Sample sheet JSON import view"""

    permission_required = 'samplesheets.edit_sheet'
    model = Investigation
    form_class = SampleSheetImportForm
    template_name = 'samplesheets/samplesheet_import_form.html'

    def get_context_data(self, *args, **kwargs):
        context = super(SampleSheetImportView, self).get_context_data(
            *args, **kwargs)
        project = self._get_project(self.request, self.kwargs)

        try:
            old_inv = Investigation.objects.get(project=project, active=True)
            context['replace_sheets'] = True
            context['irods_status'] = old_inv.irods_status

        except Investigation.DoesNotExist:
            pass

        return context

    def get_form_kwargs(self):
        """Pass kwargs to form"""
        kwargs = super(SampleSheetImportView, self).get_form_kwargs()
        project = self._get_project(self.request, self.kwargs)

        if 'project' in self.kwargs:
            kwargs.update({'project': project.omics_uuid})

        # If investigation for project already exists, set replace=True
        try:
            Investigation.objects.get(project=project, active=True)
            kwargs.update({'replace': True})

        except Investigation.DoesNotExist:
            kwargs.update({'replace': False})

        return kwargs

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        project = self._get_project(self.request, self.kwargs)
        form_kwargs = self.get_form_kwargs()
        form_action = 'replace' if form_kwargs['replace'] else 'create'

        old_inv_found = False
        old_inv_uuid = None
        old_study_uuids = {}
        old_assay_uuids = {}

        redirect_url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': project.omics_uuid})

        try:
            self.object = form.save()
            old_inv = None

            # Check for existing investigation
            try:
                old_inv = Investigation.objects.get(
                    project=project, active=True)
                old_inv_found = True
            except Investigation.DoesNotExist:
                pass    # This is fine

            if old_inv:
                # Ensure existing studies and assays are found in new inv
                if old_inv.irods_status:
                    compare_inv_replace(old_inv, self.object)

                # Save UUIDs
                old_inv_uuid = old_inv.omics_uuid

                for study in old_inv.studies.all():
                    old_study_uuids[study.get_name()] = study.omics_uuid

                    for assay in study.assays.all():
                        old_assay_uuids[assay.get_name()] = assay.omics_uuid

                # Set irods_status to our previous sheet's state
                self.object.irods_status = old_inv.irods_status
                self.object.save()

                # Delete old investigation
                old_inv.delete()

        except Exception as ex:
            # Get existing investigations under project
            invs = Investigation.objects.filter(
                project=project).order_by('-pk')
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
                    pk=old_inv.pk).delete()

            if settings.DEBUG:
                raise ex

            messages.error(self.request, str(ex))
            return redirect(redirect_url)   # NOTE: Return here with failure

        # If all went well..

        # Update UUIDs
        if old_inv_found:
            self.object.omics_uuid = old_inv_uuid
            self.object.save()

            for study in self.object.studies.all():
                if study.get_name() in old_study_uuids:
                    study.omics_uuid = old_study_uuids[study.get_name()]
                    study.save()

                for assay in study.assays.all():
                    if assay.get_name() in old_assay_uuids:
                        assay.omics_uuid = old_assay_uuids[assay.get_name()]
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
                status_type='OK')

            tl_event.add_object(
                obj=self.object,
                label='investigation',
                name=self.object.title)

            messages.success(
                self.request,
                form_action.capitalize() +
                'd sample sheets from ISAtab import')

        return redirect(redirect_url)


class SampleSheetTableExportView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, View):
    """Sample sheet table TSV export view"""
    permission_required = 'samplesheets.export_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return TSV file"""

        # Get the input study (we need study to build assay tables too)
        assay = None
        study = None

        if 'assay' in self.kwargs:
            try:
                assay = Assay.objects.get(omics_uuid=self.kwargs['assay'])
                study = assay.study

            except Exception as ex:
                pass

        elif 'study' in self.kwargs:
            try:
                study = Study.objects.get(omics_uuid=self.kwargs['study'])

            except Study.DoesNotExist:
                pass

        redirect_url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self._get_project(
                self.request, self.kwargs).omics_uuid})

        if not study:
            messages.error(
                self.request, 'Study not found, unable to render TSV')
            return redirect(redirect_url)

        # Build study tables
        tb = SampleSheetTableBuilder()

        try:
            tables = tb.build_study_tables(study)

        except Exception as ex:
            messages.error(
                self.request,
                'Unable to render table for export: {}'.format(ex))
            return redirect(redirect_url)

        if 'assay' in self.kwargs:
            table = tables['assays'][assay.get_name()]
            input_name = assay.file_name

        else:   # Study
            table = tables['study']
            input_name = study.file_name

        # Set up response
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = \
            'attachment; filename="{}.tsv"'.format(
                input_name.split('.')[0])  # TODO: TBD: Output file name?

        # Build TSV
        writer = csv.writer(response, delimiter='\t')

        # Top header
        output_row = []

        for c in table['top_header'][1:]:
            output_row.append(c['value'])

            if c['colspan'] > 1:
                output_row += [''] * (c['colspan'] - 1)

        writer.writerow(output_row)

        # Header
        writer.writerow([c['value'] for c in table['field_header'][1:]])

        # Data cells
        for row in table['table_data']:
            writer.writerow([c['value'] for c in row[1:]])

        # Return file
        return response


class SampleSheetDeleteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionMixin, TemplateView):
    """Sample sheet deletion view"""
    permission_required = 'samplesheets.delete_sheet'
    template_name = 'samplesheets/samplesheet_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        tl_event = None
        project = Project.objects.get(omics_uuid=kwargs['project'])
        investigation = Investigation.objects.get(project=project, active=True)

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_delete',
                description='delete investigation {investigation}',
                status_type='OK')

            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title)

        if taskflow and investigation.irods_status:
            if tl_event:
                tl_event.set_status('SUBMIT')

            try:
                taskflow.submit(
                    project_uuid=project.omics_uuid,
                    flow_name='sheet_delete',
                    flow_data={},
                    request=self.request)

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

        else:
            investigation.delete()

        messages.success(
            self.request, 'Sample sheets deleted.')

        return HttpResponseRedirect(reverse(
            'samplesheets:project_sheets',
            kwargs={'project': project.omics_uuid}))


class IrodsDirsView(
        LoginRequiredMixin, LoggedInPermissionMixin, InvestigationContextMixin,
        ProjectPermissionMixin, TemplateView):
    """iRODS directory structure creation confirm view"""
    template_name = 'samplesheets/irods_dirs_confirm.html'
    # NOTE: minimum perm, all checked files will be tested in post()
    permission_required = 'samplesheets.create_dirs'

    def get_context_data(self, *args, **kwargs):
        context = super(IrodsDirsView, self).get_context_data(
            *args, **kwargs)

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
                                     '{investigation}')

            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title)

        # Fail if tasflow is not available
        if not taskflow:
            if timeline:
                tl_event.set_status(
                    'FAILED', status_desc='Taskflow not enabled')

            messages.error(
                self.request,
                'Unable to {} dirs: taskflow not enabled!'.format(action))

            return redirect(reverse(
                'samplesheets:project_sheets',
                kwargs={'project': project.omics_uuid}))

        # Else go on with the creation
        if tl_event:
            tl_event.set_status('SUBMIT')

        flow_data = {
            'dirs': context['dirs']}

        try:
            taskflow.submit(
                project_uuid=project.omics_uuid,
                flow_name='sheet_dirs_create',
                flow_data=flow_data,
                request=self.request)
            messages.success(
                self.request,
                'Directory structure for sample data {}d in iRODS'.format(
                    action))

            if tl_event:
                tl_event.set_status('OK')

        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            messages.error(self.request, str(ex))

        return HttpResponseRedirect(reverse(
            'samplesheets:project_sheets',
            kwargs={'project': project.omics_uuid}))

    def get(self, request, *args, **kwargs):
        super(IrodsDirsView, self).get(request, *args, **kwargs)
        return super(IrodsDirsView, self).render_to_response(
            self.get_context_data())


# Javascript API Views ---------------------------------------------------


class IrodsObjectListAPIView(
        LoginRequiredMixin, ProjectContextMixin, ProjectPermissionMixin,
        APIPermissionMixin, APIView):
    """View for listing relevant sample dataobjects in iRODS via Ajax"""
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, **kwargs):
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return Response('Backend not enabled', status=500)

        try:
            assay = Assay.objects.get(omics_uuid=kwargs['assay'])

        except Assay.DoesNotExist:
            return Response('Assay not found', status=500)

        # Ensure path corresponds to assay
        assay_path = irods_backend.get_path(assay)

        if assay_path not in kwargs['path']:
            return Response('Invalid path', status=400)

        try:
            ret_data = irods_backend.get_objects(kwargs['path'])

        except FileNotFoundError:
            return Response('Collection not found', status=404)

        except Exception as ex:
            return Response(str(ex), status=500)

        return Response(ret_data, status=200)


# Taskflow API Views -----------------------------------------------------


# TODO: Limit access to localhost


# TODO: Use GET instead of POST
class SampleSheetDirStatusGetAPIView(APIView):
    """View for getting the sample sheet iRODS dir status"""
    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__omics_uuid=request.data['project_uuid'], active=True)

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        return Response({'dir_status': investigation.irods_status}, 200)


class SampleSheetDirStatusSetAPIView(APIView):
    """View for creating or updating a role assignment based on params"""
    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__omics_uuid=request.data['project_uuid'], active=True)

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        investigation.irods_status = request.data['dir_status']
        investigation.save()

        return Response('ok', status=200)


class SampleSheetDeleteAPIView(APIView):
    """View for deleting the sample sheets of a project"""
    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__omics_uuid=request.data['project_uuid'], active=True)

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        investigation.delete()
        return Response('ok', status=200)
