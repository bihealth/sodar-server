"""Plugin tests for the the microarray assay plugin"""

import os

from copy import deepcopy

from django.conf import settings

from samplesheets.assayapps.microarray.plugins import RAW_DATA_COLL
from samplesheets.assayapps.tests.base import AssayPluginTestBase


# Local constants
HYBRID_SCAN_NAME = 'alpha-S1-E1-H1'
SCAN_NAME_UPDATE = 'alpha-S1-E1-scan-name'
IMAGE_FILE = 'image.tiff'
ARRAY_DATA_FILE = 'data.dat'
MATRIX_FILE = "mat.rix"


class TestMicroarrayAssayPlugin(AssayPluginTestBase):
    """Tests for microarray assay plugin"""

    plugin_name = 'samplesheets_assay_microarray'
    template_name = 'microarray'

    def test_get_row_path(self):
        """Test get_row_path()"""
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        expected = os.path.join(
            self.assay_path, RAW_DATA_COLL, HYBRID_SCAN_NAME, HYBRID_SCAN_NAME
        )
        self.assertEqual(row_path, expected)

    def test_get_row_path_rename_scan(self):
        """Test get_row_path() with renamed scan name"""
        self.assay_table['table_data'][0][24]['value'] = SCAN_NAME_UPDATE
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        expected = os.path.join(
            self.assay_path, RAW_DATA_COLL, HYBRID_SCAN_NAME, SCAN_NAME_UPDATE
        )
        self.assertEqual(row_path, expected)

    def test_update_row_default(self):
        """Test update_row() with default template values"""
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)

    def test_update_row_files(self):
        """Test update_row() with filled file values"""
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        self.assay_table['table_data'][0][25]['value'] = IMAGE_FILE
        self.assay_table['table_data'][0][26]['value'] = ARRAY_DATA_FILE
        self.assay_table['table_data'][0][27]['value'] = MATRIX_FILE
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row_ex[25]['link'] = settings.IRODS_WEBDAV_URL + os.path.join(
            row_path, IMAGE_FILE
        )
        row_ex[26]['link'] = settings.IRODS_WEBDAV_URL + os.path.join(
            row_path, ARRAY_DATA_FILE
        )
        row_ex[27]['link'] = settings.IRODS_WEBDAV_URL + os.path.join(
            row_path, MATRIX_FILE
        )
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)
