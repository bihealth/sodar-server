"""Plugin tests for the the germline study app"""

from unittest import skipIf

from django.conf import settings

# from django.forms.models import model_to_dict

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

from samplesheets.tests.test_models import SampleSheetModelMixin
from samplesheets.tests.test_rendering import TestRenderingBase
from samplesheets.plugins import SampleSheetStudyPluginPoint


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.studyapps.germline'
PLUGIN_NAME_CANCER = 'samplesheets_study_cancer'
PLUGIN_TITLE_CANCER = 'Sample Sheets Cancer Study Plugin'

PLUGIN_NAME_GERMLINE = 'samplesheets_study_germline'
PLUGIN_TITLE_GERMLINE = 'Sample Sheets Germline Study Plugin'

# SHEET_DIR = os.path.dirname(__file__) + '/../../tests/isatab/'
# SHEET_PATH = SHEET_DIR + 'i_small2.zip'


IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestGermlinePlugins(SampleSheetModelMixin, TestRenderingBase):
    """Class for testing the germline studyapp plugins"""

    def setUp(self):
        super().setUp()

        # Init admin user
        self.admin_user = self.make_user(settings.PROJECTROLES_DEFAULT_ADMIN)
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True

        # HACK: Set configuration
        self.investigation = self._set_configuration(
            self.investigation, 'bih_germline'
        )

    def test_plugin_retrieval(self):
        """Test retrieving SampleSheetStudyPlugin from the database"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_GERMLINE)
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.get_model().name, PLUGIN_NAME_GERMLINE)
        self.assertEqual(plugin.name, PLUGIN_NAME_GERMLINE)
        self.assertEqual(plugin.get_model().title, PLUGIN_TITLE_GERMLINE)
        self.assertEqual(plugin.title, PLUGIN_TITLE_GERMLINE)

    # TODO: Plugin function tests (requires example germline ISAtab)
