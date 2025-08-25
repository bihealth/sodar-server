"""Plugins for the taskflowbackend app"""

import logging

from irods.exception import GroupDoesNotExist

from django.contrib.auth import get_user_model

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import RoleAssignment, SODAR_CONSTANTS, ROLE_RANKING
from projectroles.plugins import (
    BackendPluginPoint,
    ProjectModifyPluginMixin,
    PluginAPI,
)

from taskflowbackend.api import TaskflowAPI
from taskflowbackend.irods_utils import get_flow_role


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
plugin_api = PluginAPI()
User = get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_VIEWER = SODAR_CONSTANTS['PROJECT_ROLE_VIEWER']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']

# Local constants
APP_NAME = 'taskflowbackend'
IRODS_CAT_SKIP_MSG = 'Categories are not synchronized into iRODS'
RANK_OWNER = ROLE_RANKING[PROJECT_ROLE_OWNER]
RANK_DELEGATE = ROLE_RANKING[PROJECT_ROLE_DELEGATE]
RANK_VIEWER = ROLE_RANKING[PROJECT_ROLE_VIEWER]
TASKFLOW_INFO_SETTINGS = [
    'TASKFLOW_IRODS_CONN_TIMEOUT',
    'TASKFLOW_LOCK_RETRY_COUNT',
    'TASKFLOW_LOCK_RETRY_INTERVAL',
    'TASKFLOW_ZONE_PROGRESS_INTERVAL',
]
TL_SUBMIT_DESC = 'Job submitted to Taskflow'


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

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = TASKFLOW_INFO_SETTINGS

    # Internal helpers ---------------------------------------------------------

    @classmethod
    def _get_child_projects(cls, project):
        """
        Return category children of type PROJECT.

        :param project: Project object
        :return: List
        """
        if project.is_project():
            return []
        return [p for p in project.get_children(flat=True) if p.is_project()]

    # API methods --------------------------------------------------------------

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
        **kwargs,
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
        # Skip for categories unless moving under a different category
        if project.is_category() and (
            action == PROJECT_ACTION_CREATE
            or old_data['parent'] == project.parent
        ):
            logger.debug('Skipping: Nothing to modify')
            return

        taskflow = self.get_api()
        timeline = plugin_api.get_backend_api('timeline_backend')
        owner = project.get_owner().user
        all_roles = [
            a for a in project.get_roles() if a.role.rank < RANK_VIEWER
        ]
        all_members = [a.user.username for a in all_roles]
        children = self._get_child_projects(project)

        if project.is_project():
            flow_data = {
                'owner': owner.username,
                'settings': project_settings,
                'roles_add': [],
            }
            if (
                action == PROJECT_ACTION_UPDATE
                and old_data['parent'] != project.parent
            ):
                inh_members = [
                    get_flow_role(project, a.user, a.role.rank)
                    for a in all_roles
                    if a.project != project and a.user != owner
                ]
                flow_data['roles_add'] = inh_members
                old_inh_members = [
                    get_flow_role(project, a.user, a.role.rank)
                    for a in old_data['parent'].get_roles()
                ]
                flow_data['roles_delete'] = [
                    r
                    for r in old_inh_members
                    if r['user_name'] not in all_members
                ]
            else:  # Create
                flow_data['roles_add'] = [
                    get_flow_role(project, a.user, a.role.rank)
                    for a in all_roles
                    if a.user != owner
                ]
            taskflow.submit(
                project=project,
                flow_name=f'project_{action.lower()}',
                flow_data=flow_data,
            )
        # If updating parent in category, add role_update_irods_batch call
        elif (
            action == PROJECT_ACTION_UPDATE
            and children
            and old_data['parent'] != project.parent
        ):
            flow_data = {'roles_add': [], 'roles_delete': []}
            old_inh_roles = (
                old_data['parent'].get_roles() if old_data['parent'] else []
            )
            for c in children:
                for a in all_roles:
                    flow_data['roles_add'].append(
                        get_flow_role(c, a.user, a.role.rank)
                    )
                c_members = [a.user.username for a in c.get_roles()]
                for a in old_inh_roles:
                    if a.user.username not in c_members:
                        flow_data['roles_delete'].append(
                            get_flow_role(c, a.user, a.role.rank)
                        )
            taskflow.submit(
                project=None,
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )

        if timeline:
            # Change event name and description if called from syncmodifyapi
            tl_action = (
                'sync' if kwargs.get('sync_modify_api') else action.lower()
            )
            timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name=f'project_{tl_action}',
                description=f'{tl_action} {project.type.lower()} in iRODS',
                status_type=timeline.TL_STATUS_OK,
            )

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

        irods_backend = plugin_api.get_backend_api('omics_irods')
        timeline = plugin_api.get_backend_api('timeline_backend')
        project_path = irods_backend.get_path(project)

        with irods_backend.get_session() as irods:
            if irods.collections.exists(project_path):
                logger.debug(f'Removing project collection: {project_path}')
                irods.collections.remove(project_path)
            project_group = irods_backend.get_group_name(project)
            try:
                irods.user_groups.get(project_group)
                logger.debug(f'Removing user group: {project_group}')
                irods.users.remove(project_group)
            except GroupDoesNotExist:
                pass
            project_group = irods_backend.get_group_name(project, owner=True)
            try:
                irods.user_groups.get(project_group)
                logger.debug(f'Removing owner group: {project_group}')
                irods.users.remove(project_group)
            except GroupDoesNotExist:
                pass

        if timeline:
            timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='project_create_revert',
                description='revert project creation in iRODS',
                status_type=timeline.TL_STATUS_OK,
            )

    def perform_role_modify(self, role_as, action, old_role=None, request=None):
        """
        Perform additional actions to finalize role assignment creation or
        update.

        :param role_as: RoleAssignment object
        :param action: Action to perform (CREATE or UPDATE)
        :param old_role: Role object for previous role in case of an update
        :param request: Request object or None
        """
        owner_update = False
        if action == PROJECT_ACTION_UPDATE:
            owner_update = not (
                (
                    role_as.role.rank <= RANK_DELEGATE
                    and old_role.rank <= RANK_DELEGATE
                )
                or (
                    role_as.role.rank > RANK_DELEGATE
                    and old_role.rank > RANK_DELEGATE
                )
            )
        # Skip for update (unless updating to/from viewer, finder, owner or
        # delegate)
        if (
            action == PROJECT_ACTION_UPDATE
            and role_as.role.rank < RANK_VIEWER
            and old_role.rank < RANK_VIEWER
            and not owner_update
        ):
            logger.debug('Skipping: No iRODS update needed')
            return

        taskflow = self.get_api()
        timeline = plugin_api.get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        children = self._get_child_projects(project)
        flow_data = {'roles_add': [], 'roles_delete': []}
        role_rank = role_as.role.rank
        # Set overriding inherited role if present
        # NOTE: In practice we should not call this method with a role of higher
        #       rank than what already exists, but it may happen e.g. in testing
        if project.parent:
            parent_role_as = project.parent.get_role(user)
            if parent_role_as and parent_role_as.role.rank < role_rank:
                role_rank = parent_role_as.role.rank

        if project.is_project():
            if role_as.role.rank < RANK_VIEWER:
                flow_data['roles_add'].append(
                    get_flow_role(project, user, role_rank)
                )
            elif old_role and old_role.rank < RANK_VIEWER:
                flow_data['roles_delete'].append(
                    get_flow_role(project, user, role_rank)
                )
        elif children:  # Category children
            for c in children:
                c_role = c.get_role(user)
                if role_as.role.rank >= RANK_VIEWER and (
                    not c_role or c_role.role.rank >= RANK_VIEWER
                ):
                    flow_data['roles_delete'].append(
                        get_flow_role(c, user, role_rank)
                    )
                else:  # Update user, ensure child rank is not downgraded
                    c_rank = role_rank
                    if c_role and c_role.role.rank < role_rank:
                        c_rank = c_role.role.rank
                    flow_data['roles_add'].append(
                        get_flow_role(c, user, c_rank)
                    )
        taskflow.submit(
            project=None,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )

        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_update',
                description='update {} iRODS access for user {{{}}}'.format(
                    project.type.lower(), 'user'
                ),
                status_type=timeline.TL_STATUS_OK,
            )
            tl_event.add_object(obj=user, label='user', name=user.username)

    def revert_role_modify(self, role_as, action, old_role=None, request=None):
        """
        Revert role assignment creation or update if errors have occurred in
        other apps.

        :param role_as: RoleAssignment object
        :param action: Action which was performed (CREATE or UPDATE)
        :param old_role: Role object for previous role in case of an update
        :param request: Request object or None
        """
        timeline = plugin_api.get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        user_name = user.username
        flow_data = {'roles_add': [], 'roles_delete': []}
        owner_update = False
        if action == PROJECT_ACTION_UPDATE:
            owner_update = not (
                (
                    role_as.role.rank <= RANK_DELEGATE
                    and old_role.rank <= RANK_DELEGATE
                )
                or (
                    role_as.role.rank > RANK_DELEGATE
                    and old_role.rank > RANK_DELEGATE
                )
            )

        # Revert creation or update from viewer/finder role for project
        if project.is_project() and (
            action == PROJECT_ACTION_CREATE
            or (old_role and old_role.rank >= RANK_VIEWER)
        ):
            flow_data['roles_delete'].append(
                get_flow_role(
                    project, user_name, old_role.rank if old_role else None
                )
            )
        # Update project owner/delegate
        elif (
            project.is_project()
            and action == PROJECT_ACTION_UPDATE
            and owner_update
        ):
            # Update happens with roles_add
            flow_data['roles_add'].append(
                get_flow_role(
                    project, user_name, old_role.rank if old_role else None
                )
            )
        # Update roles in category child projects
        elif project.is_category():
            children = self._get_child_projects(project)
            for c in children:
                # Search for inherited roles for child
                # NOTE: role_as still exists so it has to be excluded
                c_as = (
                    RoleAssignment.objects.filter(
                        user=user, project__in=[c] + list(c.get_parents())
                    )
                    .order_by('role__rank')
                    .exclude(sodar_uuid=role_as.sodar_uuid)
                    .first()
                )
                batch_role = get_flow_role(
                    c, user_name, c_as.role.rank if c_as else None
                )
                local_access = c_as and c_as.role.rank < RANK_VIEWER
                if action == PROJECT_ACTION_CREATE and not local_access:
                    flow_data['roles_delete'].append(batch_role)
                elif action == PROJECT_ACTION_UPDATE:
                    if old_role.rank < RANK_VIEWER or local_access:
                        flow_data['roles_add'].append(batch_role)
                    elif old_role.rank >= RANK_VIEWER and not local_access:
                        flow_data['roles_delete'].append(batch_role)

        if flow_data['roles_add'] or flow_data['roles_delete']:
            self.get_api().submit(
                project=None,
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )

        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_update_revert',
                description='revert adding iRODS access for '
                'user {{{}}}'.format('user'),
                status_type=timeline.TL_STATUS_OK,
            )
            tl_event.add_object(user, 'user', user_name)

    def perform_role_delete(self, role_as, request=None):
        """
        Perform additional actions to finalize role assignment deletion.

        :param role_as: RoleAssignment object
        :param request: Request object or None
        """
        timeline = plugin_api.get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        user_name = user.username
        flow_data = {'roles_add': [], 'roles_delete': []}

        if project.is_project():
            inh_as = (
                RoleAssignment.objects.filter(
                    user=user, project__in=project.get_parents()
                )
                .order_by('role__rank')
                .first()
            )
            if not inh_as or inh_as.role.rank >= RANK_VIEWER:
                flow_data['roles_delete'].append(
                    get_flow_role(
                        project, user_name, inh_as.role.rank if inh_as else None
                    )
                )
            elif inh_as:  # Update role to match inherited role
                flow_data['roles_add'].append(
                    get_flow_role(project, user_name, inh_as.role.rank)
                )
        else:  # Category
            children = self._get_child_projects(project)
            for c in children:
                # NOTE: role_as still exists so it has to be excluded
                c_as = (
                    RoleAssignment.objects.filter(
                        user=user, project__in=[c] + list(c.get_parents())
                    )
                    .order_by('role__rank')
                    .exclude(sodar_uuid=role_as.sodar_uuid)
                    .first()
                )
                if not c_as or c_as.role.rank >= RANK_VIEWER:
                    flow_data['roles_delete'].append(
                        get_flow_role(
                            c, user_name, c_as.role.rank if c_as else None
                        )
                    )
                # Update child role if owner/delegate role is deleted
                elif (
                    c_as
                    and c_as.role.rank >= RANK_DELEGATE >= role_as.role.rank
                ):
                    flow_data['roles_add'].append(
                        get_flow_role(c, user_name, c_as.role.rank)
                    )

        if flow_data['roles_add'] or flow_data['roles_delete']:
            self.get_api().submit(
                project=None,
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )

        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_delete',
                description='remove project iRODS access from user {user}',
                status_type=timeline.TL_STATUS_OK,
            )
            tl_event.add_object(obj=user, label='user', name=user_name)

    def revert_role_delete(self, role_as, request=None):
        """
        Revert role assignment deletion deletion if errors have occurred in
        other apps.

        :param role_as: RoleAssignment object
        :param request: Request object or None
        """
        timeline = plugin_api.get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        user_name = user.username
        flow_data = {'roles_add': [], 'roles_delete': []}

        if project.is_project():
            user_as = project.get_role(user)
            if user_as and user_as.role.rank < RANK_VIEWER:
                flow_data['roles_add'].append(
                    get_flow_role(project, user_name, user_as.role.rank)
                )
        else:  # Category
            children = self._get_child_projects(project)
            for c in children:
                # NOTE: role_as still exists so it has to be excluded
                if role_as.role.rank < RANK_VIEWER:
                    flow_data['roles_add'].append(
                        get_flow_role(c, user_name, role_as.role.rank)
                    )
                else:
                    c_as = (
                        RoleAssignment.objects.filter(
                            user=user, project__in=[c] + list(c.get_parents())
                        )
                        .order_by('role__rank')
                        .exclude(sodar_uuid=role_as.sodar_uuid)
                        .first()
                    )
                    if c_as and c_as.role.rank < RANK_VIEWER:
                        k = 'roles_add'
                    else:
                        k = 'roles_delete'
                    flow_data[k].append(
                        get_flow_role(
                            c, user_name, c_as.role.rank if c_as else None
                        )
                    )

        if flow_data['roles_add'] or flow_data['roles_delete']:
            self.get_api().submit(
                project=None,
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )

        if timeline:
            tl_event = timeline.add_event(
                project=role_as.project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_delete_revert',
                description='revert removing iRODS access from '
                'user {{{}}}'.format('user'),
                status_type=timeline.TL_STATUS_OK,
            )
            tl_event.add_object(role_as.user, 'user', user_name)

    def perform_owner_transfer(
        self, project, new_owner, old_owner, old_owner_role=None, request=None
    ):
        """
        Perform additional actions to finalize project ownership transfer.

        :param project: Project object
        :param new_owner: SODARUser object for new owner
        :param old_owner: SODARUser object for previous owner
        :param old_owner_role: Role object for new role of old owner or None
        :param request: Request object or None
        """
        timeline = plugin_api.get_backend_api('timeline_backend')
        n_user_name = new_owner.username
        o_user_name = old_owner.username
        o_rank = old_owner_role.rank if old_owner_role else None
        flow_data = {'roles_add': [], 'roles_delete': []}

        if project.is_project():
            flow_data['roles_add'].append(
                get_flow_role(
                    project, n_user_name, ROLE_RANKING[PROJECT_ROLE_OWNER]
                )
            )
            if not old_owner_role or old_owner_role.rank >= RANK_VIEWER:
                flow_data['roles_delete'].append(
                    get_flow_role(project, o_user_name, RANK_OWNER)
                )
            else:
                # Update owner role with roles_add
                flow_data['roles_add'].append(
                    get_flow_role(project, o_user_name, o_rank)
                )
        else:  # Category
            children = self._get_child_projects(project)
            for c in children:
                flow_data['roles_add'].append(
                    get_flow_role(
                        c, n_user_name, ROLE_RANKING[PROJECT_ROLE_OWNER]
                    )
                )
                if not old_owner_role or old_owner_role.rank >= RANK_VIEWER:
                    flow_data['roles_delete'].append(
                        get_flow_role(c, o_user_name, RANK_OWNER)
                    )
                else:
                    flow_data['roles_add'].append(
                        get_flow_role(c, o_user_name, o_rank)
                    )
        if flow_data['roles_add'] or flow_data['roles_delete']:
            self.get_api().submit(
                project=None,
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )

        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                plugin_name='taskflow',
                user=request.user if request else None,
                event_name='role_owner_transfer',
                description='update iRODS access for ownership transfer '
                'from {old_owner} to {new_owner}',
                status_type=timeline.TL_STATUS_OK,
            )
            tl_event.add_object(
                obj=old_owner, label='old_owner', name=o_user_name
            )
            tl_event.add_object(
                obj=new_owner, label='new_owner', name=n_user_name
            )

    # NOTE: revert_owner_transfer() not needed at the moment
    # (No other plugin gets called after taskflowbackend)

    def perform_project_sync(self, project):
        """
        Synchronize existing projects to ensure related data exists when the
        syncmodifyapi management comment is called. Should mostly be used in
        development when the development databases have been e.g. modified or
        recreated.

        :param project: Current project object (Project)
        """
        # Skip for categories, inherited roles get synced for projects
        if project.is_category():
            logger.debug(f'Skipping: {IRODS_CAT_SKIP_MSG}')
            return
        irods_backend = plugin_api.get_backend_api('omics_irods')
        if not irods_backend:
            logger.error('iRODS backend not enabled')
            return
        # Perform project create
        logger.info('Syncing project iRODS collection, metadata and access..')
        self.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project
            ),
            **{'sync_modify_api': True},
        )
        # Remove inactive roles
        project_group = irods_backend.get_group_name(project)
        flow_data = {'roles_add': [], 'roles_delete': []}
        with irods_backend.get_session() as irods:
            for irods_user in irods.user_groups.getmembers(project_group):
                user = User.objects.filter(username=irods_user.name).first()
                role_as = project.get_role(user)
                if not role_as or role_as.role.rank >= RANK_VIEWER:
                    flow_data['roles_delete'].append(
                        get_flow_role(
                            project,
                            irods_user.name,
                            role_as.role.rank if role_as else None,
                        )
                    )
        if flow_data['roles_delete']:
            self.get_api().submit(
                project=None,
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )

    def perform_project_delete(self, project):
        """
        Perform additional actions to finalize project deletion.

        NOTE: This operation can not be undone so there is no revert method.

        :param project: Project object (Project)
        """
        # NOTE: Checks for project/category permissions done in SODAR Core views
        # Skip for categories, nothing to do
        if project.is_category():
            logger.debug(f'Skipping: {IRODS_CAT_SKIP_MSG}')
            return
        irods_backend = plugin_api.get_backend_api('omics_irods')
        if not irods_backend:
            logger.error('iRODS backend not enabled')
            return

        timeline = plugin_api.get_backend_api('timeline_backend')
        tl_event = None
        project_path = irods_backend.get_path(project)
        user_group = irods_backend.get_group_name(project)
        owner_group = irods_backend.get_group_name(project, owner=True)
        errors = []
        # Create separate timeline event
        if timeline:
            tl_event = timeline.add_event(
                project=None,  # No project as it has been deleted
                app_name='taskflowbackend',
                plugin_name='taskflow',
                user=None,
                event_name='project_delete',
                description=f'Delete iRODS collection and user group from '
                f'project {project.get_log_title()}',
                extra_data={
                    'project_path': project_path,
                    'user_group': user_group,
                },
                classified=True,
            )

        with irods_backend.get_session() as irods:
            # Delete project collection and subcollections
            try:
                irods.collections.remove(project_path, recurse=True)
                logger.debug(f'Project collection deleted: {project_path}')
            except Exception as ex:
                ex_msg = (
                    f'Error deleting project collection '
                    f'({project_path}): {ex}'
                )
                logger.error(ex_msg)
                errors.append(ex_msg)
            try:  # Delete project user group
                # NOTE: Use users instead of user_groups here
                irods.users.remove(user_group)
                logger.debug(f'User group deleted: {user_group}')
            except Exception as ex:
                ex_msg = f'Error deleting user group ({user_group}): {ex}'
                logger.error(ex_msg)
                errors.append(ex_msg)
            try:  # Delete project owner group
                irods.users.remove(owner_group)
                logger.debug(f'Owner group deleted: {owner_group}')
            except Exception as ex:
                ex_msg = f'Error deleting owner group ({owner_group}): {ex}'
                logger.error(ex_msg)
                errors.append(ex_msg)

        if tl_event and errors:
            tl_event.set_status(timeline.TL_STATUS_FAILED, '; '.join(errors))
        elif tl_event:
            tl_event.set_status(timeline.TL_STATUS_OK)
