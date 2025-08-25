"""Utilities for the samplesheets app"""

import json
import os
import random
import re
import string

from openpyxl import Workbook
from openpyxl.workbook.child import INVALID_TITLE_REGEX
from typing import Any, Optional, Union

from django.conf import settings
from django.db.models import Model
from django.http import HttpResponse
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, SODARUser
from projectroles.plugins import PluginAPI

from samplesheets.constants import DEFAULT_EXTERNAL_LINK_LABELS

# NOTE: Can't import samplesheets models for type hints due to circular import
# TODO: Refactor utils into models and/or other modules where applicable


plugin_api = PluginAPI()


# Local constants
ALT_NAMES_COUNT = 3  # Needed for ArrayField hack
CONFIG_LABEL_CREATE = 'Created With Configuration'
CONFIG_LABEL_OPEN = 'Last Opened With Configuration'
NAME_FIELDS = ['name', 'protocol']


def get_alt_names(name: str) -> list[str]:
    """
    Return list of alternative names for an object.

    :param name: Original name/ID (string)
    :return: List of strings
    """
    name = name.lower()  # Convert all versions lowercase for indexed search
    return [name.replace('_', '-'), re.sub(r'[^a-zA-Z0-9]', '', name), name]


def get_sample_colls(investigation: Any) -> list[str]:
    """
    Return study and assay collections without parent colls for the sample data
    collection structure.

    :param investigation: Investigation object
    :return: List of strings
    """
    ret = []
    irods_backend = plugin_api.get_backend_api('omics_irods')
    if irods_backend:
        for study in investigation.studies.all():
            ret.append(irods_backend.get_sub_path(study))
            for assay in study.assays.all():
                ret.append(irods_backend.get_sub_path(assay))
    return ret


def compare_inv_replace(inv1: Any, inv2: Any) -> bool:
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
    render_table: dict,
    header_value: str,
    obj_cls: Optional[Model] = None,
    item_type: Optional[str] = None,
) -> Optional[int]:
    """
    Return the column index based on field header value.

    :param render_table: Study/assay render table (dict)
    :param header_value: Header value (string)
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


# TODO: Add tests
def get_last_material_index(table: dict) -> Optional[int]:
    """
    Return index of the last non-DATA material in a table row.

    :param table: Study/assay render table (dict)
    :return: Int or None if not found
    """
    row = table['table_data'][0]
    for i in range(len(row) - 1, -1, -1):
        cell = row[i]
        header = table['field_header'][i]
        if (
            header['obj_cls'] == 'GenericMaterial'
            and header['item_type'] != 'DATA'
            and header['value'].lower() == 'name'
            and cell['value']
        ):
            return i
    return None


def get_last_material_name(row: list[dict], table: dict) -> Optional[str]:
    """
    Return name of the last non-DATA material in a table row.

    :param row: List of dicts
    :param table: Dict
    :return: String or None if not found
    """
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


def get_isa_field_name(field: Union[dict, str]) -> str:
    """
    Return the name of an ISA field. In case of an ontology reference, returns
    field['name'].

    :param field: Field of an ISA Django model
    :return: String
    """
    if isinstance(field, dict):
        return field['name']
    return field


def get_sheets_url(project: Project) -> str:
    """
    Return sample sheets app URL for project.

    :param project: Project object
    :return: String
    """
    return reverse(
        'samplesheets:project_sheets', kwargs={'project': project.sodar_uuid}
    )


def get_comment(obj: Any, key: str) -> Optional[str]:
    """
    Return comment value for object based on key or None if not found.
    TODO: Remove once reimporting sample sheets (#629, #631)

    :param obj: Object parsed from ISA-Tab
    :param key: Key for comment
    :return: String or None
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


def get_comments(obj: Any) -> Optional[dict]:
    """
    Return comments for an object or None if they don't exist.

    :param obj: Object parsed from ISA-Tab
    :return: Dict or None
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


def get_unique_name(
    study: Any, assay: Any, name: str, item_type: Optional[str] = None
):
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


def get_node_obj(**query_kwargs) -> Any:
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


def get_config_name(config: str) -> str:
    """
    Return sample sheet configuration name. Remove any identifying local
    directory information if present.

    :param config: Original configuration name (string)
    :return: String
    """
    if config.find('/') == -1 and config.find('\\') == -1:
        return config
    return re.split('[/\\\\]', config)[-1]


def write_excel_table(table: dict, output: HttpResponse, display_name: str):
    """
    Write an Excel 2010 file (.xlsx) from a rendered study/assay table.

    :param table: Study/assay render table (dict)
    :param output: HttpResponse object in which output will be written
    :param display_name: Study or assay display name (string)
    """

    def _get_val(c_val):
        if isinstance(c_val, str):
            return c_val
        elif isinstance(c_val, dict):
            return c_val['name']
        elif isinstance(c_val, list):
            return ';'.join([_get_val(x) for x in c_val])
        return ''

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


def get_top_header(table: dict, field_idx: int) -> Optional[dict]:
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


def clean_sheet_dir_name(name: str) -> str:
    """
    Clean up / sanitize sample sheet directory name.

    :param name: String
    :return: String
    """
    return re.sub(r'[\s]+', '_', re.sub(r'[^\w\s-]', '', name).strip())


def get_webdav_url(project: Project, user: SODARUser) -> Optional[str]:
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
    # TODO: Update for viewer role
    elif (
        (not user or user.is_anonymous)
        and settings.PROJECTROLES_ALLOW_ANONYMOUS
        and project.public_access
    ):
        app_settings = AppSettingAPI()
        ticket = app_settings.get(
            'samplesheets', 'public_access_ticket', project=project
        )
        if not ticket:
            return None
        return settings.IRODS_WEBDAV_URL_ANON_TMPL.format(
            user=settings.IRODS_WEBDAV_USER_ANON, ticket=ticket, path=''
        )


def get_ext_link_labels() -> dict:
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


def get_latest_file_path(paths: list[str]) -> str:
    """
    Return last file by file name.

    :param paths: List of strings
    """
    return sorted(paths, key=lambda x: x.split('/')[-1], reverse=True)[0]


def get_bool(bool_string: str) -> bool:
    """
    Return freeform string as boolean.

    NOTE: Doing this as distutils is deprecated/removed..

    :param bool_string: String
    :raise: ValueError if value is not a string or can't be parsed
    :return: bool
    """
    if bool_string.strip().lower() in ['1', 't', 'true', 'y', 'yes']:
        return True
    if bool_string.strip().lower() in ['0', 'f', 'false', 'n', 'no']:
        return False
    raise ValueError(f'Unable to parse value: {bool_string}')
