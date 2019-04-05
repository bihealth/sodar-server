"""Utilities for the samplesheets app"""

import re

from django.db.models import QuerySet

# Projectroles dependency
from projectroles.plugins import get_backend_api


ALT_NAMES_COUNT = 3  # Needed for ArrayField hack


def get_alt_names(name):
    """
    Return list of alternative names for an object
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
    Return libraries for samples
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
                last_name = get_last_material_name(row)

                if last_name not in library_names:
                    library_names.append(last_name)

    return GenericMaterial.objects.filter(
        study=study, name__in=library_names
    ).order_by('name')


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
