"""General utility functions for samplesheets study apps"""

import hashlib
from lxml import etree as ET


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
                'name': vcf_title + ' ' + vcf_name,
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
