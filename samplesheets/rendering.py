"""Rendering utilities for samplesheets"""

import itertools
import logging
import time

# Projectroles dependency
from projectroles.project_settings import get_project_setting

from .models import Assay, Process, GenericMaterial


TOP_HEADER_MATERIAL_COLOURS = {
    'SOURCE': 'info',
    'SAMPLE': 'warning',
    'MATERIAL': 'success',
    'DATA': 'success'}

TOP_HEADER_MATERIAL_VALUES = {
    'SOURCE': 'Source',
    'SAMPLE': 'Sample',
    'MATERIAL': 'Material',
    'DATA': 'Data File'}

EMPTY_VALUE = '-'

STUDY_HIDEABLE_CLASS = 'omics-ss-hideable-study'
SOURCE_SEARCH_STR = '-source-'
ONTOLOGY_URL_TEMPLATE = 'https://bioportal.bioontology.org/ontologies/' \
                        '{ontology_name}/?p=classes&conceptid={accession}'


logger = logging.getLogger(__name__)


# Graph traversal / reference table building -----------------------------------


class Digraph:
    """Simple class encapsulating directed graph with vertices and arcs"""
    def __init__(self, vertices, arcs):
        self.vertices = vertices
        self.arcs = arcs
        self.v_by_name = {v.unique_name: v for v in self.vertices}
        self.a_by_name = {(a[0], a[1]) for a in self.arcs}
        self.source_names = [
            k for k in self.v_by_name.keys() if SOURCE_SEARCH_STR in k]
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
            uf.union_by_name(
                arc[0],
                arc[1])

        result = {}

        for v_name in self.digraph.v_by_name.keys():
            result.setdefault(v_name, []).append(v_name)

        return list(result.values())

    def _dump_row(self, v_names):
        # print('row: {}'.format(v_names))
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

    @classmethod
    def _get_ontology_link(cls, ontology_name, accession):
        """
        Build ontology link.
        :param ontology_name: Ontology name
        :param accession: Ontology accession URL
        :return: String
        """
        return ONTOLOGY_URL_TEMPLATE.format(
                ontology_name=ontology_name,
                accession=accession)

    def _add_top_header(self, obj, colspan, hiding={}):
        """Append columns to top header"""
        if type(obj) == GenericMaterial:    # Material
            colour = TOP_HEADER_MATERIAL_COLOURS[obj.item_type]
            value = obj.material_type if obj.material_type else \
                TOP_HEADER_MATERIAL_VALUES[obj.item_type]

        else:   # Process
            colour = 'danger'
            value = 'Process'

        self._top_header.append({
            'value': value,
            'colour': colour,
            'colspan': colspan,
            'hiding': hiding})

    def _add_header(self, value, classes=list()):
        """
        Add column header value
        :param value: Value to be displayed
        :param classes: Optional extra classes
        """
        self._field_header.append({
            'value': value,
            'classes': classes})

    def _add_cell(
            self, value=None, unit=None, link=None,
            obj_type=None, field_name=None, tooltip=None, attrs=None,
            classes=list()):
        """
        Add cell data
        :param value: Value to be displayed in the cell
        :param unit: Unit to be displayed in the cell
        :param link: Link from the value (URL string)
        :param obj_type: HACK: Original object type (string)
        :param field_name: HACK: Field name (string)
        :param tooltip: Tooltip to be shown on mouse hover (string)
        :param attrs: Optional attributes (dict)
        :param classes: Optional extra classes (list)
        """
        self._row.append({
            'value': value,
            'unit': unit,
            'link': link,
            'obj_type': obj_type,
            'field_name': field_name,
            'tooltip': tooltip,
            'attrs': attrs,
            'classes': classes})

        # Store value for detecting unfilled columns
        col_value = 0 if not value else 1

        if self._first_row:
            self._col_values.append(col_value)

        elif col_value == 1 and self._col_values[self._col_idx] == 0:
            self._col_values[self._col_idx] = 1

        self._col_idx += 1

    def _add_annotation_headers(self, annotations, classes=list()):
        """Append annotation columns to field header"""
        a_count = 0

        for a in annotations:
            self._add_header(a.capitalize(), classes)
            a_count += 1

        return a_count

    def _add_annotations(self, annotations, classes=list()):
        """Append annotations to row columns"""
        if not annotations:
            return None

        for k, v in annotations.items():
            val = ''
            unit = None
            link = None
            tooltip = None

            if type(v['value']) == dict:
                if v['value']['ontology_name']:
                    tooltip = v['value']['ontology_name']

                val += v['value']['name']
                link = self._get_ontology_link(
                    v['value']['ontology_name'], v['value']['accession'])

            else:
                val = v['value']

            # TODO: Test unit
            if 'unit' in v:
                if type(v['unit']) == dict:
                    unit = v['unit']['name']

                else:
                    unit = v['unit']

            self._add_cell(
                val, unit=unit, link=link, tooltip=tooltip,
                classes=classes)

    def _add_element(self, obj, study_data_in_assay=False):
        """
        Append GenericMaterial or Process element to row along with its
        attributes
        :param obj: GenericMaterial or Pocess element
        :param study_data_in_assay: Whether we are adding hideable study data in
        an assay table (boolean)
        """
        # TODO: Contains repetition, refactor
        hide_cls = [STUDY_HIDEABLE_CLASS] if study_data_in_assay else list()

        # Headers
        if self._first_row:
            field_count = 0
            hideable_count = 0

            # Material headers
            if type(obj) == GenericMaterial:
                self._add_header(
                    'Name', hide_cls if obj.item_type in
                    ['DATA', 'MATERIAL'] else list())           # Name
                field_count += 1

                if (obj.material_type == 'Labeled Extract Name' and
                        obj.extract_label):
                    self._add_header('Label', hide_cls)         # Extract label
                    field_count += 1

                a_header_count = self._add_annotation_headers(
                    obj.characteristics, hide_cls)              # Character.
                field_count += a_header_count
                hideable_count += a_header_count

                if obj.item_type == 'SAMPLE':
                    a_header_count = self._add_annotation_headers(
                        obj.factor_values, hide_cls)            # Factor values
                    field_count += a_header_count
                    hideable_count += a_header_count

                if obj.material_type:
                    top_header_type = obj.material_type

                else:
                    top_header_type = obj.item_type

            # Process headers
            else:   # type(obj) == Process
                if obj.protocol and obj.protocol.name:
                    self._add_header('Protocol', hide_cls)      # Protocol
                    field_count += 1

                self._add_header('Name', hide_cls)              # Name
                field_count += 1

                a_header_count = self._add_annotation_headers(
                    obj.parameter_values, hide_cls)             # Param values
                field_count += a_header_count
                hideable_count += a_header_count

                top_header_type = 'PROCESS'

            a_header_count = self._add_annotation_headers(
                obj.comments, hide_cls)                         # Comments
            field_count += a_header_count
            hideable_count += a_header_count

            self._add_top_header(
                obj, field_count, hiding={
                    STUDY_HIDEABLE_CLASS: hideable_count if
                    study_data_in_assay else 0})

        # Material data
        if type(obj) == GenericMaterial:
            # Add material info for iRODS links Ajax querying

            self._add_cell(
                obj.name, obj_type=obj.item_type,
                field_name='name')                              # Name + attrs

            if (obj.material_type == 'Labeled Extract Name' and
                    obj.extract_label):
                self._add_cell(obj.extract_label)               # Extract label

            self._add_annotations(
                obj.characteristics, hide_cls)                  # Character.

            if obj.item_type == 'SAMPLE':
                self._add_annotations(
                    obj.factor_values, hide_cls)                # Factor values

        # Process data
        elif type(obj) == Process:
            if obj.protocol and obj.protocol.name:
                self._add_cell(
                    obj.protocol.name, classes=hide_cls)        # Protocol

            self._add_cell(obj.name, classes=hide_cls)          # Name

            self._add_annotations(
                obj.parameter_values, hide_cls)                 # Param values

        self._add_annotations(obj.comments, hide_cls)           # Comments

    def _append_row(self):
        """Append current row to table data and cleanup"""
        self._table_data.append(self._row)
        self._row = []
        self._first_row = False
        self._col_idx = 0

    def _build_table(self, table_refs, node_lookup, sample_pos, table_parent):
        """
        Function for building a table for rendering.
        :param table_refs: Object unique_name:s in a list of lists
        :param node_lookup: Dictionary containing objects
        :param sample_pos: Position of sample column (int)
        :param table_parent: Parent object of table (Study or Assay)
        :return: Dict
        """
        self._row = []
        self._top_header = []
        self._field_header = []
        self._table_data = []
        self._first_row = True
        self._col_values = []
        self._col_idx = 0

        # Add row column headers
        self._top_header.append({
            'value': 'Row',
            'colour': 'secondary',
            'colspan': 1,
            'hiding': {}})
        self._add_header('#')
        row_id = 1

        for input_row in table_refs:
            col_pos = 0

            # Add row column cell
            self._add_cell(str(row_id), classes=['text-muted'])

            # Add elements on row
            for col in input_row:
                obj = node_lookup[col]
                study_data_in_assay = True if \
                    type(table_parent) == Assay and \
                    col_pos <= sample_pos else False
                self._add_element(obj, study_data_in_assay)
                col_pos += 1

            self._append_row()
            row_id += 1

        return {
            'top_header': self._top_header,
            'field_header': self._field_header,
            'table_data': self._table_data,
            'col_values': self._col_values}

    @classmethod
    def build_study_reference(cls, study, nodes=None):
        """
        Get study reference table for building final table data
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

        # Ensure the study does not exceed project limitations
        row_limit = get_project_setting(
            study.get_project(), 'samplesheets', 'study_row_limit')

        if len(all_refs) > row_limit:
            raise SampleSheetRenderingException(
                'Row limit set in samplesheets.study_row_limit reached ({}), '
                'unable to render study'.format(
                    len(all_refs)))

        return all_refs

    def build_study_tables(self, study):
        """
        Build study table and associated assay tables for rendering
        :param study: Study object
        :return: Dict
        """
        s_start = time.time()
        logger.debug('Building study "{}" (pk={})..'.format(
            study.get_name(), study.pk))

        ret = {
            'study': None,
            'assays': {}}

        nodes = study.get_nodes()
        all_refs = self.build_study_reference(study, nodes)

        sample_pos = [
            i for i, col in enumerate(all_refs[0]) if
            '-sample-' in col][0]
        node_lookup = {n.unique_name: n for n in nodes}

        # Study ref table without duplicates
        sr = [row[:sample_pos + 1] for row in all_refs]
        study_refs = list(sr for sr, _ in itertools.groupby(sr))

        ret['study'] = self._build_table(
            study_refs, node_lookup, sample_pos, study)

        logger.debug(
            'Building study OK ({:.1f}s)'.format(time.time() - s_start))

        # Assay tables
        assay_count = 0

        for assay in study.assays.all().order_by('file_name'):
            a_start = time.time()
            logger.debug('Building assay "{}" (pk={})..'.format(
                assay.get_name(), assay.pk))

            assay_search_str = '-a{}-'.format(assay_count)
            assay_refs = []

            for row in all_refs:
                if (len(row) > sample_pos + 1 and
                        assay_search_str in row[sample_pos + 1]):
                    assay_refs.append(row)

            ret['assays'][assay.get_name()] = self._build_table(
                assay_refs, node_lookup, sample_pos, assay)

            assay_count += 1
            logger.debug(
                'Building assay OK ({:.1f}s)'.format(
                    time.time() - a_start))

        return ret
