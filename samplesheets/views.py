from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, UpdateView,\
    CreateView, DeleteView, View, FormView
from django.views.generic.edit import ModelFormMixin, DeletionMixin
from django.views.generic.detail import SingleObjectMixin


# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.project_settings import get_project_setting
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin, HTTPRefererMixin

from .forms import SampleSheetImportForm
from .models import Investigation


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

        except Investigation.DoesNotExist:
            context['investigation'] = None

        return context


class SampleSheetImportView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        FormView):
    """Sample sheet JSON import view"""

    permission_required = 'samplesheets.edit_sheet'
    model = Investigation
    form_class = SampleSheetImportForm
    template_name = 'samplesheets/samplesheet_import_form.html'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

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


class SampleSheetDeleteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        TemplateView):
    """SampleSheet deletion view"""
    permission_required = 'samplesheets.delete_sheet'
    template_name = 'samplesheets/samplesheet_confirm_delete.html'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        return Project.objects.get(pk=self.kwargs['project'])

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
