"""Utilities for the samplesheets app"""

# Projectroles dependency
from projectroles.plugins import get_backend_api


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
