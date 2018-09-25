"""Views for the cancer study app"""


from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin, ProjectPermissionMixin

# Samplesheets dependency
from samplesheets.models import GenericMaterial
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_index_by_header, get_last_material_name, \
    get_sample_libraries
from samplesheets.studyapps.utils import get_igv_xml, FILE_TYPE_SUFFIXES

# Local helper for authenticating with auth basic
from omics_data_mgmt.users.auth import fallback_to_auth_basic


class BaseCancerConfigView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, View):
    """Base view from which actual views are extended"""

    def __init__(self, *args, **kwargs):
        super(BaseCancerConfigView, self).__init__(*args, **kwargs)
        self.redirect_url = None
        self.source = None
        self.library = None
        self.study_tables = None

    @classmethod
    def _get_library_file_url(
            cls, file_type, library):
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
                if (obj['name'].lower().endswith(
                        FILE_TYPE_SUFFIXES[file_type])):
                    file_paths.append(obj['path'])

        except FileNotFoundError:
            pass

        if not file_paths:
            return None

        # Get the last file of type by file name
        file_path = sorted(file_paths, key=lambda x: x.split('/')[-1])[-1]
        file_url = '{}{}'.format(
            settings.IRODS_WEBDAV_URL, file_path)
        return file_url

    def get(self, request, *args, **kwargs):
        """Override get() to set up stuff and return with failure if something
        is missing"""
        irods_backend = get_backend_api('omics_irods')

        self.redirect_url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self._get_project(
                self.request, self.kwargs).omics_uuid})

        if not irods_backend:
            messages.error(self.request, 'iRODS Backend not available')
            return redirect(self.redirect_url)

        if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
            messages.error(self.request, 'iRODS WebDAV not available')
            return redirect(self.redirect_url)

        if 'genericmaterial' not in self.kwargs:
            messages.error(self.request, 'No material given for linking')
            return redirect(self.redirect_url)


class FileRedirectView(BaseCancerConfigView):
    """BAM/VCF file link view"""
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return URL to file"""
        super(FileRedirectView, self).get(request, *args, **kwargs)
        file_type = kwargs['file_type']

        if file_type not in FILE_TYPE_SUFFIXES.keys():
            messages.error(
                self.request, 'Unsupported file type "{}"'.format(file_type))
            return redirect(self.redirect_url)

        # Get library
        try:
            self.library = GenericMaterial.objects.get(
                omics_uuid=self.kwargs['genericmaterial'])

        except GenericMaterial.DoesNotExist:
            messages.error(
                self.request,
                'Library not found, unable to redirect to file')
            return redirect(self.redirect_url)

        # Get source
        # HACK: May fail if naming conventions are not followed in ISAtab?
        try:
            self.source = GenericMaterial.objects.get(
                item_type='SOURCE', name=self.library.name.split('-')[0])

        except GenericMaterial.DoesNotExist:
            messages.error(
                self.request,
                'Source not found, unable to redirect to file')
            return redirect(self.redirect_url)

        file_url = self._get_library_file_url(
            file_type=file_type,
            library=self.library)

        if not file_url:
            messages.warning(
                self.request, 'No {} file found for {}'.format(
                    file_type.upper(), self.library.name))
            return redirect(self.redirect_url)

        # Return with link to file in DavRods
        return redirect(file_url)


@fallback_to_auth_basic
class IGVSessionFileRenderView(BaseCancerConfigView):
    """IGV session file rendering view"""
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return IGV session file"""
        super(IGVSessionFileRenderView, self).get(request, *args, **kwargs)

        # Get source
        try:
            self.source = GenericMaterial.objects.get(
                omics_uuid=self.kwargs['genericmaterial'])

        except GenericMaterial.DoesNotExist:
            messages.error(
                self.request,
                'Source not found, unable to redirect to file')
            return redirect(self.redirect_url)

        ###################
        # Get resource URLs
        ###################

        samples = self.source.get_samples()

        # Build render table
        tb = SampleSheetTableBuilder()
        study_tables = tb.build_study_tables(self.source.study)

        # Get libraries
        libraries = get_sample_libraries(samples, study_tables)

        bam_urls = {}
        vcf_urls = {}

        for library in libraries:
            bam_url = self._get_library_file_url(
                file_type='bam',
                library=library)

            if bam_url:
                bam_urls[library.name] = bam_url

            vcf_url = self._get_library_file_url(
                file_type='vcf',
                library=library)

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
            request=request)

        ###########
        # Serve XML
        ###########

        file_name = self.source.name + '.case.igv.xml'

        # Set up response
        response = HttpResponse(xml_str, content_type='text/xml')
        response['Content-Disposition'] = \
            'attachment; filename="{}"'.format(file_name)
        return response
