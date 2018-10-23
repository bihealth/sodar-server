import random
import re
import string

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.html import escape

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from ..models import Investigation, Study, Assay, GenericMaterial, \
    GENERIC_MATERIAL_TYPES
from ..plugins import find_study_plugin as _find_study_plugin, \
    find_assay_plugin as _find_assay_plugin
from ..utils import get_sample_libraries as _get_sample_libraries


irods_backend = get_backend_api('omics_irods')
num_re = re.compile('^(?=.)([+-]?([0-9]*)(\.([0-9]+))?)$')

register = template.Library()


# Omics constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants

EMPTY_VALUE = '-'

# TODO: Add a more dynamic way to render special fields (e.g. a plugin)
SPECIAL_FIELDS = [
    'external links',
    'primary contact',
    'provider contact',
    'requestor contact',
    'center contact']

EXTERNAL_LINK_LABELS = settings.SHEETS_EXTERNAL_LINK_LABELS


# General ----------------------------------------------------------------------


@register.simple_tag
def get_investigation(project):
    """Return Investigation for a project"""
    try:
        return Investigation.objects.get(project=project)

    except Investigation.DoesNotExist:
        return None


@register.simple_tag
def get_study_plugin(study):
    """Return study app plugin or None if not found"""
    return _find_study_plugin(study.investigation.get_configuration())


@register.simple_tag
def get_assay_plugin(assay):
    """Return assay app plugin or None if not found"""
    return _find_assay_plugin(assay.measurement_type, assay.technology_type)


@register.simple_tag
def get_table_id(parent):
    """
    Return table id for DataTable reference
    :param parent: Study or Assay object
    :return: string
    """
    return 'omics-ss-data-table-{}-{}'.format(
        parent.__class__.__name__.lower(), parent.sodar_uuid)


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
def get_search_item_type(item):
    """Return printable version of search item type"""
    if item['type'] == 'file':
        return 'Data File'

    return GENERIC_MATERIAL_TYPES[item['type']]


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


# TODO: This should be in germline app template tags
@register.simple_tag
def get_families(study):
    """
    Return list of families
    :param study: Study object
    :return: List of strings
    """
    sources = GenericMaterial.objects.filter(study=study, item_type='SOURCE')
    ret = sorted(list(set([
        s.characteristics['Family']['value'] for s in sources if (
            'Family' in s.characteristics and
            'value' in s.characteristics['Family'] and
            s.characteristics['Family']['value'])])))

    if not ret or not ret[0]:
        ret = GenericMaterial.objects.filter(
            study=study, item_type='SOURCE').values_list(
            'name', flat=True).order_by('name')

    return ret


# TODO: This should be in germline app template tags
@register.simple_tag
def get_family_sources(study, family_id):
    """
    Return sources for a family in a study
    :param study: Study object
    :param family_id: String
    :return: QuerySet of GenericMaterial objects
    """
    ret = GenericMaterial.objects.filter(
        study=study,
        item_type='SOURCE',
        characteristics__Family__value=family_id)

    if ret.count() == 0:
        ret = GenericMaterial.objects.filter(
            study=study,
            item_type='SOURCE',
            name=family_id)

    return ret


@register.simple_tag
def get_study_sources(study):
    """
    Return list of samples within this study
    :param study: Study object
    :return: GenericMaterial objects
    """
    return GenericMaterial.objects.filter(
        study=study, item_type='SOURCE').order_by('name')


@register.simple_tag
def get_sample_libraries(sample, study_table):
    """Return libraries per sample"""
    return _get_sample_libraries(sample, study_table)


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
                   '>{}</th>\n'.format(
                    section['colour'],
                    final_colspan,     # Actual colspan
                    final_colspan,     # Original colspan
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
            ret += '<th class="omics-ss-data-header {}">{}</th>\n'.format(
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
def render_cells(row, table, assay=None, assay_plugin=None):
    """
    Render cells of a table row
    :param row: Row of cells (list)
    :param table: The full table (dict)
    :param assay: Assay object (optional)
    :param assay_plugin: SampleSheetAssayPlugin object (optional)
    :return: String (contains HTML)
    """
    ret = ''

    # Update row through the assay plugin
    if assay and assay_plugin:
        row = assay_plugin.update_row(row, table, assay)

    # Iterate through row, render only if there is data in column
    for i in range(0, len(row)):
        cell = row[i]

        if table['col_values'][i]:
            td_class_str = 'omics-ss-data-cell ' + ' '.join(cell['classes'])

            ret += '<td '

            # Right aligning
            if (cell['field_name'] != 'name' and cell['value'] and
                    num_re.match(cell['value'])):
                td_class_str += ' text-right'

            # Add extra attrs if present
            if cell['attrs']:
                for k, v in cell['attrs'].items():
                    ret += '{}="{}" '.format(k, v)

            ret += 'class="{}">'.format(td_class_str)

            # Add cell value
            if cell['value']:
                ret += '<div class="omics-overflow-container ' \
                       'omics-overflow-hover"'

                # Tooltip
                if cell['tooltip']:
                    ret += ' title="{}" data-toggle="tooltip" ' \
                           'data-placement="top"'.format(cell['tooltip'])

                ret += '>'

                # Special cases
                if cell['field_name'] in SPECIAL_FIELDS:
                    ret += render_special_field(cell)

                else:
                    value = escape(cell['value'])

                    # Ontology link
                    if cell['link']:
                        ret += '<a href="{}" {}>{}</a>'.format(
                            cell['link'],
                            'target="_blank"' if not cell['link_file'] else '',
                            value)

                    else:
                        ret += value

                    # Unit if present
                    if cell['unit']:
                        ret += '&nbsp;<span class="text-muted">' \
                               '{}</span>'.format(
                                cell['unit'])

                ret += '</div>'

            else:  # Empty value
                ret += EMPTY_VALUE

            ret += '</td>\n'
    return ret


def render_special_field(cell):
    """
    Render the value of a special cell
    :param cell: Dict
    :return: String (contains HTML)
    """
    field_name = cell['field_name'].lower()
    ret = ''

    # External links
    if field_name == 'external links':
        for v in cell['value'].split(';'):
            link = v.split(':')[0]
            id_val = v.split(':')[1]

            if link in EXTERNAL_LINK_LABELS:
                ret += '<span class="badge-group" data-toggle="tooltip" ' \
                       'data-placement="top" title="{}">' \
                       '<span class="badge badge-secondary">ID</span>' \
                       '<span class="badge badge-info">{}</span></span>'.format(
                        EXTERNAL_LINK_LABELS[link], id_val)

    # Contact field
    elif field_name in [
            'primary contact', 'provider contact', 'requestor contact',
            'center contact']:
        email_result = re.findall(r'<(.+?)>', cell['value'])

        if len(email_result) > 0:
            ret += '<a href="mailto:{}">{}</a>'.format(
                email_result[0], cell['value'].split('<')[0].strip())

        else:
            ret += cell['value']

    return ret if ret != '' else EMPTY_VALUE


@register.simple_tag
def get_irods_row_path(assay, assay_table, row, assay_plugin):
    """
    Return iRODS path for an assay row. If the configuration is not recognized,
    Returns a link for the whole assay
    :param assay: Assay object
    :param assay_table: Assay table from SampleSheetTableBuilder
    :param row: Row from SampleSheetTableBuilder
    :param assay_plugin: SampleSheetAssayPlugin object
    :return: String
    """
    if assay_plugin:
        path = assay_plugin.get_row_path(row, assay_table, assay)

        if path:
            return path

    # If path was not returned by plugin, get detaulf path
    if irods_backend:
        return irods_backend.get_path(assay)

    return None


@register.simple_tag
def get_irods_path(obj, sub_path=None):
    """
    Return iRODS path for an object or None if not found
    :param obj: Study, Assay etc. type object
    :param sub_path: If defined, add a sub path below object
    :return: String or none
    """
    if irods_backend:
        path = irods_backend.get_path(obj)

        if sub_path:
            path += '/' + sub_path

        return path

    return None


@register.simple_tag
def get_assay_list_url(assay, path=None):
    """
    Return iRODS file list querying URL for assay
    :param assay: Assay object
    :param path: iRODS path: if None, default path for assay will be used
    :return: String
    """
    if not irods_backend:
        return None

    if not path:
        path = irods_backend.get_path(assay)

    return reverse(
        'irodsbackend:list',
        kwargs={
            'project': assay.get_project().sodar_uuid,
            'path': path,
            'md5': 0})


@register.simple_tag
def get_icon(obj):
    """
    Get Study or Assay icon
    :param obj: Study or Assay object
    :return: String (contains HTML)
    """
    if type(obj) == Study:
        return '<i class="fa fa-fw fa-list-alt text-info"></i>'

    elif type(obj) == Assay:
        return '<i class="fa fa-fw fa-table text-danger"></i>'
