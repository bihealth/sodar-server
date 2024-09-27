"""Plugin tests for the the dna_sequencing assay plugin"""

import os

from copy import deepcopy

from samplesheets.assayapps.tests.base import AssayPluginTestBase


# Local constants
MATERIAL_NAME = 'alpha'
MATERIAL_NAME_UPDATE = 'alpha-material-update'


class TestDNASequencingAssayPlugin(AssayPluginTestBase):
    """Tests for dna_sequencing assay plugin"""

    plugin_name = 'samplesheets_assay_dna_sequencing'
    template_name = 'generic'

    def test_get_row_path(self):
        """Test get_row_path()"""
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        expected = os.path.join(self.assay_path, MATERIAL_NAME)
        self.assertEqual(row_path, expected)

    def test_get_row_path_rename(self):
        """Test get_row_path() with renamed material name"""
        self.assay_table['table_data'][0][-1]['value'] = MATERIAL_NAME_UPDATE
        row_path = self.plugin.get_row_path(
            self.assay_table['table_data'][0],
            self.assay_table,
            self.assay,
            self.assay_path,
        )
        expected = os.path.join(self.assay_path, MATERIAL_NAME_UPDATE)
        self.assertEqual(row_path, expected)

    def test_update_row(self):
        """Test update_row()"""
        row_ex = deepcopy(self.assay_table['table_data'][0])
        row = self.plugin.update_row(
            self.assay_table['table_data'][0], self.assay_table, self.assay, 0
        )
        self.assertEqual(row, row_ex)
