"""Rendering utilities for samplesheets"""

from altamisa.constants import table_headers as th
from altamisa.isatab.write_assay_study import RefTableBuilder
from datetime import date
import functools
import itertools
import logging
from packaging import version
import re
import time

from django.conf import settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI

from samplesheets.models import Process, GenericMaterial


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

# HACK: Special cases for inline file linking (see issue #817)
SPECIAL_FILE_LINK_HEADERS = ['report file']

header_re = re.compile(r'^([a-zA-Z\s]+)[\[](.+)[\]]$')
contact_re = re.compile(r'(.+?)\s?(?:[<|[])(.+?)(?:[>\]])')
logger = logging.getLogger(__name__)
app_settings = AppSettingAPI()


# Table building ---------------------------------------------------------------


class SampleSheetRenderingException(Exception):
    """Sample sheet rendering exception"""

    pass


class SampleSheetTableBuilder:
    """Class for building a dict table with table cells, their properties and
    headers, to be rendered as HTML on the site"""

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
        self._edit = False
        self._sheet_config = None

    # General data and cell functions ------------------------------------------

    @classmethod
    def _get_value(cls, field):
        """
        Return value of a field which can be either free text or term reference
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

    @classmethod
    def _get_ontology_url(cls, ontology_name, accession):
        """
        Return full URL for ontology reference.

        :param ontology_name: String
        :param accession: String (contains an URL)
        :return: String
        """
        if not settings.SHEETS_ONTOLOGY_URL_TEMPLATE:
            return accession

        # HACK: "HPO" is "HP" in bioontology.org
        # TODO: If there are more exceptions like this,
        # TODO: create a proper map in settings
        if (
            'bioontology.org' in settings.SHEETS_ONTOLOGY_URL_TEMPLATE
            and ontology_name == 'HPO'
        ):
            ontology_name = 'HP'

        return settings.SHEETS_ONTOLOGY_URL_TEMPLATE.format(
            ontology_name=ontology_name, accession=accession
        )

    @classmethod
    def _get_ontology_link(cls, ontology_name, accession):
        """
        Build ontology link(s).

        :param ontology_name: Ontology name
        :param accession: Ontology accession URL
        :return: String
        """
        return ';'.join(
            [
                cls._get_ontology_url(ontology_name, a)
                for a in accession.split(';')
            ]
        )

    def _add_top_header(self, obj, colspan):
        """Append columns to top header"""
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

        th = {'value': value.strip(), 'colour': colour, 'colspan': colspan}

        if self._edit:
            th['headers'] = obj.headers  # Store the full header for editing

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
            'obj_cls': obj.__class__.__name__,
            'item_type': obj.item_type
            if isinstance(obj, GenericMaterial)
            else None,
            'num_col': False,  # Will be checked for sorting later
            'config_set': False,
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
        if field_config and field_config.get('format') in ['double', 'integer']:
            header['col_type'] = (
                'UNIT' if field_config.get('unit') else 'NUMERIC'
            )

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

        elif (
            name.lower() == 'name' and header['item_type'] == 'DATA'
        ) or name.lower() in SPECIAL_FILE_LINK_HEADERS:  # HACK for issue #817
            header['col_type'] = 'LINK_FILE'

        else:
            header['col_type'] = None  # Default / to be determined later

        # Add extra data for editing
        if self._edit:
            header['type'] = header_type

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
        basic_val=True,
        # attrs=None,  # :param attrs: Optional attributes (dict)
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
        :param basic_val: Whether the value is a basic string (HACK for #730)
        """

        # Add header if first row
        if header_name and obj and self._first_row:
            self._add_header(header_name, header_type=header_type, obj=obj)

        # Get printable value in case the function is called with a reference
        if isinstance(value, dict):
            value = self._get_value(value)

        cell = {'value': value.strip() if isinstance(value, str) else value}

        if unit:
            cell['unit'] = unit.strip() if isinstance(unit, str) else unit

        if link:
            cell['link'] = link

        if tooltip:
            cell['tooltip'] = tooltip

        # Add extra data for editing
        if self._edit:
            cell['uuid'] = str(obj.sodar_uuid)  # Node UUID

            # Object reference UUID for special cases
            if header_type == 'protocol':
                cell['uuid_ref'] = str(obj.protocol.sodar_uuid)

        self._row.append(cell)

        # Store value for detecting unfilled columns
        col_value = 0 if not value else 1

        if self._first_row:
            self._col_values.append(col_value)

        elif col_value == 1 and self._col_values[self._col_idx] == 0:
            self._col_values[self._col_idx] = 1

        # Modify column type according to data
        if not self._field_header[self._col_idx]['col_type']:
            if (
                not basic_val
                or cell.get('link')
                or header_type == 'extract_label'
                or isinstance(cell['value'], dict)
                or (
                    isinstance(cell['value'], list)
                    and len(cell['value']) > 0
                    and isinstance(cell['value'][0], dict)
                )
            ):
                self._field_header[self._col_idx]['col_type'] = 'ONTOLOGY'

            elif cell.get('unit'):
                self._field_header[self._col_idx]['col_type'] = 'UNIT'

        self._col_idx += 1

    def _add_ordered_element(self, obj):
        """
        Append GenericMaterial or Process element to row along with its
        attributes. To be used with altamISA v0.1+, requires the "headers"
        field in each object.

        :param obj: GenericMaterial or Pocess object
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
                    header_type='field',
                    obj=obj,
                )

            # Special case: First Dimension
            elif isinstance(obj, Process) and h == th.SECOND_DIMENSION:
                self._add_annotation(
                    {'value': obj.second_dimension},
                    'Second Dimension',
                    header_type='field',
                    obj=obj,
                )

        # Add top header
        if self._first_row:
            self._add_top_header(obj, len(self._field_header) - old_header_len)

    def _add_annotation(self, ann, header, header_type, obj):
        """
        Append a single annotation to row as multiple cells. To be used with
        altamISA v0.1+.

        :param ann: Annotation value (string or Dict)
        :param header: Name of the column header (string)
        :param header_type: Header type (string or None)
        :param obj: GenericMaterial or Pocess object the annotation belongs to
        """
        val = ''
        unit = None
        link = None
        tooltip = None
        basic_val = False

        # Special case: Comments as parsed in SODAR v0.5.2 (see #629)
        # TODO: TBD: Should these be added in this function at all?
        if isinstance(ann, str):
            val = ann
            basic_val = True

        # Ontology reference
        # TODO: add original accession and ontology name when editing
        elif (
            isinstance(ann['value'], dict)
            and 'name' in ann['value']
            and ann['value']['name']
        ):
            if ann['value']['ontology_name']:
                tooltip = ann['value']['ontology_name']

            val = ann['value']['name']

            if ann['value']['ontology_name'] and ann['value']['accession']:
                link = self._get_ontology_link(
                    ann['value']['ontology_name'], ann['value']['accession']
                )

        # Empty ontology reference (this can happen with altamISA v0.1)
        elif isinstance(ann['value'], dict) and (
            'name' not in ann['value'] or not ann['value']['name']
        ):
            val = ''

        # List of dicts (altamISA v0.1+, SODAR v0.5.2+)
        # TODO: Refactor
        elif (
            isinstance(ann['value'], list)
            and len(ann['value']) > 0
            and isinstance(ann['value'][0], dict)
        ):
            val = list(ann['value'])

            for i in range(len(val)):
                new_val = dict(val[i])

                if isinstance(new_val['name'], str):
                    new_val['name'] = new_val['name'].strip()

                new_val['accession'] = self._get_ontology_url(
                    new_val['ontology_name'], new_val['accession']
                )
                val[i] = new_val

        # Basic value string OR a list of strings
        else:
            val = ann['value']
            basic_val = True

        # Add unit if present
        if isinstance(ann, dict) and 'unit' in ann:
            if isinstance(ann['unit'], dict):
                unit = ann['unit']['name']

            else:
                unit = ann['unit']

        self._add_cell(
            val,
            header,
            unit=unit,
            link=link,
            header_type=header_type,
            obj=obj,
            tooltip=tooltip,
            basic_val=basic_val,
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

    def _build_table(self, table_refs, node_map, study=None, assay=None):
        """
        Function for building a table for rendering.

        :param table_refs: Object unique_name:s in a list of lists
        :param node_map: Lookup dictionary containing objects
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

        for input_row in table_refs:
            col_pos = 0

            # Add elements in row
            for col in input_row:
                self._add_ordered_element(node_map[col])
                col_pos += 1

            self._append_row()
            row_id += 1

        # Aggregate column data for Vue app
        # TODO: Un-hackify and move this somewhere else
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
            header_len = round(_get_length(self._field_header[i]['value']))
            col_type = self._field_header[i]['col_type']

            if col_type == 'CONTACT':
                max_cell_len = max(
                    [
                        (
                            _get_length(
                                re.findall(contact_re, x[i]['value'])[0][0]
                            )
                            if x[i]['value']
                            and re.findall(contact_re, x[i]['value'])
                            else 0
                        )
                        for x in self._table_data
                    ]
                )

            elif col_type == 'EXTERNAL_LINKS':  # Special case, count elements
                header_len = 0  # Header length is not comparable

                max_cell_len = max(
                    [
                        _get_length(x[i]['value'], col_type)
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

        # Store index of last visible column
        col_last_vis = (
            len(self._col_values) - self._col_values[::-1].index(1) - 1
        )

        return {
            'top_header': self._top_header,
            'field_header': self._field_header,
            'table_data': self._table_data,
            'col_values': self._col_values,
            'col_last_vis': col_last_vis,
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
                'render study. Please ensure the validity of your ISAtab files'
            )
            logger.error(error_msg)
            raise SampleSheetRenderingException(error_msg)

        return all_refs

    def build_study_tables(self, study, edit=False, use_config=True):
        """
        Build study table and associated assay tables for rendering.

        :param study: Study object
        :param edit: Return extra data for editing if true (bool)
        :param use_config: Use sheet configuration in building (bool)
        :return: Dict
        """
        s_start = time.time()
        logger.debug(
            'Building study "{}" (pk={}, edit={})..'.format(
                study.get_name(), study.pk, edit
            )
        )

        # Get study config for column type detection
        if use_config:
            self._sheet_config = app_settings.get_app_setting(
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

        self._edit = edit
        self._parser_version = (
            version.parse(study.investigation.parser_version)
            if study.investigation.parser_version
            else version.parse('')
        )

        logger.debug(
            'altamISA version at import: {}'.format(
                self._parser_version
                if not isinstance(self._parser_version, version.LegacyVersion)
                else 'LEGACY'
            )
        )

        ret = {'study': None, 'assays': {}}
        nodes = study.get_nodes()
        all_refs = self.build_study_reference(study, nodes)
        sample_pos = [
            i for i, col in enumerate(all_refs[0]) if '-sample-' in col
        ][0]
        node_map = {n.unique_name: n for n in nodes}

        # Study ref table without duplicates
        sr = [row[: sample_pos + 1] for row in all_refs]
        study_refs = list(sr for sr, _ in itertools.groupby(sr))

        ret['study'] = self._build_table(study_refs, node_map, study=study)
        logger.debug(
            'Building study OK ({:.1f}s)'.format(time.time() - s_start)
        )

        # Assay tables
        assay_count = 0

        for assay in study.assays.all().order_by('pk'):
            a_start = time.time()
            logger.debug(
                'Building assay "{}" (pk={}, edit={})..'.format(
                    assay.get_name(), assay.pk, edit
                )
            )

            assay_search_str = '-a{}-'.format(assay_count)
            assay_refs = []

            for row in all_refs:
                if (
                    len(row) > sample_pos + 1
                    and assay_search_str in row[sample_pos + 1]
                ):
                    assay_refs.append(row)

            ret['assays'][str(assay.sodar_uuid)] = self._build_table(
                assay_refs, node_map, assay=assay
            )

            assay_count += 1
            logger.debug(
                'Building assay OK ({:.1f}s)'.format(time.time() - a_start)
            )

        return ret
