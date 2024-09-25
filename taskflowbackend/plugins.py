"""Plugins for the taskflowbackend app"""

import logging

from irods.exception import UserGroupDoesNotExist

from django.contrib.auth import get_user_model

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import RoleAssignment, SODAR_CONSTANTS, ROLE_RANKING
from projectroles.plugins import (
    BackendPluginPoint,
    ProjectModifyPluginMixin,
    get_backend_api,
)

from taskflowbackend.api import TaskflowAPI
from taskflowbackend.irods_utils import get_batch_role


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
User = get_user_model()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_FINDER = SODAR_CONSTANTS['PROJECT_ROLE_FINDER']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']

# Local constants
APP_NAME = 'taskflowbackend'
IRODS_CAT_SKIP_MSG = 'Categories are not synchronized into iRODS'
RANK_FINDER = ROLE_RANKING[PROJECT_ROLE_FINDER]
TASKFLOW_INFO_SETTINGS = [
    'TASKFLOW_IRODS_CONN_TIMEOUT',
    'TASKFLOW_LOCK_RETRY_COUNT',
    'TASKFLOW_LOCK_RETRY_INTERVAL',
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
        if project.type != PROJECT_TYPE_CATEGORY:
            return []
        return [
            p
            for p in project.get_children(flat=True)
            if p.type == PROJECT_TYPE_PROJECT
        ]

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
        if project.type == PROJECT_TYPE_CATEGORY and (
            action == PROJECT_ACTION_CREATE
            or old_data['parent'] == project.parent
        ):
            logger.debug('Skipping: Nothing to modify')
            return

        taskflow = self.get_api()
        timeline = get_backend_api('timeline_backend')
        owner = project.get_owner().user
        all_roles = [
            a for a in project.get_roles() if a.role.rank < RANK_FINDER
        ]
        all_members = [a.user.username for a in all_roles]
        children = self._get_child_projects(project)

        if project.type == PROJECT_TYPE_PROJECT:
            flow_data = {
                'owner': owner.username,
                'settings': project_settings,
                'users_add': [],
            }
            if (
                action == PROJECT_ACTION_UPDATE
                and old_data['parent'] != project.parent
            ):
                inh_members = [
                    a.user.username
                    for a in all_roles
                    if a.project != project and a.user != owner
                ]
                flow_data['users_add'] = inh_members
                old_inh_members = [
                    a.user.username for a in old_data['parent'].get_roles()
                ]
                flow_data['users_delete'] = [
                    u for u in old_inh_members if u not in all_members
                ]
            else:  # Create
                flow_data['users_add'] = all_members
            taskflow.submit(
                project=project,
                flow_name='project_{}'.format(action.lower()),
                flow_data=flow_data,
            )
        # If updating parent in category, add role_update_irods_batch call
        elif (
            action == PROJECT_ACTION_UPDATE
            and children
            and old_data['parent'] != project.parent
        ):
            flow_data = {'roles_add': [], 'roles_delete': []}
            old_inh_members = (
                [a.user.username for a in old_data['parent'].get_roles()]
                if old_data['parent']  # Old parent may be None
                else []
            )
            for c in children:
                for u in all_members:
                    flow_data['roles_add'].append(get_batch_role(c, u))
                c_members = [a.user.username for a in c.get_roles()]
                for u in old_inh_members:
                    if u not in c_members:
                        flow_data['roles_delete'].append(get_batch_role(c, u))
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
                event_name='project_{}'.format(tl_action),
                description='{} {} in iRODS'.format(
                    tl_action, project.type.lower()
                ),
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

        irods_backend = get_backend_api('omics_irods')
        timeline = get_backend_api('timeline_backend')
        project_path = irods_backend.get_path(project)

        with irods_backend.get_session() as irods:
            if irods.collections.exists(project_path):
                logger.debug(
                    'Removing project collection: {}'.format(project_path)
                )
                irods.collections.remove(project_path)
            group_name = irods_backend.get_user_group_name(project)
            try:
                irods.user_groups.get(group_name)
                logger.debug('Removing user group: {}'.format(group_name))
                irods.users.remove(group_name)
            except UserGroupDoesNotExist:
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
        # Skip for update (no action needed unless updating to/from finder)
        if (
            action == PROJECT_ACTION_UPDATE
            and role_as.role.rank < RANK_FINDER
            and old_role.rank < RANK_FINDER
        ):
            logger.debug('Skipping: User already has iRODS access')
            return

        taskflow = self.get_api()
        timeline = get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        children = self._get_child_projects(project)

        if project.type == PROJECT_TYPE_PROJECT:
            flow_data = {'user_name': user.username}
            taskflow.submit(
                project=project, flow_name='role_update', flow_data=flow_data
            )
        elif children:  # Category children
            flow_data = {'roles_add': [], 'roles_delete': []}
            for c in children:
                k = (
                    'roles_delete'
                    if role_as.role.rank >= RANK_FINDER
                    and not c.get_role(user)  # Finder not returned for project
                    else 'roles_add'
                )
                flow_data[k].append(get_batch_role(c, user.username))
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
        timeline = get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        user_name = user.username
        flow_data = {'roles_add': [], 'roles_delete': []}

        # Revert creation or update from finder role for project
        if project.type == PROJECT_TYPE_PROJECT and (
            action == PROJECT_ACTION_CREATE or old_role.rank >= RANK_FINDER
        ):
            flow_data['roles_delete'].append(get_batch_role(project, user_name))
        elif project.type == PROJECT_TYPE_CATEGORY:
            children = self._get_child_projects(project)
            for c in children:
                batch_role = get_batch_role(c, user_name)
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
                local_access = c_as and c_as.role.rank < RANK_FINDER
                if action == PROJECT_ACTION_CREATE and not local_access:
                    flow_data['roles_delete'].append(batch_role)
                elif action == PROJECT_ACTION_UPDATE:
                    if old_role.rank < RANK_FINDER or local_access:
                        flow_data['roles_add'].append(batch_role)
                    elif old_role.rank >= RANK_FINDER and not local_access:
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
        timeline = get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        user_name = user.username
        flow_data = {'roles_add': [], 'roles_delete': []}

        if project.type == PROJECT_TYPE_PROJECT:
            inh_as = (
                RoleAssignment.objects.filter(
                    user=user, project__in=project.get_parents()
                )
                .order_by('role__rank')
                .first()
            )
            if not inh_as or inh_as.role.rank >= RANK_FINDER:
                flow_data['roles_delete'].append(
                    get_batch_role(project, user_name)
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
                if not c_as or c_as.role.rank >= RANK_FINDER:
                    flow_data['roles_delete'].append(
                        get_batch_role(c, user_name)
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
        timeline = get_backend_api('timeline_backend')
        project = role_as.project
        user = role_as.user
        user_name = user.username
        flow_data = {'roles_add': [], 'roles_delete': []}

        if project.type == PROJECT_TYPE_PROJECT:
            user_as = project.get_role(user)
            if user_as and user_as.role.rank < RANK_FINDER:
                flow_data['roles_add'].append(
                    get_batch_role(project, user_name)
                )
        else:  # Category
            children = self._get_child_projects(project)
            for c in children:
                batch_role = get_batch_role(c, user_name)
                # NOTE: role_as still exists so it has to be excluded
                if role_as.role.rank < RANK_FINDER:
                    flow_data['roles_add'].append(batch_role)
                else:
                    c_as = (
                        RoleAssignment.objects.filter(
                            user=user, project__in=[c] + list(c.get_parents())
                        )
                        .order_by('role__rank')
                        .exclude(sodar_uuid=role_as.sodar_uuid)
                        .first()
                    )
                    if c_as and c_as.role.rank < RANK_FINDER:
                        k = 'roles_add'
                    else:
                        k = 'roles_delete'
                    flow_data[k].append(batch_role)

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
        timeline = get_backend_api('timeline_backend')
        n_user_name = new_owner.username
        o_user_name = old_owner.username
        flow_data = {'roles_add': [], 'roles_delete': []}

        if project.type == PROJECT_TYPE_PROJECT:
            flow_data['roles_add'].append(get_batch_role(project, n_user_name))
            if old_owner_role.rank >= RANK_FINDER:
                flow_data['roles_delete'].append(
                    get_batch_role(project, o_user_name)
                )
        else:  # Category
            children = self._get_child_projects(project)
            for c in children:
                flow_data['roles_add'].append(get_batch_role(c, n_user_name))
                if old_owner_role.rank >= RANK_FINDER:
                    flow_data['roles_delete'].append(
                        get_batch_role(c, o_user_name)
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
    # (No other plugin gets called with after taskflowbackend)

    def perform_project_sync(self, project):
        """
        Synchronize existing projects to ensure related data exists when the
        syncmodifyapi management comment is called. Should mostly be used in
        development when the development databases have been e.g. modified or
        recreated.

        :param project: Current project object (Project)
        """
        # Skip for categories, inherited roles get synced for projects
        if project.type != PROJECT_TYPE_PROJECT:
            logger.debug('Skipping: {}'.format(IRODS_CAT_SKIP_MSG))
            return
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            logger.error('iRODS backend not enabled')
            return
        # Perform project create
        logger.info('Syncing project iRODS collection, metadata and access..')
        self.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(project),
            **{'sync_modify_api': True},
        )
        # Remove inactive roles
        group_name = irods_backend.get_user_group_name(project)
        flow_data = {'roles_add': [], 'roles_delete': []}
        with irods_backend.get_session() as irods:
            for irods_user in irods.user_groups.getmembers(group_name):
                user = User.objects.filter(username=irods_user.name).first()
                role_as = project.get_role(user)
                if not role_as or role_as.role.rank >= RANK_FINDER:
                    flow_data['roles_delete'].append(
                        get_batch_role(project, irods_user.name)
                    )
        if flow_data['roles_delete']:
            self.get_api().submit(
                project=None,
                flow_name='role_update_irods_batch',
                flow_data=flow_data,
            )
