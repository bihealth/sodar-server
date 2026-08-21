"""Views for the germline study app"""

from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import View

# Projectroles dependency
from projectroles.plugins import PluginAPI
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
)

# Samplesheets dependency
from samplesheets.models import GenericMaterial
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.studyapps.germline.utils import get_pedigree_file_path
from samplesheets.studyapps.utils import get_igv_xml
from samplesheets.utils import get_sheets_url

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic


plugin_api = PluginAPI()
table_builder = SampleSheetTableBuilder()


# Local constants
APP_NAME = 'samplesheets.studyapps.germline'


class BaseGermlineConfigView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    View,
):
    """Base view from which actual views are extended"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirect_url = None
        self.source = None
        self.study_tables = None

    def get(self, request, *args, **kwargs):
        """
        Override get() to set up stuff and return with failure if something is
        missing.
        """
        irods_backend = plugin_api.get_backend_api('omics_irods')
        self.redirect_url = get_sheets_url(self.get_project())

        try:
            self.source = GenericMaterial.objects.get(
                sodar_uuid=self.kwargs['genericmaterial']
            )
            self.redirect_url = self.source.study.get_url()
        except GenericMaterial.DoesNotExist:
            messages.error(request, 'Source material not found')
            return redirect(self.redirect_url)

        if not irods_backend:
            messages.error(self.request, 'iRODS Backend not available')
            return redirect(self.redirect_url)
        if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
            messages.error(self.request, 'iRODS WebDAV not available')
            return redirect(self.redirect_url)
        # Get/build render tables
        self.study_tables = table_builder.get_study_tables(self.source.study)


@fallback_to_auth_basic
class IGVSessionFileRenderView(BaseGermlineConfigView):
    """IGV session file rendering view"""

    permission_required = 'samplesheets.view_files'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_list = None
        self.cache_item = None

    def _get_path(
        self, file_type: str, source: GenericMaterial
    ) -> Optional[str]:
        """
        Return pedigree file path, either from the cache or by querying iRODS.

        :param file_type: String ("bam" or "vcf", "bam" is also used for CRAM)
        :param source: GenericMaterial of type SOURCE
        :return: String or None
        """
        if self.cache_item and source.name in self.cache_item.data[file_type]:
            return self.cache_item.data[file_type][source.name]
        # Query for iRODS object list if not pre-queried
        if not self.obj_list:
            irods_backend = plugin_api.get_backend_api('omics_irods')
            try:
                with irods_backend.get_session() as irods:
                    self.obj_list = irods_backend.get_objects(
                        irods, irods_backend.get_path(source.study)
                    )
            except Exception:
                self.obj_list = None
        return get_pedigree_file_path(
            file_type=file_type,
            source=source,
            study_tables=self.study_tables,
            obj_list=self.obj_list,
        )

    def get(self, request, *args, **kwargs):
        """Override get() to return IGV session file"""
        super().get(request, *args, **kwargs)
        cache_backend = plugin_api.get_backend_api('sodar_cache')
        vcf_urls = {}
        bam_urls = {}
        webdav_url = settings.IRODS_WEBDAV_URL
        study = self.source.study
        project = study.get_project()

        # Get iRODS paths from cache if available
        if cache_backend:
            try:
                self.cache_item = cache_backend.get_cache_item(
                    app_name=APP_NAME,
                    name=f'irods/{study.sodar_uuid}',
                    project=study.get_project(),
                )
            except Exception:
                self.cache_item = None

        # Get resource URLs
        # Get URLs to all latest bam files for all sources in family
        fam_id = None
        if 'Family' in self.source.characteristics:
            fam_id = self.source.characteristics['Family']['value']
        # Family defined
        if fam_id:
            fam_sources = GenericMaterial.objects.filter(
                study=study,
                item_type='SOURCE',
                characteristics__Family__value=fam_id,
            ).order_by('name')
            for fam_source in fam_sources:
                bam_path = self._get_path('bam', fam_source)
                if bam_path:
                    bam_urls[fam_source.name] = webdav_url + bam_path
        # If not, just add for the current source
        else:
            bam_path = self._get_path('bam', self.source)
            if bam_path:
                bam_urls[self.source.name] = webdav_url + bam_path

        # Build XML
        # Get path and URL to latest family vcf file
        # First check for entry by family ID in cache
        if fam_id and self.cache_item and fam_id in self.cache_item.data['vcf']:
            vcf_path = self.cache_item.data['vcf'][fam_id]
        else:
            vcf_path = self._get_path('vcf', self.source)
        if vcf_path:
            # Use source name if family ID not known
            if not fam_id:
                fam_id = self.source.name
            vcf_urls[fam_id] = webdav_url + vcf_path
        # Build IGV session XML file
        xml_str = get_igv_xml(
            project=project,
            bam_urls=bam_urls,
            vcf_urls=vcf_urls,
            vcf_title='Pedigree',
            request=request,
        )
        # Serve XML
        file_name = fam_id + '.pedigree.igv.xml'
        response = HttpResponse(xml_str, content_type='text/xml')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
