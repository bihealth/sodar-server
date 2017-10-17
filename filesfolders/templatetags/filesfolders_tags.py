from django import template

# Projectroles dependency
from projectroles.models import ProjectSetting

from ..models import File, HyperLink


register = template.Library()


@register.filter
def get_class(obj):
    return obj.__class__.__name__


@register.filter
def force_wrap(obj, length):
    # TODO: Could make this more elegant, wrap by special char or end of word?
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
    return ProjectSetting.objects.get_setting_value(
        project, 'files', 'allow_public_links')
