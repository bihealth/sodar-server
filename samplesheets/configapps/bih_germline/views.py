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

# Local constants
FILE_TYPE_SUFFIX = {
    'bam': '.bam',
    'vcf': '.vcf.gz'}


class FileRedirectView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, View):
    """BAM/VCF file link view"""
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return TSV file"""
        config_plugin = get_config_plugin('samplesheets_config_bih_germline')
        irods_backend = get_backend_api('omics_irods')
        study = None
        file_type = kwargs['file_type']
        family_id = kwargs['family_id']

        redirect_url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self._get_project(
                self.request, self.kwargs).omics_uuid})

        if not irods_backend:
            messages.error(self.request, 'iRODS Backend not available')
            return redirect(redirect_url)

        if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
            messages.error(self.request, 'iRODS WebDAV not available')
            return redirect(redirect_url)

        if 'genericmaterial' not in self.kwargs:
            messages.error(self.request, 'No Source material given for linking')
            return redirect(redirect_url)

        if file_type not in FILE_TYPE_SUFFIX.keys():
            messages.error(
                self.request, 'Unsupported file type "{}"'.format(file_type))
            return redirect(redirect_url)

        try:
            source = GenericMaterial.objects.get(
                item_type='SOURCE',
                omics_uuid=self.kwargs['genericmaterial'])

        except GenericMaterial.DoesNotExist:
            messages.error(
                self.request,
                'Source not found, unable to redirect to file')
            return redirect(redirect_url)

        # Build render table
        tb = SampleSheetTableBuilder()
        study_tables = tb.build_study_tables(source.study)
        query_paths = []

        # Get material names for linking
        for assay in source.study.assays.all():
            assay_table = study_tables['assays'][assay.get_name()]

            # Get family index
            try:
                fam_idx = assay_table['field_header'].index('Family')

            except ValueError:
                fam_idx = None

            for row in assay_table['table_data']:
                # TODO: Refactor after vacation because well, just look at this
                if ((file_type == 'bam' and row[1]['value'] == source.name) or (
                        file_type == 'vcf' and ((
                            fam_idx and row[fam_idx]['value'] ==
                            source.characteristics['Family']['value']) or
                        row[1]['value'] == source.name))):
                    path = config_plugin.get_row_path(assay, assay_table, row)
                    query_paths.append(path)

        file_paths = []

        for query_path in query_paths:
            try:
                obj_list = irods_backend.get_objects(query_path)

                for obj in obj_list['data_objects']:
                    if obj['name'].lower().find(
                            FILE_TYPE_SUFFIX[file_type]) != -1:
                        file_paths.append(obj['path'])

            except FileNotFoundError:
                pass

        if not file_paths:
            messages.warning(
                self.request, 'No {} file found for {}'.format(
                    file_type.upper(), source.name))
            return redirect(redirect_url)

        # Get the last file of type by file name
        file_path = sorted(file_paths, key=lambda x: x.split('/')[-1])[-1]
        file_url = '{}{}'.format(
            settings.IRODS_WEBDAV_URL, file_path)

        # Return with link to file in DavRods
        return redirect(file_url)

