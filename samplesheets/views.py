import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, FormView, View

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin, ProjectPermissionMixin

from .forms import SampleSheetImportForm
from .models import Investigation, Study, Assay, Protocol, Process, \
    GenericMaterial
from .rendering import SampleSheetTableBuilder


APP_NAME = 'samplesheets'


class ProjectSheetsView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, TemplateView):
    """Main view for displaying sample sheets in a project"""

    # Projectroles dependency
    permission_required = 'samplesheets.view_sheet'
    template_name = 'samplesheets/project_sheets.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectSheetsView, self).get_context_data(
            *args, **kwargs)

        # Investigation
        investigation = None

        try:
            investigation = Investigation.objects.get(
                project=context['project'])
            context['investigation'] = investigation

        except Investigation.DoesNotExist:
            context['investigation'] = None
            return context

        try:
            if 'study' in self.kwargs and self.kwargs['study']:
                study = Study.objects.get(
                    omics_uuid=self.kwargs['study'])
            else:
                study = Study.objects.filter(
                    investigation=investigation).first()

            context['study'] = study
            tb = SampleSheetTableBuilder()
            context['table_data'] = tb.build_study(study)

        except Study.DoesNotExist:
            return None

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
                project=context['project'])
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

    def get_form_kwargs(self):
        """Pass URL kwargs to form"""
        kwargs = super(SampleSheetImportView, self).get_form_kwargs()

        if 'project' in self.kwargs:
            kwargs.update({'project': self._get_project(
                self.kwargs, self.request).omics_uuid})

        return kwargs

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        project = self._get_project(self.kwargs, self.request)

        try:
            self.object = form.save()

            # Add event in Timeline
            if timeline:
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='sheet_create',
                    description='create investigation {investigation}',
                    status_type='OK')

                tl_event.add_object(
                    obj=self.object,
                    label='investigation',
                    name=self.object.title)

        except Exception as ex:
            try:    # Remove broken investigation if import fails
                Investigation.objects.get(project=project).delete()

            except Investigation.DoesNotExist:
                pass

            if settings.DEBUG:
                raise ex

            messages.error(self.request, str(ex))

        return redirect(reverse(
            'samplesheets:project_sheets',
            kwargs={'project': project.omics_uuid}))


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

        if not study:
            messages.error(
                self.request, 'Study not found, unable to render TSV')
            return redirect(reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self._get_project(
                    self.request, self.kwargs).omics_uuid}))

        # Build study tables
        tb = SampleSheetTableBuilder()
        tables = tb.build_study(study)

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

        for c in table['top_header']:
            output_row.append(c['value'])

            if c['colspan'] > 1:
                output_row += [''] * (c['colspan'] - 1)

        writer.writerow(output_row)

        # Header
        writer.writerow([c['value'] for c in table['field_header']])

        # Data cells
        for row in table['table_data']:
            writer.writerow([c['value'] for c in row])

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
        project = Project.objects.get(omics_uuid=kwargs['project'])
        investigation = Investigation.objects.get(project=project)

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

        investigation.delete()

        messages.success(
            self.request, 'Sample sheets deleted.')

        return HttpResponseRedirect(reverse(
            'samplesheets:project_sheets',
            kwargs={'project': project.omics_uuid}))
