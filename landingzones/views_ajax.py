"""Ajax API views for the landingzones app"""

from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.views import ProjectContextMixin

from landingzones.models import LandingZone


class LandingZoneStatusRetrieveAjaxView(
    LoginRequiredMixin, ProjectContextMixin, APIView
):
    """Ajax API view for returning the landing zone status"""

    def get(self, *args, **kwargs):
        zone_uuid = self.kwargs['landingzone']

        try:
            zone = LandingZone.objects.get(sodar_uuid=zone_uuid)

        except LandingZone.DoesNotExist:
            return Response('LandingZone not found', status=404)

        perm = (
            'view_zones_own'
            if zone.user == self.request.user
            else 'view_zones_all'
        )

        if self.request.user.has_perm(
            'landingzones.{}'.format(perm), zone.project
        ):
            ret_data = {'status': zone.status, 'status_info': zone.status_info}
            return Response(ret_data, status=200)

        return Response('Not authorized', status=403)
