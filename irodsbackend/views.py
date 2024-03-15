"""Views for the irodsbackend app"""

import logging

from django.conf import settings
from django.http import JsonResponse

from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
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
        # Superuser and project users
        if user and (
            user.is_superuser or self.project.is_owner_or_delegate(user)
        ):
            return True
        # iRODS access
        try:
            coll = irods.collections.get(path)
        except Exception:
            return False
        perms = irods.permissions.get(coll)
        if user.username in [p.user_name for p in perms]:
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
        self.project = self.get_project()
        try:
            self.irods_backend = get_backend_api('omics_irods')
        except Exception as ex:
            return JsonResponse(self._get_detail(ex), status=500)
        if not self.irods_backend:
            return JsonResponse(self._get_detail(ERROR_NO_BACKEND), status=500)

        path = request.GET.get('path') if request.method == 'GET' else None
        if path:
            try:
                path = self.irods_backend.sanitize_path(path)
            except Exception as ex:
                return JsonResponse(self._get_detail(str(ex)), status=400)

        # Collection checks
        # NOTE: If supplying multiple paths via POST, implement these in request
        if not path:
            return super().dispatch(request, *args, **kwargs)
        if (
            self.project
            and self.irods_backend.get_path(self.project) not in path
        ):
            return JsonResponse(
                self._get_detail(ERROR_NOT_IN_PROJECT), status=400
            )

        try:
            with self.irods_backend.get_session() as irods:
                if not irods.collections.exists(path):
                    return JsonResponse(
                        self._get_detail(ERROR_NOT_FOUND), status=404
                    )
                if (
                    not request.user.is_superuser
                    and not self._check_collection_perm(
                        path, request.user, irods
                    )
                ):
                    return JsonResponse(
                        self._get_detail(ERROR_NO_AUTH), status=403
                    )
        except Exception as ex:
            return JsonResponse(self._get_detail(ex), status=500)
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
        ret = {}
        project_path = self.irods_backend.get_path(self.project)
        try:
            irods = self.irods_backend.get_session_obj()
        except Exception as ex:
            return JsonResponse(self._get_detail(ex), status=500)
        for p in request.POST.getlist('paths'):
            d = {}
            if not p.startswith(project_path):
                d['status'] = 400
            elif not self._check_collection_perm(p, request.user, irods):
                d['status'] = 403
            else:
                try:
                    if irods.collections.exists(p):
                        stats = self.irods_backend.get_object_stats(irods, p)
                        d.update(stats)
                        d['status'] = 200
                    else:
                        d['status'] = 404
                except Exception:
                    d['status'] = 500
            ret[p] = d
        irods.cleanup()
        return Response({'irods_stats': ret}, status=200)


class IrodsObjectListAjaxView(BaseIrodsAjaxView):
    """View for listing data objects in iRODS recursively"""

    permission_required = 'irodsbackend.view_files'

    def get(self, request, *args, **kwargs):
        check_md5 = bool(int(request.GET.get('md5')))
        include_colls = bool(int(request.GET.get('colls')))
        # Get files
        try:
            with self.irods_backend.get_session() as irods:
                objs = self.irods_backend.get_objects(
                    irods,
                    self.path,
                    include_md5=check_md5,
                    include_colls=include_colls,
                )
                ret = []
                md5_paths = []
                if check_md5:
                    md5_paths = [
                        o['path'] for o in objs if o['path'].endswith('.md5')
                    ]
                for o in objs:
                    if o['type'] == 'coll' and include_colls:
                        ret.append(o)
                    elif o['type'] == 'obj' and not o['path'].endswith('.md5'):
                        if check_md5:
                            o['md5_file'] = o['path'] + '.md5' in md5_paths
                        ret.append(o)
            return Response({'irods_data': ret}, status=200)
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
