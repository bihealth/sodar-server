"""Assay app plugin for samplesheets"""

from django.conf import settings

from samplesheets.models import GenericMaterial, Process
from samplesheets.plugins import SampleSheetAssayPluginPoint


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for protein expression profiling / mass spectrometry in sample
    sheets"""

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_pep_ms'

    #: Title
    title = (
        'Sample Sheets Protein Expression Profiling / Mass Spectrometry '
        'Assay Plugin'
    )

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

    #: Raw data collection name
    raw_data_coll = 'RawData'

    #: MaxQuant results collection name
    max_quant_coll = 'MaxQuantResults'

    def get_row_path(self, row, table, assay):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default directory.
        :param assay: Assay object
        :param table: List of lists (table returned by SampleSheetTableBuilder)
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :return: String with full iRODS path or None
        """
        assay_path = self.get_assay_path(assay)

        if not assay_path:
            return None

        # TODO: Alternatives for RawData?
        return assay_path + '/' + self.raw_data_coll

    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row
        :param row: Original row (list of dicts)
        :param table: Full table (list of lists)
        :param assay: Assay object
        :return: List of dicts
        """
        if not settings.IRODS_WEBDAV_ENABLED or not assay:
            return row

        assay_path = self.get_assay_path(assay)

        if not assay_path:
            return row

        base_url = settings.IRODS_WEBDAV_URL + assay_path

        # Check if MaxQuant is found
        max_quant_found = False

        for cell in row:
            if (
                cell['obj_cls'] == Process
                and cell['field_name'] == 'analysis software name'
                and cell['value'] == 'MaxQuant'
            ):
                max_quant_found = True
                break

        for cell in row:
            # Data files
            if (
                cell['obj_cls'] == GenericMaterial
                and cell['item_type'] == 'DATA'
                and cell['field_name'] == 'name'
            ):
                # .raw files
                if cell['value'].split('.')[-1].lower() == 'raw':
                    cell['link'] = (
                        base_url
                        + '/'
                        + self.raw_data_coll
                        + '/'
                        + cell['value']
                    )
                    cell['link_file'] = True

            # Process parameter files
            elif (
                max_quant_found
                and cell['obj_cls'] == Process
                and cell['field_name'] == 'analysis database file'
            ):
                cell['link'] = (
                    base_url + '/' + self.max_quant_coll + '/' + cell['value']
                )
                cell['link_file'] = True

        return row
