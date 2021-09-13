""" Utilities for the germline study app"""

# Projectroles dependency
from projectroles.plugins import get_backend_api

from samplesheets.models import GenericMaterial
from samplesheets.utils import get_index_by_header
from samplesheets.studyapps.utils import FILE_TYPE_SUFFIXES


def get_pedigree_file_path(file_type, source, study_tables):
    """
    Return iRODS path for the most recent file of type "bam" or "vcf"
    linked to the source.

    :param file_type: String ("bam" or "vcf")
    :param source: GenericMaterial of type SOURCE
    :param study_tables: Render study tables
    :return: String
    """
    irods_backend = get_backend_api('omics_irods')
    if not irods_backend:
        raise Exception('iRODS Backend not available')

    query_paths = []
    sample_names = []

    def _get_val_by_index(row, idx):
        return row[idx]['value'] if idx else None

    for assay in source.study.assays.all():
        assay_table = study_tables['assays'][str(assay.sodar_uuid)]
        assay_plugin = assay.get_plugin()
        assay_path = irods_backend.get_path(assay)
        source_fam = None
        if 'Family' in source.characteristics:
            source_fam = source.characteristics['Family']['value']
        # Get family index
        fam_idx = get_index_by_header(assay_table, 'family')
        # Get sample index
        sample_idx = get_index_by_header(
            assay_table, 'name', obj_cls=GenericMaterial, item_type='SAMPLE'
        )

        for row in assay_table['table_data']:
            row_name = row[0]['value']
            row_fam = _get_val_by_index(row, fam_idx)

            # For VCF files, also search through other samples in family
            vcf_search = False
            if file_type == 'vcf' and source_fam and row_fam == source_fam:
                vcf_search = True

            # Add sample names for source
            if row_name == source.name or vcf_search:
                sn = row[sample_idx]['value']
                if sn not in sample_names:
                    sample_names.append(sn)

            # Get query path from assay_plugin
            if assay_plugin:
                if row_name == source.name or vcf_search:
                    path = assay_plugin.get_row_path(
                        row, assay_table, assay, assay_path
                    )
                    if path not in query_paths:
                        query_paths.append(path)

        # If not assay_plugin, just search from assay path
        if not assay_plugin:
            path = assay_path
            if path not in query_paths:
                query_paths.append(path)

    # Get paths to relevant files
    file_paths = []

    for query_path in query_paths:
        try:
            obj_list = irods_backend.get_objects(query_path)
            for obj in obj_list['irods_data']:
                # NOTE: We non longer expect the SAMPLE name in filenames
                if obj['name'].lower().endswith(FILE_TYPE_SUFFIXES[file_type]):
                    file_paths.append(obj['path'])
        except FileNotFoundError:
            pass

    if not file_paths:
        return None
    # Return the last file of type by file name
    return sorted(file_paths, key=lambda x: x.split('/')[-1])[-1]


def get_families(study):
    """
    Return list of families.

    :param study: Study object
    :return: List of strings
    """
    sources = GenericMaterial.objects.filter(study=study, item_type='SOURCE')
    ret = sorted(
        list(
            set(
                [
                    s.characteristics['Family']['value']
                    for s in sources
                    if (
                        'Family' in s.characteristics
                        and 'value' in s.characteristics['Family']
                        and s.characteristics['Family']['value']
                    )
                ]
            )
        )
    )

    if not ret or not ret[0]:
        ret = (
            GenericMaterial.objects.filter(study=study, item_type='SOURCE')
            .values_list('name', flat=True)
            .order_by('name')
        )
    return ret


def get_family_sources(study, family_id):
    """
    Return sources for a family in a study.

    :param study: Study object
    :param family_id: String
    :return: QuerySet of GenericMaterial objects
    """
    ret = GenericMaterial.objects.filter(
        study=study,
        item_type='SOURCE',
        characteristics__Family__value=family_id,
    )
    if ret.count() == 0:
        ret = GenericMaterial.objects.filter(
            study=study, item_type='SOURCE', name=family_id
        )
    return ret
