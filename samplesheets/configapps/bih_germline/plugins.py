from projectroles.plugins import get_backend_api

from samplesheets.plugins import SampleSheetConfigPluginPoint
from samplesheets.utils import get_last_material_index


class SampleSheetConfigPlugin(SampleSheetConfigPluginPoint):
    """Plugin for the bih_germline sample sheet configuration"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_config_bih_germline'

    #: Title (used in templates)
    title = 'Germline Sample Sheet Configuration'

    # Properties defined in ProjectAppPluginPoint -----------------------

    #: Configuration name
    config_name = 'bih_germline'

    #: Description string
    description = 'TODO: Write a description for your config plugin'

    #: Template for study addition (Study object as "study" in context)
    study_template = 'samplesheets_config_bih_germline/_study.html'

    #: Required permission for accessing the plugin
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
