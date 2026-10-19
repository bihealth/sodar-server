"""Constants for the samplesheets app"""

# Default labels and URL patterns for external link columns
# Provide custom labels via a JSON file via SHEETS_EXTERNAL_LINK_PATH.
# Each entry should have a "label" and an optional "url".
# The URL should be a pattern containing "{id}" for the ID.
DEFAULT_EXTERNAL_LINK_LABELS = {
    'x-generic-remote': {'label': 'External ID'},
}

# ISA-Tab comment fields NOT originating from SODAR
ISA_COMM_STUDY_CONFIG_CREATE = 'Created With Configuration'
ISA_COMM_STUDY_CONFIG_OPEN = 'Last Opened With Configuration'

# Investigation ISA-Tab SODAR metadata keys
ISA_META_ALTAMISA_VERSION = 'SODAR AltamISA Version'
ISA_META_INVESTIGATION_UUID = 'SODAR Investigation UUID'
ISA_META_PROJECT_FULL_TITLE = 'SODAR Project Full Title'
ISA_META_PROJECT_URL = 'SODAR Project URL'
ISA_META_PROJECT_UUID = 'SODAR Project UUID'
ISA_META_SAVE_TIMESTAMP = 'SODAR Save Timestamp'
ISA_META_SODAR_SITE_INSTANCE = 'SODAR Site Instance Name'
ISA_META_SODAR_SITE_URL = 'SODAR Site URL'
ISA_META_SODAR_SERVER_VERSION = 'SODAR Server Version'

# Study ISA-Tab SODAR metadata keys
ISA_META_STUDY_PLUGIN = 'SODAR Study Plugin'
ISA_META_STUDY_UUID = 'SODAR Study UUID'

# Assay ISA-Tab SODAR metadata keys
ISA_META_ASSAY_DISPLAY_NAME = 'SODAR Assay Display Name'
ISA_META_ASSAY_PLUGIN = 'SODAR Assay Plugin'
ISA_META_ASSAY_UUID = 'SODAR Assay UUID'

# Export-only investigation ISA-Tab SODAR metadata keys
ISA_META_INV_EXPORT_KEYS = [
    ISA_META_ALTAMISA_VERSION,
    ISA_META_INVESTIGATION_UUID,
    ISA_META_PROJECT_FULL_TITLE,
    ISA_META_PROJECT_URL,
    ISA_META_PROJECT_UUID,
    ISA_META_SAVE_TIMESTAMP,
    ISA_META_SODAR_SITE_INSTANCE,
    ISA_META_SODAR_SITE_URL,
    ISA_META_SODAR_SERVER_VERSION,
]
# Export-only study ISA-Tab SODAR metadata keys
ISA_META_STUDY_EXPORT_KEYS = [ISA_META_STUDY_UUID]
# Export-only study ISA-Tab SODAR metadata keys
ISA_META_ASSAY_EXPORT_KEYS = [ISA_META_ASSAY_UUID]
