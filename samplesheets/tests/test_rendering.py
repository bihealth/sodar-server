"""Tests for samplesheets.rendering"""

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.models import GenericMaterial
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2.zip'


class TestRenderingBase(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Base class for rendering tests"""

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

        self.tb = SampleSheetTableBuilder()


class TestTableBuilder(TestRenderingBase):
    """Tests for SampleSheetTableBuilder"""

    def test_build_study(self):
        """Test building tables for a study"""

        def assert_row_length(table):
            """Assert uniform row length"""
            row_lengths = set([len(r) for r in table['table_data']])
            self.assertEqual(len(row_lengths), 1)

        def get_column_set(table, pos):
            """Return set of distinct values for a column at pos"""
            return set([r[pos]['value'] for r in table['table_data']])

        tables = self.tb.build_study_tables(self.study)
        self.assertIsNotNone(tables)

        # Assert tables
        self.assertIn('study', tables)
        self.assertIn('assays', tables)
        self.assertEqual(len(tables['assays']), self.study.assays.count())

        # Test study table
        assert_row_length(tables['study'])

        # Sources
        table_sources = get_column_set(tables['study'], 0)
        db_sources = set(
            GenericMaterial.objects.filter(
                study=self.study, item_type='SOURCE'
            ).values_list('name', flat=True)
        )
        self.assertEqual(table_sources, db_sources)

        # Samples
        sample_pos = 0

        for c in tables['study']['top_header']:
            if c['value'] == 'Sample':
                break

            else:
                sample_pos += c['colspan']

        table_samples = get_column_set(tables['study'], sample_pos)
        db_samples = set(
            GenericMaterial.objects.filter(
                study=self.study, item_type='SAMPLE'
            ).values_list('name', flat=True)
        )
        self.assertEqual(table_samples, db_samples)

        # Test assay tables
        for k, assay_table in tables['assays'].items():
            assert_row_length(assay_table)

    def test_get_headers(self):
        """Test get_headers()"""
        h = self.tb.get_headers(self.investigation)
        self.assertIsNotNone(h)
        self.assertEqual(len(h['studies'][0]['headers']), 15)
        self.assertEqual(len(h['studies'][0]['assays'][0]), 8)

    def test_get_headers_compare_row(self):
        """Test comparing get_headers() results for inserted rows"""
        investigation2 = self._import_isa_from_file(
            SHEET_PATH_INSERTED, self.project
        )
        h1 = self.tb.get_headers(self.investigation)
        h2 = self.tb.get_headers(investigation2)

        self.assertIsNotNone(h2)
        self.assertEqual(h1, h2)

    def test_get_headers_compare_col(self):
        """Test comparing get_headers() for different columns (should fail)"""
        investigation2 = self._import_isa_from_file(
            SHEET_PATH_ALT, self.project
        )
        h1 = self.tb.get_headers(self.investigation)
        h2 = self.tb.get_headers(investigation2)

        self.assertIsNotNone(h2)
        self.assertNotEqual(h1, h2)
