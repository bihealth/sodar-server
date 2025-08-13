"""Utilities for the cancer study app"""

import os

from samplesheets.studyapps.utils import (
    get_igv_omit_list,
    check_igv_file_suffix,
    check_igv_file_path,
)
from samplesheets.utils import get_latest_file_path


def get_library_file_path(assay, library_name, file_type, irods_backend, irods):
    """
    Return iRODS path for the most recent file of type "bam" or "vcf"
    linked to the library. CRAM files are included in "bam" searches.

    :param assay: Assay object
    :param library_name: Library name (string)
    :param file_type: String ("bam" or "vcf", "bam" is also used for CRAM)
    :param irods_backend: IrodsAPI object
    :param irods: IRODSSession object
    :return: String
    """
    assay_path = irods_backend.get_path(assay)
    query_path = os.path.join(assay_path, library_name)
    file_paths = []
    omit_list = get_igv_omit_list(assay.get_project(), file_type)
    try:
        obj_list = irods_backend.get_objects(irods, query_path)
        for obj in obj_list:
            if check_igv_file_suffix(
                obj['name'].lower(), file_type
            ) and check_igv_file_path(obj['path'], omit_list):
                file_paths.append(obj['path'])
    except Exception:
        pass
    if not file_paths:
        return None
    # Return the last file of type by file name
    return get_latest_file_path(file_paths)
