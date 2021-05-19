from django import template
from django.urls import reverse
from django.utils.http import urlencode

from irodsbackend.api import IrodsAPI

# Samplesheets dependency
from samplesheets.utils import get_webdav_url as _get_webdav_url


irods_backend = IrodsAPI(conn=False)
register = template.Library()


@register.simple_tag
def get_irods_path(obj):
    return irods_backend.get_path(obj)


@register.simple_tag
def get_stats_html(irods_path, project):
    """
    Return collection stats badge element into a template.

    :param irods_path: Full iRODS path (string)
    :param project: Project object
    :return: String (contains HTML)
    """
    url_kwargs = {'project': str(project.sodar_uuid)}
    query_string = {'path': irods_path}
    url = (
        reverse('irodsbackend:stats', kwargs=url_kwargs)
        + '?'
        + urlencode(query_string)
    )
    return (
        '<span class="badge badge-pill badge-info sodar-irods-stats" '
        'data-stats-url="{}">'
        '<i class="iconify spin" data-icon="mdi:loading"></i> Updating..'
        '</span>'.format(url)
    )


@register.simple_tag
def get_webdav_url(project, user):
    url = _get_webdav_url(project, user)
    if not url:
        return ''
    return url
