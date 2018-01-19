from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, UpdateView,\
    CreateView, DeleteView, View
from django.views.generic.edit import ModelFormMixin, DeletionMixin
from django.views.generic.detail import SingleObjectMixin


# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.project_settings import get_project_setting
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin, HTTPRefererMixin


class ProjectSheetsView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        TemplateView):
    """Main view for displaying sample sheets in a project"""

    # Projectroles dependency
    permission_required = 'samplesheets.view_sheet'
    template_name = 'samplesheets/project_sheets.html'
    # model = Project
