"""Taskflow API views for the samplesheets app"""

from rest_framework.response import Response

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views_taskflow import BaseTaskflowAPIView

from samplesheets.models import Investigation
from samplesheets.views import APP_NAME


class TaskflowCollStatusGetAPIView(BaseTaskflowAPIView):
    """View for getting the sample sheet iRODS collection status"""

    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__sodar_uuid=request.data['project_uuid'], active=True
            )

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        return Response({'dir_status': investigation.irods_status}, 200)


class TaskflowCollStatusSetAPIView(BaseTaskflowAPIView):
    """View for creating or updating a role assignment based on params"""

    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__sodar_uuid=request.data['project_uuid'], active=True
            )

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        investigation.irods_status = request.data['dir_status']
        investigation.save()

        return Response('ok', status=200)


class TaskflowSheetDeleteAPIView(BaseTaskflowAPIView):
    """View for deleting the sample sheets of a project"""

    def post(self, request):
        try:
            investigation = Investigation.objects.get(
                project__sodar_uuid=request.data['project_uuid'], active=True
            )

        except Investigation.DoesNotExist as ex:
            return Response(str(ex), status=404)

        project = investigation.project
        investigation.delete()

        # Delete cache
        cache_backend = get_backend_api('sodar_cache')

        if cache_backend:
            cache_backend.delete_cache(APP_NAME, project)

        return Response('ok', status=200)
