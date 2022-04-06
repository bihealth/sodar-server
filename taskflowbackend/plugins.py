"""Plugins for the taskflowbackend app"""

import logging
import requests

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import BackendPluginPoint, ProjectModifyPluginAPIMixin

from taskflowbackend.api import TaskflowAPI


logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']


class BackendPlugin(ProjectModifyPluginAPIMixin, BackendPluginPoint):
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

    def perform_project_modify(
        self,
        project,
        action,
        owner,
        project_settings,
        request,
        old_data=None,
        old_settings=None,
    ):
        """
        Perform additional actions to finalize project creation or update.

        :param project: Current project object (Project)
        :param action: Action to perform (CREATE or UPDATE)
        :param owner: User object of project owner
        :param project_settings: Project app settings (dict)
        :param request: Request object for triggering the creation or update
        :param old_data: Old project data in case of an update (dict or None)
        :param old_settings: Old app settings in case of update (dict or None)
        """
        taskflow = self.get_api()

        # TODO: Create separate timeline event
        # if tl_event:
        #     tl_event.set_status('SUBMIT')
        flow_data = {
            'project': project,
            'owner': owner,
            'settings': project_settings,
        }

        if action == PROJECT_ACTION_UPDATE:  # Update
            flow_data['old_owner'] = project.get_owner().user
            if old_data['parent']:
                # Get inherited owners for project and its children to add
                new_roles = taskflow.get_inherited_users(project)
                flow_data['roles_add'] = new_roles
                new_users = set([r['user'] for r in new_roles])
                # Get old inherited owners from previous parent to remove
                old_roles = taskflow.get_inherited_users(old_data['parent'])
                flow_data['roles_delete'] = [
                    r for r in old_roles if r['user'] not in new_users
                ]
        else:  # Create
            flow_data['roles_add'] = [
                {'project': project, 'user': a.user}
                for a in project.get_owners(inherited_only=True)
            ]

        try:
            taskflow.submit(
                project=project,
                flow_name='project_{}'.format(action.lower()),
                flow_data=flow_data,
            )
        except (
            requests.exceptions.ConnectionError,
            taskflow.FlowSubmitException,
        ) as ex:
            # TODO: Create timeline event
            # elif tl_event:  # Update
            #     tl_event.set_status('FAILED', str(ex))
            raise ex

    def revert_project_modify(
        self,
        project,
        action,
        owner,
        project_settings,
        request,
        old_data=None,
        old_settings=None,
    ):
        """
        Revert project creation or update if errors have occurred in other apps.

        :param project: Current project object (Project)
        :param action: Action which was performed (CREATE or UPDATE)
        :param owner: User object of project owner
        :param project_settings: Project app settings (dict)
        :param request: Request object for triggering the creation or update
        :param old_data: Old project data in case of update (dict or None)
        :param old_settings: Old app settings in case of update (dict or None)
        """
        # TODO: Run flow to remove collections and user group if creation failed
        pass

    def perform_role_modify(self, role_as, action, request, old_role=None):
        """
        Perform additional actions to finalize role assignment creation or
        update.

        :param role_as: RoleAssignment object
        :param action: Action to perform (CREATE or UPDATE)
        :param request: Request object for triggering the creation or update
        :param old_role: Role object for previous role in case of an update
        """
        taskflow = self.get_api()

        # TODO: Create separate taskflow event
        # if tl_event:
        #     tl_event.set_status('SUBMIT')
        # TODO: Update flow data
        flow_data = {
            'username': role_as.user.username,
            'user_uuid': str(role_as.user.sodar_uuid),
            'role_pk': role_as.role.pk,
        }
        try:
            taskflow.submit(
                project=role_as.project,
                flow_name='role_update',
                flow_data=flow_data,
            )
        except taskflow.FlowSubmitException as ex:
            # if tl_event:
            #     tl_event.set_status('FAILED', str(ex))
            raise ex

    def revert_role_modify(self, role_as, action, request, old_role=None):
        """
        Revert role assignment creation or update if errors have occurred in
        other apps.

        :param role_as: RoleAssignment object
        :param action: Action which was performed (CREATE or UPDATE)
        :param request: Request object for triggering the creation or update
        :param old_role: Role object for previous role in case of an update
        """
        # TODO: Implement
        pass

    def perform_role_delete(self, role_as, request):
        """
        Perform additional actions to finalize role assignment deletion.

        :param role_as: RoleAssignment object
        :param request: Request object for triggering the creation or update
        """
        # TODO: Implement
        pass
