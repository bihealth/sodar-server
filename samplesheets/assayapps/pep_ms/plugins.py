"""Assay app plugin for samplesheets"""

from django.conf import settings

# from samplesheets.models import GenericMaterial, Process
from samplesheets.plugins import SampleSheetAssayPluginPoint


# Local constants
APP_NAME = 'samplesheets.assayapps.pep_ms'
RAW_DATA_COLL = 'RawData'
MAX_QUANT_COLL = 'MaxQuantResults'


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """
    Plugin for protein expression profiling / mass spectrometry in sample
    sheets
    """

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_pep_ms'

    #: Title
    title = (
        'Sample Sheets Protein Expression Profiling / Mass Spectrometry '
        'Assay Plugin'
    )

    #: App name for dynamic reference to app in e.g. caching
    app_name = APP_NAME

    #: Identifying assay fields (used to identify plugin by assay)
    assay_fields = [
        {
            'measurement_type': 'protein expression profiling',
            'technology_type': 'mass spectrometry',
        }
    ]

    #: Description string
    description = (
        'Sample sheets protein expression profiling / mass '
        'spectrometry assay plugin'
    )

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = 'samplesheets_assay_pep_ms/_assay.html'

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

        for i in range(len(row)):
            header = table['field_header'][i]
            # Data files
            if (
                header['obj_cls'] == 'GenericMaterial'
                and header['item_type'] == 'DATA'
                and header['value'].lower() == 'name'
                and row[i]['value']
                and isinstance(row[i]['value'], str)
            ):
                # We assume all files to be in RawData
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
            },
            {
                'id': 'maxquant_results',
                'label': 'MaxQuant Results',
                'path': assay_path + '/' + MAX_QUANT_COLL,
            },
        ]
