from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, CreateView

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import Project
from projectroles.views import LoggedInPermissionMixin, \
    ProjectPermissionMixin, ProjectContextMixin
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.io import get_assay_dirs
from samplesheets.models import Assay
from samplesheets.views import InvestigationContextMixin

from landingzones.views import LandingZoneContextMixin


class ZoneTicketGetView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionMixin, LandingZoneContextMixin, TemplateView):
    """Zone iRODS ticket retrieval view"""
    http_method_names = ['get', 'post']
    template_name = 'landingzones_config_bih_proteomics_smb/ticket_get.html'
    permission_required = 'landingzones.update_zones_own'
