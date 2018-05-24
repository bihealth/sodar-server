import random
import string

from django import template
from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import get_backend_api

from ..models import Investigation, GenericMaterial, \
    GENERIC_MATERIAL_TYPES


irods_backend = get_backend_api('omics_irods')

register = template.Library()


# Local constants
EMPTY_VALUE = '-'


# General ----------------------------------------------------------------------


@register.simple_tag
def get_investigation(project):
    """Return Investigation for a project"""
    try:
        return Investigation.objects.get(project=project)

    except Investigation.DoesNotExist:
        return None


@register.simple_tag
def get_table_id(parent):
    """
    Return table id for DataTable reference
    :param parent: Study or Assay object
    :return: string
    """
    return 'omics-ss-data-table-{}-{}'.format(
        parent.__class__.__name__.lower(), parent.omics_uuid)


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
    url = reverse(
        'samplesheets:project_sheets', kwargs={
            'study': material.study.omics_uuid})

    if material.assay:
        url += '#{}'.format(material.assay.omics_uuid)

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


@register.simple_tag
def get_irods_tree(investigation):
    """Return HTML for iRODS dirs"""
    ret = '<ul><li>{}<ul>'.format(settings.IRODS_SAMPLE_DIR)

    for study in investigation.studies.all():
        ret += '<li>{}'.format(
            irods_backend.get_subdir(study, include_parent=False))

        if study.assays.all().count() > 0:
            ret += '<ul>'

            for assay in study.assays.all():
                ret += '<li>{}</li>'.format(
                    irods_backend.get_subdir(assay, include_parent=False))

            ret += '</ul>'

        ret += '</li>'

    ret += '</ul></li></ul>'

    return ret


# Table rendering --------------------------------------------------------------


@register.simple_tag
def render_top_headers(top_header, col_values):
    """
    Render the top header row
    :param top_header: Top header row (list)
    :param col_values: True/False values for column data (list)
    :return: String (contains HTML)
    """
    ret = ''
    col_idx = 0     # Index in original (non-hidden) columns

    for section in top_header:
        final_colspan = sum(col_values[col_idx:col_idx + section['colspan']])

        if final_colspan > 0:
            ret += '<th class="bg-{} text-nowrap text-white ' \
                   'omics-ss-top-header" colspan="{}" original-colspan="{}" ' \
                   '{}>{}</th>\n'.format(
                    section['colour'],
                    final_colspan,     # Actual colspan
                    final_colspan,     # Original colspan
                    ''.join(['{}-cols="{}" '.format(k, v) for
                             k, v in section['hiding'].items()]),
                    section['value'])

        col_idx += section['colspan']

    return ret


@register.simple_tag
def render_field_headers(field_header, col_values):
    """
    Render field header row for a table
    :param field_header: Field header row (list)
    :param col_values: True/False values for column data (list)
    :return: String (contains HTML)
    """
    ret = ''

    # Iterate through header row, render only if there is data in column
    for i in range(0, len(field_header)):
        header = field_header[i]

        if col_values[i]:
            ret += '<th class="{}">{}</th>\n'.format(
                ' '.join(header['classes']), header['value'])

    return ret


@register.simple_tag
def get_row_id():
    """
    Return random string for link ids
    :return: string
    """
    return ''.join(random.SystemRandom().choice(
        string.ascii_lowercase + string.digits) for x in range(16))


@register.simple_tag
def render_cells(row, col_values):
    """
    Render cells of a table row
    :param row: Row of cells (list)
    :param col_values: True/False values for column data (list)
    :return: String (contains HTML)
    """
    ret = ''

    # Right aligning
    def is_num(x):
        try:
            float(x)
            return True

        except ValueError:
            return False

    # Iterate through row, render only if there is data in column
    for i in range(0, len(row)):
        cell = row[i]

        if col_values[i]:
            td_class_str = ' '.join(cell['classes'])

            ret += '<td '

            if cell['value'] and is_num(cell['value']):
                td_class_str += 'text-right'

            # Add extra attrs if present
            if cell['attrs']:
                for k, v in cell['attrs'].items():
                    ret += '{}="{}" '.format(k, v)

            if cell['tooltip']:
                ret += 'class="{}" title="{}" data-toggle="tooltip" ' \
                       'data-placement="top">'.format(
                        td_class_str, cell['tooltip'])

            else:
                ret += 'class="{}">'.format(td_class_str)

            if cell['value']:
                if cell['link']:
                    ret += '<a href="{}" target="_blank">{}</a>'.format(
                        cell['link'], cell['value'])

                else:
                    ret += cell['value']

                if cell['unit']:
                    ret += '&nbsp;<span class=" text-muted">{}</span>'.format(
                        cell['unit'])

            else:  # Empty value
                ret += EMPTY_VALUE

            ret += '</td>\n'
    return ret


@register.simple_tag
def render_links_cell(row):
    """
    Return links cell for row as HTML
    :return: String (contains HTML)
    """
    # TODO: Add actual links
    # TODO: Refactor/cleanup, this is a quick screenshot HACK

    return '<td class="bg-light omics-ss-data-cell-links">\n' \
           '  <div class="btn-group omics-ss-data-btn-group">\n' \
           '    <button class="btn btn-secondary dropdown-toggle btn-sm ' \
           '                   omics-ss-data-dropdown"' \
           '                   type="button" data-toggle="dropdown" ' \
           '                   aria-expanded="false">' \
           '                   <i class="fa fa-external-link"></i>' \
           '    </button>' \
           '  </div>\n' \
           '</td>\n'
