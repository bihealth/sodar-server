"""UI views for the landingzones app"""

import logging

from irods.exception import GroupDoesNotExist
from typing import Optional

from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, CreateView, UpdateView

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, SODAR_CONSTANTS, ROLE_RANKING
from projectroles.plugins import PluginAPI
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
    CurrentUserFormMixin,
    PROJECT_BLOCK_MSG,
)

# Samplesheets dependency
from samplesheets.views import (
    InvestigationContextMixin,
    RESULTS_COLL,
    MISC_FILES_COLL,
    TRACK_HUBS_COLL,
)

from landingzones.constants import (
    STATUS_ALLOW_UPDATE,
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
    STATUS_FINISHED,
    STATUS_INFO_DELETE_NO_COLL,
    ZONE_STATUS_DELETED,
)
from landingzones.forms import LandingZoneForm
from landingzones.models import LandingZone
from landingzones.utils import cleanup_file_prohibit


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
plugin_api = PluginAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']

# Local constants
APP_NAME = 'landingzones'
APP_NAME_PR = 'projectroles'
ZONE_MOVE_INVALID_STATUS = 'Zone not in active state, unable to trigger action.'
ZONE_MOVE_NO_FILES = 'No files in landing zone, nothing to do.'
ZONE_UPDATE_ACTIONS = ['update', 'move', 'delete']
ZONE_UPDATE_FIELDS = ['description', 'user_message']
ZONE_CREATE_LIMIT_MSG = (
    'Landing zone creation limit for project ({limit}) reached, please move or '
    'delete existing zones before creating new ones'
)
ZONE_VALIDATE_LIMIT_MSG = (
    'Landing zone validation limit per project reached, please wait for '
    'ongoing validation jobs to finish before initiating new ones'
)


# Mixins -----------------------------------------------------------------------


class ZoneContextMixin:
    """Context mixin for LandingZones UI views"""

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['prohibit_files'] = None
        file_name_prohibit = app_settings.get(
            APP_NAME, 'file_name_prohibit', project=self.get_project()
        )
        if file_name_prohibit:
            context['prohibit_files'] = ', '.join(
                cleanup_file_prohibit(file_name_prohibit)
            )
        return context


class ZoneConfigContextMixin:
    """Context mixin for LandingZones configuration views"""

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['zone'] = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()
        return context


class ProjectZoneInfoMixin:
    """
    Mixin for providing current project zone status and limit info for UI view
    context and Ajax views.
    """

    @classmethod
    def get_project_zone_info(cls, project: Project) -> dict:
        """
        Return project zone info for view context and Ajax views.

        :param project: Project object
        :return: Dict
        """
        taskflow = plugin_api.get_backend_api('taskflow')
        ret = {}
        # Project lock status
        project_lock = False
        if taskflow:
            try:
                project_lock = taskflow.is_locked(project)
            except Exception as ex:
                logger.error(f'Exception querying lock status: {ex}')
        ret['project_lock'] = project_lock
        # Active zone count and zone creation limit
        active_count = (
            LandingZone.objects.filter(project=project)
            .exclude(status__in=STATUS_FINISHED)
            .count()
        )
        create_limit = settings.LANDINGZONES_ZONE_CREATE_LIMIT
        ret['zone_active_count'] = active_count
        ret['zone_create_limit'] = create_limit
        ret['zone_create_limit_reached'] = (
            create_limit is not None and active_count >= create_limit
        )
        # Validating zone count and validation limit
        valid_count = LandingZone.objects.filter(
            project=project,
            status__in=[ZONE_STATUS_PREPARING, ZONE_STATUS_VALIDATING],
        ).count()
        valid_limit = settings.LANDINGZONES_ZONE_VALIDATE_LIMIT or 1
        ret['zone_validate_count'] = valid_count
        ret['zone_validate_limit'] = valid_limit
        ret['zone_validate_limit_reached'] = valid_count >= valid_limit
        return ret


class ZoneModifyPermissionMixin:
    """Required permission override for landing zone updating views"""

    #: Action for zone modification
    zone_action = None

    def get_permission_required(self):
        """Override to return the correct landing zone permission"""
        if not hasattr(self, 'zone_action'):
            raise ImproperlyConfigured('Attribute "zone_action" not set')
        if self.zone_action.lower() not in ZONE_UPDATE_ACTIONS:
            raise ImproperlyConfigured(
                'Invalid value "{}" for zone_action. Valid values: {}'.format(
                    self.zone_action, ', '.join(ZONE_UPDATE_ACTIONS)
                )
            )
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()
        # NOTE: UI views with PermissionRequiredMixin expect an iterable
        if zone and zone.user == self.request.user:
            return [f'landingzones.{self.zone_action.lower()}_zone_own']
        return [f'landingzones.{self.zone_action.lower()}_zone_all']


class ZoneConfigPluginMixin:
    """Landing zone configuration plugin operations"""

    @classmethod
    def get_flow_data(
        cls, zone: LandingZone, flow_name: str, data: dict
    ) -> dict:
        """
        Update flow data parameters according to config.

        :param zone: LandingZone object
        :param flow_name: Name of flow (string)
        :param data: Flow data parameters (dict)
        :return: dict
        """
        if zone.configuration:
            from landingzones.plugins import get_zone_config_plugin

            config_plugin = get_zone_config_plugin(zone)
            if config_plugin:
                data = {
                    **data,
                    **config_plugin.get_extra_flow_data(zone, flow_name),
                }
        return data


class ZoneModifyMixin(ZoneConfigPluginMixin):
    """Mixin to be used in zone creation/update in UI and REST API views"""

    @classmethod
    def check_create_limit(cls, project: Project):
        """
        Raise Exception if zone create limit has been reached.

        :param project: Project object
        """
        limit = settings.LANDINGZONES_ZONE_CREATE_LIMIT
        if limit and limit > 0:
            zones = LandingZone.objects.filter(project=project).exclude(
                status__in=STATUS_FINISHED
            )
            if zones.count() >= limit:
                raise Exception(ZONE_CREATE_LIMIT_MSG.format(limit=limit))

    def submit_create(
        self,
        zone: LandingZone,
        create_colls: bool = False,
        restrict_colls: bool = False,
        request: HttpRequest = None,
        sync: bool = False,
    ):
        """
        Handle timeline updating and taskflow initialization after a LandingZone
        object has been created.

        :param zone: LandingZone object
        :param create_colls: Auto-create expected collections (boolean)
        :param restrict_colls: Restrict access to created collections (boolean)
        :param request: HttpRequest object or None
        :param sync: Whether method is called from syncmodifyapi (boolean)
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        taskflow = plugin_api.get_backend_api('taskflow')
        timeline = plugin_api.get_backend_api('timeline_backend')
        irods_backend = plugin_api.get_backend_api('omics_irods')
        project = zone.project
        tl_event = None
        config_str = (
            f' with configuration "{zone.configuration}"'
            if zone.configuration
            else ''
        )

        # Add event in Timeline
        if timeline:
            tl_action = 'sync' if sync else 'create'
            tl_extra = {
                'title': zone.title,
                'assay': str(zone.assay.sodar_uuid),
                'description': zone.description,
                'create_colls': create_colls,
                'restrict_colls': restrict_colls,
                'user_message': zone.user_message,
                'configuration': zone.configuration,
                'config_data': zone.config_data,
            }
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=request.user if request else None,
                event_name=f'zone_{tl_action}',
                description='{} landing zone {{{}}}{} for {{{}}} in '
                '{{{}}}'.format(tl_action, 'zone', config_str, 'user', 'assay'),
                status_type=timeline.TL_STATUS_SUBMIT,
                extra_data=tl_extra,
            )
            tl_event.add_object(obj=zone, label='zone', name=zone.title)
            tl_event.add_object(
                obj=zone.user, label='user', name=zone.user.username
            )
            tl_event.add_object(
                obj=zone.assay, label='assay', name=zone.assay.get_name()
            )

        # Gather collections to generate automatically
        # NOTE: Currently requires sodar_cache to be enabled!
        colls = []
        if create_colls:
            logger.debug('Creating default landing zone collections..')
            assay_path = irods_backend.get_path(zone.assay)
            colls = [RESULTS_COLL, MISC_FILES_COLL, TRACK_HUBS_COLL]
            plugin = zone.assay.get_plugin()
            # First try the cache
            cache_backend = plugin_api.get_backend_api('sodar_cache')
            if plugin and cache_backend:
                cache_obj = cache_backend.get_cache_item(
                    'samplesheets.assayapps.'
                    + '_'.join(plugin.name.split('_')[2:]),
                    f'irods/rows/{zone.assay.sodar_uuid}',
                    project=zone.project,
                )
                if cache_obj and cache_obj.data:
                    colls += [
                        p.replace(assay_path + '/', '')
                        for p in cache_obj.data['paths'].keys()
                    ]
                    logger.debug('Retrieved collections from cache')
            # TODO: If no cache, build tables and get rows directly from plugin?
            # Add shortcut paths
            if plugin:
                shortcuts = plugin.get_shortcuts(zone.assay) or []
                for s in shortcuts:
                    path = s.get('path')
                    if path:
                        path = path.replace(assay_path + '/', '')
                    if path and path not in colls:
                        colls.append(path)
                        logger.debug(
                            'Added shorctut collection "{}"'.format(s.get('id'))
                        )
        logger.debug('Collections to be created: {}'.format(', '.join(colls)))

        # In case of legacy project and no syncmodifyapi, create owner group
        owner_group = irods_backend.get_group_name(project, owner=True)
        with irods_backend.get_session() as irods:
            try:
                irods.user_groups.get(owner_group)
            except GroupDoesNotExist:
                logger.info('Creating missing project owner group in iRODS..')
                od_roles = project.get_roles(
                    max_rank=ROLE_RANKING[PROJECT_ROLE_DELEGATE]
                )
                flow_data = {
                    'roles_add': [
                        taskflow.get_flow_role(project, r.user, r.role.rank)
                        for r in od_roles
                    ],
                    'roles_delete': [],
                }
                try:
                    taskflow.submit(
                        project=project,
                        flow_name='role_update_irods_batch',
                        flow_data=flow_data,
                        async_mode=False,
                    )
                except taskflow.FlowSubmitException as ex:
                    zone.delete()
                    raise ex

        flow_name = 'landing_zone_create'
        flow_data = self.get_flow_data(
            zone,
            flow_name,
            {
                'zone_uuid': str(zone.sodar_uuid),
                'colls': list(set(colls)),
                'restrict_colls': restrict_colls,
            },
        )
        try:
            taskflow.submit(
                project=project,
                flow_name=flow_name,
                flow_data=flow_data,
                async_mode=True,
                tl_event=tl_event,
            )
        except taskflow.FlowSubmitException as ex:
            zone.delete()
            raise ex

    def update_zone(
        self, zone: LandingZone, request: Optional[HttpRequest] = None
    ):
        """
        Handle timeline updating after a LandingZone object has been updated.

        :param zone: LandingZone object
        :param request: HttpRequest object or None
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        timeline = plugin_api.get_backend_api('timeline_backend')
        user = request.user if request else None

        # Add event in Timeline
        if timeline:
            description = 'update landing zone {zone} for {user} in {assay}'
            tl_extra = {
                'title': zone.title,
                'assay': str(zone.assay.sodar_uuid),
                'description': zone.description,
                'user_message': zone.user_message,
            }
            tl_event = timeline.add_event(
                project=zone.project,
                app_name=APP_NAME,
                user=user,
                event_name='zone_update',
                description=description,
                status_type=timeline.TL_STATUS_OK,
                extra_data=tl_extra,
            )
            tl_event.add_object(obj=zone, label='zone', name=zone.title)
            tl_event.add_object(obj=user, label='user', name=user.username)
            tl_event.add_object(
                obj=zone.assay, label='assay', name=zone.assay.get_name()
            )


class ZoneDeleteMixin(ZoneConfigPluginMixin):
    """Mixin to be used in zone creation"""

    def submit_delete(self, zone: LandingZone):
        """
        Handle timeline updating and initialize taskflow operation for
        LandingZone deletion, or delete zone directly if no iRODS collection is
        found.

        :param zone: LandingZone object
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        irods_backend = plugin_api.get_backend_api('omics_irods')
        taskflow = plugin_api.get_backend_api('taskflow')
        timeline = plugin_api.get_backend_api('timeline_backend')
        tl_event = None
        project = zone.project

        # Init Timeline event
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='zone_delete',
                description='delete landing zone {{{}}} in {{{}}} '
                'from {{{}}}'.format('zone', 'assay', 'user'),
            )
            tl_event.add_object(obj=zone, label='zone', name=zone.title)
            tl_event.add_object(
                obj=zone.assay,
                label='assay',
                name=zone.assay.get_display_name(),
            )
            tl_event.add_object(
                obj=zone.user, label='user', name=zone.user.username
            )

        # Check zone root collection status
        zone_path = irods_backend.get_path(zone)
        with irods_backend.get_session() as irods:
            zone_exists = irods.collections.exists(zone_path)

        if zone_exists:  # Submit with taskflow
            flow_name = 'landing_zone_delete'
            flow_data = self.get_flow_data(
                zone, flow_name, {'zone_uuid': str(zone.sodar_uuid)}
            )
            if tl_event:
                tl_event.set_status(timeline.TL_STATUS_SUBMIT)
            taskflow.submit(
                project=project,
                flow_name=flow_name,
                flow_data=flow_data,
                async_mode=True,
                tl_event=tl_event if tl_event else None,
            )
        else:  # Delete locally
            zone.set_status(ZONE_STATUS_DELETED, STATUS_INFO_DELETE_NO_COLL)
            if tl_event:
                tl_event.set_status(timeline.TL_STATUS_OK)
        self.object = None


class ZoneMoveMixin(ZoneConfigPluginMixin):
    """Mixin to be used in zone validation/moving"""

    def submit_validate_move(
        self,
        zone: LandingZone,
        validate_only: bool,
        request: Optional[HttpRequest] = None,
    ):
        """
        Handle timeline updating and initialize taskflow operation for
        LandingZone moving and/or validation.

        :param zone: LandingZone object
        :param validate_only: Only perform validation if true (bool)
        :param request: HttpRequest object or None
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        if not request and hasattr(self, 'request'):
            request = self.request
        user = request.user if request else zone.user
        timeline = plugin_api.get_backend_api('timeline_backend')
        taskflow = plugin_api.get_backend_api('taskflow')
        project = zone.project
        tl_event = None
        event_name = 'zone_validate' if validate_only else 'zone_move'

        # Add event in Timeline
        if timeline:
            desc = 'validate '
            if not validate_only:
                desc += 'and move '
            desc += 'files from landing zone {zone} from {user} in {assay}'
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=user,
                event_name=event_name,
                description=desc,
            )
            tl_event.add_object(obj=zone, label='zone', name=zone.title)
            tl_event.add_object(
                obj=zone.user, label='user', name=zone.user.username
            )
            tl_event.add_object(
                obj=zone.assay,
                label='assay',
                name=zone.assay.get_display_name(),
            )
            tl_event.set_status(timeline.TL_STATUS_SUBMIT)

        # TODO: Remove access_cleanup after implementing #2215
        flow_data = self.get_flow_data(
            zone=zone,
            flow_name='landing_zone_move',
            data={
                'zone_uuid': str(zone.sodar_uuid),
                'file_name_prohibit': app_settings.get(
                    APP_NAME, 'file_name_prohibit', project=project
                ),
                'access_cleanup': app_settings.get(
                    APP_NAME, 'zone_access_cleanup'
                ),
            },
        )
        if validate_only:
            flow_data['validate_only'] = True
        taskflow.submit(
            project=project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
            async_mode=True,
            tl_event=tl_event,
        )


# UI Views ---------------------------------------------------------------------


class ProjectZoneView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    ZoneContextMixin,
    ProjectZoneInfoMixin,
    TemplateView,
):
    """View for displaying landing zones for a project"""

    permission_required = 'landingzones.view_zone_own'
    template_name = 'landingzones/project_zones.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        project = context['project']
        # iRODS backend
        context['irods_backend_enabled'] = (
            True if plugin_api.get_backend_api('omics_irods') else False
        )
        # Landing zones
        zones = (
            LandingZone.objects.filter(project=project)
            .exclude(status__in=STATUS_FINISHED)
            .order_by('title')
        )
        # Only show own zones to users without view_zone_all perm
        if not self.request.user.has_perm(
            'landingzones.view_zone_all', project
        ):
            zones = zones.filter(user=self.request.user)
        context['zones'] = zones
        # Status query interval
        context['zone_status_interval'] = settings.LANDINGZONES_STATUS_INTERVAL
        # Disable status
        context['zone_access_disabled'] = (
            settings.LANDINGZONES_DISABLE_FOR_USERS
            and not self.request.user.is_superuser
        )
        context.update(self.get_project_zone_info(project))
        return context


class ZoneCreateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    CurrentUserFormMixin,
    ZoneModifyMixin,
    ZoneContextMixin,
    CreateView,
):
    """LandingZone creation view"""

    model = LandingZone
    form_class = LandingZoneForm
    permission_required = 'landingzones.create_zone'

    def get_form_kwargs(self):
        """Pass project to form"""
        kwargs = super().get_form_kwargs()
        kwargs.update({'project': self.kwargs['project']})
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        project = self.get_project()
        try:
            self.check_create_limit(project)
        except Exception as ex:
            messages.error(request, str(ex) + '.')
            return redirect(
                reverse(
                    'landingzones:list',
                    kwargs={'project': project.sodar_uuid},
                )
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        taskflow = plugin_api.get_backend_api('taskflow')
        context = self.get_context_data()
        project = context['project']
        investigation = context['investigation']
        error_msg = 'Unable to create zone: '
        redirect_url = reverse(
            'landingzones:list', kwargs={'project': project.sodar_uuid}
        )

        if not taskflow:
            messages.error(self.request, error_msg + 'Taskflow not enabled.')
            return redirect(redirect_url)
        elif not investigation:
            messages.error(
                self.request, error_msg + 'Sample sheets not available.'
            )
            return redirect(redirect_url)
        elif not investigation.irods_status:
            messages.error(
                self.request,
                error_msg + 'Sample sheet collections not created.',
            )
            return redirect(redirect_url)

        # Create landing zone object in Django db
        # NOTE: We have to do this beforehand to work properly as async
        zone = form.save()

        try:
            # Create timeline event and initialize taskflow
            self.submit_create(
                zone=zone,
                create_colls=form.cleaned_data.get('create_colls'),
                restrict_colls=form.cleaned_data.get('restrict_colls'),
                request=self.request,
            )
            config_str = (
                f' with configuration "{zone.configuration}"'
                if zone.configuration
                else ''
            )
            msg = (
                f'Landing zone "{zone.title}" creation initiated{config_str}: '
                f'see the zone list for the creation status.'
            )
            if (
                form.cleaned_data.get('create_colls')
                and 'sodar_cache' in settings.ENABLED_BACKEND_PLUGINS
            ):
                msg += ' Collections will be created.'
            messages.info(self.request, msg)
        except taskflow.FlowSubmitException as ex:
            messages.error(self.request, str(ex))
        return redirect(
            reverse('landingzones:list', kwargs={'project': project.sodar_uuid})
        )


class ZoneUpdateView(
    LoginRequiredMixin,
    InvestigationContextMixin,
    ZoneModifyMixin,
    UpdateView,
):
    """LandingZone update view"""

    model = LandingZone
    form_class = LandingZoneForm
    slug_url_kwarg = 'landingzone'
    slug_field = 'sodar_uuid'

    def get_permission_required(self, user):
        """Get custom permission for user"""
        if self.request.user == user:
            return 'landingzones.update_zone_own'
        else:
            return 'landingzones.update_zone_all'

    def get(self, request, *args, **kwargs):
        """Override get() to ensure the zone status"""
        zone = LandingZone.objects.get(sodar_uuid=self.kwargs['landingzone'])
        project = zone.project
        redirect_url = reverse(
            'landingzones:list', kwargs={'project': project.sodar_uuid}
        )
        # Check for project access block
        # TODO: Use is_project_accessible() once fixed
        #       (see bihealth/sodar-core#1744)
        if not self.request.user.is_superuser and app_settings.get(
            APP_NAME_PR, 'project_access_block', project=project
        ):
            msg = PROJECT_BLOCK_MSG.format(project_type='project')
            messages.error(request, msg)
            return redirect(redirect_url)
        # Check permissions
        if not self.request.user.has_perm(
            self.get_permission_required(zone.user), project
        ):
            msg = 'You do not have permission to update this landing zone.'
            messages.error(request, msg)
            return redirect(redirect_url)

        # Check status
        if zone.status not in STATUS_ALLOW_UPDATE:
            messages.error(
                request,
                f'Unable to update a landing zone with the status of '
                f'"{zone.status}".',
            )
            return redirect(redirect_url)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        self.zone = LandingZone.objects.get(
            sodar_uuid=self.kwargs['landingzone']
        )
        redirect_url = reverse(
            'landingzones:list',
            kwargs={'project': self.zone.project.sodar_uuid},
        )

        # Check permissions
        if not self.request.user.has_perm(
            self.get_permission_required(self.zone.user), self.zone.project
        ):
            messages.error(
                self.request,
                'You do not have permission to update this landing zone.',
            )
            return redirect_url

        # Double check that only allowed fields are updated
        # Remove create_colls and restrict_colls from changed_data
        # as they are passed to the form automatically
        if (
            set(form.changed_data)
            - {'create_colls', 'restrict_colls'}
            - set(ZONE_UPDATE_FIELDS)
        ):
            messages.error(
                self.request,
                "You can only update the following fields: {}".format(
                    ', '.join(ZONE_UPDATE_FIELDS)
                ),
            )
            return redirect(redirect_url)

        # Update zone
        self.zone = form.save()
        self.update_zone(zone=self.zone, request=self.request)
        msg = f'Landing zone "{self.zone.title}" was updated.'
        messages.success(self.request, msg)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'landingzones:list',
            kwargs={'project': self.object.project.sodar_uuid},
        )


class ZoneDeleteView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ZoneModifyPermissionMixin,
    ProjectPermissionMixin,
    CurrentUserFormMixin,
    ZoneDeleteMixin,
    TemplateView,
):
    """LandingZone deletion view"""

    # NOTE: Not using DeleteView here as we don't delete the object in async
    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_delete.html'
    zone_action = 'delete'
    # NOTE: permission_required comes from ZoneModifyPermissionMixin

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['zone'] = LandingZone.objects.get(
            sodar_uuid=self.kwargs['landingzone']
        )
        return context

    def get(self, request, *args, **kwargs):
        """Override get() to ensure the zone status"""
        zone = LandingZone.objects.get(sodar_uuid=self.kwargs['landingzone'])
        if zone.status not in STATUS_ALLOW_UPDATE:
            messages.error(
                request,
                f'Unable to delete a landing zone with the status of '
                f'"{zone.status}".',
            )
            return redirect(
                reverse(
                    'landingzones:list',
                    kwargs={'project': zone.project.sodar_uuid},
                )
            )
        return super().get(request, *args, **kwargs)

    def post(self, *args, **kwargs):
        taskflow = plugin_api.get_backend_api('taskflow')
        zone = LandingZone.objects.get(sodar_uuid=self.kwargs['landingzone'])
        redirect_url = reverse(
            'landingzones:list', kwargs={'project': zone.project.sodar_uuid}
        )
        if not taskflow:
            messages.error(
                self.request, 'Taskflow not enabled, unable to modify zone!'
            )
            return redirect(redirect_url)
        try:
            self.submit_delete(zone)
            messages.info(
                self.request,
                f'Landing zone deletion initiated for '
                f'"{self.request.user.username}/{zone.title}" in assay '
                f'{zone.assay.get_display_name()}.',
            )
        except Exception as ex:
            messages.error(self.request, str(ex))
        return redirect(redirect_url)


class ZoneMoveView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ZoneModifyPermissionMixin,
    ProjectPermissionMixin,
    ZoneMoveMixin,
    TemplateView,
):
    """LandingZone validation and moving triggering view"""

    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_move.html'
    zone_action = 'move'
    # NOTE: permission_required comes from ZoneModifyPermissionMixin

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['zone'] = LandingZone.objects.get(
            sodar_uuid=self.kwargs['landingzone']
        )
        # Validate only mode
        if self.request.get_full_path() == reverse(
            'landingzones:validate',
            kwargs={'landingzone': context['zone'].sodar_uuid},
        ):
            context['validate_only'] = True
        context['sample_dir'] = settings.IRODS_SAMPLE_COLL
        return context

    def get(self, request, *args, **kwargs):
        """Override get() to ensure the zone status"""
        zone = LandingZone.objects.get(sodar_uuid=self.kwargs['landingzone'])
        try:
            irods_backend = plugin_api.get_backend_api('omics_irods')
            path = irods_backend.get_path(zone)
            with irods_backend.get_session() as irods:
                stats = irods_backend.get_stats(irods, path)
                if stats['file_count'] == 0:
                    messages.info(request, ZONE_MOVE_NO_FILES)
                    return redirect(
                        reverse(
                            'landingzones:list',
                            kwargs={'project': zone.project.sodar_uuid},
                        )
                    )
        except Exception as ex:
            messages.error(request, str(ex))
            return redirect(
                reverse(
                    'landingzones:list',
                    kwargs={'project': zone.project.sodar_uuid},
                )
            )

        if zone.status not in STATUS_ALLOW_UPDATE:
            messages.error(
                request,
                f'Unable to validate or move a landing zone with the status of '
                f'"{zone.status}".',
            )
            return redirect(
                reverse(
                    'landingzones:list',
                    kwargs={'project': zone.project.sodar_uuid},
                )
            )
        return super().get(request, *args, **kwargs)

    def post(self, request, **kwargs):
        taskflow = plugin_api.get_backend_api('taskflow')
        irods_backend = plugin_api.get_backend_api('omics_irods')
        zone = LandingZone.objects.get(sodar_uuid=self.kwargs['landingzone'])
        project = zone.project
        redirect_url = reverse(
            'landingzones:list', kwargs={'project': project.sodar_uuid}
        )

        if not taskflow or not irods_backend:
            messages.error(
                self.request,
                'Required backends (Taskflow/Irodsbackend) not enabled, '
                'unable to modify zone.',
            )
            return redirect(redirect_url)
        if zone.status not in STATUS_ALLOW_UPDATE:
            messages.error(self.request, ZONE_MOVE_INVALID_STATUS)
            return redirect(redirect_url)

        # Check limit
        valid_count = LandingZone.objects.filter(
            project=project,
            status__in=[ZONE_STATUS_PREPARING, ZONE_STATUS_VALIDATING],
        ).count()
        valid_limit = settings.LANDINGZONES_ZONE_VALIDATE_LIMIT or 1
        if valid_count >= valid_limit:
            messages.error(self.request, ZONE_VALIDATE_LIMIT_MSG + '.')
            return redirect(redirect_url)

        # Validate/move or validate only
        validate_only = False
        if self.request.get_full_path() == reverse(
            'landingzones:validate', kwargs={'landingzone': zone.sodar_uuid}
        ):
            validate_only = True
        try:
            self.submit_validate_move(zone, validate_only)
            messages.info(
                self.request,
                'Validating {}landing zone, see job progress in the '
                'zone list.'.format('and moving ' if not validate_only else ''),
            )
        except Exception as ex:
            messages.error(self.request, str(ex))
        return redirect(redirect_url)
