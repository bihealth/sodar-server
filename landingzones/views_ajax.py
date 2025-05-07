"""Ajax API views for the landingzones app"""

from django.http import Http404, HttpResponseForbidden

from rest_framework.response import Response

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views_ajax import SODARBaseProjectAjaxView

from landingzones.models import LandingZone
from landingzones.utils import get_zone_create_limit


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


class ZoneStatusRetrieveAjaxView(ZoneBaseAjaxView):
    """Ajax API view for returning project landing zone statuses"""

    permission_required = 'landingzones.view_zone_own'

    def post(self, request, *args, **kwargs):
        project = self.get_project()
        ret = {'zones': {}, 'zone_create_limit': get_zone_create_limit(project)}
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
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs.get('landingzone')
        ).first()
        if not zone:
            return Response({'detail': 'Not found'}, status=404)
        if not self.check_zone_permission(zone, self.request.user):
            return Response(
                {'detail': 'Access not granted for zone'}, status=403
            )
        zone_path = irods_backend.get_path(zone)
        try:
            with irods_backend.get_session() as irods:
                objs = irods_backend.get_objects(
                    irods, zone_path, include_md5=True, include_colls=True
                )
                ret = []
                md5_paths = [
                    o['path'] for o in objs if o['path'].endswith('.md5')
                ]
                for o in objs:
                    if o['type'] == 'coll':
                        ret.append(o)
                    elif o['type'] == 'obj' and not o['path'].endswith('.md5'):
                        o['md5_file'] = o['path'] + '.md5' in md5_paths
                        ret.append(o)
            return Response({'irods_data': ret}, status=200)
        except Exception as ex:
            return Response(
                {'detail': f'Exception in iRODS file list retrieval: {ex}'},
                status=500,
            )
