"""Tests for utility functions in the samplesheets app"""

from test_plus.test import TestCase
from unittest import skipIf

from django.conf import settings

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import GenericMaterial, Process
from ..rendering import SampleSheetTableBuilder
from ..utils import (
    get_alt_names,
    get_sample_dirs,
    get_index_by_header,
    get_last_material_name,
)
from .test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small2.zip'
OBJ_NAME = 'AA_BB_01'
OBJ_ALT_NAMES = ['aa-bb-01', 'aabb01', 'aa_bb_01']

IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


class TestUtilsBase(
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
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        self.tb = SampleSheetTableBuilder()


class TestGetAltNames(TestUtilsBase):
    """Tests for get_alt_names()"""

    def test_get_alt_names(self):
        """Test get_alt_names() with a typical object name"""
        self.assertEqual(get_alt_names(OBJ_NAME), OBJ_ALT_NAMES)

    # TODO: See issue #494
    def test_get_alt_names_dupe(self):
        """Test get_alt_names() resulting in dupes"""
        self.assertEqual(
            get_alt_names(OBJ_ALT_NAMES[1]), [OBJ_ALT_NAMES[1]] * 3
        )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestGetSampleDirs(TestUtilsBase):
    """Tests for get_sample_dirs()"""

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods')

    def test_get_sample_dirs(self):
        """Test get_sample_dirs() with a minimal ISAtab example"""
        expected = [
            self.irods_backend.get_sub_path(self.study),
            self.irods_backend.get_sub_path(self.assay),
        ]

        self.assertEqual(get_sample_dirs(self.investigation), expected)


# TODO: Test compare_inv_replace() (requires special ISAtabs, see #434)


class TestGetIndexByHeader(TestUtilsBase):
    """Tests for get_index_by_header()"""

    def setUp(self):
        super().setUp()
        tb = SampleSheetTableBuilder()
        self.study_tables = tb.build_study_tables(self.study)

    def test_get_sample_name(self):
        """Test getting sample name from study table"""
        self.assertEqual(
            get_index_by_header(
                render_table=self.study_tables['study'],
                header_value='name',
                obj_cls=GenericMaterial,
                item_type='SAMPLE',
            ),
            2,
        )

    def test_get_process_protocol(self):
        """Test getting process protocol from assay"""
        self.assertEqual(
            get_index_by_header(
                render_table=self.study_tables['assays'][
                    str(self.assay.sodar_uuid)
                ],
                header_value='protocol',
                obj_cls=Process,
            ),
            1,
        )

    def test_get_no_cls(self):
        """Test getting index without an object class"""
        self.assertEqual(
            get_index_by_header(
                render_table=self.study_tables['assays'][
                    str(self.assay.sodar_uuid)
                ],
                header_value='replicate',
            ),
            8,
        )

    def test_get_not_found(self):
        """Test getting a non-existent column"""
        self.assertIsNone(
            get_index_by_header(
                render_table=self.study_tables['study'],
                header_value='Oequ5aiL Xe8Ahnuv',
            )
        )


class TestGetLastMaterialName(TestUtilsBase):
    """Tests for get_last_material_name()"""

    def setUp(self):
        super().setUp()
        tb = SampleSheetTableBuilder()
        self.study_tables = tb.build_study_tables(self.study)

    def test_get_study(self):
        """Test getting the last non-DATA material name with a study"""
        study_table = self.study_tables['study']
        # TODO: Assert ordering or use a specific row instead of index
        self.assertIn(
            get_last_material_name(study_table['table_data'][0], study_table),
            ['0815-N1', '0815-T1'],
        )


# TODO: Decent way to test get_sample_libraries()?
