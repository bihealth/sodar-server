"""Rendering utilities for samplesheets"""

import functools
import itertools
import logging
import re
import time

from datetime import date
from packaging import version

from altamisa.constants import table_headers as th
from altamisa.isatab.write_assay_study import RefTableBuilder

from django.conf import settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.plugins import get_backend_api

# Sodarcache dependency (see bihealth/sodar-core#1068)
from sodarcache.models import JSONCacheItem

from samplesheets.models import Process, GenericMaterial
from samplesheets.utils import get_node_obj


# Regex for headers
header_re = re.compile(r'^([a-zA-Z\s]+)[\[](.+)[\]]$')
# Rexex for simple links and contacts
link_re = re.compile(r'(.+?)\s?(?:[<|[])(.+?)(?:[>\]])')
logger = logging.getLogger(__name__)
app_settings = AppSettingAPI()


APP_NAME = 'samplesheets'
TOP_HEADER_MATERIAL_COLOURS = {
    'SOURCE': 'info',
    'SAMPLE': 'warning',
    'MATERIAL': 'success',
    'DATA': 'success',
}
TOP_HEADER_MATERIAL_VALUES = {
    'SOURCE': 'Source',
    'SAMPLE': 'Sample',
    'MATERIAL': 'Material',
    'DATA': 'Data File',
}
EMPTY_VALUE = '-'
STUDY_HIDEABLE_CLASS = 'sodar-ss-hideable-study'
SOURCE_SEARCH_STR = '-source-'
NARROW_CHARS = 'fIijlt;:.,/"!\'!()[]{}'
WIDE_CHARS = 'ABCDEFHKLMNOPQRSTUVXYZ<>%$_'
IGNORED_HEADERS = ['Unit', 'Term Source REF', 'Term Accession Number']
# Name fields (NOTE: Missing labeled extract name by purpose)
ALTAMISA_MATERIAL_NAMES = [
    th.EXTRACT_NAME,
    th.LIBRARY_NAME,
    th.SAMPLE_NAME,
    th.SOURCE_NAME,
]
# Attribute list lookup
LIST_ATTR_MAP = {
    th.CHARACTERISTICS: 'characteristics',
    th.COMMENT: 'comments',
    th.FACTOR_VALUE: 'factor_values',
    th.PARAMETER_VALUE: 'parameter_values',
}
# Basic fields lookup (header -> member of node)
BASIC_FIELD_MAP = {th.PERFORMER: 'performer', th.DATE: 'perform_date'}
# altamISA -> SODAR header name lookup
HEADER_MAP = {
    th.LABELED_EXTRACT_NAME: 'Label',
    th.PROTOCOL_REF: 'Protocol',
    th.PERFORMER: 'Performer',
    th.DATE: 'Perform Date',
}
# Map JSON attributes to model attributes
MODEL_JSON_ATTRS = [
    'characteristics',
    'comments',
    'factor_values',
    'parameter_values',
]
STUDY_TABLE_CACHE_ITEM = 'sheet/tables/study/{study}'
SIMPLE_LINK_TEMPLATE = '{label} <{url}>'


# Table building ---------------------------------------------------------------


class SampleSheetRenderingException(Exception):
    """Sample sheet rendering exception"""


class SampleSheetTableBuilder:
    """
    Class for building a sample sheet table as dict. Contains table cells, their
    properties and headers, to be rendered as HTML on the site or used in
    backend operations.
    """

    def __init__(self):
        self._study = None
        self._assay = None
        self._row = []
        self._top_header = []
        self._field_header = []
        self._field_configs = []
        self._table_data = []
        self._first_row = True
        self._col_values = []
        self._col_idx = 0
        self._node_idx = 0
        self._field_idx = 0
        self._parser_version = None
        self._sheet_config = None

    # General Data and Cell Functions ------------------------------------------

    @classmethod
    def _get_value(cls, field):
        """
        Return value of a field which can be either free text or term reference.

        :param field: Field (string or dict)
        :return: String
        """
        if isinstance(field, str):
            return field
        if isinstance(field, dict) and 'value' in field:
            if isinstance(field['value'], dict) and 'name' in field['value']:
                return field['value']['name']
            return field['value']
        return ''

    def _add_top_header(self, obj, colspan):
        """
        Append columns to top header.

        :param obj: GenericMaterial or Process object
        :param colspan: Column count for the node
        """
        if isinstance(obj, GenericMaterial):  # Material
            colour = TOP_HEADER_MATERIAL_COLOURS[obj.item_type]
            value = (
                obj.material_type
                if obj.material_type
                and obj.item_type not in ['SOURCE', 'SAMPLE']
                else TOP_HEADER_MATERIAL_VALUES[obj.item_type]
            )
        else:  # Process
            colour = 'danger'
            value = 'Process'
        th = {
            'value': value.strip(),
            'colour': colour,
            'colspan': colspan,
            'headers': obj.headers,
        }
        self._top_header.append(th)
        self._node_idx += 1
        self._field_idx = 0

    def _add_header(self, name, header_type=None, obj=None):
        """
        Add column field header value.

        :param name: Header name to be displayed as "value"
        :param header_type: Header type
        :param obj: Original Django model object
        """
        header = {
            'value': name.strip().title(),  # TODO: Better titling (#576)
            'name': name,  # Store original field name
            'type': header_type,
            'obj_cls': obj.__class__.__name__,
            'item_type': obj.item_type
            if isinstance(obj, GenericMaterial)
            else None,
        }
        field_config = None

        # Get existing field config
        if self._sheet_config:
            study_config = self._sheet_config['studies'][
                str(self._study.sodar_uuid)
            ]
            if not self._assay or self._node_idx < len(study_config['nodes']):
                field_config = study_config['nodes'][self._node_idx]['fields'][
                    self._field_idx
                ]
            else:  # Assay
                a_node_idx = self._node_idx - len(study_config['nodes'])
                field_config = study_config['assays'][
                    str(self._assay.sodar_uuid)
                ]['nodes'][a_node_idx]['fields'][self._field_idx]

        # Save info on whether a pre-existing config is set for this field
        if field_config and field_config.get('format'):
            self._field_configs.append(True)
        else:
            self._field_configs.append(False)

        # Column type (the ones we can determine at this point)
        if (
            field_config
            and field_config.get('format') in ['double', 'integer']
            and not obj.has_unit(name, header_type)
        ):
            header['col_type'] = 'NUMERIC'

        # Else detect type without config
        elif (
            name.lower() == 'name' or name in th.PROCESS_NAME_HEADERS
        ) and header['item_type'] != 'DATA':
            header['col_type'] = 'NAME'
        elif name.lower() == 'protocol':
            header['col_type'] = 'PROTOCOL'
        elif 'contact' in name.lower() or name == 'Performer':
            header['col_type'] = 'CONTACT'
        elif name == 'Perform Date':
            header['col_type'] = 'DATE'
        elif name.lower() == 'external links':
            header['col_type'] = 'EXTERNAL_LINKS'
        elif name.lower() == 'name' and header['item_type'] == 'DATA':
            header['col_type'] = 'LINK_FILE'
        # Recognize ONTOLOGY by headers
        elif obj.is_ontology_field(name, header_type):
            header['col_type'] = 'ONTOLOGY'
        # Recognize UNIT by headers
        elif obj.has_unit(name, header_type):
            header['col_type'] = 'UNIT'
        else:
            header['col_type'] = None  # Default / to be determined later

        self._field_header.append(header)
        self._field_idx += 1

    def _add_cell(
        self,
        value,
        header_name,
        unit=None,
        link=None,
        header_type=None,
        obj=None,
        tooltip=None,
    ):
        """
        Add cell data. Also maintain column value list and insert header if on
        the first row and required parameters are supplied.

        :param value: Value to be displayed in the cell
        :param header_name: Name of the column header
        :param unit: Unit to be displayed in the cell
        :param link: Link from the value (URL string)
        :param header_type: Header type (string)
        :param obj: Original Django model object
        :param tooltip: Tooltip to be shown on mouse hover (string)
        """
        # Add header if first row
        if header_name and obj and self._first_row:
            self._add_header(header_name, header_type=header_type, obj=obj)

        # Get printable value in case the function is called with a reference
        if isinstance(value, dict):
            value = self._get_value(value)
        # Format date into text
        if isinstance(value, date):
            value = value.strftime('%Y-%m-%d')
        cell = {'value': value.strip() if isinstance(value, str) else value}
        if unit:
            cell['unit'] = unit.strip() if isinstance(unit, str) else unit
        if link:
            cell['link'] = link
        if tooltip:
            cell['tooltip'] = tooltip

        # Add extra data for editing
        # Only add object UUID for name and protocol headers
        if header_type in ['name', 'protocol']:
            cell['uuid'] = str(obj.sodar_uuid)
        # Reference UUID to another object for special cases
        if header_type == 'protocol':
            cell['uuid_ref'] = str(obj.protocol.sodar_uuid)
        self._row.append(cell)

        # Store value for detecting unfilled columns
        col_value = 0 if not value else 1
        if self._first_row:
            self._col_values.append(col_value)
        elif col_value == 1 and self._col_values[self._col_idx] == 0:
            self._col_values[self._col_idx] = 1
        self._col_idx += 1

    def _add_ordered_element(self, obj):
        """
        Append GenericMaterial or Process element to row along with its
        attributes. To be used with altamISA v0.1+, requires the "headers"
        field in each object.

        :param obj: GenericMaterial or Process object
        """
        old_header_len = len(self._field_header)
        headers = [h for h in obj.headers if h not in IGNORED_HEADERS]

        for h in headers:
            list_ref = re.findall(header_re, h)
            # Value lists with possible ontology annotation
            if list_ref:
                h_type = list_ref[0][0]
                h_name = list_ref[0][1]
                if h_type in LIST_ATTR_MAP and hasattr(
                    obj, LIST_ATTR_MAP[h_type]
                ):
                    obj_attr = getattr(obj, LIST_ATTR_MAP[h_type])
                    if h_name in obj_attr:
                        self._add_annotation(
                            obj_attr[h_name],
                            h_name,
                            header_type=LIST_ATTR_MAP[h_type],
                            obj=obj,
                        )
            # Basic fields we can simply map using BASIC_FIELD_MAP
            elif h in BASIC_FIELD_MAP and hasattr(obj, BASIC_FIELD_MAP[h]):
                self._add_cell(
                    getattr(obj, BASIC_FIELD_MAP[h]),
                    HEADER_MAP[h],
                    header_type=BASIC_FIELD_MAP[h],
                    obj=obj,
                )
            # Special case: Name
            elif h in ALTAMISA_MATERIAL_NAMES or h in th.DATA_FILE_HEADERS:
                self._add_cell(obj.name, 'Name', header_type='name', obj=obj)
            # Special case: Labeled Extract Name & Label
            elif h == th.LABELED_EXTRACT_NAME and hasattr(obj, 'extract_label'):
                self._add_cell(obj.name, 'Name', header_type='name', obj=obj)
                self._add_annotation(
                    {'value': obj.extract_label},
                    HEADER_MAP[th.LABELED_EXTRACT_NAME],
                    header_type='extract_label',
                    obj=obj,
                )
            # Special case: Array Design REF (NOTE: not actually a reference!)
            elif h == th.ARRAY_DESIGN_REF and hasattr(obj, 'array_design_ref'):
                self._add_cell(
                    obj.array_design_ref, 'Array Design REF', obj=obj
                )
            # Special case: Protocol Name
            elif (
                h == th.PROTOCOL_REF
                and hasattr(obj, 'protocol')
                and obj.protocol
            ):
                self._add_cell(
                    obj.protocol.name,
                    HEADER_MAP[th.PROTOCOL_REF],
                    header_type='protocol',
                    obj=obj,
                )
            # Special case: Process Name
            elif isinstance(obj, Process) and h in th.PROCESS_NAME_HEADERS:
                self._add_cell(obj.name, h, header_type='process_name', obj=obj)
            # Special case: First Dimension
            elif isinstance(obj, Process) and h == th.FIRST_DIMENSION:
                self._add_annotation(
                    {'value': obj.first_dimension},
                    'First Dimension',
                    header_type='first_dimension',
                    obj=obj,
                )
            # Special case: Second Dimension
            elif isinstance(obj, Process) and h == th.SECOND_DIMENSION:
                self._add_annotation(
                    {'value': obj.second_dimension},
                    'Second Dimension',
                    header_type='second_dimension',
                    obj=obj,
                )

        # Add top header
        if self._first_row:
            self._add_top_header(obj, len(self._field_header) - old_header_len)

    def _add_annotation(self, ann, header, header_type, obj):
        """
        Append an ontology annotation or list of values to a row as a single
        cell.

        :param ann: Annotation value (string or Dict)
        :param header: Name of the column header (string)
        :param header_type: Header type (string or None)
        :param obj: GenericMaterial or Process object the annotation belongs to
        """
        unit = None
        # Special case: Comments as parsed in SODAR v0.5.2 (see #629)
        # TODO: TBD: Should these be added in this function at all?
        if isinstance(ann, str):
            val = ann
        # Ontology reference(s) (altamISA v0.1+, SODAR v0.5.2+)
        elif isinstance(ann['value'], dict) or (
            isinstance(ann['value'], list)
            and len(ann['value']) > 0
            and isinstance(ann['value'][0], dict)
        ):
            val = []
            tmp_val = ann['value']
            # Make single reference into a list for simpler rendering
            if isinstance(ann['value'], dict):
                tmp_val = [ann['value']]
            if not tmp_val[0].get('name'):
                val = ''
            else:
                for v in tmp_val:
                    v = dict(v)
                    if isinstance(v['name'], str):
                        v['name'] = v['name'].strip()  # Cleanup name
                    elif v['name'] is None:
                        v['name'] = ''
                    val.append(v)
        # Basic value string OR a list of strings
        else:
            val = ann['value']

        # Add unit if present (only for non-list values)
        # TODO: provide full ontology value for editing once supporting
        if isinstance(ann, dict) and 'unit' in ann:
            if isinstance(ann['unit'], dict):
                unit = ann['unit']['name']
            else:
                unit = ann['unit']

        self._add_cell(
            val,
            header,
            unit=unit,
            link=None,  # Link will be retrieved from each ontology term
            header_type=header_type,
            obj=obj,
            tooltip=None,  # Tooltip will be retrieved from each ontology term
        )

    # Table building functions -------------------------------------------------

    def _append_row(self):
        """Append current row to table data and cleanup"""
        self._table_data.append(self._row)
        self._row = []
        self._first_row = False
        self._col_idx = 0
        self._node_idx = 0
        self._field_idx = 0

    def _add_ui_table_data(self):
        """Add UI specific data to a table"""
        # TODO: Un-hackify

        def _get_length(value, col_type=None):
            """Return estimated length for proportional text"""
            if not value:
                return 0
            # Convert perform date
            if isinstance(value, date):
                value = str(value)
            # Lists (altamISA v0.1+)
            elif isinstance(value, list) and col_type != 'EXTERNAL_LINKS':
                if isinstance(value[0], dict):
                    value = '; '.join([x['name'] for x in value])
                elif isinstance(value[0], list) and value[0]:
                    value = '; '.join([x[0] for x in value])
                elif isinstance(value[0], str):
                    value = '; '.join(value)
            # Simple link or contact
            else:
                link_groups = re.findall(link_re, value)
                if link_groups:
                    value = link_groups[0][0]

            # Very unscientific and font-specific, don't try this at home
            nc = sum([value.count(c) for c in NARROW_CHARS])
            wc = sum([value.count(c) for c in WIDE_CHARS])
            return round(len(value) - nc - wc + 0.6 * nc + 1.3 * wc)

        def _is_num(value):
            """Return whether a value contains an integer/double"""
            if isinstance(value, str) and '_' in value:
                return False  # HACK because float() accepts underscore
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False

        top_idx = 0  # Top header index
        grp_idx = 0  # Index within current top header group
        for i in range(len(self._field_header)):
            header_name = self._field_header[i]['value']
            # Set column type to NUMERIC if values are all numeric or empty
            # (except if name or process name)
            # Skip check if column is already defined as UNIT
            if (
                header_name != 'Name'
                and header_name not in th.PROCESS_NAME_HEADERS
                and not self._field_configs[i]
                and self._field_header[i]['col_type'] not in ['NUMERIC', 'UNIT']
                and any(_is_num(x[i]['value']) for x in self._table_data)
                and all(
                    (_is_num(x[i]['value']) or not x[i]['value'])
                    for x in self._table_data
                )
            ):
                self._field_header[i]['col_type'] = 'NUMERIC'

            # Maximum column value length for column width estimate
            field_header_len = round(
                _get_length(self._field_header[i]['value'])
            )
            # If there is only one column in top header, use top header length
            if self._top_header[top_idx]['colspan'] == 1:
                top_header_len = round(
                    _get_length(self._top_header[top_idx]['value'])
                )
                header_len = max(field_header_len, top_header_len)
            else:
                header_len = field_header_len

            col_type = self._field_header[i]['col_type']
            if col_type == 'CONTACT':
                max_cell_len = max(
                    [
                        (
                            _get_length(
                                re.findall(link_re, x[i]['value'])[0][0]
                            )
                            if re.findall(link_re, x[i].get('value'))
                            else len(x[i].get('value') or '')
                        )
                        for x in self._table_data
                    ]
                )
            elif col_type == 'EXTERNAL_LINKS':  # Special case, count elements
                header_len = 0  # Header length is not comparable
                max_cell_len = max(
                    [
                        len(x[i]['value'])
                        if (x[i]['value'] and isinstance(x[i]['value'], list))
                        else 0
                        for x in self._table_data
                    ]
                )
            else:  # Generic type
                max_cell_len = max(
                    [
                        _get_length(x[i]['value'], col_type)
                        + _get_length(x[i].get('unit'), col_type)
                        + 1
                        for x in self._table_data
                    ]
                )
            self._field_header[i]['max_value_len'] = max(
                [header_len, max_cell_len]
            )

            if grp_idx == self._top_header[top_idx]['colspan'] - 1:
                top_idx += 1
                grp_idx = 0
            else:
                grp_idx += 1

    def _build_table(self, table_refs, node_map=None, study=None, assay=None):
        """
        Build a table from the node graph reference.

        :param table_refs: Object unique_name:s in a list of lists
        :param node_map: Lookup dictionary containing objects (optional)
        :param study: Study object (optional, required if rendering study)
        :param assay: Assay object (optional, required if rendering assay)
        :raise: ValueError if both study and assay are None
        :return: Dict
        """
        if not study and not assay:
            raise ValueError('Either study or assay must be defined')

        self._study = study or assay.study
        self._assay = assay
        self._row = []
        self._top_header = []
        self._field_header = []
        self._field_configs = []
        self._table_data = []
        self._first_row = True
        self._col_values = []
        self._col_idx = 0
        row_id = 0
        if not node_map:
            node_map = self.get_node_map(self._study.get_nodes())

        for input_row in table_refs:
            col_pos = 0
            # Add elements in row
            for col in input_row:
                self._add_ordered_element(node_map[col])
                col_pos += 1
            self._append_row()
            row_id += 1

        # Aggregate UI specific data, store index of last visible column
        self._add_ui_table_data()
        return {
            'top_header': self._top_header,
            'field_header': self._field_header,
            'table_data': self._table_data,
            'col_values': self._col_values,
            'col_last_vis': len(self._col_values)
            - self._col_values[::-1].index(1)
            - 1,
        }

    @classmethod
    def build_study_reference(cls, study, nodes=None):
        """
        Get study reference table for building final table data.

        :param study: Study object
        :param nodes: Study nodes (optional)
        :return: Nodes (list), table (list)
        """
        if not nodes:
            nodes = study.get_nodes()
        arcs = study.arcs
        for a in study.assays.all().order_by('file_name'):
            arcs += a.arcs

        def _is_of_starting_type(starting_type, v):
            """Predicate to select vertices based on starting type."""
            return getattr(v, 'item_type', None) == starting_type

        # starting_type = 'Source Name'
        tb = RefTableBuilder(
            nodes, arcs, functools.partial(_is_of_starting_type, 'SOURCE')
        )
        all_refs = tb.run()
        if not all_refs:
            error_msg = (
                'RefTableBuilder failed to build a table from graph, unable to '
                'render study. Please ensure the validity of your ISA-Tab files'
            )
            logger.error(error_msg)
            raise SampleSheetRenderingException(error_msg)
        return all_refs

    @classmethod
    def get_sample_idx(cls, all_refs):
        """
        Get sample index for a reference table.

        :param all_refs: All references for a study (list).
        :return: Integer
        """
        return [i for i, col in enumerate(all_refs[0]) if '-sample-' in col][0]

    @classmethod
    def get_node_map(cls, nodes):
        """
        Get dict mapped by unique name for a QuerySet or list of node objects.

        :param nodes: QuerySet or list
        :return: Dict
        """
        return {n.unique_name: n for n in nodes}

    @classmethod
    def get_study_refs(cls, all_refs, sample_idx=None):
        """
        Get study table references without duplicates.

        :param all_refs: All references for a study.
        :param sample_idx: Integer for sample column index (optional)
        :return: List
        """
        if not sample_idx:
            sample_idx = cls.get_sample_idx(all_refs)
        sr = [row[: sample_idx + 1] for row in all_refs]
        return list(sr for sr, _ in itertools.groupby(sr))

    @classmethod
    def get_assay_refs(cls, all_refs, assay_id, sample_idx, study_cols=True):
        """
        Return assay table references based on assay ID.

        :param all_refs:
        :param assay_id: Integer for assay ID
        :param sample_idx: Integer for sample column index
        :param study_cols: Include study columns if True (bool)
        :return: List
        """
        assay_search_str = '-a{}-'.format(assay_id)
        assay_refs = []
        start_idx = 0 if study_cols else sample_idx
        for row in all_refs:
            if (
                len(row) > sample_idx + 1
                and assay_search_str in row[sample_idx + 1]
            ):
                assay_refs.append(row[start_idx:])
        return assay_refs

    def get_headers(self, investigation):
        """
        Return lists of headers for the studies and assays in an investigation.

        :param investigation: Investigation object
        :return: Dict
        """
        ret = {'studies': []}
        for study in investigation.studies.all().order_by('pk'):
            study_data = {'headers': [], 'assays': []}
            all_refs = self.build_study_reference(study, study.get_nodes())
            sample_idx = self.get_sample_idx(all_refs)
            study_refs = self.get_study_refs(all_refs, sample_idx)
            assay_id = 0

            for n in study_refs[0]:
                study_data['headers'] += get_node_obj(
                    study=study, unique_name=n
                ).headers

            for assay in study.assays.all().order_by('pk'):
                assay_refs = self.get_assay_refs(all_refs, assay_id, sample_idx)
                assay_headers = []
                for i in range(sample_idx + 1, len(assay_refs[0])):
                    assay_headers += get_node_obj(
                        assay=assay, unique_name=assay_refs[0][i]
                    ).headers
                study_data['assays'].append(assay_headers)
                assay_id += 1

            ret['studies'].append(study_data)
        return ret

    def build_study_tables(self, study, use_config=True):
        """
        Build study table and associated assay tables for rendering.

        :param study: Study object
        :param use_config: Use sheet configuration in building (bool)
        :return: Dict
        """
        s_start = time.time()
        logger.debug(
            'Building study "{}" ({})..'.format(
                study.get_name(), study.sodar_uuid
            )
        )
        # Get study config for column type detection
        if use_config:
            self._sheet_config = app_settings.get(
                'samplesheets', 'sheet_config', project=study.get_project()
            )
        # HACK: In case of deletion from database bypassing the database,
        # HACK: make sure the correct UUIDs are in the config
        if (
            self._sheet_config
            and str(study.sodar_uuid) not in self._sheet_config['studies']
        ):
            logger.warning(
                'Unable to use sheet configuration, study UUID not found'
            )
            self._sheet_config = None
        elif self._sheet_config:
            logger.debug('Using sheet configuration from app settings')
        elif not use_config:
            logger.debug('Not using sheet configuration (use_config=False)')
        else:
            logger.debug('No sheet configuration found in app settings')

        # NOTE: Parsing version here in case of version-specific tweaks
        self._parser_version = (
            version.parse(study.investigation.parser_version)
            if study.investigation.parser_version
            else None
        )
        logger.debug(
            'altamISA version at import: {}'.format(
                self._parser_version if self._parser_version else 'LEGACY'
            )
        )

        ret = {'study': None, 'assays': {}}
        nodes = study.get_nodes()
        all_refs = self.build_study_reference(study, nodes)
        sample_idx = self.get_sample_idx(all_refs)
        node_map = self.get_node_map(nodes)

        # Study ref table without duplicates
        study_refs = self.get_study_refs(all_refs, sample_idx)
        ret['study'] = self._build_table(study_refs, node_map, study=study)
        logger.debug(
            'Building study OK ({:.1f}s)'.format(time.time() - s_start)
        )

        # Assay tables
        assay_id = 0
        for assay in study.assays.all().order_by('pk'):
            a_start = time.time()
            logger.debug(
                'Building assay "{}" ({})..'.format(
                    assay.get_name(), assay.sodar_uuid
                )
            )
            assay_refs = self.get_assay_refs(all_refs, assay_id, sample_idx)
            ret['assays'][str(assay.sodar_uuid)] = self._build_table(
                assay_refs, node_map, assay=assay
            )
            assay_id += 1
            logger.debug(
                'Building assay OK ({:.1f}s)'.format(time.time() - a_start)
            )
        return ret

    def build_inv_tables(self, investigation, use_config=True):
        """
        Build all study and assay tables of an investigation for rendering.

        :param investigation: Investigation object
        :param use_config: Use sheet configuration in building (bool)
        :return: Dict
        """
        ret = {}
        for study in investigation.studies.all().order_by('pk'):
            ret[study] = self.build_study_tables(study, use_config=use_config)
        return ret

    def get_study_tables(self, study):
        """
        Get study and assay tables for rendering. Retrieve from sodarcache or
        build and save to cache if not found.

        :param study: Study object
        :return: Dict
        """
        logger.info(
            'Retrieving cached render tables for study "{}" ({})'.format(
                study.get_name(), study.sodar_uuid
            )
        )
        cache_backend = get_backend_api('sodar_cache')
        item_name = STUDY_TABLE_CACHE_ITEM.format(study=study.sodar_uuid)
        project = study.get_project()
        if settings.SHEETS_ENABLE_STUDY_TABLE_CACHE:
            # Get cached tables
            if cache_backend:
                item = cache_backend.get_cache_item(
                    app_name=APP_NAME,
                    name=item_name,
                    project=project,
                )
                if item and item.data:
                    logger.debug('Returning cached study tables')
                    return item.data
                logger.debug('Cache item "{}" not set'.format(item_name))
        else:
            logger.debug(
                'Study table cache disabled in settings, building new tables'
            )

        # If not found in cache, build and save tables
        study_tables = self.build_study_tables(study, use_config=True)
        if cache_backend:
            try:
                cache_backend.set_cache_item(
                    app_name=APP_NAME,
                    name=item_name,
                    data=study_tables,
                    project=project,
                )
                logger.debug('Set cache item "{}"'.format(item_name))
            except Exception as ex:
                logger.error(
                    'Failed to set cache item "{}": {}'.format(item_name, ex)
                )
        return study_tables

    @classmethod
    def clear_study_cache(cls, study, delete=False):
        """
        Clear study render table data from sodarcache, if cache is enabled and
        cached tables exist.

        :param study: Study object
        :param delete: Delete item instead of clearing value if true (bool)
        """
        cache_backend = get_backend_api('sodar_cache')
        if cache_backend:
            item_name = STUDY_TABLE_CACHE_ITEM.format(study=study.sodar_uuid)
            project = study.get_project()
            item_kwargs = {
                'app_name': APP_NAME,
                'name': item_name,
                'project': project,
            }
            try:
                msg = 'Cleared cache item "{}"'.format(item_name)
                if delete:
                    # TODO: Use delete method (see bihealth/sodar-core#1068)
                    item = JSONCacheItem.objects.filter(**item_kwargs).first()
                    if item:
                        item.delete()
                        logger.debug(msg + ' (delete setting object)')
                else:
                    item = cache_backend.get_cache_item(**item_kwargs)
                    if item:
                        cache_backend.set_cache_item(
                            app_name=APP_NAME,
                            name=item_name,
                            data={},
                            project=project,
                        )
                        logger.debug(msg + ' (clear value)')
            except Exception as ex:
                logger.error(
                    'Failed to clear cache item "{}": {}'.format(item_name, ex)
                )
