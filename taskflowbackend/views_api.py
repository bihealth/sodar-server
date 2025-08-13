"""REST API views for the taskflowbackend app"""

from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.versioning import AcceptHeaderVersioning
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.plugins import PluginAPI
from rest_framework.response import Response
from projectroles.views_api import SODARAPIGenericProjectMixin


plugin_api = PluginAPI()


# Local constants
TASKFLOW_API_MEDIA_TYPE = 'application/vnd.bihealth.sodar.taskflowbackend+json'
TASKFLOW_API_ALLOWED_VERSIONS = ['1.0']
TASKFLOW_API_DEFAULT_VERSION = '1.0'
CATEGORY_EX_MSG = 'Project locking is not available for categories'


class TaskflowAPIVersioningMixin:
    """
    Taskflow API view versioning mixin for overriding media type and
    accepted versions.
    """

    class TaskflowAPIRenderer(JSONRenderer):
        media_type = TASKFLOW_API_MEDIA_TYPE

    class TaskflowAPIVersioning(AcceptHeaderVersioning):
        allowed_versions = TASKFLOW_API_ALLOWED_VERSIONS
        default_version = TASKFLOW_API_DEFAULT_VERSION

    renderer_classes = [TaskflowAPIRenderer]
    versioning_class = TaskflowAPIVersioning


class ProjectLockStatusAPIView(
    TaskflowAPIVersioningMixin, SODARAPIGenericProjectMixin, APIView
):
    """
    Return project lock status. Returns True if project is currently locked for
    taskflow and iRODS operations, False if it is not.

    Can only be called on projects, not categories.

    **URL:** ``/taskflowbackend/api/lock/status/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:**

    - ``is_locked``: Lock status (boolean)
    """

    http_method_names = ['get']
    permission_required = 'taskflowbackend.view_lock'
    serializer_class = None

    def get(self, request, *args, **kwargs):
        taskflow = plugin_api.get_backend_api('taskflow')
        if not taskflow:
            return Response(
                {'detail': 'Taskflow backend not enabled'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        project = self.get_project()
        if project.is_category():
            return Response(
                {'detail': CATEGORY_EX_MSG}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            lock_status = taskflow.is_locked(project)
        except Exception as ex:
            return Response(
                {'detail': 'Exception in querying lock status: {}'.format(ex)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({'is_locked': lock_status}, status=status.HTTP_200_OK)
