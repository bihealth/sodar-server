"""Constants for the samplesheets app"""

# Default labels and URL patterns for external link columns
# Provide custom labels via a JSON file via SHEETS_EXTERNAL_LINK_PATH.
# Each entry should have a "label" and an optional "url".
# The URL should be a pattern containing "{id}" for the ID.
DEFAULT_EXTERNAL_LINK_LABELS = {
    'x-generic-remote': {'label': 'External ID'},
}

# ISA-Tab comment keys for SODAR-specific metadata and overrides
ISA_META_ASSAY_DISPLAY_NAME = 'SODAR Assay Display Name'
ISA_META_ASSAY_PLUGIN = 'SODAR Assay Plugin'
ISA_META_STUDY_PLUGIN = 'SODAR Study Plugin'
