"""Views for the irodsbackend app"""

import logging

from django.conf import settings
from django.http import JsonResponse

from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import RoleAssignment, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.views_ajax import SODARBaseProjectAjaxView

from sodar.users.auth import fallback_to_auth_basic


logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']

# Local constants
ERROR_NOT_IN_PROJECT = 'Collection does not belong to project'
ERROR_NOT_FOUND = 'Collection not found'
ERROR_NO_AUTH = 'User not authorized for iRODS collection'
ERROR_NO_BACKEND = (
    'Unable to initialize omics_irods backend, iRODS server '
    'possibly unavailable'
)


class BaseIrodsAjaxView(SODARBaseProjectAjaxView):
    """Base iRODS Ajax API View"""

    irods_backend = None
    permission_required = 'irodsbackend.view_stats'  # Default perm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = None
        self.path = None

    @staticmethod
    def _get_detail(msg):
        """
        Return detail message as a dict to be returned as JSON.

        :param msg: String or Exception
        :return: Dict
        """
        return {'detail': str(msg)}

    def _check_collection_perm(self, path, user, irods):
        """
        Check if request user has any perms for iRODS collection by path.

        :param path: Full path to iRODS collection
        :param user: User object
        :param irods: iRODSSession object
        :return: Boolean
        """
        # Just in case this was called with superuser..
        if user and user.is_superuser:
            return True
        try:
            coll = irods.collections.get(path)
        except Exception:
            return False

        # Project users
        perms = irods.permissions.get(coll)
        owner_or_delegate = False
        user_as = RoleAssignment.objects.get_assignment(user, self.project)
        if user_as and user_as.role.name in [
            PROJECT_ROLE_OWNER,
            PROJECT_ROLE_DELEGATE,
        ]:
            owner_or_delegate = True
        if owner_or_delegate or user.username in [p.user_name for p in perms]:
            return True

        # Public guest access
        if (
            self.project.public_guest_access
            and (user.is_authenticated or settings.PROJECTROLES_ALLOW_ANONYMOUS)
            and self.irods_backend.get_sample_path(self.project) in path
        ):
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        """Perform required checks before processing a request"""
        path = request.GET.get('path') if request.method == 'GET' else None
        if request.method == 'GET' and not path:
            return JsonResponse(self._get_detail('Path not set'), status=400)
        try:
            self.irods_backend = get_backend_api('omics_irods')
        except Exception as ex:
            return JsonResponse(self._get_detail(ex), status=500)
        if not self.irods_backend:
            return JsonResponse(self._get_detail(ERROR_NO_BACKEND), status=500)

        # Collection checks
        # NOTE: If supplying multiple paths via POST, implement these in request
        self.project = self.get_project()
        if path:
            if (
                self.project
                and self.irods_backend.get_path(self.project) not in path
            ):
                return JsonResponse(
                    self._get_detail(ERROR_NOT_IN_PROJECT), status=400
                )
            if not self.irods_backend.collection_exists(path):
                return JsonResponse(
                    self._get_detail(ERROR_NOT_FOUND), status=404
                )
            with self.irods_backend.get_session() as irods:
                if (
                    not request.user.is_superuser
                    and not self._check_collection_perm(
                        path, request.user, irods
                    )
                ):
                    return JsonResponse(
                        self._get_detail(ERROR_NO_AUTH), status=403
                    )
        self.path = path
        return super().dispatch(request, *args, **kwargs)


class IrodsStatisticsAjaxView(BaseIrodsAjaxView):
    """View for returning collection file statistics for the UI"""

    def get(self, *args, **kwargs):
        try:
            with self.irods_backend.get_session() as irods:
                stats = self.irods_backend.get_object_stats(irods, self.path)
            return Response(stats, status=200)
        except Exception as ex:
            return Response(self._get_detail(ex), status=500)

    def post(self, request, *args, **kwargs):
        data = {'coll_objects': []}
        q_dict = request.POST
        project_path = self.irods_backend.get_path(self.project)

        with self.irods_backend.get_session() as irods:
            for path in q_dict.getlist('paths'):
                if project_path not in path:
                    data['coll_objects'].append(
                        {'path': path, 'status': '400', 'stats': {}}
                    )
                    break
                if not self._check_collection_perm(path, request.user, irods):
                    data['coll_objects'].append(
                        {'path': path, 'status': '403', 'stats': {}}
                    )
                    break
                try:
                    if not irods.collections.exists(path):
                        data['coll_objects'].append(
                            {'path': path, 'status': '404', 'stats': {}}
                        )
                    else:
                        ret_data = self.irods_backend.get_object_stats(
                            irods, path
                        )
                        data['coll_objects'].append(
                            {'path': path, 'status': '200', 'stats': ret_data}
                        )
                except Exception:
                    data['coll_objects'].append(
                        {'path': path, 'status': '500', 'stats': {}}
                    )
        return Response(data, status=200)


class IrodsObjectListAjaxView(BaseIrodsAjaxView):
    """View for listing data objects in iRODS recursively"""

    permission_required = 'irodsbackend.view_files'

    def get(self, request, *args, **kwargs):
        md5 = request.GET.get('md5')
        colls = request.GET.get('colls')
        # Get files
        try:
            with self.irods_backend.get_session() as irods:
                ret_data = self.irods_backend.get_objects(
                    irods,
                    self.path,
                    check_md5=bool(int(md5)),
                    include_colls=bool(int(colls)),
                )
            return Response(ret_data, status=200)
        except Exception as ex:
            return Response(self._get_detail(ex), status=500)


@fallback_to_auth_basic
class LocalAuthAPIView(APIView):
    """
    REST API view for verifying login credentials for local users in iRODS.

    Should only be used in local development and testing situations or when an
    external LDAP/AD login is not available.
    """

    def post(self, request, *args, **kwargs):
        # TODO: Limit access to iRODS host?
        log_prefix = 'Local auth'
        if not settings.IRODS_SODAR_AUTH:
            not_enabled_msg = 'IRODS_SODAR_AUTH not enabled'
            logger.error('{} failed: {}'.format(log_prefix, not_enabled_msg))
            return JsonResponse({'detail': not_enabled_msg}, status=500)
        if request.user.is_authenticated:
            logger.info(
                '{} successful: {}'.format(log_prefix, request.user.username)
            )
            return JsonResponse({'detail': 'ok'}, status=200)
        logger.error(
            '{} failed: User {} not authenticated'.format(
                log_prefix, request.user.username
            )
        )
        raise NotAuthenticated()
