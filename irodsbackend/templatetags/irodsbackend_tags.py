from django import template
from django.urls import reverse

from ..api import IrodsAPI


irods_backend = IrodsAPI()

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
    url_kwargs = {'path': irods_path}

    if project:
        url_kwargs['project'] = project.omics_uuid

    return '<span class="badge badge-pill badge-info omics-irods-stats"' \
           'stats-url="{url}">' \
           '<i class="fa fa-spin fa-circle-o-notch"></i> Updating stats..' \
           '</span>'.format(
            url=reverse('irodsbackend:stats', kwargs=url_kwargs))
