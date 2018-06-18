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

