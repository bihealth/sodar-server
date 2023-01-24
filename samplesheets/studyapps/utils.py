"""General utility functions for samplesheets study apps"""

import hashlib

from lxml import etree as ET

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI


app_settings = AppSettingAPI()


# Constants
IGV_URL_BASE = 'http://127.0.0.1:60151'
FILE_TYPE_SUFFIXES = {'bam': '.bam', 'vcf': '.vcf.gz'}
INVALID_TYPE_MSG = 'Invalid value for file_type'


def get_igv_omit_override(project, file_type):
    """
    Get IGV omit override setting for a project. NOTE: Added as a separate
    method to avoid redundant database queries.

    :param project: Project object
    :param file_type: String ("bam" or "vcf")
    :return: List or None
    """
    ft = file_type.lower()
    if ft not in ['bam', 'vcf']:
        raise ValueError(INVALID_TYPE_MSG)
    setting = app_settings.get(
        'samplesheets', 'igv_omit_{}'.format(ft), project=project
    )
    if setting:
        return [s.strip() for s in setting.split(',')]
    return None


def check_igv_file_name(file_name, file_type, override=None):
    """
    Check if file is acceptable for IGV session inclusion. Returns False if
    suffix is found in env vars of omittable files.

    :param file_name: String
    :param file_type: String ("bam" or "vcf")
    :param override: File suffixes to override site-wide setting (list or None)
    :raise: ValueError if file_type is incorrect
    :return: Boolean (True if name is OK)
    """
    ft = file_type.lower()
    if ft not in ['bam', 'vcf']:
        raise ValueError(INVALID_TYPE_MSG)
    fn = file_name.lower()
    if override:
        return not any([s.lower() for s in override if fn.endswith(s)])
    ol = getattr(settings, 'SHEETS_IGV_OMIT_' + file_type.upper(), [])
    return not any([s.lower() for s in ol if fn.endswith(s)])


def get_igv_session_url(source, app_name, merge=False):
    """
    Return URL for opening a generated session file in IGV.

    :param source: GenericMaterial object of type SOURCE
    :param app_name: App name for study app to use, must conform to study app
                     URL config (string)
    :param merge: Merge into current session (bool, default=False)
    :return: String
    """
    if settings.IRODS_WEBDAV_IGV_PROXY:
        file_prefix = settings.IRODS_WEBDAV_URL + '/__sodar'
    else:
        file_prefix = settings.SODAR_API_DEFAULT_HOST.geturl()
    file_url = reverse(
        '{}:igv'.format(app_name), kwargs={'genericmaterial': source.sodar_uuid}
    )
    return '{}/load?merge={}&file={}{}.xml'.format(
        IGV_URL_BASE,
        str(merge).lower(),
        file_prefix,
        file_url,
    )


def get_igv_irods_url(irods_path, merge=True):
    """
    Return URL for opening an iRODS file in IGV.

    :param irods_path: Full iRODS path for the file (string)
    :param merge: Merge into current session (bool, default=True)
    :return: String
    """
    return '{}/load?merge={}&file={}'.format(
        IGV_URL_BASE, str(merge).lower(), settings.IRODS_WEBDAV_URL + irods_path
    )


def get_igv_xml(project, bam_urls, vcf_urls, vcf_title, request, string=True):
    """
    Build IGV session XML file.

    :param project: Project object
    :param bam_urls: BAM file URLs (dict {name: url})
    :param vcf_urls: VCF file URLs (dict {name: url})
    :param vcf_title: VCF title to prefix to VCF title strings (string)
    :param request: Django request
    :param string: Convert result to string (bool, default=True)
    :return: String (contains XML)
    """
    genome_id = app_settings.get('samplesheets', 'igv_genome', project=project)
    # Session
    xml_session = ET.Element(
        'Session',
        attrib={
            'genome': genome_id,
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
                'color': '175,175,175',
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
            'id': '{}_genes'.format(genome_id),
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
    if not string:
        return xml_session
    xml_str = ET.tostring(
        xml_session,
        encoding='utf-8',
        method='xml',
        xml_declaration=True,
        pretty_print=True,
    )
    return xml_str
