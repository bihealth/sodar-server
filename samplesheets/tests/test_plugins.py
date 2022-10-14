"""Tests for plugins in the samplesheets app"""

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.plugins import get_irods_content
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
)


# Local constants
SHEET_PATH_SMALL2 = SHEET_DIR + 'i_small2.zip'


class TestPluginsBase(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Class for samplesheets utils tests"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.assignment_owner = self._make_assignment(
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
        self.assertEqual(
            len(
                ret_data['tables']['assays'][str(self.assay.sodar_uuid)][
                    'irods_paths'
                ]
            ),
            12,
        )
        self.assertEqual(
            len(
                ret_data['tables']['assays'][str(self.assay.sodar_uuid)][
                    'shortcuts'
                ]
            ),
            4,
        )
