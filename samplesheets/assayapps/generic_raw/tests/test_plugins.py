"""Plugin tests for the the generic_raw assay plugin"""

import os

from copy import deepcopy

from samplesheets.assayapps.generic_raw.plugins import RAW_DATA_COLL
from samplesheets.assayapps.tests.base import AssayPluginTestBase
from samplesheets.models import ISA_META_ASSAY_PLUGIN


# Local constants
PLUGIN_NAME = 'samplesheets_assay_generic_raw'
FILE_NAME = 'file1.txt'
FILE_NAME2 = 'file2.txt'


class TestGenericRawAssayPlugin(AssayPluginTestBase):
    """Tests for generic_raw assay plugin"""

    plugin_name = PLUGIN_NAME
    template_name = 'ms_meta_biocrates'

    def setUp(self):
        super().setUp()
        # Override plugin
        self.assay.comments[ISA_META_ASSAY_PLUGIN] = PLUGIN_NAME
        self.assay.save()

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
        # NOTE: only "raw data file" fields get updated
        # Rename top header value to raw data file
        self.assay_table['top_header'][7]['value'] = 'Raw Data File'
        self.assay_table['table_data'][0][44]['value'] = FILE_NAME
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[44]['link'] = os.path.join(
            self.base_url, RAW_DATA_COLL, FILE_NAME
        )
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_empty_file_name(self):
        """Test update_row() with empty file name"""
        self.assay_table['top_header'][7]['value'] = 'Raw Data File'
        self.assertEqual(self.assay_table['table_data'][0][44]['value'], '')
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_default(self):
        """Test update_row()"""
        row_ex = deepcopy(self.assay_table['table_data'][0])
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
