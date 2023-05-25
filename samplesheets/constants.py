"""Constants for the samplesheets app"""

import re

from django.conf import settings

# Projectroles dependency
from projectroles.plugins import get_backend_api


irods_backend = get_backend_api('omics_irods')


# Default labels and URL patterns for external link columns
# Provide custom labels via a JSON file via SHEETS_EXTERNAL_LINK_PATH.
# Each entry should have a "label" and an optional "url".
# The URL should be a pattern containing "{id}" for the ID.
DEFAULT_EXTERNAL_LINK_LABELS = {
    'x-generic-remote': {'label': 'External ID'},
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

# Path for external link labels (JSON file)
path_re = re.compile(
    '^' + irods_backend.get_projects_path() + '/[0-9a-f]{2}/'
    '(?P<project_uuid>[0-9a-f-]{36})/'
    + settings.IRODS_SAMPLE_COLL
    + '/study_(?P<study_uuid>[0-9a-f-]{36})/'
    'assay_(?P<assay_uuid>[0-9a-f-]{36})/.+$'
)
