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

# Samplesheets dependency
from samplesheets.models import Investigation, Study, Assay, Protocol, Process, \
    GenericMaterial
from samplesheets.plugins import get_config_plugin
from samplesheets.rendering import SampleSheetTableBuilder


class BamFileRedirectView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, View):
    """Source material BAM file link view"""
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return TSV file"""
        config_plugin = get_config_plugin('samplesheets_config_bih_germline')
        irods_backend = get_backend_api('omics_irods')
        study = None

        redirect_url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self._get_project(
                self.request, self.kwargs).omics_uuid})

        if not irods_backend:
            messages.error(self.request, 'iRODS Backend not available')
            return redirect(redirect_url)

        if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
            messages.error(self.request, 'iRODS WebDAV not available')

        if 'genericmaterial' not in self.kwargs:
            messages.error(self.request, 'No Source material given for linking')
            return redirect(redirect_url)

        try:
            source = GenericMaterial.objects.get(
                item_type='SOURCE',
                omics_uuid=self.kwargs['genericmaterial'])

        except GenericMaterial.DoesNotExist:
            messages.error(
                self.request,
                'Source not found, unable to redirect to BAM file')
            return redirect(redirect_url)

        # Build render table
        tb = SampleSheetTableBuilder()
        study_tables = tb.build_study_tables(source.study)
        query_paths = []

        # Get material names for linking
        for assay in source.study.assays.all():
            assay_table = study_tables['assays'][assay.get_name()]

            for row in assay_table['table_data']:
                if row[1]['value'] == source.name:
                    path = config_plugin.get_row_path(assay, assay_table, row)
                    query_paths.append(path)

        bam_paths = []

        for query_path in query_paths:
            try:
                obj_list = irods_backend.get_objects(query_path)

                for obj in obj_list['data_objects']:
                    if obj['name'].lower().find('.bam') != -1:
                        bam_paths.append(obj['path'])

            except FileNotFoundError:
                pass

        if not bam_paths:
            messages.warning(
                self.request, 'No BAM file found for {}'.format(source.name))
            return redirect(redirect_url)

        # Get the last bam file by file name
        bam_path = sorted(bam_paths, key=lambda x: x.split('/')[-1])[-1]
        bam_url = '{}{}'.format(
            settings.IRODS_WEBDAV_URL, bam_path)

        # Return with link to file in DavRods
        return redirect(bam_url)
