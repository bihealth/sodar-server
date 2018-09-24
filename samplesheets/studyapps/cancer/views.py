"""Views for the cancer study app"""

# TODO: Refactor to remove repetition between germline and cancer study app

import hashlib                  # TEMP
from lxml import etree as ET    # TEMP

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
from samplesheets.plugins import find_assay_plugin
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_index_by_header, get_last_material_name
from samplesheets.studyapps.utils import get_igv_xml

# Local helper for authenticating with auth basic
from omics_data_mgmt.users.auth import fallback_to_auth_basic

# Local constants
FILE_TYPE_SUFFIXES = {
    'bam': '.bam',
    'vcf': '.vcf.gz'}


# NOTE: TEMPORARY HACK for short notice demo
# TODO: merged with samplesheets.studyapps.utils.get_igv_xml()

def get_cancer_igv_xml(bam_urls, vcf_urls, request):
    """
    Get IGV session XML file for cancer
    :param bam_urls: BAM file URLs (dict {name: url})
    :param vcf_urls: VCF file URLs (dict {name: url})
    :param request: Django request
    :return: String (contains XML)
    """
    # Session
    xml_session = ET.Element('Session', attrib={
        'genome': 'b37',
        'hasGeneTrack': 'true',
        'hasSequenceTrack': 'true',
        'locus': 'All',
        'path': request.build_absolute_uri(),
        'version': '8'})

    # Resources
    xml_resources = ET.SubElement(xml_session, 'Resources')

    # VCF resource
    for vcf_name, vcf_url in vcf_urls.items():
        ET.SubElement(xml_resources, 'Resource', attrib={'path': vcf_url})

    # BAM resources
    for bam_name, bam_url in bam_urls.items():
        ET.SubElement(xml_resources, 'Resource', attrib={'path': bam_url})

    # VCF panel (under Session)
    for vcf_name, vcf_url in vcf_urls.items():
        xml_vcf_panel = ET.SubElement(xml_session, 'Panel', attrib={
            'height': '70',
            'name': 'DataPanel',
            'width': '1129'})

        xml_vcf_panel_track = ET.SubElement(
            xml_vcf_panel, 'Track', attrib={
                'SQUISHED_ROW_HEIGHT': '4',
                'altColor': '0,0,178',
                'autoScale': 'false',
                'clazz': 'org.broad.igv.track.FeatureTrack',
                'color': '0,0,178',
                'colorMode': 'GENOTYPE',
                'displayMode': 'EXPANDED',
                'featureVisibilityWindow': '1994000',
                'fontSize': '10',
                'grouped': 'false',
                'id': vcf_url,
                'name': 'Library ' + vcf_name,
                'renderer': 'BASIC_FEATURE',
                'siteColorMode': 'ALLELE_FREQUENCY',
                'sortable': 'false',
                'variantBandHeight': '25',
                'visible': 'true',
                'windowFunction': 'count'})

    # BAM panels
    for bam_name, bam_url in bam_urls.items():
        # Generating unique panel name with hashlib
        xml_bam_panel = ET.SubElement(xml_session, 'Panel', attrib={
            'height': '70',
            'name': 'Panel' + hashlib.md5(
                bam_url.encode('utf-8')).hexdigest(),
            'width': '1129'})

        xml_bam_panel_track_coverage = ET.SubElement(
            xml_bam_panel, 'Track', attrib={
                'altColor': '0,0,178',
                'autoScale': 'true',
                'color': '175,175,175',
                'displayMode': 'COLLAPSED',
                'featureVisibilityWindow': '-1',
                'fontSize': '10',
                'id': bam_url + '_coverage',
                'name': bam_name + ' Coverage',
                'showReference': 'false',
                'snpThreshold': '0.05',
                'sortable': 'true',
                'visible': 'true'})

        xml_bam_panel_track_datarange = ET.SubElement(
            xml_bam_panel_track_coverage, 'DataRange', attrib={
                'baseline': '0.0',
                'drawBaseline': 'true',
                'flipAxis': 'false',
                'maximum': '60.0',
                'minimum': '0.0',
                'type': 'LINEAR'})

        xml_bam_panel_track = ET.SubElement(
            xml_bam_panel, 'Track', attrib={
                'altColor': '0,0,178',
                'autoScale': 'false',
                'color': '0,0,178',
                'displayMode': 'SQUISHED',
                'featureVisibilityWindow': '-1',
                'fontSize': '10',
                'id': bam_url,
                'name': bam_name,
                'sortable': 'true',
                'visible': 'true'})

        xml_bam_panel_track_renderoptions = ET.SubElement(
            xml_bam_panel_track, 'RenderOptions', attrib={
                'colorByTag': '',
                'colorOption': 'UNEXPECTED_PAIR',
                'flagUnmappedPairs': 'true',
                'groupByTag': '',
                'maxInsertSize': '1000',
                'minInsertSize': '50',
                'shadeBasesOption': 'QUALITY',
                'shadeCenters': 'true',
                'showAllBases': 'false',
                'sortByTag': ''})

    xml_feature_panel = ET.SubElement(
        xml_session, 'Panel', attrib={
            'height': '40',
            'name': 'FeaturePanel',
            'width': '1129'})

    xml_feature_panel_track = ET.SubElement(
        xml_feature_panel, 'Track', attrib={
            'altColor': '0,0,178',
            'autoScale': 'false',
            'color': '0,0,178',
            'displayMode': 'COLLAPSED',
            'featureVisibilityWindow': '-1',
            'fontSize': '10',
            'id': 'Reference sequence',
            'name': 'Reference sequence',
            'sortable': 'false',
            'visible': 'true'})

    xml_feature_panel_track2 = ET.SubElement(
        xml_feature_panel, 'Track', attrib={
            'altColor': '0,0,178',
            'autoScale': 'false',
            'clazz': 'org.broad.igv.track.FeatureTrack',
            'color': '0,0,178',
            'colorScale':
                'ContinuousColorScale;0.0;368.0;255,255,255;0,0,178,',
            'displayMode': 'COLLAPSED',
            'featureVisibilityWindow': '-1',
            'fontSize': '10',
            'id': 'b37_genes',
            'name': 'Gene',
            'renderer': 'BASIC_FEATURE',
            'sortable': 'false',
            'visible': 'true',
            'windowFunction': 'count'})

    xml_feature_panel_track2_datarange = ET.SubElement(
        xml_feature_panel_track2, 'DataRange', attrib={
            'baseline': '0.0',
            'drawBaseline': 'true',
            'flipAxis': 'false',
            'maximum': '368.0',
            'minimum': '0.0',
            'type': 'LINEAR'})

    xml_panel_layout = ET.SubElement(xml_session, 'PanelLayout', attrib={
        'dividerFractions': '0.12411347517730496,0.39184397163120566,'
                            '0.6595744680851063,0.9273049645390071'})

    xml_hidden_attrs = ET.SubElement(xml_session, 'HiddenAttributes')
    ET.SubElement(
        xml_hidden_attrs, 'Attribute', attrib={'name': 'DATA FILE'})
    ET.SubElement(
        xml_hidden_attrs, 'Attribute', attrib={'name': 'DATA TYPE'})
    ET.SubElement(
        xml_hidden_attrs, 'Attribute', attrib={'name': 'NAME'})

    xml_str = ET.tostring(
        xml_session,
        encoding='utf-8',
        method='xml',
        xml_declaration=True,
        pretty_print=True)

    return xml_str


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
        sample_names = [s.name for s in samples]

        # Build render table
        tb = SampleSheetTableBuilder()
        study_tables = tb.build_study_tables(self.source.study)

        # Get libraries
        library_names = []

        # TODO: Repeated in samplesheets_tags, make this a generic helper
        for k, assay_table in study_tables['assays'].items():
            sample_idx = get_index_by_header(
                assay_table, 'name',
                obj_cls=GenericMaterial, item_type='SAMPLE')

            for row in assay_table['table_data']:
                if row[sample_idx]['value'] in sample_names:
                    last_name = get_last_material_name(row)

                    if last_name not in library_names:
                        library_names.append(last_name)

        libraries = GenericMaterial.objects.filter(
            study=self.source.study, name__in=library_names).order_by('name')

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
        xml_str = get_cancer_igv_xml(
            bam_urls=bam_urls,
            vcf_urls=vcf_urls,
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
