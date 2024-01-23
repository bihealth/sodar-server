"""Assay app plugin for samplesheets"""

from django.conf import settings

# from samplesheets.models import GenericMaterial, Process
from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.rendering import SIMPLE_LINK_TEMPLATE
from samplesheets.utils import get_top_header
from samplesheets.views import MISC_FILES_COLL, RESULTS_COLL


# Local constants
APP_NAME = 'samplesheets.assayapps.meta_ms'
RAW_DATA_COLL = 'RawData'


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for Metabolite profiling / mass spectrometry in sample sheets"""

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_meta_ms'

    #: Title
    title = (
        'Sample Sheets Metabolite Profiling / Mass Spectrometry Assay Plugin'
    )

    #: App name for dynamic reference to app in e.g. caching
    app_name = APP_NAME

    #: Identifying assay fields (used to identify plugin by assay)
    assay_fields = [
        {
            'measurement_type': 'metabolite profiling',
            'technology_type': 'mass spectrometry',
        }
    ]

    #: Description string
    description = (
        'Sample sheets metabolite profiling / mass spectrometry assay plugin'
    )

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
        # TODO: Alternatives for RawData?
        return assay_path + '/' + RAW_DATA_COLL

    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row.

        :param row: Original row (list of dicts)
        :param table: Full table (dict)
        :param assay: Assay object
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
            # Protocol file links within processes
            if (
                header['obj_cls'] == 'Process'
                and header['value'].lower() == 'protocol file'
            ):
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url
                    + '/'
                    + MISC_FILES_COLL
                    + '/'
                    + row[i]['value'],
                )
            # Method file links within processes
            if header['obj_cls'] == 'Process' and header[
                'value'
            ].lower().endswith('method file'):
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url
                    + '/'
                    + MISC_FILES_COLL
                    + '/'
                    + row[i]['value'],
                )
            # Report file links within processes
            elif (
                header['obj_cls'] == 'Process'
                and header['value'].lower() == 'report file'
            ):
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url + '/' + RESULTS_COLL + '/' + row[i]['value'],
                )
            # Log file links within processes
            elif (
                header['obj_cls'] == 'Process'
                and header['value'].lower() == 'log file'
            ):
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url + '/' + RESULTS_COLL + '/' + row[i]['value'],
                )
            # Data files
            elif (
                header['obj_cls'] == 'GenericMaterial'
                and header['item_type'] == 'DATA'
                and header['value'].lower() == 'name'
                and top_header['value'].lower()
                in ['metabolite assignment file', 'raw spectral data file']
            ):
                if top_header['value'].lower() == 'metabolite assignment file':
                    coll_name = MISC_FILES_COLL
                else:
                    coll_name = RAW_DATA_COLL
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url + '/' + coll_name + '/' + row[i]['value'],
                )
            elif (
                header['obj_cls'] == 'GenericMaterial'
                and header['item_type'] == 'DATA'
                and header['value'].lower() == 'name'
                and top_header['value'].lower() == 'derived data file'
            ):
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url + '/' + RESULTS_COLL + '/' + row[i]['value'],
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
