"""Tests for samplesheets.rendering"""

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import GenericMaterial
from ..rendering import SampleSheetTableBuilder
from .test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small2.zip'


class TestRenderingBase(
        ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase):
    """Base class for rendering tests"""
    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None)
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER'])[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner)

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
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
        table_sources = get_column_set(tables['study'], 1)
        db_sources = set(GenericMaterial.objects.filter(
            study=self.study, item_type='SOURCE').values_list(
            'name', flat=True))
        self.assertEqual(table_sources, db_sources)

        # Samples
        sample_pos = 0

        for c in tables['study']['top_header']:
            if c['value'] == 'Sample':
                break

            else:
                sample_pos += c['colspan']

        table_samples = get_column_set(tables['study'], sample_pos)
        db_samples = set(GenericMaterial.objects.filter(
            study=self.study, item_type='SAMPLE').values_list(
            'name', flat=True))
        self.assertEqual(table_samples, db_samples)

        # Test assay tables
        for k, assay_table in tables['assays'].items():
            assert_row_length(assay_table)


# TODO: Move to test_templatetags


'''
class TestHTMLRenderer(TestRenderingBase):
    """Tests for SampleSheetHTMLRenderer"""

    def setUp(self):
        super().setUp()
        self.tables = self.tb.build_study_tables(self.study)

    def test_render_top_header(self):
        """Test render_top_header()"""

        def check_top_headers(table):
            for section in table['top_header']:
                html = SampleSheetHTMLRenderer.render_top_header(section)
                bs = BeautifulSoup(html, 'html.parser')
                self.assertEqual(bs.getText().strip(), section['value'])
                self.assertEqual(
                    int(bs.find('th')['colspan']), section['colspan'])
                self.assertEqual(
                    int(bs.find('th')['original-colspan']), section['colspan'])

        check_top_headers(self.tables['study'])

        for assay_table in self.tables['assays'].values():
            check_top_headers(assay_table)

    def test_render_header(self):
        """Test render_header()"""

        def check_headers(table):
            for header in table['field_header']:
                html = SampleSheetHTMLRenderer.render_header(header)
                bs = BeautifulSoup(html, 'html.parser')
                self.assertEqual(bs.getText().strip(), header['value'])

        check_headers(self.tables['study'])

        for assay_table in self.tables['assays'].values():
            check_headers(assay_table)

    def test_render_cell(self):
        """Test render_cell()"""

        def check_cell_content(cell):
            html = SampleSheetHTMLRenderer.render_cell(cell)
            bs = BeautifulSoup(html, 'html.parser')

            text = bs.getText().strip()

            if cell['unit']:
                self.assertEqual(text, '{}\xa0{}'.format(
                    cell['value'], cell['unit']))

            elif not cell['value']:
                self.assertEqual(text, EMPTY_VALUE)

            else:
                self.assertEqual(text, cell['value'])

            if cell['tooltip']:
                self.assertEqual(bs.find('td')['title'], cell['tooltip'])

            if cell['link']:
                self.assertTrue(bool(bs.find('td').find('a')))
                self.assertEqual(bs.find('td').find('a')['href'], cell['link'])

        def check_cells(table):
            for row in table['table_data']:
                for cell in row:
                    check_cell_content(cell)

        check_cells(self.tables['study'])

        for assay_table in self.tables['assays'].values():
            check_cells(assay_table)
'''
