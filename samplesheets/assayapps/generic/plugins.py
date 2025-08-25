"""Assay app plugin for samplesheets"""

import re

from typing import Optional

from altamisa.constants import table_headers as th

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODARUser

from samplesheets.models import Assay
from samplesheets.plugins import SampleSheetAssayPluginPoint
from samplesheets.rendering import SIMPLE_LINK_TEMPLATE
from samplesheets.utils import get_top_header
from samplesheets.views import MISC_FILES_COLL, RESULTS_COLL


# Local constants
APP_NAME = 'samplesheets.assayapps.generic'
RESULTS_COMMENT = 'SODAR Assay Link ResultsReports'
MISC_FILES_COMMENT = 'SODAR Assay Link MiscFiles'
DATA_COMMENT_PREFIX = 'SODAR Assay Row Path'
DATA_LINK_COMMENT = 'SODAR Assay Link Row'
LINK_NAME_HEADERS = th.DATA_FILE_HEADERS + th.MATERIAL_NAME_HEADERS


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
    description = 'Creates data links from comments in ISA investigation file'

    #: Template for assay addition (Assay object as "assay" in context)
    assay_template = None

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    display_row_links = True

    @staticmethod
    def _link_from_comment(
        cell, header: dict, top_header: dict, target_cols: list, url: str
    ) -> bool:
        """
        Create collection links for targeted columns.

        :param cell: Dict (obtained by iterating over a row)
        :param header: Column header (dict)
        :param top_header: Column top header (dict)
        :param target_cols: List of column names
        :param url: Base URL for link target
        :return: Bool
        """
        # Special case for material names
        if (
            top_header['value'] in LINK_NAME_HEADERS
            and top_header['value'].lower() in target_cols
            and (header['value'].lower() == 'name')
        ):
            cell['link'] = f"{url}/{cell['value']}"
            return True
        # Handle everything else
        if header['value'].lower() in target_cols:
            cell['value'] = SIMPLE_LINK_TEMPLATE.format(
                label=cell['value'],
                url=f"{url}/{cell['value']}",
            )
            return True
        return False

    @classmethod
    def _get_col_value(
        cls, target_col: str, row: list[dict], table: dict
    ) -> Optional[str]:
        """
        Return value of last matched column.

        :param target_col: Column name (string)
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :return: String with cell value of last matched column or None
        """
        # Returns last match of row
        value = None
        if target_col:
            for i in range(len(row)):
                header = table['field_header'][i]
                if header['value'].lower() == target_col.lower():
                    value = row[i]['value']

        if isinstance(value, str):
            return value
        elif isinstance(value, list) and len(value) == 1:  # OntologyTermRefs
            return value[0]['name']
        return None

    def get_row_path(
        self, row: list[dict], table: dict, assay: Assay, assay_path: str
    ) -> Optional[str]:
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
            col_value = self._get_col_value(column_name, row, table)
            if col_value:
                data_collections.append(col_value)
        # Build iRODS path from list and stop at first None value
        if data_collections:
            data_path = '/' + '/'.join(data_collections)
            return assay_path + data_path
        return None

    def update_row(
        self, row: list[dict], table: dict, assay: Assay, index: int
    ) -> list[dict]:
        """
        Update render table row with e.g. links. Return the modified row.

        :param row: Original row (list of dicts)
        :param table: Full table (dict)
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

        results_cols = assay.comments.get(RESULTS_COMMENT)
        if results_cols:
            results_cols = results_cols.lower().split(';')
        misc_cols = assay.comments.get(MISC_FILES_COMMENT)
        if misc_cols:
            misc_cols = misc_cols.lower().split(';')
        data_cols = assay.comments.get(DATA_LINK_COMMENT)
        if data_cols:
            data_cols = data_cols.lower().split(';')
            if 'irods_paths' in table and table['irods_paths'][index]:
                row_path = table['irods_paths'][index]['path']
            else:
                row_path = self.get_row_path(row, table, assay, assay_path)

        for i in range(len(row)):
            header = table['field_header'][i]
            if not top_header or i >= th_colspan:
                top_header = get_top_header(table, i)
                th_colspan += top_header['colspan']
            # Skip if value is empty, not a string or already contains a link
            if (
                not row[i]['value']
                or not isinstance(row[i]['value'], str)
                or re.search('.+ <.*>', row[i]['value'])
            ):
                continue
            # TODO: Check if two comments reference the same column header?
            # Create Results link
            if results_cols and self._link_from_comment(
                row[i],
                header,
                top_header,
                results_cols,
                f'{base_url}/{RESULTS_COLL}',
            ):
                continue
            # Create MiscFiles link
            if misc_cols and self._link_from_comment(
                row[i],
                header,
                top_header,
                misc_cols,
                f'{base_url}/{MISC_FILES_COLL}',
            ):
                continue
            # Create DataCollection link
            if data_cols:
                self._link_from_comment(
                    row[i],
                    header,
                    top_header,
                    data_cols,
                    f'{settings.IRODS_WEBDAV_URL}{row_path}',
                )
        return row

    def update_cache(
        self,
        name: Optional[str] = None,
        project: Optional[str] = None,
        user: Optional[SODARUser] = None,
    ):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        self.update_cache_rows(APP_NAME, name, project, user)
