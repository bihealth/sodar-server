import hashlib
from lxml import etree as ET

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
from samplesheets.utils import get_index_by_header

# Local helper for authenticating with auth basic
from omics_data_mgmt.users.auth import fallback_to_auth_basic

# Local constants
FILE_TYPE_SUFFIX = {
    'bam': '.bam',
    'vcf': '.vcf.gz'}


class BaseGermlineConfigView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, View):
    """Base view from which actual views are extended"""

    def __init__(self, *args, **kwargs):
        super(BaseGermlineConfigView, self).__init__(*args, **kwargs)
        self.redirect_url = None
        self.source = None
        self.study_tables = None

    @classmethod
    def _get_pedigree_file_url(
            cls, file_type, source, study_tables):
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
                assay.measurement_type, assay.technology_type)
            source_fam = None

            if 'Family' in source.characteristics:
                source_fam = source.characteristics['Family']['value']

            # Get family index
            fam_idx = get_index_by_header(assay_table, 'family')

            # Get sample index
            sample_idx = get_index_by_header(
                assay_table, 'name',
                obj_cls=GenericMaterial, item_type='SAMPLE')

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
                            row, assay_table, assay)
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
                    if (obj['name'].lower().endswith(
                            FILE_TYPE_SUFFIX[file_type]) and
                            any(x in obj['name'] for x in sample_names)):
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
            messages.error(self.request, 'No Source material given for linking')
            return redirect(self.redirect_url)

        try:
            self.source = GenericMaterial.objects.get(
                item_type='SOURCE',
                omics_uuid=self.kwargs['genericmaterial'])

        except GenericMaterial.DoesNotExist:
            messages.error(
                self.request,
                'Source not found, unable to redirect to file')
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

        if file_type not in FILE_TYPE_SUFFIX.keys():
            messages.error(
                self.request, 'Unsupported file type "{}"'.format(file_type))
            return redirect(self.redirect_url)

        file_url = self._get_pedigree_file_url(
            file_type=file_type,
            source=self.source,
            study_tables=self.study_tables)

        if not file_url:
            if file_type != 'bam' and 'Family' in self.source.characteristics:
                target_name = self.source.characteristics['Family']['value']

            else:
                target_name = self.source.name

            messages.warning(
                self.request, 'No {} file found for {}'.format(
                    file_type.upper(), target_name))
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

        ###################
        # Get resource URLs
        ###################

        # Get URL to latest family vcf file
        vcf_url = self._get_pedigree_file_url(
            file_type='vcf',
            source=self.source,
            study_tables=self.study_tables)

        # Get URLs to all latest bam files for all sources in family
        bam_urls = {}

        # Family defined
        if 'Family' in self.source.characteristics:
            fam_id = self.source.characteristics['Family']['value']

        else:
            fam_id = None

        if fam_id:
            fam_sources = GenericMaterial.objects.filter(
                study=self.source.study, item_type='SOURCE',
                characteristics__Family__value=fam_id).order_by('name')

            for fam_source in fam_sources:
                bam_url = self._get_pedigree_file_url(
                    file_type='bam',
                    source=fam_source,
                    study_tables=self.study_tables)

                if bam_url:
                    bam_urls[fam_source.name] = bam_url

        # If not, just add for the current source
        else:
            bam_url = self._get_pedigree_file_url(
                file_type='bam',
                source=self.source,
                study_tables=self.study_tables)

            if bam_url:
                bam_urls[self.source.name] = bam_url

        ###########
        # Build XML
        ###########

        if not fam_id:
            fam_id = self.source.name   # Use source name if family ID not known

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
        if vcf_url:
            ET.SubElement(xml_resources, 'Resource', attrib={'path': vcf_url})

        # BAM resources
        for source_name, bam_url in bam_urls.items():
            ET.SubElement(xml_resources, 'Resource', attrib={'path': bam_url})

        # VCF panel (under Session)
        if vcf_url:

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
                    'name': 'Pedigree ' + fam_id,
                    'renderer': 'BASIC_FEATURE',
                    'siteColorMode': 'ALLELE_FREQUENCY',
                    'sortable': 'false',
                    'variantBandHeight': '25',
                    'visible': 'true',
                    'windowFunction': 'count'})

        # BAM panels
        for source_name, bam_url in bam_urls.items():

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
                    'name': source_name + ' Coverage',
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
                    'name': source_name,
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

        ###########
        # Serve XML
        ###########

        xml_output = ET.tostring(
            xml_session,
            encoding='utf-8',
            method='xml',
            xml_declaration=True,
            pretty_print=True)

        file_name = fam_id + '.pedigree.igv.xml'

        # Set up response
        response = HttpResponse(xml_output, content_type='text/xml')
        response['Content-Disposition'] = \
            'attachment; filename="{}"'.format(file_name)
        return response
