from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import Project
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin

from .models import ProjectEvent


class ProjectTimelineView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ListView):
    """View for displaying files and folders for a project"""
    permission_required = 'timeline.view_timeline'

    template_name = 'timeline/project_timeline.html'
    model = ProjectEvent
    paginate_by = settings.TIMELINE_PAGINATION

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(id=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_queryset(self):
        set_kwargs = {
            'project': self.kwargs['project']}

        if not self.request.user.has_perm(
                    'timeline.view_classified_event',
                    self.get_permission_object()):
            set_kwargs['classified'] = False

        return ProjectEvent.objects.filter(
            **set_kwargs).order_by('-pk')


# Taskflow API Views -----------------------------------------------------


class TimelineEventStatusSetAPIView(APIView):
    def post(self, request):
        try:
            tl_event = ProjectEvent.objects.get(pk=request.data['event_pk'])

        except ProjectEvent.DoesNotExist:
            return Response('Timeline event not found', status=404)

        try:
            tl_event.set_status(
                status_type=request.data['status_type'],
                status_desc=request.data['status_desc'],
                extra_data=request.data['extra_data'] if
                'extra_data' in request.data else None)

        except TypeError:
            return Response('Invalid status type', status=400)

        return Response('ok', status=200)
