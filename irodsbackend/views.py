import logging

from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.plugins import get_backend_api


# TODO: TBD: Do we need perms other than the user being logged in?
class IrodsStatisticsGetAPIView(LoginRequiredMixin, APIView):
    """View for returning collection file statistics for the UI"""

    def get(self, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return Response('iRODS backend not enabled', status=500)

        if 'path' not in self.kwargs:
            return Response('Path not set', status=400)

        try:
            stats = irods_backend.get_object_stats(self.kwargs['path'])
            return Response(stats, status=200)

        except FileNotFoundError:
            return Response('Not found', status=404)

        except Exception as ex:
            return Response(str(ex), status=500)
