"""Plugins for the taskflowbackend app"""

import logging
import requests

from irods.exception import UserGroupDoesNotExist

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import RoleAssignment, SODAR_CONSTANTS
from projectroles.plugins import (
    BackendPluginPoint,
    ProjectModifyPluginMixin,
    get_backend_api,
)

from taskflowbackend.api import TaskflowAPI


app_settings = AppSettingAPI()
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


class BackendPlugin(ProjectModifyPluginMixin, BackendPluginPoint):
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
        project_settings,
        old_data=None,
        old_settings=None,
        request=None,
    ):
        """
        Perform additional actions to finalize project creation or update.

        :param project: Current project object (Project)
        :param action: Action to perform (CREATE or UPDATE)
        :param project_settings: Project app settings (dict)
        :param old_data: Old project data in case of an update (dict or None)
        :param old_settings: Old app settings in case of update (dict or None)
        :param request: Request object or None
        """
        # Skip for categories
        if project.type != PROJECT_TYPE_PROJECT:
            logger.debug('Skipping: {}'.format(IRODS_CAT_SKIP_MSG))
            return

        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='project_{}'.format(action.lower()),
                description='{} project in iRODS'.format(action.lower()),
            )
            tl_event.set_status('SUBMIT', TL_SUBMIT_DESC)

        taskflow = self.get_api()
        owner = project.get_owner().user
        flow_data = {'owner': owner.username, 'settings': project_settings}
        inh_owners = [
            a.user.username for a in project.get_owners(inherited_only=True)
        ]

        if action == PROJECT_ACTION_UPDATE:  # Update
            flow_data['users_add'] = []
            all_members = [a.user.username for a in project.get_all_roles()]
            if old_data['parent'] != project.parent:
                flow_data['users_add'] = inh_owners
                old_parent_owners = [
                    a.user.username for a in old_data['parent'].get_owners()
                ]
                flow_data['users_delete'] = [
                    u for u in old_parent_owners if u not in all_members
                ]
            if owner.username not in flow_data['users_add']:
                flow_data['users_add'].append(owner.username)
        else:  # Create
            flow_data['users_add'] = inh_owners

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
        project_settings,
        old_data=None,
        old_settings=None,
        request=None,
    ):
        """
        Revert project creation or update if errors have occurred in other apps.

        :param project: Current project object (Project)
        :param action: Action which was performed (CREATE or UPDATE)
        :param project_settings: Project app settings (dict)
        :param old_data: Old project data in case of update (dict or None)
        :param old_settings: Old app settings in case of update (dict or None)
        :param request: Request object or None
        """
        if action == PROJECT_ACTION_UPDATE:
            return  # Reverting an update is not needed as no other app can fail

        irods_backend = get_backend_api('omics_irods')
        irods_session = irods_backend.get_session()
        timeline = get_backend_api('timeline_backend')
        project_path = irods_backend.get_path(project)
        reverted = False

        if irods_session.collections.exists(project_path):
            logger.debug('Removing project collection: {}'.format(project_path))
            irods_session.collections.remove(project_path)
            reverted = True
        group_name = irods_backend.get_user_group_name(project)

        try:
            irods_session.user_groups.get(group_name)
            logger.debug('Removing user group: {}'.format(group_name))
            irods_session.user_groups.remove(group_name)
            reverted = True
        except UserGroupDoesNotExist:
            pass

        if timeline and reverted:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='project_create_revert',
                description='revert project creation in iRODS',
            )
            tl_event.set_status('OK')

    def perform_role_modify(self, role_as, action, old_role=None, request=None):
        """
        Perform additional actions to finalize role assignment creation or
        update.

        :param role_as: RoleAssignment object
        :param action: Action to perform (CREATE or UPDATE)
        :param old_role: Role object for previous role in case of an update
        :param request: Request object or None
        """
        # Skip for categories
        if role_as.project.type != PROJECT_TYPE_PROJECT:
            logger.debug('Skipping: {}'.format(IRODS_CAT_SKIP_MSG))
            return

        # Skip for update (bo action needed)
        if action == PROJECT_ACTION_UPDATE:
            logger.debug('Skipping: User already has iRODS access')
            return

        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=role_as.project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
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

    def revert_role_modify(self, role_as, action, old_role=None, request=None):
        """
        Revert role assignment creation or update if errors have occurred in
        other apps.

        :param role_as: RoleAssignment object
        :param action: Action which was performed (CREATE or UPDATE)
        :param old_role: Role object for previous role in case of an update
        :param request: Request object or None
        """
        if action == PROJECT_ACTION_UPDATE:
            return  # No action needed for update

        irods_backend = get_backend_api('omics_irods')
        irods_session = irods_backend.get_session()
        timeline = get_backend_api('timeline_backend')
        group_name = irods_backend.get_user_group_name(role_as.project)
        user_name = role_as.user.username
        reverted = False

        try:
            group = irods_session.user_groups.get(group_name)
            logger.debug(
                'Removing user {} from group {}'.format(user_name, group_name)
            )
            if group.hasmember(user_name):
                group.removemember(
                    user_name=user_name, user_zone=irods_session.zone
                )
                reverted = True
        except Exception as ex:
            logger.error('Error removing member: {}'.format(ex))
            return

        if timeline and reverted:
            tl_event = timeline.add_event(
                project=role_as.project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_update_revert',
                description='revert adding iRODS access for '
                'user {{{}}}'.format('user'),
            )
            tl_event.add_object(role_as.user, 'user', user_name)
            tl_event.set_status('OK')

    def perform_role_delete(self, role_as, request=None):
        """
        Perform additional actions to finalize role assignment deletion.

        :param role_as: RoleAssignment object
        :param request: Request object or None
        """
        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=role_as.project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
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

    def revert_role_delete(self, role_as, request=None):
        """
        Revert role assignment deletion deletion if errors have occurred in
        other apps.

        :param role_as: RoleAssignment object
        :param request: Request object or None
        """
        irods_backend = get_backend_api('omics_irods')
        irods_session = irods_backend.get_session()
        timeline = get_backend_api('timeline_backend')
        group_name = irods_backend.get_user_group_name(role_as.project)
        user_name = role_as.user.username
        reverted = False

        try:
            group = irods_session.user_groups.get(group_name)
            logger.debug(
                'Adding user {} to group {}'.format(user_name, group_name)
            )
            if not group.hasmember(user_name):
                group.addmember(
                    user_name=user_name, user_zone=irods_session.zone
                )
                reverted = True
        except Exception as ex:
            logger.error('Error adding member: {}'.format(ex))
            return

        if timeline and reverted:
            tl_event = timeline.add_event(
                project=role_as.project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_delete_revert',
                description='revert removing iRODS access from '
                'user {{{}}}'.format('user'),
            )
            tl_event.add_object(role_as.user, 'user', user_name)
            tl_event.set_status('OK')

    def perform_owner_transfer(
        self, project, new_owner, old_owner, old_owner_role, request=None
    ):
        """
        Perform additional actions to finalize project ownership transfer.

        :param project: Project object
        :param new_owner: SODARUser object for new owner
        :param old_owner: SODARUser object for previous owner
        :param old_owner_role: Role object for new role of previous owner
        :param request: Request object or None
        """
        # Skip for projects as both users retain the same iRODS access
        if project.type == PROJECT_TYPE_PROJECT:
            logger.debug('Skipping: Only used for category updates')
            return

        def _get_inherited_roles(project, user, roles=None):
            if roles is None:
                roles = []
            if (
                project.type == PROJECT_TYPE_PROJECT
                and not RoleAssignment.objects.filter(
                    project=project, user=user
                )
            ):
                r = {
                    'project_uuid': str(project.sodar_uuid),
                    'user_name': user.username,
                }
                if r not in roles:  # Avoid unnecessary dupes
                    roles.append(r)
            for child in project.get_children():
                roles = _get_inherited_roles(child, user, roles)
            return roles

        timeline = get_backend_api('timeline_backend')
        tl_event = None
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_owner_transfer',
                description='update iRODS access for ownership transfer '
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
            'roles_add': _get_inherited_roles(project, new_owner),
            'roles_delete': _get_inherited_roles(project, old_owner),
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

    # NOTE: revert_owner_transfer() not needed at the moment
    # (No other plugin gets called with after taskflowbackend)

    def perform_project_sync(self, project):
        """
        Synchronize existing projects to ensure related data exists when the
        syncmodifyapi management comment is called. Should mostly be used in
        development when the development databases have been e.g. modified or
        recreated.

        :param project: Current project object (Project)
        """
        # Skip for categories
        if project.type != PROJECT_TYPE_PROJECT:
            logger.debug('Skipping: {}'.format(IRODS_CAT_SKIP_MSG))
            return
        self.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all_settings(project),
        )
