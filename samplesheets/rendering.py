"""Rendering utilities for samplesheets"""

from altamisa.constants import table_headers as th
from datetime import date
import itertools
import logging
from packaging import version
import re
import time

from django.conf import settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI

from .models import Process, GenericMaterial


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

# Basic fields lookup (header -> member of element)
BASIC_FIELD_MAP = {th.PERFORMER: 'performer', th.DATE: 'perform_date'}

# altamISA -> SODAR header name lookup
HEADER_MAP = {
    th.LABELED_EXTRACT_NAME: 'Label',
    th.PROTOCOL_REF: 'Protocol',
    th.PERFORMER: 'Performer',
    th.DATE: 'Perform Date',
}

header_re = re.compile(r'^([a-zA-Z\s]+)[\[](.+)[\]]$')
contact_re = re.compile(r'(.+?)\s?(?:[<|[])(.+?)(?:[>\]])')
logger = logging.getLogger(__name__)
app_settings = AppSettingAPI()


# Graph traversal / reference table building -----------------------------------


class Digraph:
    """Simple class encapsulating directed graph with vertices and arcs"""

    def __init__(self, vertices, arcs):
        self.vertices = vertices
        self.arcs = arcs
        self.v_by_name = {v.unique_name: v for v in self.vertices}
        self.a_by_name = {(a[0], a[1]) for a in self.arcs}
        self.source_names = [
            k for k in self.v_by_name.keys() if SOURCE_SEARCH_STR in k
        ]
        self.outgoing = {}

        for s_name, t_name in self.a_by_name:
            self.outgoing.setdefault(s_name, []).append(t_name)


class UnionFind:
    """Union-Find (disjoint set) data structure allowing to address by vertex
    name"""

    def __init__(self, vertex_names):
        self.name_to_id = {i: v for i, v in enumerate(vertex_names)}
        self.id_to_name = {v: i for i, v in self.name_to_id.items()}
        self._id = list(range(len(vertex_names)))
        self._sz = [1] * len(vertex_names)

    def find(self, v):
        assert type(v) is int
        j = v

        while j != self._id[j]:
            self._id[j] = self._id[self._id[j]]
            j = self._id[j]

        return j

    def find_by_name(self, v_name):
        return self.find(self.id_to_name[v_name])

    def union_by_name(self, v_name, w_name):
        self.union(self.find_by_name(v_name), self.find_by_name(w_name))

    def union(self, v, w):
        assert type(v) is int
        assert type(w) is int
        i = self.find(v)
        j = self.find(w)

        if i == j:
            return

        if self._sz[i] < self._sz[j]:
            self._id[i] = j
            self._sz[j] += self._sz[i]

        else:
            self._id[j] = i

        self._sz[i] += self._sz[j]


class RefTableBuilder:
    """Class for building reference table from a graph"""

    def __init__(self, nodes, arcs):
        self.digraph = Digraph(nodes, arcs)
        self._rows = []

    def _partition(self):
        uf = UnionFind(self.digraph.v_by_name.keys())

        for arc in self.digraph.arcs:
            uf.union_by_name(arc[0], arc[1])

        result = {}

        for v_name in self.digraph.v_by_name.keys():
            result.setdefault(v_name, []).append(v_name)

        return list(result.values())

    def _dump_row(self, v_names):
        self._rows.append(list(v_names))

    def _dfs(self, source, path):
        next_v_names = None

        if source in self.digraph.outgoing:
            next_v_names = self.digraph.outgoing[source]

        if next_v_names:
            for target in next_v_names:
                path.append(target)
                self._dfs(target, path)
                path.pop()

        else:
            self._dump_row(path)

    def _process_component(self, v_names):
        sources = list(sorted(set(v_names) & set(self.digraph.source_names)))

        for source in sources:
            self._dfs(source, [source])

    def run(self):
        components = self._partition()

        for component in components:
            self._process_component(component)

        return self._rows


# Table building ---------------------------------------------------------------


class SampleSheetRenderingException(Exception):
    """Sample sheet rendering exception"""

    pass


class SampleSheetTableBuilder:
    """Class for building a dict table with table cells, their properties and
    headers, to be rendered as HTML on the site"""

    def __init__(self):
        self._row = []
        self._top_header = []
        self._field_header = []
        self._table_data = []
        self._first_row = True
        self._col_values = []
        self._col_idx = 0
        self._parser_version = None

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
                else TOP_HEADER_MATERIAL_VALUES[obj.item_type]
            )

        else:  # Process
            colour = 'danger'
            value = 'Process'

        self._top_header.append(
            {'value': value, 'colour': colour, 'colspan': colspan}
        )

    def _add_header(self, value, obj=None):
        """
        Add column field header value.

        :param value: Value to be displayed
        :param obj: Original Django model object
        """
        self._field_header.append(
            {
                'value': value.title(),  # TODO: Better titling (see #576)
                'obj_cls': obj.__class__.__name__,
                'item_type': obj.item_type
                if isinstance(obj, GenericMaterial)
                else None,
            }
        )

    def _add_cell(
        self,
        value=None,  # TODO: Make mandatory when removing legacy parser support
        header=None,  # TODO: Make mandatory when removing legacy parser support
        unit=None,
        link=None,
        obj=None,  # noqa: Temporarily not in use
        tooltip=None,
        # attrs=None,  # :param attrs: Optional attributes (dict)
    ):
        """
        Add cell data. Also maintain column value list and insert header if on
        the first row and required parameters are supplied.

        :param value: Value to be displayed in the cell
        :param header: Name of the column header
        :param unit: Unit to be displayed in the cell
        :param link: Link from the value (URL string)
        :param obj: Original Django model object
        :param tooltip: Tooltip to be shown on mouse hover (string)
        """

        # Add header if first row
        if header and obj and self._first_row:
            self._add_header(header, obj)

        # Handle new list value notation in altamISA>=0.1
        # TODO: Not working, fix!
        '''
        if isinstance(value, list):
            value = ';'.join([self._get_value(x) for x in value])
        '''

        # Get printable value in case the function is called with a reference
        if isinstance(value, dict):
            value = self._get_value(value)

        self._row.append(
            {
                'value': value,
                'unit': unit,
                'link': link,
                'link_file': False,
                'tooltip': tooltip,
                # 'uuid': str(obj.sodar_uuid),  # TODO: Enable for editing
                # 'attrs': attrs,  # TODO: TBD: Remove entirely?
            }
        )

        # Store value for detecting unfilled columns
        col_value = 0 if not value else 1

        if self._first_row:
            self._col_values.append(col_value)

        elif col_value == 1 and self._col_values[self._col_idx] == 0:
            self._col_values[self._col_idx] = 1

        self._col_idx += 1

    # Legacy altamISA Functions (to be deprecated) -----------------------------

    def _add_annotation_headers(self, annotations, obj):
        """Append annotation columns to field header"""
        a_count = 0

        for a in annotations:
            self._add_header(a, obj)
            a_count += 1

        return a_count

    def _add_annotations(self, annotations, obj=None):
        """Append annotations to row columns"""
        if not annotations:
            return None

        for k, v in annotations.items():
            val = ''
            unit = None
            link = None
            tooltip = None

            # Ontology reference
            if (
                isinstance(v['value'], dict)
                and 'name' in v['value']
                and v['value']['name']
            ):
                if v['value']['ontology_name']:
                    tooltip = v['value']['ontology_name']

                val += v['value']['name']

                if v['value']['ontology_name'] and v['value']['accession']:
                    link = self._get_ontology_link(
                        v['value']['ontology_name'], v['value']['accession']
                    )

            # Empty ontology reference (this can happen with altamISA v0.1)
            elif isinstance(v['value'], dict) and (
                'name' not in v['value'] or not v['value']['name']
            ):
                val = ''

            # Basic value string
            else:
                val = v['value']

            if 'unit' in v:
                if isinstance(v['unit'], dict):
                    unit = v['unit']['name']

                else:
                    unit = v['unit']

            self._add_cell(val, unit=unit, link=link, obj=obj, tooltip=tooltip)

    def _add_element(self, obj):
        """
        Append GenericMaterial or Process element to row along with its
        attributes. To be used only with LEGACY versions of altamISA.

        :param obj: GenericMaterial or Pocess element
        """
        obj_type = type(obj)

        # Headers
        if self._first_row:
            field_count = 0

            # Material headers
            if obj_type == GenericMaterial:
                self._add_header('Name', obj)  # Name
                field_count += 1

                # TODO: TBD: How to render new extract label notation?
                if (
                    obj.material_type == 'Labeled Extract Name'
                    and obj.extract_label
                ):
                    self._add_header('Label', obj)  # Extract label
                    field_count += 1

                # Characteristics
                a_header_count = self._add_annotation_headers(
                    obj.characteristics, obj
                )
                field_count += a_header_count

                # Factor values
                if obj.item_type == 'SAMPLE':
                    a_header_count = self._add_annotation_headers(
                        obj.factor_values, obj
                    )
                    field_count += a_header_count

            # Process headers
            else:  # obj_type == Process
                if obj.protocol and obj.protocol.name:
                    self._add_header('Protocol', obj)  # Protocol
                    field_count += 1

                self._add_header('Name', obj)  # Name
                field_count += 1

                if obj.performer and obj.perform_date:
                    self._add_header('Performer', obj)
                    self._add_header('Perform Date', obj)
                    field_count += 2

                # Param values
                a_header_count = self._add_annotation_headers(
                    obj.parameter_values, obj
                )
                field_count += a_header_count

            # Comments
            a_header_count = self._add_annotation_headers(obj.comments, obj)
            field_count += a_header_count

            self._add_top_header(obj, field_count)

        # Material data
        if obj_type == GenericMaterial:
            # Add material info for iRODS links Ajax querying

            self._add_cell(obj.name, obj=obj)  # Name + attrs

            # TODO: TBD: How to render new extract label notation?
            if (
                obj.material_type == 'Labeled Extract Name'
                and obj.extract_label
            ):
                self._add_cell(obj.extract_label, obj=obj)  # Extract label

            # Characteristics
            self._add_annotations(obj.characteristics, obj=obj)

            if obj.item_type == 'SAMPLE':
                # Factor values
                self._add_annotations(obj.factor_values, obj=obj)

        # Process data
        elif obj_type == Process:
            if obj.protocol and obj.protocol.name:
                self._add_cell(obj.protocol.name, obj=obj)  # Protocol

            # Name
            self._add_cell(obj.name, obj=obj)

            if obj.performer and obj.perform_date:
                self._add_cell(obj.performer, obj=obj)
                self._add_cell(str(obj.perform_date), obj=obj)

            # Param values
            self._add_annotations(obj.parameter_values, obj=obj)

        # Comments
        self._add_annotations(obj.comments, obj=obj)

    # New altamISA v0.1+ Functions ---------------------------------------------

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
                        self._add_annotation(obj_attr[h_name], h_name, obj)

            # Basic fields we can simply map using BASIC_FIELD_MAPE
            elif h in BASIC_FIELD_MAP and hasattr(obj, BASIC_FIELD_MAP[h]):
                self._add_cell(
                    getattr(obj, BASIC_FIELD_MAP[h]), HEADER_MAP[h], obj=obj
                )

            # Special case: Name
            elif h in ALTAMISA_MATERIAL_NAMES:
                self._add_cell(obj.name, 'Name', obj=obj)

            # Special case: Labeled Extract Name
            elif h == th.LABELED_EXTRACT_NAME and hasattr(obj, 'extract_label'):
                self._add_cell(
                    obj.extract_label,
                    HEADER_MAP[th.LABELED_EXTRACT_NAME],
                    obj=obj,
                )

            # Special case: Protocol Name
            elif (
                h == th.PROTOCOL_REF
                and hasattr(obj, 'protocol')
                and obj.protocol
            ):
                self._add_cell(
                    obj.protocol.name, HEADER_MAP[th.PROTOCOL_REF], obj=obj
                )

            # Special case: Process Name
            elif isinstance(obj, Process) and h in th.PROCESS_NAME_HEADERS:
                self._add_cell(obj.name, 'Name', obj=obj)

        # Add top header
        if self._first_row:
            self._add_top_header(obj, len(self._field_header) - old_header_len)

    def _add_annotation(self, ann, header, obj):
        """
        Append a single annotation to row as multiple cells. To be used with
        altamISA v0.1+.

        :param ann: Annotation value (string or Dict)
        :param header: Name of the column header
        :param obj: GenericMaterial or Pocess object the annotation belongs to
        """
        val = ''
        unit = None
        link = None
        tooltip = None

        # Ontology reference
        if (
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

        # List value (altamISA v0.1+)
        elif isinstance(ann['value'], list) and len(ann['value']) > 0:
            # Apparently we can have empty lists as values (fixes issue #586)
            val = [x for x in list(ann['value']) if len(x) == 3]

            for i in range(len(val)):
                new_val = list(val[i])
                new_val[1] = self._get_ontology_url(new_val[2], new_val[1])
                val[i] = new_val

        # Basic value string
        else:
            val = ann['value']

        if 'unit' in ann:
            if isinstance(ann['unit'], dict):
                unit = ann['unit']['name']

            else:
                unit = ann['unit']

        self._add_cell(
            val, header, unit=unit, link=link, obj=obj, tooltip=tooltip
        )

    # Table building functions -------------------------------------------------

    def _append_row(self):
        """Append current row to table data and cleanup"""
        self._table_data.append(self._row)
        self._row = []
        self._first_row = False
        self._col_idx = 0

    def _build_table(self, table_refs, node_map):
        """
        Function for building a table for rendering.

        :param table_refs: Object unique_name:s in a list of lists
        :param node_map: Lookup dictionary containing objects
        :return: Dict
        """
        self._row = []
        self._top_header = []
        self._field_header = []
        self._table_data = []
        self._first_row = True
        self._col_values = []
        self._col_idx = 0

        row_id = 0

        for input_row in table_refs:
            col_pos = 0

            # Add elements on row
            for col in input_row:
                obj = node_map[col]

                # altamISA v0.1+ parsing with "headers" ordering
                if not isinstance(self._parser_version, version.LegacyVersion):
                    self._add_ordered_element(obj)

                # Legacy altamISA parsing
                # TODO: To be removed
                else:
                    self._add_element(obj)

                col_pos += 1

            self._append_row()
            row_id += 1

        # Aggregate column data for Vue app
        # TODO: Move this into a separate function

        def _get_length(value):
            """Return estimated length for proportional text"""
            if not value:
                return 0

            if isinstance(value, date):  # Convert perform date
                value = str(value)

            # Very unscientific and font-specific, don't try this at home
            nc = sum([value.count(c) for c in NARROW_CHARS])
            wc = sum([value.count(c) for c in WIDE_CHARS])
            return round(len(value) - nc - wc + 0.6 * nc + 1.3 * wc)

        for i in range(len(self._field_header)):
            header_name = self._field_header[i]['value'].lower()

            # Column type
            if 'contact' in header_name:
                col_type = 'CONTACT'

            elif header_name == 'external links':
                col_type = 'EXTERNAL_LINKS'

            elif (
                header_name == 'name'
                and self._field_header[i]['item_type'] == 'DATA'
            ):
                col_type = 'LINK_FILE'

            elif any([x[i]['link'] for x in self._table_data]):
                col_type = 'ONTOLOGY'

            elif any([x[i]['unit'] for x in self._table_data]):
                col_type = 'UNIT'

            else:
                col_type = None

            self._field_header[i]['col_type'] = col_type

            # Maximum column value length for column width estimate
            header_len = round(_get_length(self._field_header[i]['value']))

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
                        _get_length(x[i]['value'].split(';'))
                        if x[i]['value']
                        else 0
                        for x in self._table_data
                    ]
                )

            else:  # Generic type
                max_cell_len = max(
                    [
                        _get_length(x[i]['value'])
                        + _get_length(x[i]['unit'])
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

        tb = RefTableBuilder(nodes, arcs)
        all_refs = tb.run()

        if not all_refs:
            error_msg = (
                'RefTableBuilder failed to build a table from graph, unable to '
                'render study. Please ensure the validity of your ISAtab files'
            )
            logger.error(error_msg)
            raise SampleSheetRenderingException(error_msg)

        # Ensure the study does not exceed project limitations
        row_limit = app_settings.get_app_setting(
            'samplesheets', 'study_row_limit', project=study.get_project()
        )

        if len(all_refs) > row_limit:
            error_msg = (
                'Row limit set in samplesheets.study_row_limit '
                'reached ({}), unable to render study'.format(len(all_refs))
            )
            logger.error(error_msg)
            raise SampleSheetRenderingException(error_msg)

        return all_refs

    def build_study_tables(self, study):
        """
        Build study table and associated assay tables for rendering.

        :param study: Study object
        :return: Dict
        """
        s_start = time.time()
        logger.debug(
            'Building study "{}" (pk={})..'.format(study.get_name(), study.pk)
        )

        self._parser_version = (
            version.parse(study.investigation.parser_version)
            if study.investigation.parser_version
            else version.parse('')
        )

        logger.debug(
            'Import parser version: {}'.format(
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

        ret['study'] = self._build_table(study_refs, node_map)

        logger.debug(
            'Building study OK ({:.1f}s)'.format(time.time() - s_start)
        )

        # Assay tables
        assay_count = 0

        for assay in study.assays.all().order_by('file_name'):
            a_start = time.time()
            logger.debug(
                'Building assay "{}" (pk={})..'.format(
                    assay.get_name(), assay.pk
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
                assay_refs, node_map
            )

            assay_count += 1
            logger.debug(
                'Building assay OK ({:.1f}s)'.format(time.time() - a_start)
            )

        return ret
