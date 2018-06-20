from projectroles.plugins import get_backend_api

from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.utils import get_last_material_index


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for nucleotide sequencing assays in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_nucleotide_sequencing'

    #: Title
    title = 'Sample Sheets Nucleotide Sequencing Assay Plugin'

    # Properties defined in SampleSheetAssayPluginPoint ------------------

    #: Identifying assay fields (used to identify plugin by assay)
    measurement_type = 'genome sequencing'
    technology_type = 'nucleotide sequencing'

    #: Description string
    description = 'Sample sheets nucleotide sequencing assay app'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = None

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    def get_row_path(self, assay, table, row):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default directory.
        :param assay: Assay object
        :param table: List of lists (table returned by SampleSheetTableBuilder)
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :return: String with full iRODS path or None
        """
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return None

        # Get index of last material's name column
        idx = get_last_material_index(table)
        material_name = row[idx]['value']
        return irods_backend.get_path(assay) + '/' + material_name
