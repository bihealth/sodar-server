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
from samplesheets.models import Study, GenericMaterial
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.studyapps.utils import get_igv_xml, FILE_TYPE_SUFFIXES

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic

from ..utils import get_pedigree_file_url


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


class FileRedirectView(BaseGermlineConfigView):
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

        file_url = get_pedigree_file_url(
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
class IGVSessionFileRenderView(BaseGermlineConfigView):
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
        vcf_url = get_pedigree_file_url(
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
                bam_url = get_pedigree_file_url(
                    file_type='bam',
                    source=fam_source,
                    study_tables=self.study_tables,
                )

                if bam_url:
                    bam_urls[fam_source.name] = bam_url

        # If not, just add for the current source
        else:
            bam_url = get_pedigree_file_url(
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
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """Check existence of BAM/VCF files view"""

    permission_required = 'samplesheets.view_sheet'

    def post(self, request, *args, **kwargs):
        data = {'files': []}
        study = Study.objects.filter(sodar_uuid=kwargs['study']).first()
        q_dict = request.POST

        # Build render table
        tb = SampleSheetTableBuilder()
        study_tables = tb.build_study_tables(study)

        valid_objs = [
            str(u)
            for u in GenericMaterial.objects.filter(
                study=study, item_type='SOURCE'
            ).values_list('sodar_uuid', flat=True)
        ]

        for file_path in q_dict.getlist('paths'):
            file_type = file_path.split('/')[5]
            obj = file_path.split('/')[6]
            existence = False
            source = GenericMaterial.objects.filter(sodar_uuid=obj).first()

            if obj in valid_objs and source:
                if get_pedigree_file_url(
                    file_type=file_type,
                    source=source,
                    study_tables=study_tables,
                ):
                    existence = True
            else:
                existence = ''

            data['files'].append({'path': file_path, 'exists': existence})

        return Response(data, status=200)
