from django import template
from django.urls import reverse
from django.utils.timezone import localtime

# Projectroles dependency
from projectroles.plugins import ProjectAppPluginPoint

from timeline.api import TimelineAPI
from timeline.models import ProjectEvent

register = template.Library()


STATUS_STYLES = {
    'OK': 'bg-success',
    'INIT': 'bg-secondary',
    'SUBMIT': 'bg-warning',
    'FAILED': 'bg-danger',
    'INFO': 'bg-info',
    'CANCEL': 'bg-dark'}


@register.simple_tag
def get_status_style(status):
    return (STATUS_STYLES[status.status_type] + ' text-light') \
        if status.status_type in STATUS_STYLES else 'bg-light'


@register.simple_tag
def get_timestamp(obj):
    return localtime(obj.get_timestamp()).strftime('%Y-%m-%d %H:%M:%S')


@register.simple_tag
def get_app_url(event):
    # Projectroles is a special case
    if event.app == 'projectroles':
        return reverse('project_detail', kwargs={'pk': event.project.pk})

    else:
        app_plugin = ProjectAppPluginPoint.get_plugin(event.app)

        if app_plugin:
            return reverse(
                app_plugin.entry_point_url_id,
                kwargs={'project': event.project.pk})

    return '#'


@register.simple_tag
def get_event_description(event):
    """Return printable version of event description"""
    timeline = TimelineAPI()
    return timeline.get_event_description(event)


@register.simple_tag
def get_event_details(event):
    """Return HTML data for event detail popover"""
    ret = '<table class="table table-striped omics-card-table omics-tl-table-detail">'
    ret += '\n<thead>\n<th>Timestamp</th>\n<th>Description</th>\n' \
           '<th>Status</th>\n</thead>\n<tbody>'

    status_changes = event.get_status_changes(reverse=True)

    for status in status_changes:
        ret += '\n<tr><td>{}</td>\n<td>{}</td>\n' \
               '<td class="{}">{}</td>\n</tr>'.format(
                    get_timestamp(status),
                    status.description[:256] + (
                        '<em class="text-muted"> (...)</em>'
                        if len(status.description) > 256 else ''),
                    get_status_style(status),
                    status.status_type)
    ret += '\n</tbody>\n</table>'
    return ret


@register.simple_tag
def get_details_events(project, view_classified):
    """Return recent events for card on project details page"""
    events = ProjectEvent.objects.filter(project=project)

    if not view_classified:
        events = events.exclude(classified=True)

    events = events.order_by('-pk')

    return [
        x for x in events if x.get_current_status().status_type == 'OK'][:5]
