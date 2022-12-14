"""Views for the cancer study app"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import View

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
)

from samplesheets.models import GenericMaterial
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_sheets_url
from samplesheets.studyapps.utils import get_igv_xml


table_builder = SampleSheetTableBuilder()


APP_NAME = 'samplesheets.studyapps.cancer'


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
        self.redirect_url = get_sheets_url(self.get_project())
        try:
            self.material = GenericMaterial.objects.get(
                sodar_uuid=self.kwargs['genericmaterial']
            )
            self.redirect_url = get_sheets_url(self.material.study)
        except GenericMaterial.DoesNotExist:
            messages.error(request, 'Material not found')
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
        cache_backend = get_backend_api('sodar_cache')
        webdav_url = settings.IRODS_WEBDAV_URL
        study = self.material.study

        cache_item = None
        if cache_backend:
            cache_item = cache_backend.get_cache_item(
                app_name=APP_NAME,
                name='irods/{}'.format(study.sodar_uuid),
                project=study.get_project(),
            )
        bam_urls = {}
        vcf_urls = {}
        if cache_item:
            for k, v in cache_item.data['bam'].items():
                if v:
                    bam_urls[k] = webdav_url + v
            for k, v in cache_item.data['vcf'].items():
                if v:
                    vcf_urls[k] = webdav_url + v

        # Build IGV session XML file
        xml_str = get_igv_xml(
            bam_urls=bam_urls,
            vcf_urls=vcf_urls,
            vcf_title='Library',
            request=request,
        )
        # Serve XML
        file_name = self.material.name + '.case.igv.xml'
        # Set up response
        response = HttpResponse(xml_str, content_type='text/xml')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            file_name
        )
        return response
