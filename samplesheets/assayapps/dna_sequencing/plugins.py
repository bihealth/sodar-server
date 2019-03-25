"""Assay app plugin for samplesheets"""


from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.utils import get_last_material_name


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
            'technology_type': 'nucleotide sequencing',
        },
        {
            'measurement_type': 'exome sequencing',
            'technology_type': 'nucleotide sequencing',
        },
        {
            'measurement_type': 'transcription profiling',
            'technology_type': 'nucleotide sequencing',
        },
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

    def get_row_path(self, row, table, assay, assay_path):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default directory.
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :param assay_path: Root path for assay
        :return: String with full iRODS path or None
        """
        # Get the name of the last material
        last_material_name = get_last_material_name(row, table)

        if last_material_name:
            return assay_path + '/' + last_material_name

        return None

    # TODO: Rework for vue.js viewer
    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row
        :param row: Original row (list of dicts)
        :param table: Full table (list of lists)
        :param assay: Assay object
        :return: List of dicts
        """
        return row
