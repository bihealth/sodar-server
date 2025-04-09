"""Ajax API views for the landingzones app"""

from django.http import Http404, HttpResponseForbidden

from rest_framework.response import Response

# Projectroles dependency
from projectroles.views_ajax import SODARBaseProjectAjaxView

from landingzones.models import LandingZone


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
    """Ajax API view for returning the landing zone status"""

    permission_required = 'landingzones.view_zone_own'

    def post(self, request, *args, **kwargs):
        ret = {}
        zone_data = request.data.get('zones')
        if not zone_data:
            return Response(ret, status=200)
        project = self.get_project()
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
            ret[str(zone.sodar_uuid)] = {
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
