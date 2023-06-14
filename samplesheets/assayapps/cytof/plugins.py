"""Assay app plugin for samplesheets"""

from django.conf import settings

from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.utils import get_top_header
from samplesheets.views import MISC_FILES_COLL
from samplesheets.rendering import SIMPLE_LINK_TEMPLATE


# Local constants
APP_NAME = 'samplesheets.assayapps.cytof'


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for mass cytometry assays in sample sheets"""

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_cytof'

    #: Title
    title = 'Mass Cytometry Assay Plugin'

    #: App name for dynamic reference to app in e.g. caching
    app_name = APP_NAME

    #: Identifying assay fields (used to identify plugin by assay)
    assay_fields = [
        {
            'measurement_type': 'protein expression profiling',
            'technology_type': 'mass cytometry',
        },
    ]

    #: Description string
    description = 'Sample sheets mass cytometry assay app'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = None

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    display_row_links = True

    def __get_mc_assay_name(self, row, table):
        """
        Return assay name of last mass cytometry process.
        Also works when there are consecutive processes of the same name.

        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        """
        name = None
        span_end = len(row)
        for i in range(len(row)):
            cell = row[i]
            header = table['field_header'][i]
            if (
                header['obj_cls'] == 'Process'
                and header['value'].lower() == 'protocol'
                and cell['value'].lower() == 'mass cytometry'
            ):
                top_header = get_top_header(table, i)
                span_end = i + top_header['colspan']

            # consider only columns of mass cytometry process
            if i < span_end and header['value'].lower() == 'assay name':
                name = cell['value']
        return name

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
        # Get the value of Mass cytometry Assay Name column
        mc_assay_name = self.__get_mc_assay_name(row, table)
        if mc_assay_name:
            return assay_path + '/' + mc_assay_name

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

        # Get the value of Mass cytometry Assay Name column
        mc_assay_name = self.__get_mc_assay_name(row, table)

        if not mc_assay_name:
            return row

        base_url = settings.IRODS_WEBDAV_URL + assay_path

        for i in range(len(row)):
            header = table['field_header'][i]
            top_header = get_top_header(table, i)

            # Create barcode key & antibody panel links in processes
            if (
                header['obj_cls'] == 'Process'
                and (
                    header['value'].lower() == 'antibody panel'
                    or header['value'].lower() == 'barcode key'
                )
                and row[i]['value']
            ):
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url
                    + '/'
                    + MISC_FILES_COLL
                    + '/'
                    + row[i]['value'],
                )

            # Create report file links in processes
            elif (
                header['obj_cls'] == 'Process'
                and header['value'].lower() == 'report file'
                and row[i]['value']
            ):
                row[i]['value'] = SIMPLE_LINK_TEMPLATE.format(
                    label=row[i]['value'],
                    url=base_url + '/' + mc_assay_name + '/' + row[i]['value'],
                )

            # Create data file links
            elif (
                header['obj_cls'] == 'GenericMaterial'
                and header['item_type'] == 'DATA'
                and header['value'].lower() == 'name'
                and top_header['value'].lower()
                in ['raw data file', 'derived data file']
            ):
                row[i]['link'] = (
                    base_url + '/' + mc_assay_name + '/' + row[i]['value']
                )

        return row

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        self._update_cache_rows(APP_NAME, name, project, user)
