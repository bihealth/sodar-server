"""Template tags for the irodsbackend app"""

from django import template
from django.db.models import Model

from irodsbackend.api import IrodsAPI

# Projectroles dependency
from projectroles.models import Project, SODARUser

# Samplesheets dependency
from samplesheets.utils import get_webdav_url as _get_webdav_url


irods_backend = IrodsAPI()
register = template.Library()


@register.simple_tag
def get_irods_path(obj: Model) -> str:
    return irods_backend.get_path(obj)


@register.simple_tag
def get_stats_html(irods_path: str, project: Project) -> str:
    """
    Return collection stats badge element into a template.

    :param irods_path: Full iRODS path (string)
    :param project: Project object
    :return: String (contains HTML)
    """
    return (
        f'<span class="badge badge-pill badge-info sodar-irods-stats" '
        f'data-stats-path="{irods_path}" '
        f'data-project-uuid="{project.sodar_uuid}">'
        f'<i class="iconify spin" data-icon="mdi:loading"></i> Updating..'
        f'</span>'
    )


@register.simple_tag
def get_webdav_url(project: Project, user: SODARUser) -> str:
    url = _get_webdav_url(project, user)
    if not url:
        return ''
    return url
