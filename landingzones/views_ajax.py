"""Ajax API views for the landingzones app"""

import logging
import math

from django.conf import settings
from django.http import Http404, HttpResponseForbidden, HttpResponseBadRequest
from django.urls import reverse

from rest_framework.response import Response

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views_ajax import SODARBaseProjectAjaxView

from landingzones.models import LandingZone
from landingzones.views import ProjectZoneInfoMixin


logger = logging.getLogger(__name__)


# Local constants
STATUS_TRUNCATE_LEN = 320


class ZoneBaseAjaxView(SODARBaseProjectAjaxView):
    """Base view for landingzones Ajax Views"""

    def check_zone_permission(self, zone, user):
        permission = (
            'landingzones.view_zone_own'
            if zone.user == self.request.user
            else 'landingzones.view_zone_all'
        )
        return user.has_perm(permission, obj=zone.project)


class ZoneStatusRetrieveAjaxView(ProjectZoneInfoMixin, ZoneBaseAjaxView):
    """Ajax API view for returning project landing zone statuses"""

    permission_required = 'landingzones.view_zone_own'

    def post(self, request, *args, **kwargs):
        project = self.get_project()
        ret = self.get_project_zone_info(project)
        ret['zones'] = {}
        zone_data = request.data.get('zones')
        if not zone_data:
            return Response(ret, status=200)
        zones = LandingZone.objects.filter(
            sodar_uuid__in=list(zone_data.keys()), project=project
        )
        for zone in zones:
            # Check permissions
            if not self.check_zone_permission(zone, self.request.user):
                continue
            # Skip if zone hasn't changed
            post_modified = zone_data[str(zone.sodar_uuid)].get('modified')
            if (
                post_modified
                and float(post_modified) == zone.date_modified.timestamp()
            ):
                continue
            status_info = zone.status_info[:STATUS_TRUNCATE_LEN]
            truncated = False
            if len(zone.status_info) > len(status_info):
                truncated = True
            ret['zones'][str(zone.sodar_uuid)] = {
                'modified': zone.date_modified.timestamp(),
                'status': zone.status,
                'status_info': status_info,
                'truncated': truncated,
            }
        return Response(ret, status=200)


class ZoneStatusInfoRetrieveAjaxView(ZoneBaseAjaxView):
    """Ajax API view for returning full status info for given landing zone"""

    permission_required = 'landingzones.view_zone_own'

    def get(self, request, *args, **kwargs):
        # TODO: Remove repetition
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs.get('landingzone')
        ).first()
        if not zone:
            return Http404()
        if not self.check_zone_permission(zone, self.request.user):
            return HttpResponseForbidden()
        return Response({'status_info': zone.status_info}, status=200)


class ZoneIrodsListRetrieveAjaxView(ZoneBaseAjaxView):
    """View for landing zone data objects list in iRODS"""

    permission_required = 'landingzones.view_zone_own'

    def get(self, request, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            return Response({'detail': 'iRODS backend not enabled'}, status=503)
        # TODO: Remove repetition
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs.get('landingzone')
        ).first()
        if not zone:
            return Http404()
        if not self.check_zone_permission(zone, self.request.user):
            return HttpResponseForbidden()

        page = int(request.GET.get('page', '1'))
        limit = settings.LANDINGZONES_FILE_LIST_PAGINATION
        offset = 0 if page == 1 else (page - 1) * limit
        zone_path = irods_backend.get_path(zone)
        url = reverse(
            'landingzones:ajax_irods_list',
            kwargs={'landingzone': zone.sodar_uuid},
        )
        try:
            with irods_backend.get_session() as irods:
                objs = irods_backend.get_objects(
                    irods,
                    zone_path,
                    include_checksum=False,  # Info retrieved in separate query
                    include_colls=True,
                    limit=limit,
                    offset=offset,
                )
                stats = irods_backend.get_stats(
                    irods, zone_path, include_colls=True
                )
            count = stats['file_count'] + stats['coll_count']
            ret = {
                'results': objs,
                'count': count,
                'page': page,
                'page_count': math.ceil(count / limit),
                'next': (
                    (url + f'?page={page + 1}') if count > page * limit else ''
                ),
                'previous': (url + f'?page={page - 1}') if page > 1 else '',
            }
            return Response(ret, status=200)
        except Exception as ex:
            return Response(
                {'detail': f'Exception in iRODS file list retrieval: {ex}'},
                status=500,
            )


class ZoneChecksumStatusRetrieveAjaxView(ZoneBaseAjaxView):
    """View for retrieving iRODS checksum status for zone data objects"""

    permission_required = 'landingzones.view_zone_own'

    def post(self, request, *args, **kwargs):
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            return Response({'detail': 'iRODS backend not enabled'}, status=503)

        # TODO: Remove repetition
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs.get('landingzone')
        ).first()
        if not zone:
            return Http404()
        if not self.check_zone_permission(zone, self.request.user):
            return HttpResponseForbidden()

        ret = {'checksum_status': {}}
        zone_path = irods_backend.get_path(zone)
        paths = request.data.get('paths')
        if not paths:
            return Response(ret, status=200)

        hash_scheme = settings.IRODS_HASH_SCHEME
        with irods_backend.get_session() as irods:
            for path in paths:
                try:  # Get past at parent path injection etc
                    irods_backend.sanitize_path(path)
                except ValueError:
                    logger.error(f'Invalid path: {path}')
                    return HttpResponseBadRequest()
                # Fail if user attempts to provide path outside of zone
                if not path.startswith(zone_path + '/'):
                    logger.error(f'Path not in zone: {path}')
                    return HttpResponseBadRequest()
                chk_path = path + '.' + hash_scheme.lower()
                ret['checksum_status'][path] = irods.data_objects.exists(
                    chk_path
                )
        return Response(ret, status=200)
