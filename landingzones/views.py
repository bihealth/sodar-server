from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, CreateView, DeleteView

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import Project
from projectroles.views import LoggedInPermissionMixin, \
    ProjectPermissionMixin, ProjectContextMixin
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.io import get_base_dirs, get_assay_dirs
from samplesheets.models import Investigation, Assay
from samplesheets.views import InvestigationContextMixin

from .forms import LandingZoneForm
from .models import LandingZone

# Access Django user model
User = auth.get_user_model()


APP_NAME = 'landingzones'


class ProjectZoneView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        InvestigationContextMixin, TemplateView):
    """View for displaying user landing zones for a project"""

    permission_required = 'landingzones.view_zones_own'
    template_name = 'landingzones/project_zones.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectZoneView, self).get_context_data(
            *args, **kwargs)

        # Assay context (optional)
        assay = None

        if 'assay' in self.kwargs:
            try:
                assay = Assay.objects.get(omics_uuid=self.kwargs['assay'])
                context['assay'] = assay

            except Assay.DoesNotExist:
                pass

        # Add flag for taskflow
        context['taskflow_enabled'] = True if \
            get_backend_api('taskflow') else False

        # Flags for links
        context['irods_webdav_enabled'] = \
            settings.IRODS_WEBDAV_ENABLED

        # WebDAV URL for JQuery
        if settings.IRODS_WEBDAV_ENABLED:
            context['irods_webdav_url'] = settings.IRODS_WEBDAV_URL.rstrip('/')

        # Add iRODS query API
        context['irods_backend'] = get_backend_api('omics_irods')

        # Zones and title according to user perms
        zone_query = {'project': context['project']}

        if assay:
            zone_query['assay'] = assay

        if self.request.user.has_perm(
                'landingzones.view_zones_all', context['project']):
            context['zone_list_title'] = 'All Zones'

        else:
            zone_query['user'] = self.request.user
            context['zone_list_title'] = 'Your Zones'

        context['zones'] = LandingZone.objects.filter(
            **zone_query).order_by('-pk')

        # Status query interval
        context['zone_status_interval'] = settings.LANDINGZONES_STATUS_INTERVAL

        return context


class ZoneCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        InvestigationContextMixin, CreateView):
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

            # Add event in Timeline
            if timeline:
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='zone_create',
                    description='create landing zone '
                                '{{{}}} for user {{{}}} in '
                                'assay {{{}}}'.format(
                                    'zone', 'user', 'assay'),
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

            flow_data = {
                'zone_title': zone.title,
                'zone_uuid': zone.omics_uuid,
                'user_name': self.request.user.username,
                'user_uuid': self.request.user.omics_uuid,
                'study_dir': assay.study.get_dir(landing_zone=True),
                'assay_dir': assay.get_dir(
                    include_study=False, landing_zone=True),
                'description': zone.description,
                'dirs': dirs}

            try:
                taskflow.submit(
                    project_uuid=project.omics_uuid,
                    flow_name='landing_zone_create',
                    flow_data=flow_data,
                    timeline_uuid=tl_event.omics_uuid,
                    request_mode='async',
                    request=self.request)

                messages.warning(
                    self.request,
                    'Landing zone "{}" creation initiated: '
                    'see the zone list for the creation status'.format(
                        zone.title))

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
        ProjectPermissionMixin, DeleteView):
    """RoleAssignment deletion view"""
    model = LandingZone
    slug_url_kwarg = 'landingzone'
    slug_field = 'omics_uuid'
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

    def post(self, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        tl_event = None
        zone = LandingZone.objects.get(
            omics_uuid=kwargs['landingzone'])
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

            flow_data = {
                'zone_title': zone.title,
                'zone_uuid': zone.omics_uuid,
                'study_dir': zone.assay.study.get_dir(landing_zone=True),
                'assay_dir': zone.assay.get_dir(
                    include_study=False, landing_zone=True),
                'user_name': zone.user.username}

            try:
                taskflow.submit(
                    project_uuid=project.omics_uuid,
                    flow_name='landing_zone_delete',
                    flow_data=flow_data,
                    request=self.request)
                self.object = None

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return redirect(redirect_url)

        if tl_event:
            tl_event.set_status('OK')

        messages.success(
            self.request,
            'Landing zone "{}" for {} removed from assay {}.'.format(
                zone.title,
                self.request.user.username,
                zone.assay.get_display_name()))

        return redirect(redirect_url)

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(ZoneDeleteView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


'''
class ZoneMoveView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        TemplateView):
    """Zone validation and moving triggering view"""
    http_method_names = ['get', 'post']
    template_name = 'landingzones/zone_move_confirm.html'
    # NOTE: minimum perm, all checked files will be tested in post()
    permission_required = 'landingzones.update_zones_own'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(id=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super(ZoneMoveView, self).get_context_data(
            *args, **kwargs)

        context['zone'] = LandingZone.objects.get(pk=self.kwargs['pk'])

        return context

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        project = Project.objects.get(pk=self.kwargs['project'])
        zone = LandingZone.objects.get(pk=self.kwargs['pk'])
        tl_event = None

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='zone_move',
                description='validate and move files from landing zone '
                            '{zone_user}/{zone}')

            tl_event.add_object(
                obj=zone.user,
                label='zone_user',
                name=zone.user.username)

            tl_event.add_object(
                obj=zone,
                label='zone',
                name=zone.title)

        # Fail if tasflow is not available
        if not taskflow:
            if timeline:
                tl_event.set_status(
                    'FAILED', status_desc='Taskflow not enabled')

            messages.error(
                self.request, 'Unable to create dirs: taskflow not enabled!')

            return redirect(reverse(
                'project_zones', kwargs={'project': project.pk}))

        # Else go on with the creation
        if tl_event:
            tl_event.set_status('SUBMIT')

        flow_data = {
            'zone_title': str(zone.title),
            'zone_pk': zone.pk,
            'user_name': str(zone.user.username)}

        try:
            taskflow.submit(
                project_pk=project.pk,
                flow_name='landing_zone_move',
                flow_data=flow_data,
                request=self.request,
                request_mode='async',
                timeline_pk=tl_event.pk)

            messages.warning(
                self.request,
                'Validating and moving landing zone, see job progress in the '
                'zone list')

        except taskflow.FlowSubmitException as ex:
            zone.set_status('FAILED', str(ex))

            if tl_event:
                tl_event.set_status('FAILED', str(ex))

            messages.error(self.request, str(ex))

        return HttpResponseRedirect(
            reverse('project_zones', kwargs={
                'project': project.pk}))

    def get(self, request, **kwargs):
        return super(TemplateView, self).render_to_response(
            self.get_context_data())


class ZoneClearView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        TemplateView):
    """Zone validation and moving triggering view"""
    http_method_names = ['get', 'post']
    template_name = 'landingzones/zone_clear_confirm.html'
    # NOTE: minimum perm, all checked files will be tested in post()
    permission_required = 'landingzones.update_zones_own'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(id=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        project = Project.objects.get(pk=self.kwargs['project'])
        tl_event = None

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='zones_clear',
                description='Clear moved zones from user {user}')

            tl_event.add_object(
                obj=self.request.user,
                label='user',
                name=self.request.user.username)

        try:
            LandingZone.objects.filter(
                user=self.request.user, status='MOVED').delete()
            messages.success(
                self.request,
                'Landing zones cleared for user "{}"'.format(
                    self.request.user.username))

            if tl_event:
                tl_event.set_status('OK')

        except Exception as ex:
            messages.error(
                self.request, 'Unable to clear landing zones: {}'.format(ex))

            if tl_event:
                tl_event.set_status('FAILED', str(ex))

        return HttpResponseRedirect(
            reverse('project_zones', kwargs={
                'project': project.pk}))

    def get(self, request, **kwargs):
        return super(TemplateView, self).render_to_response(
            self.get_context_data())
'''

# Javascript API Views ---------------------------------------------------


class LandingZoneObjectListAPIView(
        LoginRequiredMixin, ProjectContextMixin, APIView):
    """View for listing landing zone objects in iRODS via Ajax"""

    def get(self, request, landingzone, **kwargs):
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return Response('Backend not enabled', status=500)

        try:
            zone = LandingZone.objects.get(omics_uuid=landingzone)

        except LandingZone.DoesNotExist:
            return Response('Zone not found', status=400)

        perm = 'view_zones_own' if \
            zone.user == request.user else 'view_zones_all'

        if request.user.has_perm('landingzones.{}'.format(perm), zone.project):
            try:
                ret_data = irods_backend.list_objects(zone.get_path())

            except Exception as ex:     # TODO: 404 if dir not found
                return Response(ex, status=500)

            return Response(ret_data, status=200)

        return Response('Not authorized', status=403)


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


# Taskflow API Views -----------------------------------------------------


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


class ZoneDeleteAPIView(APIView):
    def post(self, request):
        try:
            zone = LandingZone.objects.get(omics_uuid=request.data['zone_uuid'])

        except (LandingZone.DoesNotExist, User.DoesNotExist) as ex:
            return Response('Not found', status=404)

        zone.delete()
        return Response('ok', status=200)


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

        return Response('ok', status=200)
