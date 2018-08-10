import logging

from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, CreateView

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.email import send_generic_mail
from projectroles.models import Project
from projectroles.views import LoggedInPermissionMixin, \
    ProjectPermissionMixin, ProjectContextMixin
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.io import get_assay_dirs
from samplesheets.models import Assay
from samplesheets.views import InvestigationContextMixin

# Local helper for authenticating with auth basic
from omics_data_mgmt.users.auth import fallback_to_auth_basic

from .forms import LandingZoneForm
from .models import LandingZone

# Access Django user model
User = auth.get_user_model()

# Get logger
logger = logging.getLogger(__name__)


APP_NAME = 'landingzones'


EMAIL_MESSAGE_MOVED = r'''
Data was successfully validated and moved into the project
sample data repository from your landing zone.

You can browse the assay metadata and related files at
the following URL:
{url} 

Project: {project}
Assay: {assay}
Landing zone: {zone}
Zone owner: {user} <{user_email}>
Zone UUID: {zone_uuid}

Status message:
"{status_info}"'''.lstrip()


EMAIL_MESSAGE_FAILED = r'''
Validating and moving data from your landing zone into the
project sample data repository has failed. Please verify your
data and request for support if the problem persists.

Manage your landing zone at the following URL:
{url}

Project: {project}
Assay: {assay}
Landing zone: {zone}
Zone owner: {user} <{user_email}>
Zone UUID: {zone_uuid}

Status message:
"{status_info}"'''.lstrip()


class LandingZoneContextMixin:
    """Context mixing for LandingZones"""
    def get_context_data(self, *args, **kwargs):
        context = super(LandingZoneContextMixin, self).get_context_data(
            *args, **kwargs)

        try:
            context['zone'] = LandingZone.objects.get(
                omics_uuid=self.kwargs['landingzone'])

        except LandingZone.DoesNotExist:
            context['zone'] = None

        return context


class LandingZoneConfigPluginMixin:
    """Landing zone configuration plugin operations"""

    def get_flow_data(self, zone, flow_name, data):
        """
        Update flow data parameters according to config
        :param zone: LandingZone object
        :param flow_name: Name of flow (string)
        :param data: Flow data parameters (dict)
        :return: dict
        """
        if zone.configuration:
            from .plugins import get_zone_config_plugin
            config_plugin = get_zone_config_plugin(zone)

            if config_plugin:
                data = {
                    **data,
                    **config_plugin.get_extra_flow_data(zone, flow_name)}

        return data


class ProjectZoneView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        InvestigationContextMixin, TemplateView):
    """View for displaying user landing zones for a project"""

    permission_required = 'landingzones.view_zones_own'
    template_name = 'landingzones/project_zones.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectZoneView, self).get_context_data(
            *args, **kwargs)

        # Add flag for taskflow
        context['taskflow_enabled'] = True if \
            get_backend_api('taskflow') else False

        # iRODS backend
        context['irods_backend_enabled'] = True if \
            get_backend_api('omics_irods') else False

        # iRODS WebDAV
        context['irods_webdav_enabled'] = \
            int(settings.IRODS_WEBDAV_ENABLED)

        if settings.IRODS_WEBDAV_ENABLED:
            context['irods_webdav_url'] = settings.IRODS_WEBDAV_URL.rstrip('/')

        # User zones
        context['zones_own'] = LandingZone.objects.filter(
            project=context['project'],
            user=self.request.user).order_by('title')

        # Other zones
        # TODO: Add individual zone perm check if/when we implement issue #57
        if self.request.user.has_perm(
                'landingzones.view_zones_all', context['project']):
            context['zones_other'] = LandingZone.objects.filter(
                project=context['project']).exclude(
                user=self.request.user).exclude(
                    status__in=['MOVED', 'DELETED']).order_by(
                        'user__username', 'title')

        # Status query interval
        context['zone_status_interval'] = settings.LANDINGZONES_STATUS_INTERVAL

        return context


class ZoneCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        InvestigationContextMixin, LandingZoneConfigPluginMixin, CreateView):
    """ProjectInvite creation view"""
    model = LandingZone
    form_class = LandingZoneForm
    permission_required = 'landingzones.add_zones'

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(ZoneCreateView, self).get_form_kwargs()
        kwargs.update({
            'current_user': self.request.user,
            'project': self.kwargs['project']})
        return kwargs

    def form_valid(self, form):
        taskflow = get_backend_api('taskflow')
        timeline = get_backend_api('timeline_backend')
        irods_backend = get_backend_api('omics_irods')
        tl_event = None
        context = self.get_context_data()
        project = context['project']
        investigation = context['investigation']
        assay = form.cleaned_data.get('assay')

        error_msg = 'Unable to create zone: '

        if not taskflow:
            messages.error(
                self.request, error_msg + 'Taskflow not enabled')

        elif not investigation:
            messages.error(
                self.request, error_msg + 'Sample sheets not available')

        elif not investigation.irods_status:
            messages.error(
                self.request,
                error_msg + 'Sample sheet directory structure not created')

        else:
            # Create landing zone object in Django db
            # NOTE: We have to do this beforehand to work properly as async
            zone = form.save()
            config_str = ' with configuration "{}"'.format(
                zone.configuration) if zone.configuration else ''

            # Add event in Timeline
            if timeline:
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='zone_create',
                    description='create landing zone {{{}}}{} for {{{}}} in '
                                '{{{}}}'.format(
                                    'zone', config_str, 'user', 'assay'),
                    status_type='SUBMIT')

                tl_event.add_object(
                    obj=zone,
                    label='zone',
                    name=zone.title)

                tl_event.add_object(
                    obj=self.request.user,
                    label='user',
                    name=self.request.user.username)

                tl_event.add_object(
                    obj=assay,
                    label='assay',
                    name=assay.get_name())

            # Build assay dirs
            dirs = get_assay_dirs(assay)
            flow_name = 'landing_zone_create'

            flow_data = self.get_flow_data(
                zone, flow_name, {
                    'zone_title': zone.title,
                    'zone_uuid': zone.omics_uuid,
                    'user_name': self.request.user.username,
                    'user_uuid': self.request.user.omics_uuid,
                    'assay_path': irods_backend.get_subdir(
                        assay, landing_zone=True),
                    'description': zone.description,
                    'zone_config': zone.configuration,
                    'dirs': dirs})

            try:
                taskflow.submit(
                    project_uuid=project.omics_uuid,
                    flow_name=flow_name,
                    flow_data=flow_data,
                    timeline_uuid=tl_event.omics_uuid,
                    request_mode='async',
                    request=self.request)

                messages.warning(
                    self.request,
                    'Landing zone "{}" creation initiated{}: '
                    'see the zone list for the creation status'.format(
                        zone.title, config_str))

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                zone.delete()
                messages.error(self.request, str(ex))

            return redirect(reverse(
                'landingzones:list',
                kwargs={'project': project.omics_uuid}))


class ZoneDeleteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionMixin, LandingZoneConfigPluginMixin, TemplateView):
    """RoleAssignment deletion view"""
    # NOTE: Not using DeleteView here as we don't delete the object in async
    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_delete.html'
    permission_required = 'landingzones.update_zones_own'

    def has_permission(self):
        """Override has_permission to check perms depending on owner"""
        try:
            zone = LandingZone.objects.get(
                omics_uuid=self.kwargs['landingzone'])

            if zone.user == self.request.user:
                return self.request.user.has_perm(
                    'landingzones.update_zones_own',
                    self.get_permission_object())

            else:
                return self.request.user.has_perm(
                    'landingzones.update_zones_all',
                    self.get_permission_object())

        except LandingZone.DoesNotExist:
            return False

    def get_context_data(self, *args, **kwargs):
        context = super(ZoneDeleteView, self).get_context_data(
            *args, **kwargs)

        context['zone'] = LandingZone.objects.get(
            omics_uuid=self.kwargs['landingzone'])

        return context

    def post(self, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        irods_backend = get_backend_api('omics_irods')  # TODO: Ensure it exists
        tl_event = None

        zone = LandingZone.objects.get(omics_uuid=self.kwargs['landingzone'])
        project = zone.project

        redirect_url = reverse(
            'landingzones:list',
            kwargs={'project': project.omics_uuid})

        if not taskflow:
            messages.error(
                self.request, 'Taskflow not enabled, unable to modify zone!')
            return redirect(redirect_url)

        # Init Timeline event
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='zone_delete',
                description='delete landing zone {{{}}} in {{{}}} '
                            'from {{{}}}'.format(
                    'zone', 'assay', 'user'))

            tl_event.add_object(
                obj=zone,
                label='zone',
                name=zone.title)

            tl_event.add_object(
                obj=zone.assay,
                label='assay',
                name=zone.assay.get_display_name())

            tl_event.add_object(
                obj=zone.user,
                label='user',
                name=zone.user.username)

        # Submit with taskflow
        if taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_name = 'landing_zone_delete'

            flow_data = self.get_flow_data(
                zone, flow_name, {
                    'zone_title': zone.title,
                    'zone_uuid': zone.omics_uuid,
                    'zone_config': zone.configuration,
                    'assay_path': irods_backend.get_subdir(
                        zone.assay, landing_zone=True),
                    'user_name': zone.user.username})

            try:
                taskflow.submit(
                    project_uuid=project.omics_uuid,
                    flow_name=flow_name,
                    flow_data=flow_data,
                    request=self.request,
                    request_mode='async',
                    timeline_uuid=tl_event.omics_uuid)
                self.object = None

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return redirect(redirect_url)

        messages.warning(
            self.request,
            'Landing zone deletion initiated for "{}/{}" in assay {}.'.format(
                self.request.user.username,
                zone.title,
                zone.assay.get_display_name()))

        return redirect(redirect_url)

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(ZoneDeleteView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


class ZoneMoveView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionMixin, LandingZoneConfigPluginMixin, TemplateView):
    """Zone validation and moving triggering view"""
    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_move.html'
    # NOTE: minimum perm, all checked files will be tested in post()
    permission_required = 'landingzones.update_zones_own'

    def get_context_data(self, *args, **kwargs):
        context = super(ZoneMoveView, self).get_context_data(
            *args, **kwargs)

        context['zone'] = LandingZone.objects.get(
            omics_uuid=self.kwargs['landingzone'])

        # Validate only mode
        if self.request.get_full_path() == reverse(
                'landingzones:validate',
                kwargs={'landingzone': context['zone'].omics_uuid}):
            context['validate_only'] = True

        context['sample_dir'] = settings.IRODS_SAMPLE_DIR

        return context

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        irods_backend = get_backend_api('omics_irods')  # TODO: Ensure it exists

        zone = LandingZone.objects.get(omics_uuid=self.kwargs['landingzone'])
        project = zone.project
        tl_event = None
        validate_only = False
        event_name = 'zone_move'

        # Validate only mode
        if self.request.get_full_path() == reverse(
                'landingzones:validate',
                kwargs={'landingzone': zone.omics_uuid}):
            validate_only = True
            event_name = 'zone_validate'

        # Add event in Timeline
        if timeline:
            desc = 'validate '

            if not validate_only:
                desc += 'and move '

            desc += 'files from landing zone {zone} from ' \
                    '{user} in {assay}'

            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name=event_name,
                description=desc)

            tl_event.add_object(
                obj=zone,
                label='zone',
                name=zone.title)

            tl_event.add_object(
                obj=zone.user,
                label='user',
                name=zone.user.username)

            tl_event.add_object(
                obj=zone.assay,
                label='assay',
                name=zone.assay.get_display_name())

        # Fail if tasflow is not available
        if not taskflow:
            if timeline:
                tl_event.set_status(
                    'FAILED', status_desc='Taskflow not enabled')

            messages.error(
                self.request, 'Unable to process zone: taskflow not enabled!')

            return redirect(reverse(
                'landingzones:list', kwargs={'project': project.omics_uuid}))

        # Else go on with the creation
        if tl_event:
            tl_event.set_status('SUBMIT')

        flow_name = 'landing_zone_move'

        flow_data = self.get_flow_data(
            zone, flow_name, {
                'zone_title': str(zone.title),
                'zone_uuid': zone.omics_uuid,
                'zone_config': zone.configuration,
                'assay_path_samples': irods_backend.get_subdir(
                    zone.assay, landing_zone=False),
                'assay_path_zone': irods_backend.get_subdir(
                    zone.assay, landing_zone=True),
                'user_name': str(zone.user.username)})

        if validate_only:
            flow_data['validate_only'] = True

        try:
            taskflow.submit(
                project_uuid=project.omics_uuid,
                flow_name='landing_zone_move',
                flow_data=flow_data,
                request=self.request,
                request_mode='async',
                timeline_uuid=tl_event.omics_uuid)

            messages.warning(
                self.request,
                'Validating {}landing zone, see job progress in the '
                'zone list'.format(
                    'and moving ' if not validate_only else ''))

        except taskflow.FlowSubmitException as ex:
            zone.set_status('FAILED', str(ex))

            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            messages.error(self.request, str(ex))

        return HttpResponseRedirect(
            reverse('landingzones:list', kwargs={
                'project': project.omics_uuid}))


class ZoneClearView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectPermissionMixin, TemplateView):
    """Zone validation and moving triggering view"""
    http_method_names = ['get', 'post']
    template_name = 'landingzones/landingzone_confirm_clear.html'
    # NOTE: minimum perm, all checked files will be tested in post()
    permission_required = 'landingzones.update_zones_own'

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        project = Project.objects.get(omics_uuid=self.kwargs['project'])
        tl_event = None

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='zones_clear',
                description='clear inactive landing zones from {user}')

            tl_event.add_object(
                obj=self.request.user,
                label='user',
                name=self.request.user.username)

        try:
            inactive_zones = LandingZone.objects.filter(
                user=self.request.user, status__in=[
                    'MOVED', 'NOT CREATED', 'DELETED'])
            zone_count = inactive_zones.count()
            inactive_zones.delete()

            messages.success(
                self.request,
                'Cleared {} inactive landing zone{} for user {}'.format(
                    zone_count,
                    's' if zone_count != 1 else '',
                    self.request.user.username))

            if tl_event:
                tl_event.set_status('OK')

        except Exception as ex:
            messages.error(
                self.request,
                'Unable to clear inactive landing zones: {}'.format(ex))

            if tl_event:
                tl_event.set_status('FAILED', str(ex))

        return HttpResponseRedirect(
            reverse('landingzones:list', kwargs={
                'project': project.omics_uuid}))


# General API Views ------------------------------------------------------------


class LandingZoneStatusGetAPIView(
        LoginRequiredMixin, ProjectContextMixin, APIView):
    """View for returning landing zone status for the UI"""

    def get(self, *args, **kwargs):
        zone_uuid = self.kwargs['landingzone']

        try:
            zone = LandingZone.objects.get(
                omics_uuid=zone_uuid)

        except LandingZone.DoesNotExist:
            return Response('LandingZone not found', status=404)

        perm = 'view_zones_own' if \
            zone.user == self.request.user else 'view_zones_all'

        if self.request.user.has_perm(
                'landingzones.{}'.format(perm), zone.project):

            ret_data = {
                'status': zone.status,
                'status_info': zone.status_info}

            return Response(ret_data, status=200)

        return Response('Not authorized', status=403)


@fallback_to_auth_basic
class LandingZoneListAPIView(APIView):
    """View for returning a landing zone list based on its configuration"""

    # TODO: TBD: Do we also need this to work without a configuration param?

    def get(self, *args, **kwargs):
        from .plugins import get_zone_config_plugin
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return Response('iRODS backend not enabled', status=500)

        zone_config = self.kwargs['configuration']
        zones = LandingZone.objects.filter(configuration=zone_config)

        if zones.count() == 0:
            return Response('LandingZone not found', status=404)

        config_plugin = get_zone_config_plugin(zones.first())
        ret_data = {}

        for zone in zones:
            ret_data[str(zone.omics_uuid)] = {
                'title': zone.title,
                'assay': zone.assay.get_name(),
                'user': zone.user.username,
                'status': zone.status,
                'configuration': zone.configuration,
                'irods_path': irods_backend.get_path(zone)}

            if config_plugin:
                for field in config_plugin.api_config_data:
                    if field in zone.config_data:
                        ret_data[str(zone.omics_uuid)][field] = \
                            zone.config_data[field]

        return Response(ret_data, status=200)


# Taskflow API Views -----------------------------------------------------


# TODO: Limit access to localhost


class ZoneCreateAPIView(APIView):
    def post(self, request):
        try:
            user = User.objects.get(omics_uuid=request.data['user_uuid'])
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'])
            assay = Assay.objects.get(
                omics_uuid=request.data['assay_uuid'])

        except (
                User.DoesNotExist,
                Project.DoesNotExist,
                Assay.DoesNotExist) as ex:
            return Response('Not found', status=404)

        zone = LandingZone(
            assay=assay,
            title=request.data['title'],
            project=project,
            user=user,
            description=request.data['description'])
        zone.save()

        return Response({'zone_uuid': zone.omics_uuid}, status=200)


'''
class ZoneStatusGetAPIView(APIView):
    def post(self, request):
        try:
            zone = LandingZone.objects.get(omics_uuid=request.data['zone_uuid'])

        except LandingZone.DoesNotExist:
            return Response('LandingZone not found', status=404)

        ret_data = {
            'zone_pk': zone.pk,
            'status': zone.status,
            'status_info': zone.status_info}

        return Response(ret_data, status=200)
'''


class ZoneStatusSetAPIView(APIView):
    def post(self, request):
        try:
            zone = LandingZone.objects.get(
                omics_uuid=request.data['zone_uuid'])

        except LandingZone.DoesNotExist:
            return Response('LandingZone not found', status=404)

        try:
            zone.set_status(
                status=request.data['status'],
                status_info=request.data['status_info'] if
                request.data['status_info'] else None)

        except TypeError:
            return Response('Invalid status type', status=400)

        zone.refresh_from_db()

        # Send email
        if zone.status in ['MOVED', 'FAILED']:
            subject_body = 'Landing zone {}: {} / {}'.format(
                zone.status.lower(), zone.project.title, zone.title)

            message_body = EMAIL_MESSAGE_MOVED if \
                zone.status == 'MOVED' else EMAIL_MESSAGE_FAILED

            if zone.status == 'MOVED':
                email_url = request.build_absolute_uri(reverse(
                    'samplesheets:project_sheets',
                    kwargs={'study': zone.assay.study.omics_uuid}) + \
                            '#' + str(zone.assay.omics_uuid))

            else:   # FAILED
                email_url = request.build_absolute_uri(reverse(
                    'landingzones:list',
                    kwargs={'project': zone.project.omics_uuid}) + \
                            '#' + str(zone.omics_uuid))

            message_body = message_body.format(
                zone=zone.title,
                project=zone.project.title,
                assay=zone.assay.get_display_name(),
                user=zone.user.username,
                user_email=zone.user.email,
                zone_uuid=str(zone.omics_uuid),
                status_info=zone.status_info,
                url=email_url)

            send_generic_mail(
                subject_body, message_body, [zone.user], request)

        # If zone is deleted, call plugin function
        if request.data['status'] in ['MOVED', 'DELETED']:
            from .plugins import get_zone_config_plugin  # See issue #269
            config_plugin = get_zone_config_plugin(zone)

            if config_plugin:
                try:
                    config_plugin.cleanup_zone(zone)

                except Exception as ex:
                    logger.error(
                        'Unable to cleanup zone "{}" with plugin '
                        '"{}": {}'.format(zone.title, config_plugin.name, ex))

        return Response('ok', status=200)
