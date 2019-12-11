"""Assay app plugin for samplesheets"""

from django.conf import settings

# from samplesheets.models import GenericMaterial, Process
from samplesheets.plugins import SampleSheetAssayPluginPoint


# Local constants
APP_NAME = 'samplesheets.assayapps.meta_ms'


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

    #: Raw data collection name
    raw_data_coll = 'RawData'

    def get_row_path(self, row, table, assay, assay_path):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default directory.
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :param assay_path: Root path for assay
        :return: String with full iRODS path or None
        """
        # TODO: Alternatives for RawData?
        return assay_path + '/' + self.raw_data_coll

    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row
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

        for i in range(len(row)):
            header = table['field_header'][i]

            # Data files
            if (
                header['obj_cls'] == 'GenericMaterial'
                and header['item_type'] == 'DATA'
                and header['value'].lower() == 'name'
            ):
                # .raw files
                if row[i]['value'].split('.')[-1].lower() == 'raw':
                    row[i]['link'] = (
                        base_url
                        + '/'
                        + self.raw_data_coll
                        + '/'
                        + row[i]['value']
                    )

        return row

    def get_extra_table(self, table, assay):
        """
        Return data for an extra content/shortcut table.

        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :return: Dict or None
        """
        assay_path = self.get_assay_path(assay)

        ret = {
            'schema': {'title': 'Shortcuts for Metabolite Profiling'},
            'cols': [
                {'field': 'directory', 'type': 'label', 'title': 'Directory'},
                {'field': 'links', 'type': 'irods_buttons', 'title': 'Links'},
            ],
            'rows': [
                {
                    'directory': {'value': 'Raw Data'},
                    'links': {'path': assay_path + '/' + self.raw_data_coll},
                }
            ],
        }
        return ret