from django.http import JsonResponse  # To return exceptions from dispatch()

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import RoleAssignment, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.views import (
    LoginRequiredMixin,
    ProjectPermissionMixin,
    APIPermissionMixin,
)

# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']

# Local constants
ERROR_NOT_IN_PROJECT = 'Collection does not belong to project'
ERROR_NOT_FOUND = 'Collection not found'
ERROR_NO_AUTH = 'User not authorized for iRODS collection'


class BaseIrodsAPIView(
    LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin, APIView
):
    """Base iRODS API View"""

    permission_required = 'irodsbackend.view_stats'  # Default perm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = None
        self.path = None

    @staticmethod
    def _get_msg(msg):
        """
        Return message as a dict to be returned as JSON.

        :param msg: String or Exception
        :return: Dict
        """
        return {'message': str(msg)}

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
            self.request.user, self.project
        )

        if user_as and user_as.role.name in [
            PROJECT_ROLE_OWNER,
            PROJECT_ROLE_DELEGATE,
        ]:
            owner_or_delegate = True

        if owner_or_delegate or self.request.user.username in [
            p.user_name for p in perms
        ]:
            return True

        return False

    def dispatch(self, request, *args, **kwargs):
        """Perform required checks before processing a request"""
        self.project = self.get_project()
        path = request.GET.get('path') if request.method == 'GET' else None

        if not self.project and not request.user.is_superuser:
            return JsonResponse(
                self._get_msg('Project UUID required for regular user'),
                status=400,
            )

        if request.method == 'GET' and not path:
            return JsonResponse(self._get_msg('Path not set'), status=400)

        try:
            irods_backend = get_backend_api('omics_irods')

        except Exception as ex:
            return JsonResponse(self._get_msg(ex), status=500)

        # Collection checks
        # NOTE: If supplying path(s) via POST, implement these in request func
        if path:
            if (
                self.project
                and irods_backend.get_path(self.project) not in path
            ):
                return JsonResponse(
                    self._get_msg(ERROR_NOT_IN_PROJECT), status=400
                )

            if not irods_backend.collection_exists(path):
                return JsonResponse(self._get_msg(ERROR_NOT_FOUND), status=404)

            if (
                request.user.is_authenticated
                and not request.user.is_superuser
                and not self._check_collection_perm(path)
            ):
                return JsonResponse(self._get_msg(ERROR_NO_AUTH), status=403)

        self.path = path
        return super().dispatch(request, *args, **kwargs)


class IrodsStatisticsAPIView(BaseIrodsAPIView):
    """View for returning collection file statistics for the UI"""

    def get(self, *args, **kwargs):
        try:
            irods_backend = get_backend_api('omics_irods')
            stats = irods_backend.get_object_stats(self.path)
            return Response(stats, status=200)

        except Exception as ex:
            return Response(self._get_msg(ex), status=500)

    def post(self, request, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')

        data = {'coll_objects': []}
        q_dict = request.POST
        self.project = self.get_project()

        for obj in q_dict.getlist('paths'):

            if self.project and irods_backend.get_path(self.project) not in obj:
                data['coll_objects'].append(
                    {'path': obj, 'status': '400', 'stats': []}
                )
                break

            try:
                if not irods_backend.collection_exists(obj):
                    data['coll_objects'].append(
                        {'path': obj, 'status': '404', 'stats': []}
                    )
                else:
                    ret_data = irods_backend.get_object_stats(obj)
                    data['coll_objects'].append(
                        {'path': obj, 'status': '200', 'stats': ret_data}
                    )

            except Exception:
                data['coll_objects'].append(
                    {'path': obj, 'status': '500', 'stats': []}
                )

        return Response(data, status=200)


class IrodsObjectListAPIView(BaseIrodsAPIView):
    """View for listing data objects in iRODS recursively"""

    permission_required = 'irodsbackend.view_files'

    def get(self, request, *args, **kwargs):
        try:
            irods_backend = get_backend_api('omics_irods')

        except Exception as ex:
            return Response(self._get_msg(ex), status=500)

        md5 = request.GET.get('md5')

        # Get files
        try:
            ret_data = irods_backend.get_objects(
                self.path, check_md5=bool(int(md5))
            )
            return Response(ret_data, status=200)

        except Exception as ex:
            return Response(self._get_msg(ex), status=500)
