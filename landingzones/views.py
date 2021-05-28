import logging

from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, CreateView

# Projectroles dependency
from projectroles.models import Project
from projectroles.views import (
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    ProjectContextMixin,
)
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.views import (
    InvestigationContextMixin,
    RESULTS_COLL,
    MISC_FILES_COLL,
    TRACK_HUBS_COLL,
)

from landingzones.forms import LandingZoneForm
from landingzones.models import (
    LandingZone,
    STATUS_ALLOW_UPDATE,
    STATUS_ALLOW_CLEAR,
)

# Access Django user model
User = auth.get_user_model()

# Get logger
logger = logging.getLogger(__name__)


# Local constants
APP_NAME = 'landingzones'
SAMPLESHEETS_APP_NAME = 'samplesheets'


# Mixins -----------------------------------------------------------------------


class ZoneContextMixin:
    """Context mixing for LandingZones"""

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['zone'] = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()
        return context


class ZoneUpdateRequiredPermissionMixin:
    """Required permission override for landing zone updating views"""

    def get_permission_required(self):
        """Override to return the correct landing zone permission"""
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()

        # NOTE: UI views with PermissionRequiredMixin expect an iterable
        if zone and zone.user == self.request.user:
            return ['landingzones.update_zones_own']

        return ['landingzones.update_zones_all']


class ZoneConfigPluginMixin:
    """Landing zone configuration plugin operations"""

    @classmethod
    def _get_flow_data(cls, zone, flow_name, data):
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


class ZoneCreateMixin(ZoneConfigPluginMixin):
    """Mixin to be used in zone creation in UI and REST API views"""

    def _submit_create(self, zone, create_colls=False):
        """
        Handle timeline updating and taskflow initialization after a LandingZone
        object has been created.

        :param zone: LandingZone object
        :param create_colls: Auto-create expected collections (boolean)
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        taskflow = get_backend_api('taskflow')
        timeline = get_backend_api('timeline_backend')
        irods_backend = get_backend_api('omics_irods', conn=False)
        project = zone.project
        tl_event = None
        config_str = (
            ' with configuration "{}"'.format(zone.configuration)
            if zone.configuration
            else ''
        )

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='zone_create',
                description='create landing zone {{{}}}{} for {{{}}} in '
                '{{{}}}'.format('zone', config_str, 'user', 'assay'),
                status_type='SUBMIT',
            )
            tl_event.add_object(obj=zone, label='zone', name=zone.title)
            tl_event.add_object(
                obj=self.request.user,
                label='user',
                name=self.request.user.username,
            )
            tl_event.add_object(
                obj=zone.assay, label='assay', name=zone.assay.get_name()
            )

        # Gather collections to generate automatically
        # NOTE: Currently requires sodar_cache to be enabled!
        colls = []
        if create_colls:
            logger.debug('Creating default landing zone collections..')
            colls = [RESULTS_COLL, MISC_FILES_COLL, TRACK_HUBS_COLL]
            plugin = zone.assay.get_plugin()
            # First try the cache
            cache_backend = get_backend_api('sodar_cache')
            if plugin and cache_backend:
                cache_obj = cache_backend.get_cache_item(
                    'samplesheets.assayapps.'
                    + '_'.join(plugin.name.split('_')[2:]),
                    'irods/rows/{}'.format(zone.assay.sodar_uuid),
                    project=zone.project,
                )
                if cache_obj and cache_obj.data:
                    assay_path = irods_backend.get_path(zone.assay)
                    colls += [
                        p.replace(assay_path + '/', '')
                        for p in cache_obj.data['paths'].keys()
                    ]
                    logger.debug('Retrieved collections from cache')
            elif plugin:
                pass  # TODO: Build tables, get rows directly from plugin?
                # plugin = zone.assay.get_plugin()
        logger.debug('Collections to be created: {}'.format(', '.join(colls)))

        flow_name = 'landing_zone_create'
        flow_data = self._get_flow_data(
            zone,
            flow_name,
            {
                'zone_title': zone.title,
                'zone_uuid': zone.sodar_uuid,
                'user_name': self.request.user.username,
                'user_uuid': self.request.user.sodar_uuid,
                'assay_path': irods_backend.get_sub_path(
                    zone.assay, landing_zone=True
                ),
                'description': zone.description,
                'zone_config': zone.configuration,
                'colls': list(set(colls)),
            },
        )

        try:
            taskflow.submit(
                project_uuid=project.sodar_uuid,
                flow_name=flow_name,
                flow_data=flow_data,
                timeline_uuid=tl_event.sodar_uuid,
                request_mode='async',
                request=self.request,
            )
        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))
            zone.delete()
            raise ex


class ZoneDeleteMixin(ZoneConfigPluginMixin):
    """Mixin to be used in zone creation"""

    def _submit_delete(self, zone):
        """
        Handle timeline updating and initialize taskflow operation for
        LandingZone deletion.

        :param zone: LandingZone object
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        irods_backend = get_backend_api('omics_irods', conn=False)
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
            tl_event.set_status('SUBMIT')

        # Submit with taskflow
        flow_name = 'landing_zone_delete'
        flow_data = self._get_flow_data(
            zone,
            flow_name,
            {
                'zone_title': zone.title,
                'zone_uuid': zone.sodar_uuid,
                'zone_config': zone.configuration,
                'assay_path': irods_backend.get_sub_path(
                    zone.assay, landing_zone=True
                ),
                'user_name': zone.user.username,
            },
        )

        try:
            taskflow.submit(
                project_uuid=project.sodar_uuid,
                flow_name=flow_name,
                flow_data=flow_data,
                request=self.request,
                request_mode='async',
                timeline_uuid=tl_event.sodar_uuid if tl_event else None,
            )
            self.object = None

        except taskflow.FlowSubmitException as ex:
            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            raise ex


class ZoneMoveMixin(ZoneConfigPluginMixin):
    """Mixin to be used in zone validation/moving"""

    def _submit_validate_move(self, zone, validate_only, request=None):
        """
        Handle timeline updating and initialize taskflow operation for
        LandingZone moving and/or validation.

        :param zone: LandingZone object
        :param validate_only: Only perform validation if true (bool)
        :param request: Request object (optional)
        :raise: taskflow.FlowSubmitException if taskflow submit fails
        """
        if not request and hasattr(self, 'request'):
            request = self.request

        user = request.user if request else zone.user
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        irods_backend = get_backend_api('omics_irods', conn=False)
        project = zone.project
        tl_event = None
        event_name = 'zone_validate' if validate_only else 'zone_move'

        # Add event in Timeline
        if timeline:
            desc = 'validate '

            if not validate_only:
                desc += 'and move '

            desc += 'files from landing zone {zone} from ' '{user} in {assay}'

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
            tl_event.set_status('SUBMIT')

        flow_data = self._get_flow_data(
            zone,
            'landing_zone_move',
            {
                'zone_title': str(zone.title),
                'zone_uuid': zone.sodar_uuid,
                'zone_config': zone.configuration,
                'assay_path_samples': irods_backend.get_sub_path(
                    zone.assay, landing_zone=False
                ),
                'assay_path_zone': irods_backend.get_sub_path(
                    zone.assay, landing_zone=True
                ),
                'user_name': str(zone.user.username),
            },
        )

        if validate_only:
            flow_data['validate_only'] = True

        try:
            taskflow.submit(
                project_uuid=project.sodar_uuid,
                flow_name='landing_zone_move',
                flow_data=flow_data,
                request=request,
                request_mode='async',
                timeline_uuid=tl_event.sodar_uuid,
            )

        except taskflow.FlowSubmitException as ex:
            zone.set_status('FAILED', str(ex))

            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            raise ex


# UI Views ---------------------------------------------------------------------


class ProjectZoneView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    TemplateView,
):
    """View for displaying user landing zones for a project"""

    permission_required = 'landingzones.view_zones_own'
    template_name = 'landingzones/project_zones.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # Add flag for taskflow
        context['taskflow_enabled'] = (
            True if get_backend_api('taskflow') else False
        )

        # iRODS backend
        context['irods_backend_enabled'] = (
            True if get_backend_api('omics_irods', conn=False) else False
        )

        # iRODS WebDAV
        context['irods_webdav_enabled'] = int(settings.IRODS_WEBDAV_ENABLED)

        if settings.IRODS_WEBDAV_ENABLED:
            context['irods_webdav_url'] = settings.IRODS_WEBDAV_URL.rstrip('/')

        # User zones
        context['zones_own'] = LandingZone.objects.filter(
            project=context['project'], user=self.request.user
        ).order_by('title')

        # Other zones
        # TODO: Add individual zone perm check if/when we implement issue #57
        if self.request.user.has_perm(
            'landingzones.view_zones_all', context['project']
        ):
            context['zones_other'] = (
                LandingZone.objects.filter(project=context['project'])
                .exclude(user=self.request.user)
                .order_by('user__username', 'title')
            )

        # Status query interval
        context['zone_status_interval'] = settings.LANDINGZONES_STATUS_INTERVAL

        return context


class ZoneCreateView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectPermissionMixin,
    InvestigationContextMixin,
    ZoneCreateMixin,
    CreateView,
):
    """LandingZone creation view"""

    model = LandingZone
    form_class = LandingZoneForm
    permission_required = 'landingzones.add_zones'

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                'current_user': self.request.user,
                'project': self.kwargs['project'],
            }
        )
        return kwargs

    def form_valid(self, form):
        taskflow = get_backend_api('taskflow')
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
            self._submit_create(zone, form.cleaned_data.get('create_colls'))
            config_str = (
                ' with configuration "{}"'.format(zone.configuration)
                if zone.configuration
                else ''
            )
            msg = (
                'Landing zone "{}" creation initiated{}: '
                'see the zone list for the creation status.'.format(
                    zone.title, config_str
                )
            )
            if (
                form.cleaned_data.get('create_colls')
                and 'sodar_cache' in settings.ENABLED_BACKEND_PLUGINS
            ):
                msg += ' Collections created.'
            messages.warning(self.request, msg)
        except taskflow.FlowSubmitException as ex:
            messages.error(self.request, str(ex))

        return redirect(
            reverse('landingzones:list', kwargs={'project': project.sodar_uuid})
        )


class ZoneDeleteView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ZoneUpdateRequiredPermissionMixin,
    ProjectPermissionMixin,
    ZoneDeleteMixin,
    TemplateView,
):
    """LandingZone deletion view"""

    # NOTE: Not using DeleteView here as we don't delete the object in async
    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_delete.html'
    # NOTE: permission_required comes from ZoneUpdateRequiredPermissionMixin

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
                'Unable to delete a landing zone with the '
                'status of "{}".'.format(zone.status),
            )
            return redirect(
                reverse(
                    'landingzones:list',
                    kwargs={'project': zone.project.sodar_uuid},
                )
            )

        return super().get(request, *args, **kwargs)

    def post(self, *args, **kwargs):
        taskflow = get_backend_api('taskflow')
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
            self._submit_delete(zone)
            messages.warning(
                self.request,
                'Landing zone deletion initiated for "{}/{}" in '
                'assay {}.'.format(
                    self.request.user.username,
                    zone.title,
                    zone.assay.get_display_name(),
                ),
            )

        except Exception as ex:
            messages.error(self.request, str(ex))

        return redirect(redirect_url)

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super().get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


class ZoneMoveView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ZoneUpdateRequiredPermissionMixin,
    ProjectPermissionMixin,
    ZoneMoveMixin,
    TemplateView,
):
    """LandingZone validation and moving triggering view"""

    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_move.html'
    # NOTE: permission_required comes from ZoneUpdateRequiredPermissionMixin

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

        if zone.status not in STATUS_ALLOW_UPDATE:
            messages.error(
                request,
                'Unable to validate or move a landing zone with the '
                'status of "{}".'.format(zone.status),
            )
            return redirect(
                reverse(
                    'landingzones:list',
                    kwargs={'project': zone.project.sodar_uuid},
                )
            )

        return super().get(request, *args, **kwargs)

    def post(self, request, **kwargs):
        taskflow = get_backend_api('taskflow')
        irods_backend = get_backend_api('omics_irods', conn=False)
        zone = LandingZone.objects.get(sodar_uuid=self.kwargs['landingzone'])
        project = zone.project
        redirect_url = reverse(
            'landingzones:list', kwargs={'project': project.sodar_uuid}
        )

        if not taskflow or not irods_backend:
            messages.error(
                self.request,
                'Required backends (Taskflow/Irodsbackend) not enabled, '
                'unable to modify zone!',
            )
            return redirect(redirect_url)

        # Validate/move or validate only
        validate_only = False

        if self.request.get_full_path() == reverse(
            'landingzones:validate', kwargs={'landingzone': zone.sodar_uuid}
        ):
            validate_only = True

        try:
            self._submit_validate_move(zone, validate_only)
            messages.warning(
                self.request,
                'Validating {}landing zone, see job progress in the '
                'zone list.'.format('and moving ' if not validate_only else ''),
            )

        except Exception as ex:
            messages.error(self.request, str(ex))

        return redirect(redirect_url)


class ZoneClearView(
    LoginRequiredMixin,
    LoggedInPermissionMixin,
    ProjectContextMixin,
    ProjectPermissionMixin,
    TemplateView,
):
    """LandingZone validation and moving triggering view"""

    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_clear.html'
    permission_required = 'landingzones.update_zones_own'

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        project = Project.objects.get(sodar_uuid=self.kwargs['project'])
        tl_event = None

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='zones_clear',
                description='clear inactive landing zones from {user}',
            )
            tl_event.add_object(
                obj=self.request.user,
                label='user',
                name=self.request.user.username,
            )

        try:
            inactive_zones = LandingZone.objects.filter(
                project=project,
                user=self.request.user,
                status__in=STATUS_ALLOW_CLEAR,
            )
            zone_count = inactive_zones.count()
            inactive_zones.delete()
            messages.success(
                self.request,
                'Cleared {} inactive landing zone{} for user {}.'.format(
                    zone_count,
                    's' if zone_count != 1 else '',
                    self.request.user.username,
                ),
            )
            if tl_event:
                tl_event.set_status('OK')

        except Exception as ex:
            messages.error(
                self.request,
                'Unable to clear inactive landing zones: {}'.format(ex),
            )
            if tl_event:
                tl_event.set_status('FAILED', str(ex))

        return redirect(
            reverse('landingzones:list', kwargs={'project': project.sodar_uuid})
        )
