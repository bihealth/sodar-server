"""UI tests for the samplesheets app"""

# from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_ui import TestUIBase

from .test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestProjectSheetsView(SampleSheetIOMixin, TestUIBase):
    """Tests for the project sheets view UI"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
