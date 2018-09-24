from samplesheets.plugins import SampleSheetStudyPluginPoint


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for cancer studies in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_cancer'

    #: Title (used in templates)
    title = 'Sample Sheets Cancer Study Plugin'

    # Properties defined in SampleSheetStudyPluginPoint ------------------

    #: Configuration name
    config_name = 'bih_cancer'

    #: Description string
    description = 'Sample sheets cancer study app'

    #: Template for study addition (Study object as "study" in context)
    study_template = 'samplesheets_study_cancer/_study.html'

    #: Required permission for accessing the plugin
    permission = None
