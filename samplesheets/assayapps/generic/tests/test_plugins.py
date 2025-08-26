"""Plugin tests for the the generic assay plugin"""

import os

from copy import deepcopy
from typing import Optional

from samplesheets.assayapps.generic.plugins import (
    DATA_COMMENT_PREFIX,
    DATA_LINK_COMMENT,
    MISC_FILES_COMMENT,
    RESULTS_COMMENT,
)
from samplesheets.assayapps.tests.base import AssayPluginTestBase
from samplesheets.models import ISA_META_ASSAY_PLUGIN
from samplesheets.rendering import SIMPLE_LINK_TEMPLATE
from samplesheets.views import MISC_FILES_COLL, RESULTS_COLL


# Local constants
PLUGIN_NAME = 'samplesheets_assay_generic'
NONEXISTENT_COL = 'XXXNOTEXISTINGXXX'
FILE_NAME = 'file.txt'
FOLDER_COL = 'folder name'
FOLDER_VAL = 'alpha'
STRAT_COL = 'library strategy'
STRAT_VAL = 'RNA-seq'
CUSTOM_COLL = 'custom_coll'
RAW_DATA_COL = 'raw data file'


class TestGenericAssayPlugin(AssayPluginTestBase):
    """Tests for generic assay plugin"""

    plugin_name = PLUGIN_NAME
    template_name = 'generic'

    def _get_row_path(self) -> Optional[str]:
        """Shortcut for plugin get_row_path() call with first assay row"""
        return self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )

    def _update_row(self) -> list[dict]:
        """Shortcut for plugin update_row() with first assay row"""
        return self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )

    def setUp(self):
        super().setUp()
        # Override plugin
        self.assay.comments[ISA_META_ASSAY_PLUGIN] = PLUGIN_NAME
        self.assay.save()

    def test_get_row_path(self):
        """Test get_row_path() with no assay comments"""
        row_path = self._get_row_path()
        self.assertIsNone(row_path)

    def test_get_row_path_set(self):
        """Test get_row_path() with column set"""
        self.assay.comments[DATA_COMMENT_PREFIX] = FOLDER_COL
        self.assertEqual(
            self.assay_table['table_data'][0][47]['value'], FOLDER_VAL
        )
        row_path = self._get_row_path()
        self.assertEqual(row_path, os.path.join(self.assay_path, FOLDER_VAL))

    def test_get_row_path_empty_value(self):
        """Test get_row_path() with empty column value"""
        self.assay.comments[DATA_COMMENT_PREFIX] = FOLDER_COL
        self.assay_table['table_data'][0][47]['value'] = ''
        row_path = self._get_row_path()
        self.assertIsNone(row_path)

    def test_get_row_path_set_nonexistent(self):
        """Test get_row_path() with nonexistent column"""
        self.assay.comments[DATA_COMMENT_PREFIX] = NONEXISTENT_COL
        row_path = self._get_row_path()
        self.assertIsNone(row_path)

    def test_get_row_path_set_multiple(self):
        """Test get_row_path() with multiple columns"""
        self.assay.comments[DATA_COMMENT_PREFIX + '1'] = STRAT_COL
        self.assay.comments[DATA_COMMENT_PREFIX + '2'] = FOLDER_COL
        self.assertEqual(
            self.assay_table['table_data'][0][34]['value'], STRAT_VAL
        )
        self.assertEqual(
            self.assay_table['table_data'][0][47]['value'], FOLDER_VAL
        )
        row_path = self._get_row_path()
        self.assertEqual(
            row_path, os.path.join(self.assay_path, STRAT_VAL, FOLDER_VAL)
        )

    def test_get_row_path_set_multiple_nonexistent(self):
        """Test get_row_path() with multiple columns and nonexistent column"""
        self.assay.comments[DATA_COMMENT_PREFIX + '1'] = FOLDER_COL
        self.assay.comments[DATA_COMMENT_PREFIX + '2'] = NONEXISTENT_COL
        row_path = self._get_row_path()
        self.assertEqual(row_path, os.path.join(self.assay_path, FOLDER_VAL))

    def test_get_row_path_set_multiple_empty_value(self):
        """Test get_row_path() with multiple columns and empty value"""
        self.assay.comments[DATA_COMMENT_PREFIX + '1'] = FOLDER_COL
        self.assay.comments[DATA_COMMENT_PREFIX + '2'] = STRAT_COL
        self.assay_table['table_data'][0][47]['value'] = ''
        row_path = self._get_row_path()
        self.assertEqual(row_path, os.path.join(self.assay_path, STRAT_VAL))

    def test_get_row_path_duplicate_column_names(self):
        """Test get_row_path() with duplicate column names"""
        self.assay.comments[DATA_COMMENT_PREFIX] = 'perform date'
        self.assay_table['table_data'][0][20]['value'] = '2024-10-01'
        self.assay_table['table_data'][0][45]['value'] = '2024-10-02'
        self.assay_table['table_data'][0][56]['value'] = '2024-10-03'
        row_path = self._get_row_path()
        # NOTE: The last one gets returned, is this correct?
        self.assertEqual(row_path, os.path.join(self.assay_path, '2024-10-03'))

    def test_update_row(self):
        """Test update_row() with no comments set"""
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_results(self):
        """Test update_row() with results comment"""
        self.assay.comments[RESULTS_COMMENT] = FOLDER_COL
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[47]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=FOLDER_VAL,
            url=self.base_url + os.path.join('/', RESULTS_COLL, FOLDER_VAL),
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_results_multiple(self):
        """Test update_row() with multiple results comments"""
        self.assay.comments[RESULTS_COMMENT] = ';'.join([FOLDER_COL, STRAT_COL])
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[34]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=STRAT_VAL,
            url=self.base_url + os.path.join('/', RESULTS_COLL, STRAT_VAL),
        )
        row_ex[47]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=FOLDER_VAL,
            url=self.base_url + os.path.join('/', RESULTS_COLL, FOLDER_VAL),
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_misc(self):
        """Test update_row() with misc files comment"""
        self.assay.comments[MISC_FILES_COMMENT] = FOLDER_COL
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[47]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=FOLDER_VAL,
            url=self.base_url + os.path.join('/', MISC_FILES_COLL, FOLDER_VAL),
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_misc_multiple(self):
        """Test update_row() with multiple misc files comments"""
        self.assay.comments[MISC_FILES_COMMENT] = ';'.join(
            [FOLDER_COL, STRAT_COL]
        )
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[34]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=STRAT_VAL,
            url=self.base_url + os.path.join('/', MISC_FILES_COLL, STRAT_VAL),
        )
        row_ex[47]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=FOLDER_VAL,
            url=self.base_url + os.path.join('/', MISC_FILES_COLL, FOLDER_VAL),
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_data_link_row_data(self):
        """Test update_row() with data link comment and row data column"""
        self.assay.comments[DATA_COMMENT_PREFIX] = FOLDER_COL
        self.assay.comments[DATA_LINK_COMMENT] = STRAT_COL
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[34]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=STRAT_VAL,
            url=self.base_url + os.path.join('/', FOLDER_VAL, STRAT_VAL),
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_data_link_irods_paths(self):
        """Test update_row() with data link comment and irods path"""
        # NOTE: We'll still set the row data column to ensure it is not picked
        self.assay.comments[DATA_COMMENT_PREFIX] = FOLDER_COL
        self.assay.comments[DATA_LINK_COMMENT] = STRAT_COL
        coll_path = os.path.join(self.assay_path, CUSTOM_COLL)
        self.assay_table['irods_paths'] = [{'path': coll_path}]
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[34]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=STRAT_VAL,
            url=self.base_url + os.path.join('/', CUSTOM_COLL, STRAT_VAL),
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_multiple_on_same_col(self):
        """Test update_row() with multiple comments on same column"""
        self.assay.comments[RESULTS_COMMENT] = FOLDER_COL
        self.assay.comments[MISC_FILES_COMMENT] = FOLDER_COL
        self.assay.comments[DATA_LINK_COMMENT] = FOLDER_COL
        row_ex = deepcopy(self.assay_table['table_data'][0])
        # First one should be picked
        row_ex[47]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=FOLDER_VAL,
            url=self.base_url + os.path.join('/', RESULTS_COLL, FOLDER_VAL),
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_results_file(self):
        """Test update_row() with results comment set on file column"""
        self.assay.comments[RESULTS_COMMENT] = RAW_DATA_COL
        self.assay_table['table_data'][0][57]['value'] = FILE_NAME
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[57]['link'] = self.base_url + os.path.join(
            '/', RESULTS_COLL, FILE_NAME
        )
        row = self._update_row()
        self.assertEqual(row, row_ex)

    def test_update_row_results_file_unset(self):
        """Test update_row() with results comment set on unset file column"""
        self.assay.comments[RESULTS_COMMENT] = RAW_DATA_COL
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row = self._update_row()
        # Row should not be changed
        self.assertEqual(row, row_ex)

    def test_update_row_results_file_existing_link(self):
        """Test update_row() with existing link value"""
        self.assay.comments[RESULTS_COMMENT] = RAW_DATA_COL
        self.assay_table['table_data'][0][57]['value'] = (
            SIMPLE_LINK_TEMPLATE.format(label=FILE_NAME, url='https://foo.bar/')
        )
        row_ex = deepcopy(self.assay_table['table_data'][0])
        # Row should not be changed
        row = self._update_row()
        self.assertEqual(row, row_ex)
