"""Views for the cancer study app"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import View

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
)

# Samplesheets dependency
from samplesheets.models import GenericMaterial
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_sample_libraries, get_sheets_url
from samplesheets.studyapps.utils import get_igv_xml

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic

from samplesheets.studyapps.cancer.utils import get_library_file_path


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
        """
        Override get() to set up stuff and return with failure if something
        is missing.
        """
        irods_backend = get_backend_api('omics_irods')
        self.redirect_url = get_sheets_url(self.get_project())

        try:
            self.material = GenericMaterial.objects.get(
                sodar_uuid=self.kwargs['genericmaterial']
            )
            self.redirect_url = get_sheets_url(self.material.study)
        except GenericMaterial.DoesNotExist:
            messages.error(request, 'Material not found')
            return redirect(self.redirect_url)

        if not irods_backend:
            messages.error(self.request, 'iRODS Backend not available')
            return redirect(self.redirect_url)
        if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
            messages.error(self.request, 'iRODS WebDAV not available')
            return redirect(self.redirect_url)


@fallback_to_auth_basic
class IGVSessionFileRenderView(BaseCancerConfigView):
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
        study_tables = tb.build_study_tables(self.material.study, ui=False)
        # Get libraries
        libraries = get_sample_libraries(samples, study_tables)
        bam_urls = {}
        vcf_urls = {}
        webdav_url = settings.IRODS_WEBDAV_URL

        # In case of malformed sample sheets
        for library in libraries:
            if not library.assay:
                messages.error(
                    self.request,
                    'Assay not found for library, make sure your sample sheets '
                    'are correctly formed',
                )
                return redirect(self.redirect_url)
            bam_path = get_library_file_path(file_type='bam', library=library)
            if bam_path:
                bam_urls[library.name] = webdav_url + bam_path
            vcf_path = get_library_file_path(file_type='vcf', library=library)
            if vcf_path:
                vcf_urls[library.name] = webdav_url + vcf_path

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
