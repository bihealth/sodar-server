from django.conf import settings

from projectroles.plugins import get_backend_api

from samplesheets.models import GenericMaterial, Process
from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.utils import get_last_material_index


# Local constants
RAW_DATA_COLL = 'RawData'
MAX_QUANT_COLL = 'MaxQuantResults'


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for protein expression profiling / mass spectrometry in sample
    sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_pep_ms'

    #: Title
    title = 'Sample Sheets Protein Expression Profiling / Mass Spectrometry ' \
            'Assay Plugin'

    # Properties defined in SampleSheetAssayPluginPoint ------------------

    #: Identifying assay fields (used to identify plugin by assay)
    measurement_type = 'protein expression profiling'
    technology_type = 'mass spectrometry'

    #: Description string
    description = 'Sample sheets protein expression profiling / mass ' \
                  'spectrometry assay plugin'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = 'samplesheets_assay_pep_ms/_assay.html'

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    def get_row_path(self, row, table, assay):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default directory.
        :param assay: Assay object
        :param table: List of lists (table returned by SampleSheetTableBuilder)
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :return: String with full iRODS path or None
        """
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return None

        # TODO: Alternatives for RawData?
        return irods_backend.get_path(assay) + '/' + RAW_DATA_COLL

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

        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return row

        base_url = settings.IRODS_WEBDAV_URL + irods_backend.get_path(assay)

        # Check if MaxQuant is found
        max_quant_found = False

        for cell in row:
            if (cell['obj_cls'] == Process and
                    cell['field_name'] == 'analysis software name' and
                    cell['value'] == 'MaxQuant'):
                max_quant_found = True
                break

        for cell in row:
            # Data files
            if (cell['obj_cls'] == GenericMaterial and
                    cell['item_type'] == 'DATA' and
                    cell['field_name'] == 'name'):
                # .raw files
                if cell['value'].split('.')[-1].lower() == 'raw':
                    cell['link'] = \
                        base_url + '/' + RAW_DATA_COLL + '/' + cell['value']
                    cell['link_file'] = True

            # Process parameter files
            elif (max_quant_found and
                  cell['obj_cls'] == Process and
                  cell['field_name'] == 'analysis database file'):
                cell['link'] = \
                    base_url + '/' + MAX_QUANT_COLL + '/' + cell['value']
                cell['link_file'] = True

        return row
