"""Assay app plugin for samplesheets"""

from django.conf import settings

from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.rendering import SIMPLE_LINK_TEMPLATE
from samplesheets.utils import get_top_header
from samplesheets.views import MISC_FILES_COLL, RESULTS_COLL


# Local constants
APP_NAME = 'samplesheets.assayapps.generic'
RESULTS_COMMENT = 'SODAR Assay Plugin ResRep'
MISC_FILES_COMMENT = 'SODAR Assay Plugin MiscFiles'
DATA_COMMENT_PREFIX = 'SODAR Assay Plugin Data'


class SampleSheetAssayPlugin(SampleSheetAssayPluginPoint):
    """Plugin for generic data linking in sample sheets"""

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_assay_generic'

    #: Title
    title = 'Generic Assay Plugin'

    #: App name for dynamic reference to app in e.g. caching
    app_name = APP_NAME

    #: Identifying assay fields (used to identify plugin by assay)
    # NOTE: This assay plugin is accessed by the "SODAR Assay Plugin" override
    assay_fields = []

    #: Description string
    description = 'Sample sheets generic assay app'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = None

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    display_row_links = True

    @classmethod
    def _create_linked_cols_from_comment(cls, cell, header, top_header, comment, collection):
        """
        Creates collection links for targeted columns.

        :param cell: Dict (obtained by iterating over a row)
        :param comment: Semicolon separated list of columns.
        :param collection: Target collection for links.
        """

        target_cols = assay.comments.get(comment).lower().split(';')

        if header['value'].lower() in target_cols:
            cell['value'] = SIMPLE_LINK_TEMPLATE.format(
                label=cell['value'],
                url=f"{base_url}/{collection}/{cell['value']}",
            )
        if top_header['value'].lower() in target_cols:
            cell['link'] = f"{base_url}/{collection}/{cell['value']}"

    @classmethod
    def _get_col_value(cls, target_col, row, table):
        """
        Return value of last matched column.

        :param target_col: Column name to look for
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :return: String with cell value of last matched column
        """
        # returns last match of row
        value = None
        if target_col:
            for i in range(len(row)):
                header = table['field_header'][i]
                if header['value'].lower() == target_col.lower():
                    value = row[i]['value']
        return value

    def get_row_path(self, row, table, assay, assay_path):
        """
        Return iRODS path for an assay row in a sample sheet. If None,
        display default path. Used if display_row_links = True.

        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :param assay_path: Root path for assay
        :return: String with full iRODS path or None
        """
        # Extract comments starting with DATA_COMMENT_PREFIX; sorted
        data_columns = [
            value
            for name, value in sorted(assay.comments.items())
            if name.startswith(DATA_COMMENT_PREFIX)
        ]

        data_collections = []
        for column_name in data_columns:
            data_collections.append(
                self._get_col_value(column_name, row, table)
            )

        # Build iRODS path from list and stop at first None value
        data_path = ''
        for col in data_collections:
            if col:
                data_path += f'/{col}'
            else:
                break

        if data_path:
            return assay_path + data_path
        return None

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

            # TODO: Check if two comments reference the same column header?
            # Create value links in columns
            #if assay.comments.get(RESULTS_COMMENT):
                #self._create_linked_cols_from_comment(row[i], header, top_header, RESULTS_COMMENT, RESULTS_COLL)

            # Create MiscFiles links
            #if assay.comments.get(MISC_FILES_COMMENT):
                #self._create_linked_cols_from_comment(row[i], header, top_header, MISC_FILES_COMMENT, MISC_FILES_COLL)

        return row

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        self._update_cache_rows(APP_NAME, name, project, user)
