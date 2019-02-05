"""Views for the cancer study app"""


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
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_sample_libraries
from samplesheets.studyapps.utils import get_igv_xml, FILE_TYPE_SUFFIXES

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic


class GetLibraryFileMixin:
    """Mixin for getting the URL of the most recent bam or vcf file"""

    def get_library_file_url(cls, file_type, library):
        """
        Return DavRods URL for the most recent file of type "bam" or "vcf"
        linked to library
        :param file_type: String ("bam" or "vcf")
        :param library: GenericMaterial object
        :return: String
        """
        irods_backend = get_backend_api('omics_irods')

        assay_path = irods_backend.get_path(library.assay)
        query_path = assay_path + '/' + library.name

        # Get paths to relevant files
        file_paths = []

        try:
            obj_list = irods_backend.get_objects(query_path)

            for obj in obj_list['data_objects']:
                if obj['name'].lower().endswith(FILE_TYPE_SUFFIXES[file_type]):
                    file_paths.append(obj['path'])

        except FileNotFoundError:
            pass

        if not file_paths:
            return None

        # Get the last file of type by file name
        file_path = sorted(file_paths, key=lambda x: x.split('/')[-1])[-1]
        file_url = '{}{}'.format(settings.IRODS_WEBDAV_URL, file_path)
        return file_url


class BaseCancerConfigView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Base view from which actual views are extended"""

    def __init__(self, *args, **kwargs):
        super(BaseCancerConfigView, self).__init__(*args, **kwargs)
        self.redirect_url = None
        self.material = None
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
            self.material = GenericMaterial.objects.get(
                sodar_uuid=self.kwargs['genericmaterial']
            )
            self.redirect_url = reverse(
                'samplesheets:project_sheets',
                kwargs={'study': self.material.study.sodar_uuid},
            )

        except GenericMaterial.DoesNotExist:
            messages.error(request, 'Material not found')
            return redirect(self.redirect_url)

        if not irods_backend:
            messages.error(self.request, 'iRODS Backend not available')
            return redirect(self.redirect_url)

        if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
            messages.error(self.request, 'iRODS WebDAV not available')
            return redirect(self.redirect_url)


class FileRedirectView(BaseCancerConfigView, GetLibraryFileMixin):
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

        if not self.material.assay:
            messages.error(
                self.request,
                'Assay not found for library, make sure your sample sheets '
                'are correctly formed',
            )
            return redirect(self.redirect_url)

        try:
            file_url = self.get_library_file_url(
                file_type=file_type, library=self.material
            )

        except TypeError:
            messages.error(
                self.request,
                'Library file URL retrieval failed, please make sure your '
                'sample sheet is correctly formed',
            )
            return redirect(self.redirect_url)

        if not file_url:
            messages.warning(
                self.request,
                'No {} file found for {}'.format(
                    file_type.upper(), self.material.name
                ),
            )
            return redirect(self.redirect_url)

        # Return with link to file in DavRods
        return redirect(file_url)


@fallback_to_auth_basic
class IGVSessionFileRenderView(BaseCancerConfigView, GetLibraryFileMixin):
    """IGV session file rendering view"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return IGV session file"""
        super(IGVSessionFileRenderView, self).get(request, *args, **kwargs)

        ###################
        # Get resource URLs
        ###################

        samples = self.material.get_samples()

        if not samples:
            messages.error(
                request,
                'Samples not found, make sure your sample sheets are '
                'correctly formed',
            )
            return redirect(self.redirect_url)

        # Build render table
        tb = SampleSheetTableBuilder()
        study_tables = tb.build_study_tables(self.material.study)

        # Get libraries
        libraries = get_sample_libraries(samples, study_tables)

        bam_urls = {}
        vcf_urls = {}

        # In case of malformed sample sheets
        for library in libraries:
            if not library.assay:
                messages.error(
                    self.request,
                    'Assay not found for library, make sure your sample sheets '
                    'are correctly formed',
                )
                return redirect(self.redirect_url)

            bam_url = self.get_library_file_url(
                file_type='bam', library=library
            )

            if bam_url:
                bam_urls[library.name] = bam_url

            vcf_url = self.get_library_file_url(
                file_type='vcf', library=library
            )

            if vcf_url:
                vcf_urls[library.name] = vcf_url

        ###########
        # Build XML
        ###########

        # Build IGV session XML file
        xml_str = get_igv_xml(
            bam_urls=bam_urls,
            vcf_urls=vcf_urls,
            vcf_title='Library',
            request=request,
        )

        ###########
        # Serve XML
        ###########

        file_name = self.material.name + '.case.igv.xml'

        # Set up response
        response = HttpResponse(xml_str, content_type='text/xml')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            file_name
        )
        return response


class FileExistenceCheckView(
    GetLibraryFileMixin,
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
                study__sodar_uuid=study
            ).values_list('sodar_uuid', flat=True)
        ]

        for file_path in q_dict.getlist('paths'):
            file_type = file_path.split('/')[5]
            obj = file_path.split('/')[6]
            existence = False
            lib = GenericMaterial.objects.filter(sodar_uuid=obj).first()

            # check if queried files are in the corresponding study
            if obj in valid_objs and lib:
                if self.get_library_file_url(file_type=file_type, library=lib):
                    existence = True
            else:
                existence = ''

            data['files'].append({'path': file_path, 'exists': existence})

        return Response(data, status=200)
