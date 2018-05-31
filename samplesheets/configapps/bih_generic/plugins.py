from samplesheets.plugins import SampleSheetConfigPluginPoint


class SampleSheetConfigPlugin(SampleSheetConfigPluginPoint):
    """Plugin for the bih_generic sample sheet configuration"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_config_bih_generic'

    #: Title (used in templates)
    title = 'Generic Sample Sheet Configuration'

    # Properties defined in ProjectAppPluginPoint -----------------------

    #: Configuration name
    config_name = 'bih_generic'

    #: Description string
    description = 'TODO: Write a description for your config plugin'

    #: Template for study addition (Study object as "study" in context)
    study_template = '_study.html'

    #: Required permission for accessing the plugin
    permission = None
