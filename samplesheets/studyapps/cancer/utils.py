""" Utilities for the cancer study app"""

import os

from samplesheets.studyapps.utils import FILE_TYPE_SUFFIXES
from samplesheets.utils import get_latest_file_path


def get_library_file_path(assay, library_name, file_type, irods_backend, irods):
    """
    Return iRODS path for the most recent file of type "bam" or "vcf"
    linked to the library.

    :param assay: Assay object
    :param library_name: Library name (string)
    :param file_type: String ("bam" or "vcf")
    :param irods_backend: IrodsAPI object
    :param irods: IRODSSession object
    :return: String
    """
    assay_path = irods_backend.get_path(assay)
    query_path = os.path.join(assay_path, library_name)
    file_paths = []
    try:
        obj_list = irods_backend.get_objects(irods, query_path)
        for obj in obj_list['irods_data']:
            if obj['name'].lower().endswith(FILE_TYPE_SUFFIXES[file_type]):
                file_paths.append(obj['path'])
    except Exception:
        pass
    if not file_paths:
        return None
    # Return the last file of type by file name
    return get_latest_file_path(file_paths)
