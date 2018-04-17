from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from projectroles.models import Project, Role, OMICS_CONSTANTS
from projectroles.plugins import get_active_plugins, get_backend_api


# Omics constants
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


TARGETS = ['irods']     # Submit to iRODS, data already in Omics Data Access


class Command(BaseCommand):
    help = 'Submits missing project data to external storage'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        if 'taskflow' not in settings.ENABLED_BACKEND_PLUGINS:
            print_msg('Taskflow not enabled in settings, cancelled!')
            raise CommandError

        taskflow = get_backend_api('taskflow')

        if not taskflow:
            print_msg('Taskflow backend plugin not available, cancelled!')
            raise CommandError

        def submit_sync(app_name, sync_data, raise_exception=False):
            """Submit flows found in an app's sync_data structure"""
            for item in sync_data:
                print_msg('Syncing flow "{}" by {} for project {} ({})'.format(
                    item['flow_name'],
                    app_name,
                    item['project_uuid'],
                    item['project_title']))

                try:
                    taskflow.submit(
                        project_uuid=item['project_uuid'],
                        flow_name=item['flow_name'],
                        flow_data=item['flow_data'],
                        targets=TARGETS)

                except taskflow.FlowSubmitException as ex:
                    print_msg('Exception raised by flow!')
                    print(str(ex))

                    # If we don't want to continue on failure
                    if raise_exception:
                        raise ex

        print_msg('Synchronizing project data with taskflow...')
        print_msg('Target(s) = ' + ', '.join([t for t in TARGETS]))

        # Only sync PROJECT type projects as we (currently) don't have any
        # use for CATEGORY projects in iRODS
        projects = Project.objects.filter(
            type=PROJECT_TYPE_PROJECT).order_by('pk')

        ####################
        # Projectroles sync
        ####################

        # NOTE: For projectroles, this is done here as projects must be created
        #       or we can not continue with sync.. Also, removed projects are
        #       NOT deleted automatically (they shouldn't be deleted anyway).
        #       We first set up the projects and exit if syncing them fails.

        project_sync_data = []
        role_sync_data = []

        for project in projects:
            owner_as = project.get_owner()

            # Create project
            project_sync_data.append({
                'project_uuid': str(project.omics_uuid),
                'project_title': project.title,
                'flow_name': 'project_create',
                'flow_data': {
                    'project_title': project.title,
                    'project_description': project.description,
                    'parent_uuid': str(project.parent.omics_uuid) if
                    project.parent else 0,
                    'owner_username': owner_as.user.username,
                    'owner_uuid': str(owner_as.user.omics_uuid),
                    'owner_role_pk': owner_as.role.pk}})

            # Set up roles
            role_sync_data.append({
                'project_uuid': str(project.omics_uuid),
                'project_title': project.title,
                'flow_name': 'role_sync_delete_all',
                'flow_data': {
                    'owner_username': owner_as.user.username}})

            for role_as in project.roles.exclude(
                    role=Role.objects.get(
                        name=OMICS_CONSTANTS['PROJECT_ROLE_OWNER'])):
                role_sync_data.append({
                    'project_uuid': str(project.omics_uuid),
                    'project_title': project.title,
                    'flow_name': 'role_update',
                    'flow_data': {
                        'username': role_as.user.username,
                        'user_uuid': str(role_as.user.omics_uuid),
                        'role_pk': str(role_as.role.pk)}})

        try:
            submit_sync('projectroles', project_sync_data, raise_exception=True)

        # In case of a failure here we can't continue with the rest of the sync
        except taskflow.FlowSubmitException:
            print_msg('Project creation failed! Unable to continue, exiting..')
            return

        submit_sync('projectroles', role_sync_data, raise_exception=False)

        ###########
        # App sync
        ###########

        plugins = get_active_plugins(plugin_type='project_app')

        for plugin in plugins:
            sync_data = plugin.get_taskflow_sync_data()
            print_msg('Synchronizing app "{}"...'.format(plugin.name))

            if sync_data:
                submit_sync(plugin.name, sync_data, raise_exception=False)

            else:
                print_msg('Nothing to synchronize.')

        print_msg('Project data synchronized.')


def print_msg(msg):
    print('Synctaskflow: {}'.format(msg))
