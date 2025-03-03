"""Plugin tests for the the meta_ms assay plugin"""

import os

from copy import deepcopy

from samplesheets.assayapps.meta_ms.plugins import RAW_DATA_COLL
from samplesheets.assayapps.tests.base import AssayPluginTestBase
from samplesheets.rendering import SIMPLE_LINK_TEMPLATE
from samplesheets.views import MISC_FILES_COLL, RESULTS_COLL


# Local constants
REPORT_NAME = 'report.txt'
FILE_NAME = 'file1.txt'
FILE_NAME2 = 'file2.txt'


class TestMetaMSAssayPlugin(AssayPluginTestBase):
    """Tests for meta_ms assay plugin"""

    plugin_name = 'samplesheets_assay_meta_ms'
    template_name = 'ms_meta_biocrates'

    def test_get_row_path(self):
        """Test get_row_path()"""
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        expected = os.path.join(self.assay_path, RAW_DATA_COLL)
        self.assertEqual(row_path, expected)

    def test_update_row(self):
        """Test update_row()"""
        self.assay_table['table_data'][0][44]['value'] = FILE_NAME
        self.assay_table['table_data'][0][51]['value'] = FILE_NAME2
        self.assay_table['table_data'][0][55]['value'] = REPORT_NAME
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[44]['link'] = os.path.join(
            self.base_url, RAW_DATA_COLL, FILE_NAME
        )
        row_ex[51]['link'] = os.path.join(
            self.base_url, MISC_FILES_COLL, FILE_NAME2
        )
        row_ex[55]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=REPORT_NAME,
            url=os.path.join(self.base_url, RESULTS_COLL, REPORT_NAME),
        )
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_empty_file_names(self):
        """Test update_row() with empty file names"""
        self.assertEqual(self.assay_table['table_data'][0][44]['value'], '')
        self.assertEqual(self.assay_table['table_data'][0][51]['value'], '')
        self.assay_table['table_data'][0][55]['value'] = REPORT_NAME
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[55]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=REPORT_NAME,
            url=os.path.join(self.base_url, RESULTS_COLL, REPORT_NAME),
        )
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_get_shortcuts(self):
        """Test get_shortcuts()"""
        expected = {
            'id': 'raw_data',
            'label': 'Raw Data',
            'path': os.path.join(self.assay_path, RAW_DATA_COLL),
        }
        self.assertEqual(self.plugin.get_shortcuts(self.assay), [expected])
