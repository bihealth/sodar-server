"""Ajax API views for the landingzones app"""

from rest_framework.response import Response

# Projectroles dependency
from projectroles.views_ajax import SODARBaseProjectAjaxView

from landingzones.models import LandingZone


class LandingZoneStatusRetrieveAjaxView(SODARBaseProjectAjaxView):
    """Ajax API view for returning the landing zone status"""

    def get_permission_required(self):
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()

        return (
            'landingzones.view_zones_own'
            if zone.user == self.request.user
            else 'landingzones.view_zones_all'
        )

    def get(self, *args, **kwargs):
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()
        ret_data = {'status': zone.status, 'status_info': zone.status_info}
        return Response(ret_data, status=200)
