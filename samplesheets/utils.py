"""Utilities for the samplesheets app"""

# Projectroles dependency
from projectroles.plugins import get_backend_api

from .models import Investigation


def get_sample_dirs(investigation):
    """
    Return study and assay directories without parent dirs for the sample data
    directory structure.
    :param investigation: Investigation object
    :return: List
    """
    ret = []
    irods_backend = get_backend_api('omics_irods')

    # TODO: Raise exception if backend is not found?
    if irods_backend:
        for study in investigation.studies.all():
            ret.append(irods_backend.get_subdir(study))

            for assay in study.assays.all():
                ret.append(irods_backend.get_subdir(assay))

    return ret


def compare_inv_replace(inv1, inv2):
    """
    Compare investigations for critical differences for replacing
    :param inv1: Investigation object
    :param inv2: Investigation object
    :raise: ValueError if a problem is detected
    """
    try:
        for study1 in inv1.studies.all():
            study2 = inv2.studies.get(file_name=study1.file_name)

            for assay1 in study1.assays.all():
                assay2 = study2.assays.get(file_name=assay1.file_name)

    except Exception as ex:
        raise ValueError(
            'iRODS directories exist but studies and assays '
            'do not match: unable to replace investigation')


def get_index_by_header(
        render_table, header_value, obj_cls=None, item_type=None):
    """
    Return the column index based on field header value
    :param render_table: Study/assay render table
    :param header_value: Header value
    :param obj_cls: Class of Dango model object represented by header (optional)
    :param item_type: Type of item in case of GenericMaterial (optional)
    :return: Int or None if not found
    """

    # TODO: Smarter way to iterate and find with variable amount of params?
    # TODO: My flu brain can't get around this..
    for i, h in enumerate(render_table['field_header']):
        found = True

        if h['value'].lower() != header_value.lower():
            found = False

        if found and obj_cls and h['obj_cls'] != obj_cls:
            found = False

        if found and item_type and h['item_type'] != item_type:
            found = False

        if found:
            return i

    return None


def get_last_material_index(render_table):
    """
    Return the column index for the last material in a rendered ISA table
    :param render_table: Table returned by SampleSheetTableBuilder
    :return: int
    """
    idx = 0
    row = render_table['table_data'][0]

    for i in range(0, len(row)):
        cell = row[i]

        if cell['field_name'] == 'name' and cell['obj_type'] == 'MATERIAL':
            idx = i

    return idx


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
