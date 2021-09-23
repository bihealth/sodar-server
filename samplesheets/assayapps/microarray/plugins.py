"""Assay app plugin for samplesheets"""

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.utils import get_top_header

# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.assayapps.microarray'
RAW_DATA_COLL = 'RawData'
HYBRID_NAME = 'hybridization assay name'
SCAN_NAME = 'scan name'
LINKED_FILES = [
    'image file',
    'array data file',
    'array data matrix file',
]


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for Microarray assays in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_microarray'

    #: Title
    title = 'Microarray Assay Plugin'

    # Properties defined in SampleSheetAssayPluginPoint ------------------

    #: App name for dynamic reference to app in e.g. caching
    app_name = APP_NAME

    #: Identifying assay fields (used to identify plugin by assay)
    assay_fields = [
        {
            'measurement_type': 'transcription profiling',
            'technology_type': 'microarray',
        },
        {
            'measurement_type': 'transcription profiling',
            'technology_type': 'DNA microarray',
        },
        {
            'measurement_type': 'transcriptome profiling',
            'technology_type': 'microarray',
        },
        {
            'measurement_type': 'transcriptome profiling',
            'technology_type': 'DNA microarray',
        },
    ]

    #: Description string
    description = 'Sample sheets microarray assay app'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = None

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    display_row_links = True

    def get_row_path(self, row, table, assay, assay_path):
        """
        Return iRODS path for an assay row in a sample sheet. If None,
        display default path.

        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :param assay_path: Root path for assay
        :return: String with full iRODS path or None
        """
        hybrid_name = None
        scan_name = None

        for i in range(len(row)):
            cell = row[i]
            header = table['field_header'][i]
            if (
                header['value'].lower in [HYBRID_NAME, SCAN_NAME]
                and not cell['value']
            ):
                return None  # If we can't find both, cancel
            if header['value'].lower() == HYBRID_NAME:
                hybrid_name = cell['value']
            elif header['value'].lower() == SCAN_NAME:
                scan_name = cell['value']
            if hybrid_name and scan_name:
                row_path = '/'.join(
                    [assay_path, RAW_DATA_COLL, hybrid_name, scan_name]
                )
                return row_path

        return None

    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row.

        :param row: Original row (list of dicts)
        :param table: Full table (dict)
        :param assay: Assay object
        :return: List of dicts
        """
        assay_path = self.get_assay_path(assay)
        if (
            not settings.IRODS_WEBDAV_ENABLED
            or not assay.study.investigation.irods_status
            or not assay_path
        ):
            return row
        row_path = self.get_row_path(row, table, assay, assay_path)
        if not row_path:
            return row

        base_url = settings.IRODS_WEBDAV_URL + row_path

        for i in range(len(row)):
            if (
                table['field_header'][i]['value'].lower() == 'name'
                and row[i]['value']
            ):
                top_header = get_top_header(table, i)
                if (
                    top_header['value'].lower() in LINKED_FILES
                    and row[i]['value']
                ):
                    row[i]['link'] = base_url + '/' + row[i]['value']

        return row

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        self._update_cache_rows(APP_NAME, name, project, user)
