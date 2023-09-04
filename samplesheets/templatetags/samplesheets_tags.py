"""Template tags for the samplesheets app"""

from django import template
from django.conf import settings

# Projectroles dependency
from projectroles.plugins import get_backend_api

from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    GENERIC_MATERIAL_TYPES,
)


# Local constants
TAG_COLORS = {
    'CREATE': 'info',
    'IMPORT': 'info',
    'EDIT': 'warning',
    'REPLACE': 'danger',
    'RESTORE': 'danger',
}
DEFAULT_TAG_COLOR = 'secondary'
REQUEST_STATUS_CLASSES = {
    'ACTIVE': 'bg-info text-white',
    'FAILED': 'bg-danger text-white',
    'ACCEPTED': 'bg-success text-white',
    'REJECTED': 'bg-danger text-white',
}


register = template.Library()


# General ----------------------------------------------------------------------


@register.simple_tag
def get_investigation(project):
    """Return active Investigation for a project"""
    try:
        return Investigation.objects.get(project=project, active=True)
    except Investigation.DoesNotExist:
        return None


@register.simple_tag
def get_search_item_type(item):
    """Return printable version of search item type"""
    if item['type'] == 'file':
        return 'Data File'
    return GENERIC_MATERIAL_TYPES[item['type']]


@register.simple_tag
def get_irods_tree(investigation):
    """Return HTML for iRODS collections"""
    irods_backend = get_backend_api('omics_irods')
    if not irods_backend:
        return ''
    ret = '<ul><li>{}<ul>'.format(settings.IRODS_SAMPLE_COLL)
    for study in investigation.studies.all():
        ret += '<li>{}'.format(
            irods_backend.get_sub_path(study, include_parent=False)
        )
        if study.assays.count() > 0:
            ret += '<ul>'
            for assay in study.assays.all():
                ret += '<li>{}</li>'.format(
                    irods_backend.get_sub_path(assay, include_parent=False)
                )
            ret += '</ul>'
        ret += '</li>'
    ret += '</ul></li></ul>'
    return ret


@register.simple_tag
def get_material_search_url(item):
    """Return search URL for source or sample material"""
    return item['study'].get_url() + '/filter/{}'.format(item['name'])


# Table rendering --------------------------------------------------------------


@register.simple_tag
def get_irods_path(obj, sub_path=None):
    """
    Return iRODS path for an object or None if not found.

    :param obj: Study, Assay etc. type object
    :param sub_path: If defined, add a sub path below object
    :return: String or none
    """
    irods_backend = get_backend_api('omics_irods')
    if irods_backend:
        path = irods_backend.get_path(obj)
        if sub_path:
            path += '/' + sub_path
        return path
    return None


@register.simple_tag
def get_icon(obj):
    """
    Get Study or Assay icon.

    :param obj: Study or Assay object
    :return: String (contains HTML)
    """
    if isinstance(obj, Study):
        return '<i class="iconify text-info" data-icon="mdi:folder-table"></i>'
    elif isinstance(obj, Assay):
        return '<i class="iconify text-danger" data-icon="mdi:table-large"></i>'


@register.simple_tag
def get_isatab_tag_html(isatab):
    """
    Return tags for an ISA-Tab as HTML to be displayed in the sheet version
    list.

    :param isatab: ISATab object
    :return: String (contains HTML)
    """
    if not isatab.tags:
        return '<span class="text-muted">N/A</span>'
    ret = ''
    for tag in sorted(isatab.tags):
        ret += '<span class="badge badge-pill badge-{}">' '{}</span>\n'.format(
            TAG_COLORS[tag] if tag in TAG_COLORS else DEFAULT_TAG_COLOR,
            tag.capitalize(),
        )
    return ret


@register.simple_tag
def get_request_path_html(irods_request):
    """Return IrodsDataRequest short path as HTML"""
    ps = irods_request.get_short_path().split('/')
    ret = '<span class="text-muted">{}/</span>'.format('/'.join(ps[:-1]))
    ret += ps[-1]
    return ret


@register.simple_tag
def get_request_status_class(irods_request):
    """Return IrodsDataRequest status classes"""
    if irods_request.status not in REQUEST_STATUS_CLASSES:
        return ''
    return REQUEST_STATUS_CLASSES[irods_request.status]


@register.filter
def trim_base_path(path, prefix):
    """Return modified path that was stripped from a given prefix"""
    prefix = prefix.rstrip('/')
    if path.startswith(prefix):
        return path[len(prefix) : len(path)]
    return path
