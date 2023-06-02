"""Tests for plugins in the samplesheets app"""

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

from samplesheets.plugins import get_irods_content
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
)


# Local constants
SHEET_PATH_SMALL2 = SHEET_DIR + 'i_small2.zip'


class TestPluginsBase(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Class for samplesheets utils tests"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Make owner user
        self.user_owner = self.make_user('owner')
        # Init project and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.assignment_owner = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )

        # Import investigation
        self.investigation = self.import_isa_from_file(
            SHEET_PATH_SMALL2, self.project
        )
        self.investigation.irods_status = True
        self.investigation.save()
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        self.tb = SampleSheetTableBuilder()
        self.ret_data = dict(
            study={'display_name': self.study.get_display_name()}
        )
        self.ret_data['tables'] = self.tb.build_study_tables(self.study)
        self.irods_backend = get_backend_api('omics_irods')


class TestGetIrodsContent(TestPluginsBase):
    """Tests for get_irods_content()"""

    def test_get_irods_content(self):
        """Test get_irods_content()"""
        ret_data = get_irods_content(
            self.investigation, self.study, self.irods_backend, self.ret_data
        )
        assay_data = ret_data['tables']['assays'][str(self.assay.sodar_uuid)]
        self.assertEqual(len(assay_data['irods_paths']), 12)
        self.assertEqual(len(assay_data['shortcuts']), 4)
