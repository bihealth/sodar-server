from django import template

# Projectroles dependency
from projectroles.models import ProjectSetting
from projectroles.project_settings import get_project_setting

from ..models import File, FileData, HyperLink, BaseFilesfoldersClass


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


@register.simple_tag
def get_details_items(project):
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


@register.simple_tag
def find_filesfolders_items(search_term, keyword):
    """Return files/links based on a search term and possible keyword"""

    if not keyword:
        files = File.objects.find(search_term)
        links = HyperLink.objects.find(search_term)
        ret = list(files) + list(links)
        ret.sort(key=lambda x: x.name)
        return ret

    elif keyword == 'file':
        return File.objects.find(search_term)

    elif keyword == 'link':
        return HyperLink.objects.find(search_term)

    return None


@register.simple_tag
def get_file_icon(file):
    mt = file.file.file.mimetype

    if mt == 'application/pdf':
        return 'file-pdf-o'

    elif mt == 'application/vnd.openxmlformats-officedocument.' \
               'presentationml.presentation':
        return 'file-powerpoint-o'

    elif 'compressed' in mt or 'zip' in mt:
        return 'file-archive-o'

    elif ('excel' in mt or
            mt == 'application/vnd.openxmlformats-'
                  'officedocument.spreadsheetml.sheet'):
        return 'file-excel-o'

    elif 'image/' in mt:
        return 'file-image-o'

    elif 'text/' in mt:
        return 'file-text-o'

    # Default if not found
    return 'file-o'
