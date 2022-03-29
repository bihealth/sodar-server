"""Synctaskflow management command for the taskflowbackend app"""

import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.models import Project, Role, SODAR_CONSTANTS
from projectroles.plugins import get_active_plugins, get_backend_api


logger = ManagementCommandLogger(__name__)
User = get_user_model()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']

TARGETS = settings.TASKFLOW_TARGETS
TARGETS.remove('sodar')  # Exclude SODAR from sync as data is already here


class Command(BaseCommand):
    help = 'Submits missing project data to external storage'

    def add_arguments(self, parser):
        pass

    def _submit_sync(self, app_name, sync_data, raise_exception=False):
        """Submit flows found in an app's sync_data structure"""

        for item in sync_data:
            project = Project.objects.get(sodar_uuid=item['project_uuid'])
            logger.debug(
                'Syncing flow "{}" by {} for "{}" ({})'.format(
                    item['flow_name'],
                    app_name,
                    project.title,
                    project.sodar_uuid,
                )
            )
            try:
                self.taskflow.submit(
                    project_uuid=item['project_uuid'],
                    flow_name=item['flow_name'],
                    flow_data=item['flow_data'],
                    targets=TARGETS,
                )
            except self.taskflow.FlowSubmitException as ex:
                logger.error('Exception raised by flow: {}'.format(ex))
                # If we don't want to continue on failure
                if raise_exception:
                    raise ex

    def _sync_projects(self):
        """Synchronize projects and roles (must be called first!)"""
        logger.info('Synchronizing project data with taskflow...')
        logger.info('Target(s) = ' + ', '.join([t for t in TARGETS]))

        # Only sync PROJECT type projects as we (currently) don't have any
        # use for CATEGORY projects in taskflow
        projects = Project.objects.filter(type=PROJECT_TYPE_PROJECT).order_by(
            'pk'
        )
        project_sync_data = []
        role_sync_data = []

        for project in projects:
            owner_as = project.get_owner()
            if not owner_as:  # This should not happen unless the db is corrupt
                logger.error(
                    'No owner assignment for project "{}" ({})'.format(
                        project.title, project.sodar_uuid
                    )
                )
                continue

            # Create project
            project_sync_data.append(
                {
                    'project_uuid': str(project.sodar_uuid),
                    'project_title': project.title,
                    'flow_name': 'project_create',
                    'flow_data': {
                        'project_title': project.title,
                        'project_description': project.description,
                        'parent_uuid': str(project.parent.sodar_uuid)
                        if project.parent
                        else 0,
                        'owner_username': owner_as.user.username,
                        'owner_uuid': str(owner_as.user.sodar_uuid),
                        'owner_role_pk': owner_as.role.pk,
                    },
                }
            )

            # Set up roles
            role_sync_data.append(
                {
                    'project_uuid': str(project.sodar_uuid),
                    'project_title': project.title,
                    'flow_name': 'role_sync_delete_all',
                    'flow_data': {'owner_username': owner_as.user.username},
                }
            )
            for role_as in project.roles.exclude(
                role=Role.objects.get(
                    name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
                )
            ):
                role_sync_data.append(
                    {
                        'project_uuid': str(project.sodar_uuid),
                        'project_title': project.title,
                        'flow_name': 'role_update',
                        'flow_data': {
                            'username': role_as.user.username,
                            'user_uuid': str(role_as.user.sodar_uuid),
                            'role_pk': str(role_as.role.pk),
                        },
                    }
                )

        self._submit_sync(
            'projectroles', project_sync_data, raise_exception=True
        )
        self._submit_sync('projectroles', role_sync_data, raise_exception=False)

    def _sync_inherited_owners(self):
        """Synchronize inherited owner permissions in iRODS"""
        timeline = get_backend_api('timeline_backend')
        roles_add = []
        roles_delete = []

        if not timeline:
            logger.warning(
                'Timeline backend not enabled, unable to sync '
                'inherited owner roles in SODAR Taskflow'
            )
        else:
            logger.info('Retrieving added/removed inherited owners..')
            ProjectEvent, ProjectEventObjectRef = timeline.get_models()

            for category in Project.objects.filter(type=PROJECT_TYPE_CATEGORY):
                # Get roles to add
                roles_add = self.taskflow.get_inherited_roles(
                    category, category.get_owner().user, roles_add
                )

                # Get previous owners to remove
                tl_users = (
                    ProjectEventObjectRef.objects.filter(
                        label='prev_owner',
                        event__in=ProjectEvent.objects.filter(
                            project=category, event_name='role_owner_transfer'
                        ),
                    )
                    .exclude(object_uuid=category.get_owner().user.sodar_uuid)
                    .values_list('name', flat=True)
                    .distinct()
                )

                for u_name in tl_users:
                    user = User.objects.filter(username=u_name).first()
                    if not user:
                        continue
                    roles_delete = self.taskflow.get_inherited_roles(
                        category, user, roles_delete
                    )

        if roles_add or roles_delete:
            logger.info('Changes in inherited owners found, synchronizing..')
            try:
                self.taskflow.submit(
                    project_uuid=None,
                    flow_name='role_update_irods_batch',
                    flow_data={
                        'roles_add': roles_add,
                        'roles_delete': roles_delete,
                    },
                )
            except Exception as ex:
                logger.error(
                    'Error synchronizing inherited owners: {}'.format(ex)
                )
            logger.info('Inherited owner permissions synchronized.')

    def _sync_apps(self):
        """Run taskflow synchronization methods in project app plugins"""
        plugins = get_active_plugins(plugin_type='project_app')
        for plugin in plugins:
            sync_data = plugin.get_taskflow_sync_data()
            logger.info('Synchronizing app "{}"...'.format(plugin.name))
            if sync_data:
                self._submit_sync(plugin.name, sync_data, raise_exception=False)
            else:
                logger.info('Nothing to synchronize.')

    def handle(self, *args, **options):
        """Run management command"""
        if 'taskflow' not in settings.ENABLED_BACKEND_PLUGINS:
            logger.error('Taskflow not enabled in settings, cancelled!')
            raise CommandError

        self.taskflow = get_backend_api('taskflow')
        if not self.taskflow:
            logger.error('Taskflow backend plugin not available, cancelled!')
            raise CommandError

        # Projectroles sync
        # NOTE: For projectroles, this is done here as projects must be created
        #       or we can not continue with sync.. Also, removed projects are
        #       NOT deleted automatically (they shouldn't be deleted anyway).
        #       We first set up the projects and exit if syncing them fails.
        try:
            self._sync_projects()
        except Exception as ex:
            logger.error('Exception in project sync: {}'.format(ex))
            logger.error('Project sync failed! Unable to continue, exiting..')
            sys.exit(1)

        # Inherited Owner Sync
        self._sync_inherited_owners()
        # App sync
        self._sync_apps()
        logger.info('Project data synchronized.')
