from datetime import datetime as dt, timedelta

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
from projectroles.utils import build_secret

# Samplesheets dependency
from samplesheets.io import get_assay_dirs
from samplesheets.models import Assay
from samplesheets.views import InvestigationContextMixin

# Landingzones dependency
from landingzones.models import LandingZone
from landingzones.views import LandingZoneContextMixin


# Local constants
TICKET_DATE_FORMAT = '%Y-%m-%d.%H:%M:%S'


class ZoneTicketGetView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionMixin, LandingZoneContextMixin, TemplateView):
    """Zone iRODS ticket retrieval view"""
    http_method_names = ['get', 'post']
    template_name = 'landingzones_config_bih_proteomics_smb/ticket_get.html'
    permission_required = 'landingzones.update_zones_own'

    def get_context_data(self, *args, **kwargs):
        """Override get_context_data() for ticket information"""
        context = super(ZoneTicketGetView, self).get_context_data()

        if context['zone']:
            zone = context['zone']

            if 'ticket' in zone.config_data:
                context['ticket'] = zone.config_data['ticket']
                expire_date = dt.strptime(
                    zone.config_data['ticket_expire_date'], TICKET_DATE_FORMAT)
                context['ticket_expire_date'] = expire_date

                if expire_date < dt.now():
                    context['ticket_expired'] = True

        return context

    def post(self, *args, **kwargs):
        """POST function for generating/refreshing a ticket"""
        irods_backend = get_backend_api('omics_irods')
        zone = LandingZone.objects.get(
            omics_uuid=self.kwargs['landingzone'])
        redirect_url = reverse(
            'landingzones:list', kwargs={'project': zone.project.omics_uuid})
        error = False
        ex_msg = None

        # Delete existing ticket
        if 'ticket' in zone.config_data and zone.config_data['ticket']:
            try:
                irods_backend.delete_ticket(zone.config_data['ticket'])

            except Exception as ex:
                error = True
                ex_msg = str(ex)

        if not error:
            expiry_date = dt.now() + timedelta(days=14)

            try:
                ticket = irods_backend.issue_ticket(
                    mode='write',
                    path=irods_backend.get_path(zone),
                    ticket_str=build_secret(16),
                    expiry_date=expiry_date)
                zone.config_data['ticket'] = ticket._ticket
                zone.config_data['ticket_expire_date'] = expiry_date.strftime(
                    TICKET_DATE_FORMAT)
                zone.save()

                messages.success(
                    self.request,
                    'Ticket "{}" created for zone "{}", expires on {}'.format(
                        zone.config_data['ticket'],
                        zone.title,
                        expiry_date.strftime('%Y-%m-%d %H:%M')))

            except Exception as ex:
                error = True
                ex_msg = str(ex)

        if error:
            messages.error(
                self.request, 'Error modifying ticket: {}'.format(ex_msg))

        return redirect(redirect_url)
