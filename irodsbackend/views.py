import logging
import rules

from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api


class IrodsStatisticsGetAPIView(
        LoginRequiredMixin, APIView):
    """View for returning collection file statistics for the UI"""

    def get(self, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')
        project = None

        if 'project' in self.kwargs:
            try:
                project = Project.objects.get(omics_uuid=self.kwargs['project'])

            except Project.DoesNotExist:
                return Response('Project not found', status=400)

        if not irods_backend:
            return Response('iRODS backend not enabled', status=500)

        if 'path' not in self.kwargs:
            return Response('Path not set', status=400)

        # Ensure the given path belongs in the project
        if (project and
                irods_backend.get_path(project) not in self.kwargs['path']):
            return Response('Path does not belong to project', status=400)

        # Check perms
        if (not self.request.user.is_superuser and (
                project and not self.request.user.has_perm(
                    'projectroles.view_project', project))):
            return Response('Not authorized', status=403)

        # Get stats
        try:
            stats = irods_backend.get_object_stats(self.kwargs['path'])
            return Response(stats, status=200)

        except FileNotFoundError:
            return Response('Not found', status=404)

        except Exception as ex:
            return Response(str(ex), status=500)
