from projectroles.plugins import get_backend_api

from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.utils import get_last_material_index


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for germline studies in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_germline'

    #: Title (used in templates)
    title = 'Sample Sheets Germline Study Plugin'

    # Properties defined in SampleSheetStudyPluginPoint ------------------

    #: Configuration name
    config_name = 'bih_germline'

    #: Description string
    description = 'Sample sheets germline study app'

    #: Template for study addition (Study object as "study" in context)
    study_template = 'samplesheets_study_germline/_study.html'

    #: Required permission for accessing the plugin
    permission = None
