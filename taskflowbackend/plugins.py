"""Plugins for the taskflowbackend app"""

import logging
import requests

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import (
    BackendPluginPoint,
    ProjectModifyPluginAPIMixin,
    get_backend_api,
)

from taskflowbackend.api import TaskflowAPI


logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']

# Local constants
APP_NAME = 'taskflowbackend'
TL_SUBMIT_DESC = 'Job submitted to Taskflow'
IRODS_CAT_SKIP_MSG = 'Categories are not synchronized into iRODS'


class BackendPlugin(ProjectModifyPluginAPIMixin, BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'taskflow'

    #: Title (used in templates)
    title = 'Taskflow'

    #: Iconify icon
    icon = 'mdi:database'

    #: Description string
    description = 'SODAR Taskflow backend for iRODS data transactions'

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
        # Skip for categories
        if project.type != PROJECT_TYPE_PROJECT:
            logger.debug(
                'Skipping perform_project_modify(): {}'.format(
                    IRODS_CAT_SKIP_MSG
                )
            )
            return

        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user,
                event_name='role_update',
                description='{} project in iRODS'.format(action.lower()),
            )
            tl_event.set_status('SUBMIT', TL_SUBMIT_DESC)

        taskflow = self.get_api()
        flow_data = {'owner': owner.username, 'settings': project_settings}
        if action == PROJECT_ACTION_UPDATE:  # Update
            flow_data['old_owner'] = project.get_owner().user.username
            if old_data['parent']:
                # Get inherited owners for project and its children to add
                new_roles = taskflow.get_inherited_users(project)
                flow_data['roles_add'] = new_roles
                new_users = set([r['user_name'] for r in new_roles])
                # Get old inherited owners from previous parent to remove
                old_roles = taskflow.get_inherited_users(old_data['parent'])
                flow_data['roles_delete'] = [
                    r for r in old_roles if r['user_name'] not in new_users
                ]
        else:  # Create
            flow_data['roles_add'] = [
                {
                    'project_uuid': str(project.sodar_uuid),
                    'user_name': a.user.username,
                }
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
            if tl_event:  # Update
                tl_event.set_status('FAILED', str(ex))
            raise ex
        if tl_event:
            tl_event.set_status('OK')

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
        # Skip for categories
        if role_as.project.type != PROJECT_TYPE_PROJECT:
            logger.debug(
                'Skipping perform_role_modify(): {}'.format(IRODS_CAT_SKIP_MSG)
            )
            return

        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=role_as.project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user,
                event_name='role_update',
                description='update project iRODS access for user {user}',
            )
            tl_event.add_object(
                obj=role_as.user, label='user', name=role_as.user.username
            )
            tl_event.set_status('SUBMIT', TL_SUBMIT_DESC)

        taskflow = self.get_api()
        flow_data = {'username': role_as.user.username}
        try:
            taskflow.submit(
                project=role_as.project,
                flow_name='role_update',
                flow_data=flow_data,
                tl_event=tl_event,
            )
        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))
            raise ex
        if tl_event:
            tl_event.set_status('OK')

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
        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=role_as.project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user,
                event_name='role_delete',
                description='remove project iRODS access from user {user}',
            )
            tl_event.add_object(
                obj=role_as.user, label='user', name=role_as.user.username
            )
            tl_event.set_status('SUBMIT', TL_SUBMIT_DESC)

        taskflow = self.get_api()
        flow_data = {'username': role_as.user.username}
        try:
            taskflow.submit(
                project=role_as.project,
                flow_name='role_delete',
                flow_data=flow_data,
                tl_event=tl_event,
            )
        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))
            raise ex
        if tl_event:
            tl_event.set_status('OK')

    def revert_role_delete(self, role_as, request):
        """
        Revert role assignment deletion deletion if errors have occurred in
        other apps.

        :param role_as: RoleAssignment object
        :param request: Request object for triggering the creation or update
        """
        # TODO: Implement this in your app plugin
        pass

    def perform_owner_transfer(
        self, project, new_owner, old_owner, old_owner_role, request
    ):
        """
        Perform additional actions to finalize project ownership transfer.

        :param project: Project object
        :param new_owner: SODARUser object for new owner
        :param old_owner: SODARUser object for previous owner
        :param old_owner_role: Role object for new role of previous owner
        :param request: Request object for triggering the transfer
        """
        # Skip for categories
        if project.type == PROJECT_TYPE_PROJECT:
            logger.debug(
                'Skipping perform_owner_transfer(): Only needed for inherited '
                'roles in categories'
            )
            return

        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user,
                event_name='role_owner_transfer',
                description='update iRODS user access for ownership transfer '
                'from {old_owner} to {new_owner}',
            )
            tl_event.add_object(
                obj=old_owner, label='old_owner', name=old_owner.username
            )
            tl_event.add_object(
                obj=new_owner, label='new_owner', name=new_owner.username
            )
            tl_event.set_status('SUBMIT', TL_SUBMIT_DESC)

        # Handle inherited owner roles for categories
        taskflow = self.get_api()
        flow_data = {
            'roles_add': taskflow.get_inherited_roles(project, new_owner),
            'roles_delete': taskflow.get_inherited_roles(project, old_owner),
        }
        try:
            taskflow.submit(
                project=None,  # Batch flow for multiple projects
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )
        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))
            raise ex
        if tl_event:
            tl_event.set_status('OK')

    def revert_owner_transfer(
        self, project, new_owner, old_owner, old_owner_role, request
    ):
        """
        Revert project ownership transfer if errors have occurred in other apps.

        :param project: Project object
        :param new_owner: SODARUser object for new owner
        :param old_owner: SODARUser object for previous owner
        :param old_owner_role: Role object for new role of previous owner
        :param request: Request object for triggering the transfer
        """
        # TODO: Implement this in your app plugin
        pass
