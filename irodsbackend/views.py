from django.http import HttpResponse  # To return exceptions from dispatch()

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import RoleAssignment, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.views import LoginRequiredMixin, ProjectPermissionMixin, \
    APIPermissionMixin


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']

# Local constants
ERROR_NOT_IN_PROJECT = 'Path does not belong to project'
ERROR_NOT_FOUND = 'Path not found'
ERROR_NO_AUTH = 'User not authorized for iRODS collection'


class BaseIrodsAPIView(
        LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin,
        APIView):
    """Base iRODS API View"""

    permission_required = 'irodsbackend.view_stats'  # Default perm

    def __init__(self, *args, **kwargs):
        super(BaseIrodsAPIView, self).__init__(*args, **kwargs)
        self.project = None

    def _check_collection_perm(self, path):
        """
        Check if request user has any perms for iRODS collection by path.

        :param path: Full path to iRODS collection
        :return: Boolean
        """
        # Just in case this was called with superuser..
        if self.request.user.is_superuser:
            return True

        irods_backend = get_backend_api('omics_irods')
        irods_session = irods_backend.get_session()

        try:
            coll = irods_session.collections.get(path)

        except Exception:
            return False

        # TODO: Are there cases where we should also check group membership?
        perms = irods_session.permissions.get(coll)
        owner_or_delegate = False
        user_as = RoleAssignment.objects.get_assignment(
            self.request.user, self.project)

        if user_as and user_as.role.name in [
                PROJECT_ROLE_OWNER, PROJECT_ROLE_DELEGATE]:
            owner_or_delegate = True

        if (owner_or_delegate or
                self.request.user.username in [p.user_name for p in perms]):
            return True

        return False

    def dispatch(self, request, *args, **kwargs):
        """Perform required checks before processing a request"""
        self.project = self._get_project(request, kwargs)

        if not self.project and not request.user.is_superuser:
            return HttpResponse(
                'Project UUID required for regular user', status=400)

        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return HttpResponse('iRODS backend not enabled', status=500)

        if request.method == 'GET' and 'path' not in self.kwargs:
            return HttpResponse('Path not set', status=400)

        # Collection checks
        # NOTE: If supplying path(s) via POST, implement these in request func
        if 'path' in self.kwargs:
            if (self.project and
                    irods_backend.get_path(self.project) not in
                    self.kwargs['path']):
                return HttpResponse(ERROR_NOT_IN_PROJECT, status=400)

            if not irods_backend.collection_exists(self.kwargs['path']):
                return HttpResponse(ERROR_NOT_FOUND, status=404)

            if (not request.user.is_superuser and
                    not self._check_collection_perm(self.kwargs['path'])):
                return HttpResponse(ERROR_NO_AUTH, status=403)

        return super(BaseIrodsAPIView, self).dispatch(request, *args, **kwargs)


class IrodsStatisticsAPIView(BaseIrodsAPIView):
    """View for returning collection file statistics for the UI"""

    def get(self, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')

        try:
            stats = irods_backend.get_object_stats(self.kwargs['path'])
            return Response(stats, status=200)

        except Exception as ex:
            return Response(str(ex), status=500)


class IrodsObjectListAPIView(BaseIrodsAPIView):
    """View for listing data objects in iRODS recursively"""

    permission_required = 'irodsbackend.view_files'

    def get(self, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')

        # Get files
        try:
            ret_data = irods_backend.get_objects(
                self.kwargs['path'], check_md5=bool(int(self.kwargs['md5'])))
            return Response(ret_data, status=200)

        except Exception as ex:
            return Response(str(ex), status=500)
