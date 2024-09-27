"""Plugin tests for the the cytof assay plugin"""

import os

from copy import deepcopy

from samplesheets.assayapps.tests.base import AssayPluginTestBase
from samplesheets.rendering import SIMPLE_LINK_TEMPLATE
from samplesheets.views import MISC_FILES_COLL


# Local constants
ASSAY_NAME = 'testassayname'
PANEL_NAME = 'testpanel'
REPORT_NAME = 'report.txt'
FILE_NAME = 'file1.txt'
FILE_NAME2 = 'file2.txt'
FILE_NAME3 = 'file3.txt'


class TestCytofAssayPlugin(AssayPluginTestBase):
    """Tests for cytof assay plugin"""

    plugin_name = 'samplesheets_assay_cytof'
    template_name = 'mass_cytometry'

    def test_get_row_path_filled(self):
        """Test get_row_path() with filled out assay name"""
        self.assay_table['table_data'][0][20]['value'] = ASSAY_NAME
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        expected = os.path.join(self.assay_path, ASSAY_NAME)
        self.assertEqual(row_path, expected)

    def test_get_row_path_default(self):
        """Test get_row_path() with default template values"""
        # NOTE: Assay name is not filled by default, so we return None
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        self.assertEqual(row_path, None)

    def test_update_row_panel(self):
        """Test update_row() with filled panel name"""
        # Update unset values
        self.assay_table['table_data'][0][15]['value'] = PANEL_NAME
        self.assay_table['table_data'][0][20]['value'] = ASSAY_NAME
        self.assay_table['table_data'][0][26]['value'] = FILE_NAME
        self.assay_table['table_data'][0][31]['value'] = FILE_NAME2
        self.assay_table['table_data'][0][36]['value'] = FILE_NAME3
        # Set expected data
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[15]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=PANEL_NAME,
            url=os.path.join(self.base_url, MISC_FILES_COLL, PANEL_NAME),
        )
        row_ex[26]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME)
        row_ex[31]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME2)
        row_ex[36]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME3)
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_report(self):
        """Test update_row() with filled report file"""
        self.assay_table['table_data'][0][16]['value'] = REPORT_NAME
        self.assay_table['table_data'][0][20]['value'] = ASSAY_NAME
        self.assay_table['table_data'][0][26]['value'] = FILE_NAME
        self.assay_table['table_data'][0][31]['value'] = FILE_NAME2
        self.assay_table['table_data'][0][36]['value'] = FILE_NAME3
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[16]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=REPORT_NAME,
            url=os.path.join(self.base_url, ASSAY_NAME, REPORT_NAME),
        )
        row_ex[26]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME)
        row_ex[31]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME2)
        row_ex[36]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME3)
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_barcode(self):
        """Test update_row() with filled barcode key"""
        # Rename header
        self.assay_table['field_header'][15]['value'] = 'Barcode Key'
        self.assay_table['table_data'][0][15]['value'] = PANEL_NAME
        self.assay_table['table_data'][0][20]['value'] = ASSAY_NAME
        self.assay_table['table_data'][0][26]['value'] = FILE_NAME
        self.assay_table['table_data'][0][31]['value'] = FILE_NAME2
        self.assay_table['table_data'][0][36]['value'] = FILE_NAME3
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[15]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=PANEL_NAME,
            url=os.path.join(self.base_url, MISC_FILES_COLL, PANEL_NAME),
        )
        row_ex[26]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME)
        row_ex[31]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME2)
        row_ex[36]['link'] = os.path.join(self.base_url, ASSAY_NAME, FILE_NAME3)
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_barcode_empty_file_names(self):
        """Test update_row() with filled barcode key and empty file names"""
        # Rename header
        self.assay_table['field_header'][15]['value'] = 'Barcode Key'
        self.assay_table['table_data'][0][15]['value'] = PANEL_NAME
        self.assay_table['table_data'][0][20]['value'] = ASSAY_NAME
        self.assertEqual(self.assay_table['table_data'][0][26]['value'], '')
        self.assertEqual(self.assay_table['table_data'][0][31]['value'], '')
        self.assertEqual(self.assay_table['table_data'][0][36]['value'], '')
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[15]['value'] = SIMPLE_LINK_TEMPLATE.format(
            label=PANEL_NAME,
            url=os.path.join(self.base_url, MISC_FILES_COLL, PANEL_NAME),
        )
        # File names should not be updated
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_default(self):
        """Test update_row() with default template values"""
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)
