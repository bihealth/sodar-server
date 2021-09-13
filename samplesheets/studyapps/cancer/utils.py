""" Utilities for the cancer study app"""

from projectroles.plugins import get_backend_api
from samplesheets.studyapps.utils import FILE_TYPE_SUFFIXES


def get_library_file_path(file_type, library):
    """
    Return iRODS path for the most recent file of type "bam" or "vcf"
    linked to the library.

    :param file_type: String ("bam" or "vcf")
    :param library: GenericMaterial object
    :return: String
    """
    irods_backend = get_backend_api('omics_irods')
    if not irods_backend:
        raise Exception('iRODS Backend not available')

    assay_path = irods_backend.get_path(library.assay)
    query_path = assay_path + '/' + library.name

    # Get paths to relevant files
    file_paths = []
    try:
        obj_list = irods_backend.get_objects(query_path)
        for obj in obj_list['irods_data']:
            if obj['name'].lower().endswith(FILE_TYPE_SUFFIXES[file_type]):
                file_paths.append(obj['path'])
    except FileNotFoundError:
        pass

    if not file_paths:
        return None
    # Return the last file of type by file name
    return sorted(file_paths, key=lambda x: x.split('/')[-1])[-1]
