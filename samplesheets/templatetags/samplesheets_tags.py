from django import template
from django.urls import reverse

from ..models import Investigation, Study, Assay, GenericMaterial, \
    GENERIC_MATERIAL_TYPES
from ..rendering import SampleSheetHTMLRenderer as Renderer

register = template.Library()


@register.simple_tag
def get_investigation(project):
    """Return Investigation for a project"""
    try:
        return Investigation.objects.get(project=project)

    except Investigation.DoesNotExist:
        return None


@register.simple_tag
def render_cell(cell):
    """Return assay table cell as HTML"""
    return Renderer.render_cell(cell)


@register.simple_tag
def render_links_cell(row):
    """Render iRODS/IGV links cell"""
    return Renderer.render_links_cell()


@register.simple_tag
def render_top_header(section):
    """Render section of top header"""
    return Renderer.render_top_header(section)


@register.simple_tag
def render_links_top_header():
    """Render top links header"""
    return Renderer.render_links_top_header()


@register.simple_tag
def render_header(header):
    """Render section of top header"""
    return Renderer.render_header(header)


@register.simple_tag
def render_links_header():
    """Render links column header"""
    return Renderer.render_links_header()


@register.simple_tag
def get_table_id(parent):
    """
    Return table id for DataTable reference
    :param parent: Study or Assay object
    :return: string
    """
    return 'omics-ss-data-table-{}-{}'.format(
        parent.__class__.__name__.lower(), parent.pk)


@register.simple_tag
def get_study_title(study):
    """Return printable study title"""
    return study.title if study.title else study.file_name.split('.')[0]


@register.simple_tag
def get_assay_title(assay):
    """Return printable assy title"""
    return assay.get_name()


@register.simple_tag
def get_assay_table(table_data, assay):
    """
    Return assay table for rendering
    :param table_data: Dict from context['table_data']
    :param assay: Assay object
    :return: Dict
    """
    return table_data['assays'][assay.get_name()]


@register.simple_tag
def find_samplesheets_items(search_term, user, search_type, keywords):
    """Return samplesheets items based on a search term, user and
    possible type/keywords"""
    ret = None

    # TODO: Refactor, add different types, etc.

    if not search_type:
        sources = GenericMaterial.objects.find(
            search_term, keywords, item_type='SOURCE')
        samples = GenericMaterial.objects.find(
            search_term, keywords, item_type='SAMPLE')
        data_files = GenericMaterial.objects.find(
            search_term, keywords, item_type='DATA')
        ret = list(sources) + list(samples) + list(data_files)
        ret.sort(key=lambda x: x.name.lower())

    elif search_type == 'source':
        ret = GenericMaterial.objects.find(
            search_term, keywords, item_type='SOURCE').order_by('name')

    elif search_type == 'sample':
        ret = GenericMaterial.objects.find(
            search_term, keywords, item_type='SAMPLE').order_by('name')

    elif search_type == 'file':
        ret = GenericMaterial.objects.find(
            search_term, keywords, item_type='DATA').order_by('name')

    if ret:
        ret = [x for x in ret if
               user.has_perm('samplesheets.view_sheet', x.get_project())]
        return ret

    return None


@register.simple_tag
def get_material_type(material):
    """Return printable version of material item_type"""
    return GENERIC_MATERIAL_TYPES[material.item_type]


@register.simple_tag
def get_material_link(material):
    """Return link to material"""
    url = reverse('project_sheets', kwargs={
        'project': material.get_project().pk,
        'study': material.study.pk})

    if material.assay:
        url += '#assay{}'.format(material.assay.pk)

    return url


@register.simple_tag
def get_assay_info_html(assay):
    """Return assay info popup HTML"""
    ret = '<div class="row omics-ss-assay-info-popup">\n'

    for k, v in assay.comments.items():
        if v['value']:
            ret += '<dt class="col-md-4">{}</dt>\n'.format(k)
            ret += '<dd class="col-md-8">{}</dd>\n'.format(v['value'])

    ret += '</div>\n'
    return ret