"""Constants for the samplesheets app"""

# Default external link labels used at CUBI
DEFAULT_EXTERNAL_LINK_LABELS = {
    'x-bih-buch-genomics-wetlab-id': 'Wetlab-ID assigned by BIH genomics unit '
    'in Buch',
    'x-bih-cvk-genomics-wetlab-id': 'Wetlab-ID assigned by BIH genomics unit '
    'in CVK',
    'x-bih-tcell2015-id': 'ID assigned in "T-CELL 2015" project ran at BIH',
    'x-cegat-sequencing-id': 'CeGaT Sequencing ID',
    'x-charite-bcrt-genomics-wetlab-id': 'BCRT Genomics Wet-Lab ID',
    'x-charite-medgen-array-id': 'Charite Medical Genetics Array ID',
    'x-charite-medgen-blood-book-id': 'Charite Medical Genetics Blood Book ID',
    'x-dkfz-1touch-id': 'ID assigned through Heidelberg one-touch pipeline',
    'x-dkfz-ilse-id': 'ID assigned through DFKZ sequencing',
    'x-dkfz-mtk-id': 'ID assigned through DFKZ sequencing for the Molecular '
    'Tumor Conference project',
    'x-labor-berlin-blood-book-id': 'Labor Berlin Blood Book ID',
    'x-generic-remote': 'External ID',
}

# Hide template fields listed here from the template UI (see issue #1443)
HIDDEN_SHEET_TEMPLATE_FIELDS = [
    'a_measurement_types',
    'a_technology_types',
    'assay_technology_types',
    'instruments',
    'lib_kits',
    'organisms',
    'terms',
]
