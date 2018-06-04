from samplesheets.plugins import SampleSheetConfigPluginPoint


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

    def get_row_path(self, row):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default directory.
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :return: String with full iRODS path or None
        """
        # TODO: Implement this for bih_germline
        return None
