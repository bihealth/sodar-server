from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode

from ..api import IrodsAPI


irods_backend = IrodsAPI(conn=False)

register = template.Library()


# TODO: Not needed anymore, can be removed
@register.simple_tag
def get_irods_path(obj):
    return irods_backend.get_path(obj)


@register.simple_tag
def get_stats_html(irods_path, project=None):
    """
    Return collection stats badge element into a template
    :param irods_path: Full iRODS path (string)
    :param project: Project object (optional)
    :return: String (contains HTML)
    """
    url_kwargs = {'project': str(project.sodar_uuid)} if project else None
    query_string = {'path': irods_path}
    url = (
        reverse('irodsbackend:stats', kwargs=url_kwargs)
        + '?'
        + urlencode(query_string)
    )

    return (
        '<span class="badge badge-pill badge-info sodar-irods-stats"'
        'stats-url="{}">'
        '<i class="fa fa-spin fa-circle-o-notch"></i> Updating..'
        '</span>'.format(url)
    )


@register.simple_tag
def is_webdav_enabled():
    return settings.IRODS_WEBDAV_ENABLED


@register.simple_tag
def get_webdav_url():
    if settings.IRODS_WEBDAV_ENABLED:
        return settings.IRODS_WEBDAV_URL.rstrip('/')
