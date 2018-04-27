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
            context['irods_webdav_url'] = settings.IRODS_WEBDAV_URL

        # Add iRODS query API
        # TODO: Add api backend app
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
        LoginRequiredMixin, LoggedInPermissionMixin, InvestigationContextMixin,
        CreateView):
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
                'study_uuid': assay.study.omics_uuid,
                'assay_uuid': assay.omics_uuid,
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

                messages.success(
                    self.request,
                    'Landing zone "{}" creation initiated: '
                    'see the zone list for URLs '
                    'to access the zone'.format(zone.title))

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                zone.delete()
                messages.error(self.request, str(ex))

            return redirect(reverse(
                'landingzones:list',
                kwargs={'project': project.omics_uuid}))


'''

class ZoneDeleteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        DeleteView):
    """RoleAssignment deletion view"""
    model = LandingZone
    permission_required = 'landingzones.update_zones_own'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def has_permission(self):
        """Override has_permission to check perms depending on owner"""
        try:
            obj = type(self.get_object()).objects.get(pk=self.kwargs['pk'])

            if obj.user == self.request.user:
                return self.request.user.has_perm(
                    'landingzones.update_zones_own',
                    self.get_permission_object())

            else:
                return self.request.user.has_perm(
                    'landingzones.update_zones_all',
                    self.get_permission_object())

        except type(self.get_object()).DoesNotExist:
            return False

    def post(self, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        tl_event = None

        if not taskflow:
            messages.error(
                self.request, 'Taskflow not enabled, unable to modify zone!')

        else:
            self.object = LandingZone.objects.get(pk=kwargs['pk'])
            project = self.object.project
            user = self.object.user
            title = self.object.title

            # Init Timeline event
            if timeline:
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='zone_delete',
                    description='delete landing zone {{{}}} from {{{}}}'.format(
                        'zone', 'user'))

                tl_event.add_object(
                    obj=user,
                    label='user',
                    name=user.username)

                tl_event.add_object(
                    obj=self.object,
                    label='zone',
                    name=self.object.title)

            # Submit with taskflow
            if taskflow:
                if tl_event:
                    tl_event.set_status('SUBMIT')

                flow_data = {
                    'zone_pk': self.object.pk,
                    'zone_title': self.object.title,
                    'user_name': user.username,
                    'user_pk': user.pk}

                try:
                    taskflow.submit(
                        project_pk=project.pk,
                        flow_name='landing_zone_delete',
                        flow_data=flow_data,
                        request=self.request)
                    self.object = None

                except taskflow.FlowSubmitException as ex:
                    if tl_event:
                        tl_event.set_status('FAILED', str(ex))

                    messages.error(self.request, str(ex))
                    return HttpResponseRedirect(redirect(
                        reverse(
                            'project_zones', kwargs={'project': project.pk})))

            if tl_event:
                tl_event.set_status('OK')

            messages.success(
                self.request, 'Landing zone "{}/{}" removed from {}.'.format(
                    self.request.user.username, title, project.title))

        return HttpResponseRedirect(reverse(
            'project_zones', kwargs={'project': project.pk}))

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(ZoneDeleteView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


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


# Javascript API Views ---------------------------------------------------


class IrodsObjectListAPIView(
        LoginRequiredMixin,
        # LoggedInPermissionMixin,  # NOTE: This doesn't work with APIView
        ProjectContextMixin,
        APIView):
    # permission_required = 'landingzones.view_zones_own'

    def get(self, request, path, project, zone):
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return Response('Backend not enabled', status=500)

        try:
            zone_obj = LandingZone.objects.get(pk=zone)

        except LandingZone.DoesNotExist:
            return Response('Zone not found', status=400)

        try:
            project_obj = Project.objects.get(pk=project)

        except Project.DoesNotExist:
            return Response('Project not found', status=400)

        perm = 'view_zones_own' if \
            zone_obj.user == request.user else 'view_zones_all'

        if request.user.has_perm('landingzones.{}'.format(perm), project):
            ret_data = irods_backend.list_objects(path)
            return Response(ret_data, status=200)

        return Response('Not authorized', status=403)
'''


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


'''
class ZoneDeleteAPIView(APIView):
    def post(self, request):
        try:
            zone = LandingZone.objects.get(omics_uuid=request.data['zone_uuid'])

        except (LandingZone.DoesNotExist, User.DoesNotExist) as ex:
            return Response('Not found', status=404)

        zone.delete()

        return Response('ok', status=200)


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
