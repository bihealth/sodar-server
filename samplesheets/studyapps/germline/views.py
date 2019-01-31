"""Views for the germline study app"""


from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

from rest_framework.views import APIView
from rest_framework.response import Response

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
    APIPermissionMixin,
)

# Samplesheets dependency
from samplesheets.models import GenericMaterial
from samplesheets.plugins import find_assay_plugin
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_index_by_header
from samplesheets.studyapps.utils import get_igv_xml, FILE_TYPE_SUFFIXES

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic


class GetPedigreeFileMixin:
    def get_pedigree_file_url(cls, file_type, source, study_tables):
        """
        Return DavRods URL for the most recent file of type "bam" or "vcf"
        linked to source
        :param file_type: String ("bam" or "vcf")
        :param source: GenericMaterial of type SOURCE
        :param study_tables: Render study tables
        :return: String
        """
        irods_backend = get_backend_api('omics_irods')
        query_paths = []
        sample_names = []

        for assay in source.study.assays.all():
            assay_table = study_tables['assays'][assay.get_name()]
            assay_plugin = find_assay_plugin(
                assay.measurement_type, assay.technology_type
            )
            source_fam = None

            if 'Family' in source.characteristics:
                source_fam = source.characteristics['Family']['value']

            # Get family index
            fam_idx = get_index_by_header(assay_table, 'family')

            # Get sample index
            sample_idx = get_index_by_header(
                assay_table, 'name', obj_cls=GenericMaterial, item_type='SAMPLE'
            )

            def get_val_by_index(row, idx):
                if not idx:
                    return None
                return row[idx]['value']

            for row in assay_table['table_data']:
                row_name = row[1]['value']
                row_fam = get_val_by_index(row, fam_idx)

                # For VCF files, also search through other samples in family
                vcf_search = False

                if file_type == 'vcf' and source_fam and row_fam == source_fam:
                    vcf_search = True

                # Add sample names for source
                if row_name == source.name or vcf_search:
                    sn = row[sample_idx]['value']

                    if sn not in sample_names:
                        sample_names.append(sn)

                # Get query path from assay_plugin
                if assay_plugin:
                    if row_name == source.name or vcf_search:
                        path = assay_plugin.get_row_path(
                            row, assay_table, assay
                        )
                        if path not in query_paths:
                            query_paths.append(path)

            # If not assay_plugin, just search from assay path
            if not assay_plugin:
                path = irods_backend.get_path(assay)

                if path not in query_paths:
                    query_paths.append(path)

        # Get paths to relevant files
        file_paths = []

        for query_path in query_paths:
            try:
                obj_list = irods_backend.get_objects(query_path)

                for obj in obj_list['data_objects']:
                    # NOTE: We expect the SAMPLE name to appear in filenames
                    if obj['name'].lower().endswith(
                        FILE_TYPE_SUFFIXES[file_type]
                    ) and any(x in obj['name'] for x in sample_names):
                        file_paths.append(obj['path'])

            except FileNotFoundError:
                pass

        if not file_paths:
            return None

        # Get the last file of type by file name
        file_path = sorted(file_paths, key=lambda x: x.split('/')[-1])[-1]
        file_url = '{}{}'.format(settings.IRODS_WEBDAV_URL, file_path)
        return file_url


class BaseGermlineConfigView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Base view from which actual views are extended"""

    def __init__(self, *args, **kwargs):
        super(BaseGermlineConfigView, self).__init__(*args, **kwargs)
        self.redirect_url = None
        self.source = None
        self.study_tables = None

    def get(self, request, *args, **kwargs):
        """Override get() to set up stuff and return with failure if something
        is missing"""
        irods_backend = get_backend_api('omics_irods')

        self.redirect_url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.get_project().sodar_uuid},
        )

        try:
            self.source = GenericMaterial.objects.get(
                sodar_uuid=self.kwargs['genericmaterial']
            )
            self.redirect_url = reverse(
                'samplesheets:project_sheets',
                kwargs={'study': self.source.study.sodar_uuid},
            )

        except GenericMaterial.DoesNotExist:
            messages.error(request, 'Source material not found')
            return redirect(self.redirect_url)

        if not irods_backend:
            messages.error(self.request, 'iRODS Backend not available')
            return redirect(self.redirect_url)

        if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
            messages.error(self.request, 'iRODS WebDAV not available')
            return redirect(self.redirect_url)

        # Build render table
        tb = SampleSheetTableBuilder()
        self.study_tables = tb.build_study_tables(self.source.study)


class FileRedirectView(BaseGermlineConfigView, GetPedigreeFileMixin):
    """BAM/VCF file link view"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return URL to file"""
        super(FileRedirectView, self).get(request, *args, **kwargs)
        file_type = kwargs['file_type']

        if file_type not in FILE_TYPE_SUFFIXES.keys():
            messages.error(
                self.request, 'Unsupported file type "{}"'.format(file_type)
            )
            return redirect(self.redirect_url)

        file_url = self.get_pedigree_file_url(
            file_type=file_type,
            source=self.source,
            study_tables=self.study_tables,
        )

        if not file_url:
            if file_type != 'bam' and 'Family' in self.source.characteristics:
                target_name = self.source.characteristics['Family']['value']

            else:
                target_name = self.source.name

            messages.warning(
                self.request,
                'No {} file found for {}'.format(
                    file_type.upper(), target_name
                ),
            )
            return redirect(self.redirect_url)

        # Return with link to file in DavRods
        return redirect(file_url)


@fallback_to_auth_basic
class IGVSessionFileRenderView(BaseGermlineConfigView, GetPedigreeFileMixin):
    """IGV session file rendering view"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return IGV session file"""
        super(IGVSessionFileRenderView, self).get(request, *args, **kwargs)

        vcf_urls = {}
        bam_urls = {}

        ###################
        # Get resource URLs
        ###################

        # Get URL to latest family vcf file
        vcf_url = self.get_pedigree_file_url(
            file_type='vcf', source=self.source, study_tables=self.study_tables
        )

        # Get URLs to all latest bam files for all sources in family

        # Family defined
        if 'Family' in self.source.characteristics:
            fam_id = self.source.characteristics['Family']['value']

        else:
            fam_id = None

        if fam_id:
            fam_sources = GenericMaterial.objects.filter(
                study=self.source.study,
                item_type='SOURCE',
                characteristics__Family__value=fam_id,
            ).order_by('name')

            for fam_source in fam_sources:
                bam_url = self.get_pedigree_file_url(
                    file_type='bam',
                    source=fam_source,
                    study_tables=self.study_tables,
                )

                if bam_url:
                    bam_urls[fam_source.name] = bam_url

        # If not, just add for the current source
        else:
            bam_url = self.get_pedigree_file_url(
                file_type='bam',
                source=self.source,
                study_tables=self.study_tables,
            )

            if bam_url:
                bam_urls[self.source.name] = bam_url

        ###########
        # Build XML
        ###########

        if vcf_url:
            # Use source name if family ID not known
            if not fam_id:
                fam_id = self.source.name

            vcf_urls[fam_id] = vcf_url

        # Build IGV session XML file
        xml_str = get_igv_xml(
            bam_urls=bam_urls,
            vcf_urls=vcf_urls,
            vcf_title='Pedigree',
            request=request,
        )

        ###########
        # Serve XML
        ###########

        file_name = fam_id + '.pedigree.igv.xml'

        # Set up response
        response = HttpResponse(xml_str, content_type='text/xml')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            file_name
        )
        return response


class FileExistenceCheckView(
    GetPedigreeFileMixin,
    LoginRequiredMixin,
    ProjectPermissionMixin,
    APIPermissionMixin,
    APIView,
):
    """Check existence of BAM/VCF files view"""

    permission_required = 'samplesheets.view_sheet'

    def post(self, request, *args, **kwargs):
        data = {'files': []}
        study = kwargs['study']
        q_dict = request.POST

        valid_objs = [
            str(u)
            for u in GenericMaterial.objects.filter(
                study__sodar_uuid=study, item_type='SOURCE'
            ).values_list('sodar_uuid', flat=True)
        ]

        for file_path in q_dict.getlist('paths'):
            file_type = file_path.split('/')[5]
            obj = file_path.split('/')[6]
            existence = False
            source = GenericMaterial.objects.get(sodar_uuid=obj)

            # Build render table
            tb = SampleSheetTableBuilder()
            study_tables = tb.build_study_tables(source.study)

            if obj in valid_objs:
                if self.get_pedigree_file_url(
                    file_type=file_type,
                    source=source,
                    study_tables=study_tables,
                ):
                    existence = True
            else:
                existence = ''

            data['files'].append({'path': file_path, 'exists': existence})

        return Response(data, status=200)
