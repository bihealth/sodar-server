"""Constants for the samplesheets app"""

# Default labels and URL patterns for external link columns
# Provide custom labels via a JSON file via SHEETS_EXTERNAL_LINK_PATH.
# Each entry should have a "label" and an optional "url".
# The URL should be a pattern containing "{id}" for the ID.
DEFAULT_EXTERNAL_LINK_LABELS = {
    'x-generic-remote': {'label': 'External ID'},
}
