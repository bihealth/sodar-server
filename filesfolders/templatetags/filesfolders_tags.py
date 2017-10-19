from django import template

# Projectroles dependency
from projectroles.models import ProjectSetting
from projectroles.utils import get_project_setting

from ..models import File, HyperLink


APP_NAME = 'filesfolders'


register = template.Library()


@register.filter
def get_class(obj):
    return obj.__class__.__name__


@register.filter
def force_wrap(obj, length):
    # If string contains spaces, leave wrapping to browser
    if obj.find(' ') == -1 and len(obj) > length:
        return '<wbr />'.join(
            [obj[i:i + length] for i in range(0, len(obj), length)])

    return obj


@register.assignment_tag
def get_details_files(project):
    """Return recent files/links for card on project details page"""
    files = File.objects.filter(
        project=project).order_by('-date_modified')[:5]
    links = HyperLink.objects.filter(
        project=project).order_by('-date_modified')[:5]
    ret = list(files) + list(links)
    ret.sort(key=lambda x: x.date_modified, reverse=True)
    return ret[:5]


@register.simple_tag
def allow_public_links(project):
    """Return the boolean value for allow_public_links in project settings"""
    return get_project_setting(project, APP_NAME, 'allow_public_links')
