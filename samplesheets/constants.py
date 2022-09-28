"""Constants for the samplesheets app"""

# Default external link labels
# Each entry should have a "label" and an optional "url"
# The url should be a pattern containing "{id}" for the ID
# TODO: Move internal CUBI labels from repo to env (see issue #1477)
DEFAULT_EXTERNAL_LINK_LABELS = {
    'x-bih-buch-genomics-wetlab-id': {
        'label': 'Wetlab-ID assigned by BIH genomics unit in Buch'
    },
    'x-bih-cvk-genomics-wetlab-id': {
        'label': 'Wetlab-ID assigned by BIH genomics unit in CVK'
    },
    'x-bih-tcell2015-id': {
        'label': 'ID assigned in "T-CELL 2015" project ran at BIH'
    },
    'x-cegat-sequencing-id': {'label': 'CeGaT Sequencing ID'},
    'x-charite-bcrt-genomics-wetlab-id': {'label': 'BCRT Genomics Wet-Lab ID'},
    'x-charite-medgen-array-id': {'label': 'Charite Medical Genetics Array ID'},
    'x-charite-medgen-blood-book-id': {
        'label': 'Charite Medical Genetics Blood Book ID'
    },
    'x-dkfz-1touch-id': {
        'label': 'ID assigned through Heidelberg one-touch pipeline'
    },
    'x-dkfz-ilse-id': {'label': 'ID assigned through DFKZ sequencing'},
    'x-dkfz-mtk-id': {
        'label': 'ID assigned through DFKZ sequencing for the Molecular Tumor '
        'Conference project'
    },
    'x-labor-berlin-blood-book-id': {'label': 'Labor Berlin Blood Book ID'},
    'x-generic-remote': {'label': 'External ID'},
    'x-sodar-example': {'label': 'Example ID', 'url': None},
    'x-sodar-example-link': {
        'label': 'Example ID with hyperlink',
        'url': 'https://example.com/{id}',
    },
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
