from projectroles.plugins import get_backend_api

from samplesheets.models import GenericMaterial
from samplesheets.plugins import SampleSheetAssayPluginPoint


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for DNA sequencing assays in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_dna_sequencing'

    #: Title
    title = 'DNA Sequencing Assay Plugin'

    # Properties defined in SampleSheetAssayPluginPoint ------------------

    #: Identifying assay fields (used to identify plugin by assay)
    assay_fields = [
        {
            'measurement_type': 'genome sequencing',
            'technology_type': 'nucleotide sequencing'
        },
        {
            'measurement_type': 'exome sequencing',
            'technology_type': 'nucleotide sequencing'
        }
    ]

    #: Description string
    description = 'Sample sheets DNA sequencing assay app'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = None

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    display_row_links = True

    def get_row_path(self, row, table, assay):
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

        # Get the name of the last material
        # TODO: Replace with samplesheets.utils.get_last_material_name()
        last_material_name = None

        for cell in row:
            if (cell['obj_cls'] == GenericMaterial and
                    cell['item_type'] != 'DATA' and
                    cell['field_name'] == 'name' and
                    cell['value']):
                last_material_name = cell['value']

        if last_material_name:
            return irods_backend.get_path(assay) + '/' + last_material_name

        return None

    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row
        :param row: Original row (list of dicts)
        :param table: Full table (list of lists)
        :param assay: Assay object
        :return: List of dicts
        """
        return row
