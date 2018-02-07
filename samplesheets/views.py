from isatools import isajson
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, FormView, View


# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin, ProjectPermissionObjectMixin

from .forms import SampleSheetImportForm
from .models import Investigation, Study, Assay, Protocol, Process, \
    GenericMaterial
from .utils import export_isa_json


APP_NAME = 'samplesheets'


class ProjectSheetsView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        TemplateView):
    """Main view for displaying sample sheets in a project"""

    # Projectroles dependency
    permission_required = 'samplesheets.view_sheet'
    template_name = 'samplesheets/project_sheets.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectSheetsView, self).get_context_data(
            *args, **kwargs)

        try:
            context['investigation'] = Investigation.objects.get(
                project=context['project'])

            # Statistics
            context['sheet_stats'] = {
                'study_count': Study.objects.all().count(),
                'assay_count': Assay.objects.all().count(),
                'protocol_count': Protocol.objects.all().count(),
                'process_count': Process.objects.all().count(),
                'source_count': GenericMaterial.objects.filter(
                    item_type='SOURCE').count(),
                'material_count': GenericMaterial.objects.filter(
                    item_type='MATERIAL').count(),
                'sample_count': GenericMaterial.objects.filter(
                    item_type='SAMPLE').count(),
                'data_count': GenericMaterial.objects.filter(
                    item_type='DATA').count()}

        except Investigation.DoesNotExist:
            context['investigation'] = None

        return context


class SampleSheetImportView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionObjectMixin, FormView):
    """Sample sheet JSON import view"""

    permission_required = 'samplesheets.edit_sheet'
    model = Investigation
    form_class = SampleSheetImportForm
    template_name = 'samplesheets/samplesheet_import_form.html'

    def get_form_kwargs(self):
        """Pass URL kwargs to form"""
        kwargs = super(SampleSheetImportView, self).get_form_kwargs()

        if 'project' in self.kwargs:
            kwargs.update({'project': self.kwargs['project']})

        return kwargs

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        project = Project.objects.get(pk=self.kwargs['project'])
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

        messages.success(
            self.request, 'Sample sheets imported from an ISA investigation.')

        return redirect(
            reverse('project_sheets', kwargs={
                'project': self.get_permission_object().pk}))


class SampleSheetExportJSONView(
        LoginRequiredMixin, LoggedInPermissionMixin,
        ProjectPermissionObjectMixin, View):
    """View for exporting the sample sheet as an ISA compatible JSON file"""

    permission_required = 'samplesheets.export_sheet'

    def get(self, *args, **kwargs):
        """GET request to return the JSON as attachment"""
        timeline = get_backend_api('timeline_backend')
        project = Project.objects.get(pk=self.kwargs['project'])
        investigation = Investigation.objects.get(project=project)

        # Export Investigation as dict
        json_data = export_isa_json(investigation)
        json_str = json.dumps(json_data, indent=4)

        # TODO: Validate JSON data
        # json_report = isajson.validate(...)

        if not json_str or not json_data:
            messages.error(self.request, 'JSON data not available!')

            return redirect(reverse(
                'project_sheets', kwargs={'project': kwargs['project']}))

        # Return file as attachment
        file_name = investigation.file_name
        response = HttpResponse(json_str, content_type='application/json')
        response['Content-Disposition'] = \
            'attachment; filename={}'.format(file_name)

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=investigation.project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='sheet_export',
                description='export sample sheets from {investigation}',
                status_type='INFO',
                classified=True)

            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title)

        return response


class SampleSheetDeleteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionObjectMixin, TemplateView):
    """SampleSheet deletion view"""
    permission_required = 'samplesheets.delete_sheet'
    template_name = 'samplesheets/samplesheet_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        project = Project.objects.get(pk=self.kwargs['project'])
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

        return HttpResponseRedirect(reverse('project_sheets', kwargs={
            'project': project.pk}))
