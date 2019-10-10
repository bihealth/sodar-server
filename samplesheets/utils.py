"""Utilities for the samplesheets app"""

from openpyxl import Workbook
from openpyxl.workbook.child import INVALID_TITLE_REGEX
import re

from django.db.models import QuerySet
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api

ALT_NAMES_COUNT = 3  # Needed for ArrayField hack


def get_alt_names(name):
    """
    Return list of alternative names for an object.

    :param name: Original name/ID (string)
    :return: List
    """
    name = name.lower()  # Convert all versions lowercase for indexed search

    return [name.replace('_', '-'), re.sub(r'[^a-zA-Z0-9]', '', name), name]


def get_sample_dirs(investigation):
    """
    Return study and assay directories without parent dirs for the sample data
    directory structure.

    :param investigation: Investigation object
    :return: List
    """
    ret = []
    irods_backend = get_backend_api('omics_irods')

    if irods_backend:
        for study in investigation.studies.all():
            ret.append(irods_backend.get_sub_path(study))

            for assay in study.assays.all():
                ret.append(irods_backend.get_sub_path(assay))

    return ret


def compare_inv_replace(inv1, inv2):
    """
    Compare investigations for critical differences for replacing.

    :param inv1: Investigation object
    :param inv2: Investigation object
    :raise: ValueError if a problem is detected
    """
    try:
        for study1 in inv1.studies.all():
            study2 = inv2.studies.get(file_name=study1.file_name)

            for assay1 in study1.assays.all():
                study2.assays.get(file_name=assay1.file_name)

    except Exception:
        raise ValueError(
            'iRODS directories exist but studies and assays '
            'do not match: unable to replace investigation'
        )


def get_index_by_header(
    render_table, header_value, obj_cls=None, item_type=None
):
    """
    Return the column index based on field header value.

    :param render_table: Study/assay render table
    :param header_value: Header value
    :param obj_cls: Class of Dango model object represented by header (optional)
    :param item_type: Type of item in case of GenericMaterial (optional)
    :return: Int or None if not found
    """
    header_value = header_value.lower()
    obj_cls = obj_cls.__name__ if obj_cls else None

    for i, h in enumerate(render_table['field_header']):
        found = True

        if h['value'].lower() != header_value:
            found = False

        if found and obj_cls and h['obj_cls'] != obj_cls:
            found = False

        if found and item_type and h['item_type'] != item_type:
            found = False

        if found:
            return i

    return None


def get_last_material_name(row, table):
    """Return name of the last non-DATA material in a table row"""
    name = None

    for i in range(len(row)):
        cell = row[i]
        header = table['field_header'][i]
        if (
            header['obj_cls'] == 'GenericMaterial'
            and header['item_type'] != 'DATA'
            and header['value'].lower() == 'name'
            and cell['value']
        ):
            name = cell['value']

    return name


def get_sample_libraries(samples, study_tables):
    """
    Return libraries for samples.

    :param samples: Sample object or a list of Sample objects within a study
    :param study_tables: Rendered study tables
    :return: GenericMaterial queryset
    """
    from samplesheets.models import GenericMaterial

    if type(samples) not in [list, QuerySet]:
        samples = [samples]

    sample_names = [s.name for s in samples]
    study = samples[0].study
    library_names = []

    for k, assay_table in study_tables['assays'].items():
        sample_idx = get_index_by_header(
            assay_table, 'name', obj_cls=GenericMaterial, item_type='SAMPLE'
        )

        for row in assay_table['table_data']:
            if row[sample_idx]['value'] in sample_names:
                last_name = get_last_material_name(row, assay_table)

                if last_name not in library_names:
                    library_names.append(last_name)

    return GenericMaterial.objects.filter(
        study=study, name__in=library_names
    ).order_by('name')


def get_study_libraries(study, study_tables):
    """
    Return sample libraries for an entire study.

    :param study: Study object
    :param study_tables: Rendered study tables from samplesheets.rendering
    :return: List of GenericMaterial objects
    """
    ret = []

    for source in study.get_sources():
        for sample in source.get_samples():
            ret += get_sample_libraries(sample, study_tables)

    return ret


def get_isa_field_name(field):
    """
    Return the name of an ISA field. In case of an ontology reference, returns
    field['name'].

    :param field: Field of an ISA Django model
    :return: String
    """
    if type(field) == dict:
        return field['name']

    return field


def get_sheets_url(obj):
    """
    Return URL for sample sheets compatible with the new Vue.js framework.

    :param obj: An object of type Project, Study or Assay (or any other model
                implementing get_project()
    :return: String
    """
    project = obj if isinstance(obj, Project) else obj.get_project()
    url = reverse(
        'samplesheets:project_sheets', kwargs={'project': project.sodar_uuid}
    )

    # NOTE: Importing the model fails because of circular dependency
    if obj.__class__.__name__ == 'Study':
        url += '#/study/' + str(obj.sodar_uuid)

    elif obj.__class__.__name__ == 'Assay':
        url += '#/assay' + str(obj.sodar_uuid)

    return url


def get_comment(obj, key):
    """
    Return comment value for object based on key or None if not found.
    TODO: Remove once reimporting sample sheets (#629, #631)

    :param obj: Object parsed from ISAtab
    :param key: Key for comment
    :return:
    """
    if (
        not hasattr(obj, 'comments')
        or not obj.comments
        or key not in obj.comments
    ):
        return None

    if isinstance(obj.comments[key], dict):
        return obj.comments[key]['value']

    return obj.comments[key]


def get_comments(obj):
    """
    Return comments for an object or None if they don't exist.
    TODO: Remove once reimporting sample sheets (#629, #631)

    :param obj: Object parsed from ISAtab
    :return:
    """
    if not hasattr(obj, 'comments') or not obj.comments:
        return None

    return {k: get_comment(obj, k) for k in obj.comments.keys()}


def write_excel_table(table, output, display_name):
    """
    Write an Excel 2010 file (.xlsx) from a rendered study/assay table
    :param table:
    :param output:
    :return:
    """

    def _get_val(c_val):
        if isinstance(c_val, str):
            return c_val
        elif isinstance(c_val, dict):
            return c_val['name']
        elif isinstance(c_val, list):
            return ';'.join([_get_val(x) for x in c_val])
        return ''

    # Build Excel file
    wb = Workbook()
    ws = wb.active
    ws.title = re.sub(INVALID_TITLE_REGEX, '_', display_name)
    top_header_row = []

    for c in table['top_header']:
        top_header_row.append(c['value'])

        if c['colspan'] > 1:
            top_header_row += [''] * (c['colspan'] - 1)

    ws.append(top_header_row)
    ws.append([c['value'] for c in table['field_header']])

    for row in table['table_data']:
        ws.append([_get_val(c['value']) for c in row])

    # Resize columns (plus a little extra for padding)
    # NOTE: There is a "bestFit" attribute but it doesn't really work at all
    for col_cells in ws.columns:
        length = max(len(c.value) if c.value else 0 for c in col_cells) + 2
        ws.column_dimensions[col_cells[0].column_letter].width = length

    wb.save(output)
