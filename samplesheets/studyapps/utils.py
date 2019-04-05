"""General utility functions for samplesheets study apps"""

import hashlib
from lxml import etree as ET

from django.conf import settings
from projectroles.plugins import get_backend_api

from samplesheets.models import GenericMaterial
from samplesheets.plugins import find_assay_plugin
from samplesheets.utils import get_index_by_header


# Constants

FILE_TYPE_SUFFIXES = {'bam': '.bam', 'vcf': '.vcf.gz'}


def get_igv_xml(bam_urls, vcf_urls, vcf_title, request):
    """
    Build IGV session XML file
    :param bam_urls: BAM file URLs (dict {name: url})
    :param vcf_urls: VCF file URLs (dict {name: url})
    :param vcf_title: VCF title to prefix to VCF title strings (string)
    :param request: Django request
    :return: String (contains XML)
    """
    # Session
    xml_session = ET.Element(
        'Session',
        attrib={
            'genome': 'b37',
            'hasGeneTrack': 'true',
            'hasSequenceTrack': 'true',
            'locus': 'All',
            'path': request.build_absolute_uri(),
            'version': '8',
        },
    )

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
        xml_vcf_panel = ET.SubElement(
            xml_session,
            'Panel',
            attrib={'height': '70', 'name': 'DataPanel', 'width': '1129'},
        )

        # xml_vcf_panel_track
        ET.SubElement(
            xml_vcf_panel,
            'Track',
            attrib={
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
                'name': vcf_title + ' ' + vcf_name,
                'renderer': 'BASIC_FEATURE',
                'siteColorMode': 'ALLELE_FREQUENCY',
                'sortable': 'false',
                'variantBandHeight': '25',
                'visible': 'true',
                'windowFunction': 'count',
            },
        )

    # BAM panels
    for bam_name, bam_url in bam_urls.items():
        # Generating unique panel name with hashlib
        xml_bam_panel = ET.SubElement(
            xml_session,
            'Panel',
            attrib={
                'height': '70',
                'name': 'Panel'
                + hashlib.md5(bam_url.encode('utf-8')).hexdigest(),
                'width': '1129',
            },
        )

        xml_bam_panel_track_coverage = ET.SubElement(
            xml_bam_panel,
            'Track',
            attrib={
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
                'visible': 'true',
            },
        )

        # xml_bam_panel_track_datarange
        ET.SubElement(
            xml_bam_panel_track_coverage,
            'DataRange',
            attrib={
                'baseline': '0.0',
                'drawBaseline': 'true',
                'flipAxis': 'false',
                'maximum': '60.0',
                'minimum': '0.0',
                'type': 'LINEAR',
            },
        )

        xml_bam_panel_track = ET.SubElement(
            xml_bam_panel,
            'Track',
            attrib={
                'altColor': '0,0,178',
                'autoScale': 'false',
                'color': '0,0,178',
                'displayMode': 'SQUISHED',
                'featureVisibilityWindow': '-1',
                'fontSize': '10',
                'id': bam_url,
                'name': bam_name,
                'sortable': 'true',
                'visible': 'true',
            },
        )

        # xml_bam_panel_track_renderoptions
        ET.SubElement(
            xml_bam_panel_track,
            'RenderOptions',
            attrib={
                'colorByTag': '',
                'colorOption': 'UNEXPECTED_PAIR',
                'flagUnmappedPairs': 'true',
                'groupByTag': '',
                'maxInsertSize': '1000',
                'minInsertSize': '50',
                'shadeBasesOption': 'QUALITY',
                'shadeCenters': 'true',
                'showAllBases': 'false',
                'sortByTag': '',
            },
        )

    xml_feature_panel = ET.SubElement(
        xml_session,
        'Panel',
        attrib={'height': '40', 'name': 'FeaturePanel', 'width': '1129'},
    )

    # xml_feature_panel_track
    ET.SubElement(
        xml_feature_panel,
        'Track',
        attrib={
            'altColor': '0,0,178',
            'autoScale': 'false',
            'color': '0,0,178',
            'displayMode': 'COLLAPSED',
            'featureVisibilityWindow': '-1',
            'fontSize': '10',
            'id': 'Reference sequence',
            'name': 'Reference sequence',
            'sortable': 'false',
            'visible': 'true',
        },
    )

    xml_feature_panel_track2 = ET.SubElement(
        xml_feature_panel,
        'Track',
        attrib={
            'altColor': '0,0,178',
            'autoScale': 'false',
            'clazz': 'org.broad.igv.track.FeatureTrack',
            'color': '0,0,178',
            'colorScale': 'ContinuousColorScale;0.0;368.0;255,255,255;0,0,178,',
            'displayMode': 'COLLAPSED',
            'featureVisibilityWindow': '-1',
            'fontSize': '10',
            'id': 'b37_genes',
            'name': 'Gene',
            'renderer': 'BASIC_FEATURE',
            'sortable': 'false',
            'visible': 'true',
            'windowFunction': 'count',
        },
    )

    # xml_feature_panel_track2_datarange
    ET.SubElement(
        xml_feature_panel_track2,
        'DataRange',
        attrib={
            'baseline': '0.0',
            'drawBaseline': 'true',
            'flipAxis': 'false',
            'maximum': '368.0',
            'minimum': '0.0',
            'type': 'LINEAR',
        },
    )

    # xml_panel_layout
    ET.SubElement(
        xml_session,
        'PanelLayout',
        attrib={
            'dividerFractions': '0.12411347517730496,0.39184397163120566,'
            '0.6595744680851063,0.9273049645390071'
        },
    )

    xml_hidden_attrs = ET.SubElement(xml_session, 'HiddenAttributes')
    ET.SubElement(xml_hidden_attrs, 'Attribute', attrib={'name': 'DATA FILE'})
    ET.SubElement(xml_hidden_attrs, 'Attribute', attrib={'name': 'DATA TYPE'})
    ET.SubElement(xml_hidden_attrs, 'Attribute', attrib={'name': 'NAME'})

    xml_str = ET.tostring(
        xml_session,
        encoding='utf-8',
        method='xml',
        xml_declaration=True,
        pretty_print=True,
    )

    return xml_str


# for cancer study apps
def get_library_file_url(file_type, library):
    """
    Return DavRods URL for the most recent file of type "bam" or "vcf"
    linked to library
    :param file_type: String ("bam" or "vcf")
    :param library: GenericMaterial object
    :return: String
    """
    irods_backend = get_backend_api('omics_irods')

    if not irods_backend:
        raise Exception('iRODS Backend not available')

    if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
        raise Exception('iRODS WebDAV not available')

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


# for germline study apps
def get_pedigree_file_url(file_type, source, study_tables):
    """
    Return DavRods URL for the most recent file of type "bam" or "vcf"
    linked to source
    :param file_type: String ("bam" or "vcf")
    :param source: GenericMaterial of type SOURCE
    :param study_tables: Render study tables
    :return: String
    """
    irods_backend = get_backend_api('omics_irods')

    if not irods_backend:
        raise Exception('iRODS Backend not available')

    if not settings.IRODS_WEBDAV_ENABLED or not settings.IRODS_WEBDAV_URL:
        raise Exception('iRODS WebDAV not available')

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
                    path = assay_plugin.get_row_path(row, assay_table, assay)
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
