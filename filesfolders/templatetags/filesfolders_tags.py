from django import template

# Projectroles dependency
from projectroles.project_settings import get_project_setting

from ..models import File, Folder, HyperLink, FILESFOLDERS_FLAGS


APP_NAME = 'filesfolders'


register = template.Library()


@register.filter
def get_class(obj):
    return obj.__class__.__name__


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


@register.simple_tag
def get_flag(flag_name, tooltip=True):
    f = FILESFOLDERS_FLAGS[flag_name]
    tip_str = ''

    if tooltip:
        tip_str = 'title="{}" data-toggle="tooltip" ' \
                  'data-placement="top"'.format(f['label'])

    return '<i class="fa fa-{} fa-fw text-{} sodar-ff-flag-icon" {}>' \
           '</i>'.format(
                f['icon'], f['color'], tip_str)


@register.simple_tag
def get_flag_status(val, choice):
    if val == choice:
        return 'checked="checked"'

    return ''


@register.simple_tag
def get_flag_classes(flag_name):
    """Return CSS classes for item link based on flag name"""
    return FILESFOLDERS_FLAGS[flag_name]['text_classes']
