import multiprocessing
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, FormView


# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin, ProjectPermissionObjectMixin

from .forms import SampleSheetImportForm
from .models import Investigation, Study, Assay, Protocol, Process, \
    GenericMaterial


APP_NAME = 'samplesheets'


class ProjectSheetsView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionObjectMixin, TemplateView):
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

        # Info page
        if 'subpage' in self.kwargs and self.kwargs['subpage'] == 'info':
            context['subpage'] = 'info'

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

        # Study view
        else:
            try:
                if 'study' in self.kwargs and self.kwargs['study']:
                    context['study'] = Study.objects.get(
                        pk=self.kwargs['study'])
                else:
                    context['study'] = Study.objects.filter(
                        investigation=investigation).first()

            except Study.DoesNotExist:
                return None

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

        # TODO: Add to timeline
        # TODO: Add proper reporting and cleanup in case of import failures
        # TODO: Update import status via JQuery

        '''
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
            '''


        '''
        except Exception as ex:
            if settings.DEBUG:
                raise ex
            messages.error(self.request, str(ex))
        '''

        p = multiprocessing.Process(
            target=form.save)
        p.start()

        messages.warning(
            self.request,
            'Sample sheet import from an ISA investigation initiated. '
            'See information/progress on this page.')

        time.sleep(3)    # I can't believe I'm doing this again..

        return redirect(
            reverse('project_sheets', kwargs={
                'project': project.pk}))


class SampleSheetDeleteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionObjectMixin, TemplateView):
    """Sample sheet deletion view"""
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
