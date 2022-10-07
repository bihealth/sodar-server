"""Utilities for the samplesheets app"""

import json
import os
import random
import re
import string

from openpyxl import Workbook
from openpyxl.workbook.child import INVALID_TITLE_REGEX

from django.conf import settings
from django.db.models import QuerySet
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project
from projectroles.plugins import get_backend_api

from samplesheets.constants import DEFAULT_EXTERNAL_LINK_LABELS


# Local constants
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
    :return: Bool
    """
    try:
        for study1 in inv1.studies.all():
            study2 = inv2.studies.get(
                identifier=study1.identifier, file_name=study1.file_name
            )
            for assay1 in study1.assays.all():
                study2.assays.get(file_name=assay1.file_name)
    except Exception:
        return False
    return True


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

    :param obj: Object parsed from ISA-Tab
    :param key: Key for comment
    :return: String
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

    :param obj: Object parsed from ISA-Tab
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


def get_unique_name(study, assay, name, item_type=None):
    """
    Return unique name for a node.

    :param study: Study object
    :param assay: Assay object
    :param name: Display name for material
    :param item_type: Item type for materials (string)
    :return: String
    """
    # HACK: This will of course not work on empty tables..
    # TODO: Refactor once we allow creating sheets from scratch
    study_id = study.arcs[0][0].split('-')[1][1:]
    assay_id = 0
    if assay and study.assays.count() > 1:
        assay_id = sorted([a.file_name for a in study.assays.all()]).index(
            assay.file_name
        )
    return 'p{}-s{}-{}{}{}-{}'.format(
        study.investigation.project.pk,
        study_id,
        'a{}-'.format(assay_id) if assay else '',
        '{}-'.format(item_type.lower()) if item_type else '',
        name,
        ''.join(
            random.SystemRandom().choice(string.ascii_lowercase + string.digits)
            for _ in range(8)
        ),
    )


def get_node_obj(**query_kwargs):
    """
    Get either a GenericMaterial or Process based on query kwargs.

    :param query_kwargs: Django query parameters
    :return: GenericMaterial, Process or None
    """
    # TODO: Implement in models as a manager instead? (see issue #922)
    # TODO: Add parameter to optionally use get() and raise *.DoesNotExist?
    from samplesheets.models import GenericMaterial, Process

    obj = GenericMaterial.objects.filter(**query_kwargs).first()
    if not obj:
        obj = Process.objects.filter(**query_kwargs).first()
    return obj


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
    Write an Excel 2010 file (.xlsx) from a rendered study/assay table.
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


def clean_sheet_dir_name(name):
    """
    Clean up / sanitize sample sheet directory name.

    :param name: String
    :return: String
    """
    return re.sub(r'[\s]+', '_', re.sub(r'[^\w\s-]', '', name).strip())


def get_webdav_url(project, user):
    """
    Return the WebDAV URL for accessing sample data under a specific project.
    If the project has public guest access with anonymous users enabled, return
    read-only ticket access URL. If WebDAV is not enabled, return None.

    :param project: Project object
    :param user: User object for user requesting the URL
    :return: String or None
    :raise: ValueError if path is invalid
    """
    if not settings.IRODS_WEBDAV_ENABLED:
        return None
    if user and user.is_authenticated:
        return settings.IRODS_WEBDAV_URL.rstrip('/')
    elif (
        (not user or user.is_anonymous)
        and settings.PROJECTROLES_ALLOW_ANONYMOUS
        and project.public_guest_access
    ):
        app_settings = AppSettingAPI()
        ticket = app_settings.get_app_setting(
            'samplesheets', 'public_access_ticket', project=project
        )
        if not ticket:
            return None
        return settings.IRODS_WEBDAV_URL_ANON_TMPL.format(
            user=settings.IRODS_WEBDAV_USER_ANON, ticket=ticket, path=''
        )


def get_ext_link_labels():
    """
    Return external link labels and URLs. Retrieve from config file set in
    SHEETS_EXTERNAL_LINK_PATH or default values.

    :return: Dict
    """
    ext_path = settings.SHEETS_EXTERNAL_LINK_PATH
    if ext_path and os.path.exists(ext_path):
        with open(ext_path, 'r') as f:
            return json.load(f)
    return DEFAULT_EXTERNAL_LINK_LABELS
