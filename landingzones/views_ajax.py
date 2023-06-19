"""Ajax API views for the landingzones app"""

from rest_framework.response import Response

# Projectroles dependency
from projectroles.views_ajax import SODARBaseProjectAjaxView

from landingzones.models import LandingZone


class ZoneStatusRetrieveAjaxView(SODARBaseProjectAjaxView):
    """Ajax API view for returning the landing zone status"""

    permission_required = 'landingzones.view_zone_own'

    def check_zone_permission(self, zone, user):
        permission = 'landingzones.view_zone_own' if zone.user == self.request.user else 'landingzones.view_zone_all'
        return user.has_perm(permission, obj=zone)

    def post(self, request, *args, **kwargs):
        zone_uuids = request.data.get('zone_uuids', [])
        project = self.get_project()

        # Filter landing zones based on UUIDs and project
        zones = LandingZone.objects.filter(
            sodar_uuid__in=zone_uuids, project=project
        )

        status_dict = {}
        for zone in zones:
            # Check permissions
            if not self.check_zone_permission(zone, self.request.user):
                continue

            status_dict[zone.sodar_uuid] = {
                'status': zone.status,
                'status_info': zone.status_info
            }

        return Response(status_dict, status=200)

