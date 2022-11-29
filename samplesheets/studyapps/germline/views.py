"""Views for the germline study app"""

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
from samplesheets.studyapps.germline.utils import get_pedigree_file_path
from samplesheets.studyapps.utils import get_igv_xml
from samplesheets.utils import get_sheets_url

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic


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
        irods_backend = get_backend_api('omics_irods')
        self.redirect_url = get_sheets_url(self.get_project())

        try:
            self.source = GenericMaterial.objects.get(
                sodar_uuid=self.kwargs['genericmaterial']
            )
            self.redirect_url = get_sheets_url(self.source.study)
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
        self.study_tables = tb.build_study_tables(self.source.study, ui=False)


@fallback_to_auth_basic
class IGVSessionFileRenderView(BaseGermlineConfigView):
    """IGV session file rendering view"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        """Override get() to return IGV session file"""
        super().get(request, *args, **kwargs)
        vcf_urls = {}
        bam_urls = {}
        webdav_url = settings.IRODS_WEBDAV_URL

        # Get resource URLs
        # Get URLs to all latest bam files for all sources in family
        fam_id = None
        if 'Family' in self.source.characteristics:
            fam_id = self.source.characteristics['Family']['value']
        # Family defined
        if fam_id:
            fam_sources = GenericMaterial.objects.filter(
                study=self.source.study,
                item_type='SOURCE',
                characteristics__Family__value=fam_id,
            ).order_by('name')
            for fam_source in fam_sources:
                bam_path = get_pedigree_file_path(
                    file_type='bam',
                    source=fam_source,
                    study_tables=self.study_tables,
                )
                if bam_path:
                    bam_urls[fam_source.name] = webdav_url + bam_path
        # If not, just add for the current source
        else:
            bam_path = get_pedigree_file_path(
                file_type='bam',
                source=self.source,
                study_tables=self.study_tables,
            )
            if bam_path:
                bam_urls[self.source.name] = webdav_url + bam_path

        # Build XML
        # Get URL to latest family vcf file
        vcf_path = get_pedigree_file_path(
            file_type='vcf', source=self.source, study_tables=self.study_tables
        )
        if vcf_path:
            # Use source name if family ID not known
            if not fam_id:
                fam_id = self.source.name
            vcf_urls[fam_id] = webdav_url + vcf_path
        # Build IGV session XML file
        xml_str = get_igv_xml(
            bam_urls=bam_urls,
            vcf_urls=vcf_urls,
            vcf_title='Pedigree',
            request=request,
        )

        # Serve XML
        file_name = fam_id + '.pedigree.igv.xml'
        response = HttpResponse(xml_str, content_type='text/xml')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            file_name
        )
        return response
