from projectroles.plugins import get_backend_api

from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.utils import get_last_material_index


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for protein expression profiling / mass spectrometry in sample
    sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_pep_ms'

    #: Title
    title = 'Sample Sheets Protein Expression Profiling / Mass Spectrometry ' \
            'Assay Plugin'

    # Properties defined in SampleSheetAssayPluginPoint ------------------

    #: Identifying assay fields (used to identify plugin by assay)
    measurement_type = 'protein expression profiling'
    technology_type = 'mass spectrometry'

    #: Description string
    description = 'Sample sheets protein expression profiling / mass ' \
                  'spectrometry assay plugin'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = 'samplesheets_assay_pep_ms/_assay.html'

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

        # TODO: Alternatives for RawData?
        return irods_backend.get_path(assay) + '/RawData'

    def get_file_path(self, assay, table, row, file_name):
        """Return iRODS path for a data file or None if not available.
        :param assay: Assay object
        :param table: List of lists (table returned by SampleSheetTableBuilder)
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param file_name: File name
        :return: String with full iRODS path or None
        """
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return None

        # Raw file
        if file_name.split('.')[-1] == 'raw':
            return irods_backend.get_path(assay) + '/RawData/' + file_name

