"""API for the timeline app, used by other apps to add and update events"""

import re

# Access Django user model
from omics_data_mgmt.users.models import User

# Projectroles dependency
from projectroles.plugins import ProjectAppPluginPoint
from projectroles.utils import get_app_names

from timeline.models import ProjectEvent, ProjectEventObjectRef


APP_NAMES = get_app_names()


class TimelineAPI:
    """Timeline API to be used by Django apps"""

    def __init__(self):
        pass

    def add_event(
            self, project, app_name, user, event_name, description,
            classified=False, extra_data=None, status_type=None,
            status_desc=None, status_extra_data=None):
        """
        Create and save a ProjectEvent
        :param project: Project object
        :param app_name: ID string of app from which event was invoked (NOTE:
                         should correspond to member "name" in app plugin!)
        :param user: User invoking the event
        :param event_name: Event ID string (must match schema)
        :param description: Description of status change (may include {object
            label} references)
        :param classified: Whether event is classified (boolean, optional)
        :param extra_data: Additional event data (dict, optional)
        :param status_type: Initial status type (string, optional)
        :param status_desc: Initial status description (string, optional)
        :param status_extra_data: Extra data for initial status (dict, optional)
        :return: ProjectEvent object
        :raise: TypeError if app_name is invalid
        """
        if app_name not in APP_NAMES:
            raise TypeError('Unknown app name (active apps: {})'.format(
                ', '.join(v for v in APP_NAMES)))

        event = ProjectEvent()
        event.project = project
        event.app = app_name
        event.user = user
        event.event_name = event_name
        event.description = description
        event.classified = classified

        if extra_data:
            event.extra_data = extra_data

        event.save()

        # Always add "INIT" status when creating, except for "INFO"
        if status_type != 'INFO':
            event.set_status('INIT')

        # Add additional status if set (use if e.g. event is immediately "OK")
        if status_type:
            event.set_status(status_type, status_desc, status_extra_data)

        return event

    def get_project_events(self, project, classified=False):
        """
        Return ProjectEvent objects for project
        :param project: Project object
        :param classified: Include classified
        :return: QuerySet
        """
        events = ProjectEvent.objects.filter(project=project)

        if not classified:
            events = events.filter(classified=False)

        return events

    def get_event_description(self, event):
        """Return printable version of event description"""
        desc = event.description
        unknown_label = '(unknown)'
        not_found_label = '<span class="text-danger">{}</span>'

        ref_ids = re.findall("{'?(.*?)'?\}", desc)

        if len(ref_ids) == 0:
            return event.description

        refs = {}

        for r in ref_ids:
            try:
                ref_obj = ProjectEventObjectRef.objects.get(
                    event=event,
                    label=r)

                # User is a special case
                if ref_obj.object_model == 'User':
                    try:
                        user = User.objects.get(pk=ref_obj.object_pk)
                        refs[r] = '<a href="mailto:{}">{}</a>'.format(
                            user.email, user.username)

                    except User.DoesNotExist:
                        refs[r] = unknown_label

                # Projectroles is also special
                elif event.app == 'projectroles':
                    refs[r] = not_found_label.format(ref_obj.name)

                # Apps with plugins
                else:
                    app_plugin = ProjectAppPluginPoint.get_plugin(
                        name=event.app)

                    link_data = app_plugin.get_object_link(
                        ref_obj.object_model, ref_obj.object_pk)

                    if link_data:
                        refs[r] = '<a href="{}" {}>{}</a>'.format(
                            link_data['url'],
                            ('target="_blank"'
                             if 'blank' in link_data and
                                link_data['blank'] is True else ''),
                            link_data['label'])

                    else:
                        refs[r] = not_found_label.format(ref_obj.name)

            except ProjectEventObjectRef.DoesNotExist:
                refs[r] = unknown_label

        return event.description.format(**refs)
