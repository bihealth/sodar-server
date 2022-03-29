"""Plugins for the taskflowbackend app"""

import logging
import requests

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import BackendPluginPoint

from taskflowbackend.api import TaskflowAPI


logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'taskflow'

    #: Title (used in templates)
    title = 'Taskflow'

    #: Iconify icon
    icon = 'mdi:database'

    #: Description string
    description = 'SODAR Taskflow backend for data transactions'

    def get_api(self):
        """Return API entry point object."""
        return TaskflowAPI()

    def perform_project_modification(
        self, project, action, owner, project_settings, request, old_data=None
    ):
        """
        Perform additional actions to finalize project creation or update.

        :param project: Current project object (Project)
        :param action: Action to perform (CREATE or UPDATE)
        :param owner: User object of project owner
        :param project_settings: Dict
        :param request: Request object for triggering the creation or update
        :param old_data: Old project data in case of an update (dict or None)
        """
        taskflow = self.get_api()

        # TODO: Create separate timeline event
        # if tl_event:
        #     tl_event.set_status('SUBMIT')
        flow_data = {
            'project_title': project.title,
            'project_description': project.description,
            'parent_uuid': str(project.parent.sodar_uuid)
            if project.parent
            else '',
            'public_guest_access': project.public_guest_access,
            'owner_username': owner.username,
            'owner_uuid': str(owner.sodar_uuid),
            'owner_role_pk': Role.objects.get(name=PROJECT_ROLE_OWNER).pk,
            'settings': project_settings,
        }

        if action == PROJECT_ACTION_UPDATE:  # Update
            old_owner = project.get_owner().user
            flow_data['old_owner_uuid'] = str(old_owner.sodar_uuid)
            flow_data['old_owner_username'] = old_owner.username
            flow_data['project_readme'] = project.readme.raw
            if old_data.parent:
                # Get inherited owners for project and its children to add
                new_roles = taskflow.get_inherited_users(project)
                flow_data['roles_add'] = new_roles
                new_users = set([r['username'] for r in new_roles])

                # Get old inherited owners from previous parent to remove
                old_roles = taskflow.get_inherited_users(old_data.parent)
                flow_data['roles_delete'] = [
                    r for r in old_roles if r['username'] not in new_users
                ]
        else:  # Create
            flow_data['roles_add'] = [
                {
                    'project_uuid': str(project.sodar_uuid),
                    'username': a.user.username,
                }
                for a in project.get_owners(inherited_only=True)
            ]

        try:
            taskflow.submit(
                project_uuid=str(project.sodar_uuid),
                flow_name='project_{}'.format(action.lower()),
                flow_data=flow_data,
                request=request,
            )
        except (
            requests.exceptions.ConnectionError,
            taskflow.FlowSubmitException,
        ) as ex:
            # TODO: Create timeline event
            # elif tl_event:  # Update
            #     tl_event.set_status('FAILED', str(ex))
            raise ex

    def revert_project_modification(
        self, project, action, owner, project_settings, request, old_data=None
    ):
        """
        Revert project creation or update if errors have occurred in other apps.

        :param project: Current project object (Project)
        :param action: Action which was performed (CREATE or UPDATE)
        :param owner: User object of project owner
        :param project_settings: Dict
        :param request: Request object for triggering the creation or update
        :param old_data: Old project data in case of an update (dict or None)
        """
        # TODO: Run flow to remove collections and user group if creation failed
        pass
