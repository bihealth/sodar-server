"""Tests for samplesheets.rendering"""

from django.test import override_settings
from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

from samplesheets.models import GenericMaterial
from samplesheets.rendering import (
    SampleSheetTableBuilder,
    STUDY_TABLE_CACHE_ITEM,
)
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)
from samplesheets.tests.test_sheet_config import SheetConfigMixin


app_settings = AppSettingAPI()


# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2.zip'
SHEET_PATH_EMPTY_COLS = SHEET_DIR_SPECIAL + 'i_small_empty_cols.zip'
STUDY_COL_TYPES = [
    'NAME',
    'ONTOLOGY',
    'UNIT',
    'PROTOCOL',
    None,
    'CONTACT',
    'DATE',
    'NAME',
    'NUMERIC',
    None,
]
ASSAY_COL_TYPES = STUDY_COL_TYPES + [
    'PROTOCOL',
    'NAME',
    'PROTOCOL',
    'NAME',
    'LINK_FILE',
    'LINK_FILE',
    'NAME',
    'LINK_FILE',
]


# TODO: Unify with TestTableBuilder if no other classes are needed
class SamplesheetsRenderingTestBase(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Base class for samplesheets rendering tests"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Make owner user
        self.user_owner = self.make_user('owner')
        # Init project and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.tb = SampleSheetTableBuilder()
        # Set up helpers
        self.cache_backend = get_backend_api('sodar_cache')
        self.cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=self.study.sodar_uuid
        )
        self.cache_args = [APP_NAME, self.cache_name, self.project]


class TestSampleSheetTableBuilder(
    SheetConfigMixin, SamplesheetsRenderingTestBase
):
    """Tests for SampleSheetTableBuilder"""

    def _assert_row_length(self, table):
        """Assert uniform row length"""
        row_lengths = set([len(r) for r in table['table_data']])
        self.assertEqual(len(row_lengths), 1)

    @classmethod
    def _get_column_set(cls, table, pos):
        """Return set of distinct values for a column at pos"""
        return set([r[pos]['value'] for r in table['table_data']])

    def test_get_headers(self):
        """Test get_headers()"""
        h = self.tb.get_headers(self.investigation)
        self.assertIsNotNone(h)
        self.assertEqual(len(h['studies'][0]['headers']), 15)
        self.assertEqual(len(h['studies'][0]['assays'][0]), 8)

    def test_get_headers_compare_row(self):
        """Test comparing get_headers() results for inserted rows"""
        investigation2 = self.import_isa_from_file(
            SHEET_PATH_INSERTED, self.project
        )
        h1 = self.tb.get_headers(self.investigation)
        h2 = self.tb.get_headers(investigation2)
        self.assertIsNotNone(h2)
        self.assertEqual(h1, h2)

    def test_get_headers_compare_col(self):
        """Test comparing get_headers() for different columns (should fail)"""
        investigation2 = self.import_isa_from_file(SHEET_PATH_ALT, self.project)
        h1 = self.tb.get_headers(self.investigation)
        h2 = self.tb.get_headers(investigation2)
        self.assertIsNotNone(h2)
        self.assertNotEqual(h1, h2)

    def test_build_study_tables(self):
        """Test build_study_tables()"""
        tables = self.tb.build_study_tables(self.study)
        self.assertIsNotNone(tables)
        # Assert tables
        self.assertIn('study', tables)
        self.assertIn('assays', tables)
        self.assertEqual(len(tables['assays']), self.study.assays.count())
        # Study table
        self._assert_row_length(tables['study'])
        # Sources
        table_sources = self._get_column_set(tables['study'], 0)
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
        table_samples = self._get_column_set(tables['study'], sample_pos)
        db_samples = set(
            GenericMaterial.objects.filter(
                study=self.study, item_type='SAMPLE'
            ).values_list('name', flat=True)
        )
        self.assertEqual(table_samples, db_samples)
        # Aassay tables
        for k, assay_table in tables['assays'].items():
            self._assert_row_length(assay_table)

    def test_build_study_tables_col_types(self):
        """Test build_study_tables() column types"""
        tables = self.tb.build_study_tables(self.study)
        self.assertEqual(
            [h['col_type'] for h in tables['study']['field_header']],
            STUDY_COL_TYPES,
        )
        assay_table = tables['assays'][str(self.assay.sodar_uuid)]
        self.assertEqual(
            [h['col_type'] for h in assay_table['field_header']],
            ASSAY_COL_TYPES,
        )

    def test_build_study_tables_col_types_empty(self):
        """Test build_study_tables() column types with empty columns"""
        investigation2 = self.import_isa_from_file(
            SHEET_PATH_EMPTY_COLS, self.project
        )
        study2 = investigation2.studies.first()
        assay2 = study2.assays.first()
        tables = self.tb.build_study_tables(study2)
        expected = STUDY_COL_TYPES
        STUDY_COL_TYPES[8] = None  # This should not be NUMERIC anymore
        self.assertEqual(
            [h['col_type'] for h in tables['study']['field_header']], expected
        )
        assay_table = tables['assays'][str(assay2.sodar_uuid)]
        expected = ASSAY_COL_TYPES
        ASSAY_COL_TYPES[8] = None
        self.assertEqual(
            [h['col_type'] for h in assay_table['field_header']], expected
        )

    def test_build_study_tables_config(self):
        """Test build_study_tables() with sheet config"""
        tables = self.tb.build_study_tables(self.study)
        t_field = tables['study']['field_header'][4]
        self.assertEqual(t_field['col_type'], None)

        sheet_config = self.build_sheet_config(self.investigation)
        c_field = sheet_config['studies'][str(self.study.sodar_uuid)]['nodes'][
            1
        ]['fields'][1]
        self.assertEqual(c_field.get('format'), None)
        c_field['format'] = 'integer'
        sheet_config['studies'][str(self.study.sodar_uuid)]['nodes'][1][
            'fields'
        ][1] = c_field
        app_settings.set(
            APP_NAME, 'sheet_config', sheet_config, project=self.project
        )

        tables = self.tb.build_study_tables(self.study)
        t_field = tables['study']['field_header'][4]
        self.assertEqual(t_field['col_type'], 'NUMERIC')

    def test_build_inv_tables(self):
        """Test build_inv_tables()"""
        inv_tables = self.tb.build_inv_tables(self.investigation)
        self.assertEqual(len(inv_tables.keys()), 1)
        for study, study_tables in inv_tables.items():
            self.assertEqual(
                study_tables, self.tb.build_study_tables(study, use_config=True)
            )

    def test_build_inv_tables_no_config(self):
        """Test build_inv_tables() with use_config=False"""
        inv_tables = self.tb.build_inv_tables(
            self.investigation, use_config=False
        )
        self.assertEqual(len(inv_tables.keys()), 1)
        for study, study_tables in inv_tables.items():
            self.assertEqual(
                study_tables,
                self.tb.build_study_tables(study, use_config=False),
            )

    def test_get_study_tables(self):
        """Test get_study_tables()"""
        self.assertIsNone(self.cache_backend.get_cache_item(*self.cache_args))
        study_tables = self.tb.get_study_tables(self.study)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self.assertEqual(study_tables, cache_item.data)

    def test_get_study_tables_cache(self):
        """Test get_study_tables() with existing cache item"""
        study_tables = self.tb.build_study_tables(self.study)
        cache_item = self.cache_backend.set_cache_item(
            APP_NAME, self.cache_name, study_tables, 'json', self.project
        )
        self.assertIsNotNone(
            self.cache_backend.get_cache_item(*self.cache_args)
        )
        study_tables = self.tb.get_study_tables(self.study)
        self.assertEqual(study_tables, cache_item.data)

    def test_get_study_tables_cache_disable_save(self):
        """Test get_study_tables() with disabled cache saving"""
        self.assertIsNone(self.cache_backend.get_cache_item(*self.cache_args))
        study_tables = self.tb.get_study_tables(self.study, save_cache=False)
        self.assertIsInstance(study_tables, dict)
        self.assertIsNone(self.cache_backend.get_cache_item(*self.cache_args))

    @override_settings(SHEETS_ENABLE_STUDY_TABLE_CACHE=False)
    def test_get_study_tables_update_no_cache(self):
        """Test get_study_tables() with SHEETS_ENABLE_STUDY_TABLE_CACHE=False"""
        tables = self.tb.get_study_tables(self.study)
        t_field = tables['study']['field_header'][2]
        self.assertEqual(t_field['value'], 'Age')
        self.sheet_config = self.build_sheet_config(self.investigation)

        # Change name in a model
        characteristics = (
            GenericMaterial.objects.filter(study=self.study, item_type='SOURCE')
            .first()
            .characteristics
        )
        self.assertEqual(characteristics['age']['value'], '90')
        characteristics['age']['value'] = '70'
        GenericMaterial.objects.filter(
            study=self.study, item_type='SOURCE'
        ).update(characteristics=characteristics)

        tables = self.tb.get_study_tables(self.study)
        val_field = tables['study']['table_data'][2]
        self.assertEqual(val_field[2]['value'], '70')

    def test_get_study_tables_update_cache(self):
        """Test get_study_tables() with SHEETS_ENABLE_STUDY_TABLE_CACHE=True"""
        tables = self.tb.get_study_tables(self.study)
        t_field = tables['study']['field_header'][2]
        self.assertEqual(t_field['value'], 'Age')
        self.build_sheet_config(self.investigation)

        # Change name in a model
        characteristics = (
            GenericMaterial.objects.filter(study=self.study, item_type='SOURCE')
            .first()
            .characteristics
        )
        self.assertEqual(characteristics['age']['value'], '90')
        characteristics['age']['value'] = '70'
        GenericMaterial.objects.filter(
            study=self.study, item_type='SOURCE'
        ).first().characteristics = characteristics

        tables = self.tb.get_study_tables(self.study)
        val_field = tables['study']['table_data'][2]
        self.assertEqual(val_field[2]['value'], '90')

    def test_clear_study_cache(self):
        """Test clear_study_cache()"""
        study_tables = self.tb.build_study_tables(self.study)
        self.cache_backend.set_cache_item(
            APP_NAME, self.cache_name, study_tables, 'json', self.project
        )
        self.assertIsNotNone(
            self.cache_backend.get_cache_item(*self.cache_args)
        )
        self.tb.clear_study_cache(self.study)
        # NOTE: We still have the item, but it's empty
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self.assertEqual(cache_item.data, {})

    def test_clear_study_cache_no_item(self):
        """Test clear_study_cache() without existing item"""
        self.assertIsNone(self.cache_backend.get_cache_item(*self.cache_args))
        self.tb.clear_study_cache(self.study)
        self.assertIsNone(self.cache_backend.get_cache_item(*self.cache_args))

    def test_clear_study_cache_delete(self):
        """Test clear_study_cache() with delete=True"""
        study_tables = self.tb.build_study_tables(self.study)
        self.cache_backend.set_cache_item(
            APP_NAME, self.cache_name, study_tables, 'json', self.project
        )
        self.assertIsNotNone(
            self.cache_backend.get_cache_item(*self.cache_args)
        )
        self.tb.clear_study_cache(self.study, delete=True)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self.assertIsNone(cache_item)

    def test_clear_study_cache_delete_no_item(self):
        """Test clear_study_cache() with delete=True and no existing item"""
        self.assertIsNone(self.cache_backend.get_cache_item(*self.cache_args))
        self.tb.clear_study_cache(self.study, delete=True)
        self.assertIsNone(self.cache_backend.get_cache_item(*self.cache_args))
