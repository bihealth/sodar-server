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
def get_stats_html(irods_path, classes='badge-success'):
    """
    Return collection stats badge element into a template
    :param irods_path: Full iRODS path (string)
    :param classes: Extra classes (string)
    :return: String (contains HTML)
    """
    return '<span class="badge badge-pill badge-info omics-irods-stats"' \
           'stats-url="{url}">' \
           '<i class="fa fa-spin fa-circle-o-notch"></i> Updating stats..' \
           '</span>'.format(
            classes=classes,
            url=reverse('irodsbackend:stats', kwargs={'path': irods_path}))
