from django import template
from django.conf import settings
import mistune

from ..models import RoleAssignment
from ..plugins import get_backend_api


register = template.Library()


@register.simple_tag
def omics_constant(value):
    """Get value from OMICS_CONSTANTS in settings"""
    return settings.OMICS_CONSTANTS[value] \
        if value in settings.OMICS_CONSTANTS else None


@register.simple_tag
def get_plugin_info(plugin, pk):
    """Return data from plugin get_info() with a specific project ID"""
    return plugin.get_info(pk)


@register.simple_tag
def get_latest_activity(project, timeline):
    """Return datetime for latest project activity from Timeline"""
    # TODO: Get the latest activity which 1) is OK and 2) has changed data
    # TODO: (need to make some modifications to timeline for this)

    timeline = get_backend_api('timeline_backend')

    if not timeline:
        return '<td colspan="4"></td>\n'

    events = timeline.get_project_events(project, classified=False)

    if events.count() > 0:
        latest_event = events.order_by('-pk')[0]

        ret = '<td style="white-space: nowrap;">{}</td>\n<td>' \
            '<a href="mailto:{}">{}</a></td>\n<td>{}</td>\n'.format(
                latest_event.get_timestamp().strftime('%Y-%m-%d %H:%M'),
                latest_event.user.email,
                latest_event.user.username,
                timeline.get_event_description(latest_event))
        return ret


@register.simple_tag
def get_description(project):
    """Return description, truncate if needed"""
    # TODO: Can be removed once we add a smart overflow popup in CSS
    max_len = 128
    ret = project.description[:max_len]

    if len(project.description) > max_len:
        ret += '...'

    return ret


@register.simple_tag
def get_user_role_str(project, user):
    try:
        role_as = RoleAssignment.objects.get(project=project, user=user)
        return role_as.role.name.split(' ')[1]   # HACK to save screen space :)

    except RoleAssignment.DoesNotExist:
        return ''


# TODO: Could make this a filter too I guess
@register.simple_tag
def render_markdown(raw_markdown):
    return mistune.markdown(raw_markdown)
