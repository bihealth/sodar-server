"""Assay app plugin for samplesheets"""

from django.conf import settings

# from samplesheets.models import GenericMaterial, Process
from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.utils import get_top_header


# Local constants
APP_NAME = 'samplesheets.assayapps.generic_raw'
RAW_DATA_COLL = 'RawData'


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Generic raw data assay plugin"""

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_generic_raw'

    #: Title
    title = 'Generic Raw Data Assay Plugin'

    #: App name for dynamic reference to app in e.g. caching
    app_name = APP_NAME

    #: Identifying assay fields (used to identify plugin by assay)
    # NOTE: This assay plugin is accessed by the "SODAR Assay Plugin" override
    assay_fields = []

    #: Description string
    description = 'Sample sheets generic raw data assay plugin'

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    display_row_links = False

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
        return assay_path + '/' + RAW_DATA_COLL

    def update_row(self, row, table, assay, index):
        """
        Update render table row with e.g. links. Return the modified row.

        :param row: Original row (list of dicts)
        :param table: Full table (list of lists)
        :param assay: Assay object
        :param index: Row index (int)
        :return: List of dicts
        """
        if not settings.IRODS_WEBDAV_ENABLED or not assay:
            return row
        assay_path = self.get_assay_path(assay)
        if not assay_path:
            return row

        base_url = settings.IRODS_WEBDAV_URL + assay_path
        top_header = None
        th_colspan = 0

        for i in range(len(row)):
            header = table['field_header'][i]
            if not top_header or i >= th_colspan:
                top_header = get_top_header(table, i)
                th_colspan += top_header['colspan']
            if (
                header['obj_cls'] == 'GenericMaterial'
                and header['item_type'] == 'DATA'
                and header['value'].lower() == 'name'
                and top_header['value'].lower() == 'raw data file'
            ):
                row[i]['link'] = (
                    base_url + '/' + RAW_DATA_COLL + '/' + row[i]['value']
                )

        return row

    def get_shortcuts(self, assay):
        """
        Return assay iRODS shortcuts.

        :param assay: Assay object
        :return: List or None
        """
        assay_path = self.get_assay_path(assay)
        return [
            {
                'id': 'raw_data',
                'label': 'Raw Data',
                'path': assay_path + '/' + RAW_DATA_COLL,
            }
        ]
