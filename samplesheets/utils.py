"""Utilities for the samplesheets app"""

from openpyxl import Workbook
from openpyxl.workbook.child import INVALID_TITLE_REGEX
import re

from django.db.models import QuerySet
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api

ALT_NAMES_COUNT = 3  # Needed for ArrayField hack

CONFIG_LABEL_CREATE = 'Created With Configuration'
CONFIG_LABEL_OPEN = 'Last Opened With Configuration'
NAME_FIELDS = ['name', 'protocol']


def get_alt_names(name):
    """
    Return list of alternative names for an object.

    :param name: Original name/ID (string)
    :return: List
    """
    name = name.lower()  # Convert all versions lowercase for indexed search

    return [name.replace('_', '-'), re.sub(r'[^a-zA-Z0-9]', '', name), name]


def get_sample_colls(investigation):
    """
    Return study and assay collections without parent colls for the sample data
    collection structure.

    :param investigation: Investigation object
    :return: List
    """
    ret = []
    irods_backend = get_backend_api('omics_irods', conn=False)

    if irods_backend:
        for study in investigation.studies.all():
            ret.append(irods_backend.get_sub_path(study))

            for assay in study.assays.all():
                ret.append(irods_backend.get_sub_path(assay))

    return ret


def compare_inv_replace(inv1, inv2):
    """
    Compare investigations for critical differences for replacing.

    :param inv1: Investigation object
    :param inv2: Investigation object
    :raise: ValueError if a problem is detected
    """
    try:
        for study1 in inv1.studies.all():
            study2 = inv2.studies.get(
                identifier=study1.identifier, file_name=study1.file_name
            )

            for assay1 in study1.assays.all():
                study2.assays.get(file_name=assay1.file_name)

    except Exception:
        raise ValueError(
            'iRODS collections exist but studies and assays '
            'do not match: unable to replace investigation'
        )


def get_index_by_header(
    render_table, header_value, obj_cls=None, item_type=None
):
    """
    Return the column index based on field header value.

    :param render_table: Study/assay render table
    :param header_value: Header value
    :param obj_cls: Class of Dango model object for searched header (optional)
    :param item_type: Type of searched item in GenericMaterial (optional)
    :return: Int or None if not found
    """
    header_value = header_value.lower()
    obj_cls = obj_cls.__name__ if obj_cls else None

    for i, h in enumerate(render_table['field_header']):
        if (
            h['value'].lower() == header_value
            and (not obj_cls or h['obj_cls'] == obj_cls)
            and (not item_type or h['item_type'] == item_type)
        ):
            return i

    return None


def get_last_material_name(row, table):
    """Return name of the last non-DATA material in a table row"""
    name = None

    for i in range(len(row)):
        cell = row[i]
        header = table['field_header'][i]
        if (
            header['obj_cls'] == 'GenericMaterial'
            and header['item_type'] != 'DATA'
            and header['value'].lower() == 'name'
            and cell['value']
        ):
            name = cell['value']

    return name


def get_sample_libraries(samples, study_tables):
    """
    Return libraries for samples.

    :param samples: Sample object or a list of Sample objects within a study
    :param study_tables: Rendered study tables
    :return: GenericMaterial queryset
    """
    from samplesheets.models import GenericMaterial

    if type(samples) not in [list, QuerySet]:
        samples = [samples]

    sample_names = [s.name for s in samples]
    study = samples[0].study
    library_names = []

    for k, assay_table in study_tables['assays'].items():
        sample_idx = get_index_by_header(
            assay_table, 'name', obj_cls=GenericMaterial, item_type='SAMPLE'
        )

        for row in assay_table['table_data']:
            if row[sample_idx]['value'] in sample_names:
                last_name = get_last_material_name(row, assay_table)

                if last_name not in library_names:
                    library_names.append(last_name)

    return GenericMaterial.objects.filter(
        study=study, name__in=library_names
    ).order_by('name')


def get_study_libraries(study, study_tables):
    """
    Return sample libraries for an entire study.

    :param study: Study object
    :param study_tables: Rendered study tables from samplesheets.rendering
    :return: List of GenericMaterial objects
    """
    ret = []

    for source in study.get_sources():
        for sample in source.get_samples():
            ret += get_sample_libraries(sample, study_tables)

    return ret


def get_isa_field_name(field):
    """
    Return the name of an ISA field. In case of an ontology reference, returns
    field['name'].

    :param field: Field of an ISA Django model
    :return: String
    """
    if type(field) == dict:
        return field['name']

    return field


def get_sheets_url(obj):
    """
    Return URL for sample sheets compatible with the new Vue.js framework.

    :param obj: An object of type Project, Study or Assay (or any other model
                implementing get_project()
    :return: String
    """
    project = obj if isinstance(obj, Project) else obj.get_project()
    url = reverse(
        'samplesheets:project_sheets', kwargs={'project': project.sodar_uuid}
    )

    # NOTE: Importing the model fails because of circular dependency
    if obj.__class__.__name__ == 'Study':
        url += '#/study/' + str(obj.sodar_uuid)

    elif obj.__class__.__name__ == 'Assay':
        url += '#/assay' + str(obj.sodar_uuid)

    return url


def get_comment(obj, key):
    """
    Return comment value for object based on key or None if not found.
    TODO: Remove once reimporting sample sheets (#629, #631)

    :param obj: Object parsed from ISAtab
    :param key: Key for comment
    :return:
    """
    if (
        not hasattr(obj, 'comments')
        or not obj.comments
        or key not in obj.comments
    ):
        return None

    if isinstance(obj.comments[key], dict):
        return obj.comments[key]['value']

    return obj.comments[key]


def get_comments(obj):
    """
    Return comments for an object or None if they don't exist.

    :param obj: Object parsed from ISAtab
    :return: Dict
    """
    if not hasattr(obj, 'comments') or not obj.comments:
        return None

    ret = {k: get_comment(obj, k) for k in obj.comments.keys()}

    def _clean_config(k):
        if k in ret:
            ret[k] = get_config_name(ret[k])

    _clean_config(CONFIG_LABEL_CREATE)
    _clean_config(CONFIG_LABEL_OPEN)
    return ret


def get_config_name(config):
    """
    Return sample sheet configuration name. Remove any identifying local
    directory information if present.

    :param config_val: Original configuration name (string)
    :return: String
    """
    if config.find('/') == -1 and config.find('\\') == -1:
        return config

    return re.split('[/\\\\]', config)[-1]


def write_excel_table(table, output, display_name):
    """
    Write an Excel 2010 file (.xlsx) from a rendered study/assay table
    :param table:
    :param output:
    :return:
    """

    def _get_val(c_val):
        if isinstance(c_val, str):
            return c_val
        elif isinstance(c_val, dict):
            return c_val['name']
        elif isinstance(c_val, list):
            return ';'.join([_get_val(x) for x in c_val])
        return ''

    # Build Excel file
    wb = Workbook()
    ws = wb.active
    ws.title = re.sub(INVALID_TITLE_REGEX, '_', display_name)
    top_header_row = []

    for c in table['top_header']:
        top_header_row.append(c['value'])

        if c['colspan'] > 1:
            top_header_row += [''] * (c['colspan'] - 1)

    ws.append(top_header_row)
    ws.append([c['value'] for c in table['field_header']])

    for row in table['table_data']:
        ws.append([_get_val(c['value']) for c in row])

    # Resize columns (plus a little extra for padding)
    # NOTE: There is a "bestFit" attribute but it doesn't really work at all
    for col_cells in ws.columns:
        length = max(len(c.value) if c.value else 0 for c in col_cells) + 2
        ws.column_dimensions[col_cells[0].column_letter].width = length

    wb.save(output)


def build_sheet_config(investigation):
    """
    Build basic sample sheet configuration for editing configuration.
    NOTE: Will be built from configuration template(s) eventually

    :param investigation: Investigation object
    :return: Dict
    """

    # Can't import in module root
    from samplesheets.rendering import SampleSheetTableBuilder

    tb = SampleSheetTableBuilder()
    ret = {'investigation': {}, 'studies': {}}

    def _build_nodes(study_tables, assay_uuid=None):
        from samplesheets.models import Protocol

        nodes = []
        sample_found = False
        ti = 0

        if not assay_uuid:
            table = study_tables['study']

        else:
            table = study_tables['assays'][assay_uuid]

        for th in table['top_header']:
            if not assay_uuid or sample_found:
                node = {'header': th['value'], 'fields': []}

                for i in range(ti, ti + th['colspan']):
                    h = table['field_header'][i]
                    f = {'name': h['name']}

                    if h['type']:
                        f['type'] = h['type']

                    # Set up default protocol if only one option exists in data
                    if h['type'] == 'protocol':
                        p_name = None
                        p_found = False
                        protocol = None

                        for row in table['table_data']:
                            if not p_name and row[i]['value']:
                                p_name = row[i]['value']
                                p_found = True

                            elif p_name and row[i]['value'] != p_name:
                                p_found = False
                                break

                        if p_found:
                            protocol = Protocol.objects.filter(
                                study__investigation=investigation, name=p_name
                            ).first()

                        if protocol:
                            f['default'] = str(protocol.sodar_uuid)
                            f['format'] = 'protocol'

                    node['fields'].append(f)

                nodes.append(node)

            # Leave out study columns for assays
            if assay_uuid and th['value'] == 'Sample':
                sample_found = True

            ti += th['colspan']

        return nodes

    # Add studies
    for study in investigation.studies.all().order_by('pk'):
        # Build tables (disable use_config in case we are replacing sheets)
        study_tables = tb.build_study_tables(study, edit=True, use_config=False)
        study_data = {
            'display_name': study.get_display_name(),  # For human readability
            'nodes': _build_nodes(study_tables, None),
            'assays': {},
        }

        # Add study assays
        for assay in study.assays.all().order_by('pk'):
            assay_uuid = str(assay.sodar_uuid)
            study_data['assays'][assay_uuid] = {
                'display_name': assay.get_display_name(),
                'nodes': _build_nodes(study_tables, assay_uuid),
            }

        ret['studies'][str(study.sodar_uuid)] = study_data

    return ret


def build_display_config(investigation, sheet_config):
    """
    Build default display config for project sample sheet columns.

    :param investigation: Investigation object
    :param sheet_config: Sheet editing configuration (dict)
    :return: Dict
    """

    # Can't import in module root
    from samplesheets.rendering import SampleSheetTableBuilder

    tb = SampleSheetTableBuilder()

    ret = {'investigation': {}, 'studies': {}}

    def _build_node(config_node, table, idx, assay_mode=False):
        display_node = {'header': config_node['header'], 'fields': []}
        n_idx = 0

        for config_field in config_node['fields']:
            display_field = {'name': config_field['name'], 'visible': False}

            if n_idx == 0 or (
                not assay_mode
                and (
                    config_field.get('editable') or table['col_values'][idx] > 0
                )
            ):
                display_field['visible'] = True

            display_node['fields'].append(display_field)
            idx += 1
            n_idx += 1

        return display_node, idx

    # Add studies
    for study in investigation.studies.all().order_by('pk'):
        study_uuid = str(study.sodar_uuid)
        study_tables = tb.build_study_tables(
            study, edit=False, use_config=False
        )
        h_idx = 0
        study_data = {'nodes': [], 'assays': {}}

        for config_node in sheet_config['studies'][study_uuid]['nodes']:
            display_node, h_idx = _build_node(
                config_node, study_tables['study'], h_idx
            )
            study_data['nodes'].append(display_node)

        # Add study assays
        for assay in study.assays.all().order_by('pk'):
            assay_uuid = str(assay.sodar_uuid)
            assay_table = study_tables['assays'][assay_uuid]
            h_idx = 0
            assay_data = {'nodes': []}

            # Add study nodes to assay table with only first field visible
            for config_node in sheet_config['studies'][study_uuid]['nodes']:
                node, h_idx = _build_node(
                    config_node, study_tables['study'], h_idx, assay_mode=True,
                )
                assay_data['nodes'].append(node)

            # Add actual assay nodes
            for config_node in sheet_config['studies'][study_uuid]['assays'][
                assay_uuid
            ]['nodes']:
                node, h_idx = _build_node(config_node, assay_table, h_idx)
                assay_data['nodes'].append(node)

            study_data['assays'][assay_uuid] = assay_data

        ret['studies'][study_uuid] = study_data

    return ret


def get_top_header(table, field_idx):
    """
    Return top header by field header index.

    :param table: Rendered table (dict)
    :param field_idx: Field header index (int)
    :return: dict or None
    """
    tc = 0

    for th in table['top_header']:
        tc += th['colspan']

        if tc > field_idx:
            return th
