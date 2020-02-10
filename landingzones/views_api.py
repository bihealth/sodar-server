"""REST API views for the landingzones app"""

import logging

from django.urls import reverse

from rest_framework.exceptions import APIException, NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

# Samplesheets dependency
# TODO: Import from projectroles once moved into SODAR Core
from samplesheets.views import (
    # SODARAPIBaseProjectMixin,
    SODARAPIGenericViewProjectMixin,
)

# Projectroles dependency
from projectroles.views import ProjectPermissionMixin
from projectroles.plugins import get_backend_api

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic

from landingzones.models import LandingZone, STATUS_ALLOW_UPDATE
from landingzones.serializers import LandingZoneSerializer
from landingzones.views import (
    ZoneCreateViewMixin,
    ZoneDeleteViewMixin,
    ZoneMoveViewMixin,
)

# Get logger
logger = logging.getLogger(__name__)


# Mixins and Base Views --------------------------------------------------------


# TODO: Fix has_permission() inheritance and use ZoneUpdatePermissionMixin
class LandingZoneSubmitBaseAPIView(
    ProjectPermissionMixin,
    # ZoneUpdatePermissionMixin,  # TODO: Fix
    APIView,
):
    """
    Base API view for initiating LandingZone operations via SODAR Taskflow.
    NOTE: Not tied to serializer or generic views, as the actual object will not
          be updated here.
    """

    http_method_names = ['post']
    permission_required = 'landingzones.update_zones_own'

    # TODO: This never gets called if implemented as mixin, why?
    def has_permission(self):
        """Override has_permission to check perms depending on owner"""
        try:
            zone = LandingZone.objects.get(
                sodar_uuid=self.kwargs['landingzone']
            )

            if zone.user == self.request.user:
                return self.request.user.has_perm(
                    'landingzones.update_zones_own', zone.project
                )

            else:
                return self.request.user.has_perm(
                    'landingzones.update_zones_all', zone.project
                )

        except LandingZone.DoesNotExist:
            return False

    @classmethod
    def _validate_zone_obj(cls, zone, allowed_status_types, action):
        """
        Manually validate given the LandingZone object for an update.

        :param zone: LandingZone object
        :param allowed_status_types: List of allowed zone status types
        :param action: Action to be performed (string)
        :raise: NotFound if landing zone is not found
        :raise: ValidateError if status is not in allowed types
        """
        if not zone:
            raise NotFound

        # Validate zone
        if zone.status not in allowed_status_types:
            raise ValidationError(
                'Unable to {} landing zone: status={}'.format(
                    action, zone.status
                )
            )


class LandingZoneListAPIView(SODARAPIGenericViewProjectMixin, ListAPIView):
    """
    API view for listing LandingZone objects for a project.

    If the user has rights to view all zones, every zone in the project will be
    listed. Otherwise only their own zones appear in the list.
    """

    permission_required = 'landingzones.view_zones_own'
    serializer_class = LandingZoneSerializer

    def get_queryset(self):
        """Override get_queryset() to return zones based on user perms"""
        project = self.get_project()
        ret = LandingZone.objects.filter(project=project)

        if not self.request.user.has_perm(
            'landingzones.view_zones_all', project
        ):
            return ret.filter(user=self.request.user)

        return ret


class LandingZoneRetrieveAPIView(
    SODARAPIGenericViewProjectMixin, RetrieveAPIView
):
    """
    API view for retrieving information of a specific LandingZone by UUID.
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'landingzone'
    permission_required = 'landingzones.view_zones_own'
    serializer_class = LandingZoneSerializer

    def has_permission(self):
        """Override has_permission to check perms depending on owner"""
        obj = self.get_object()

        if not obj:
            return False

        if obj.user == self.request.user:
            return self.request.user.has_perm(
                'landingzones.update_zones_own', self.get_permission_object()
            )

        else:
            return self.request.user.has_perm(
                'landingzones.update_zones_all', self.get_permission_object()
            )


class LandingZoneCreateAPIView(
    SODARAPIGenericViewProjectMixin, ZoneCreateViewMixin, CreateAPIView
):
    """
    API view for initiating LandingZone creation.
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'project'
    permission_required = 'landingzones.add_zones'
    serializer_class = LandingZoneSerializer

    def perform_create(self, serializer):
        """Override perform_create() to add timeline event and initiate
        taskflow"""
        super().perform_create(serializer)

        try:
            self._submit_create(serializer.instance)

        except Exception as ex:
            raise APIException('Creating landing zone failed: {}'.format(ex))


class LandingZoneSubmitDeleteAPIView(
    ZoneDeleteViewMixin, LandingZoneSubmitBaseAPIView
):
    """
    API view for initiating LandingZone deletion via SODAR Taskflow.
    NOTE: Not tied to serializer or generic views, as the actual object will not
          be updated here.
    """

    def post(self, request, *args, **kwargs):
        """POST request for initiating landing zone deletion"""
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()
        self._validate_zone_obj(zone, STATUS_ALLOW_UPDATE, 'delete')

        try:
            self._submit_delete(zone)

        except Exception as ex:
            raise APIException(
                'Initiating landing zone deletion failed: {}'.format(ex)
            )

        return Response(
            {
                'message': 'Landing zone deletion initiated',
                'sodar_uuid': str(zone.sodar_uuid),
            },
            status=status.HTTP_200_OK,
        )


class LandingZoneSubmitMoveAPIView(
    ZoneMoveViewMixin, LandingZoneSubmitBaseAPIView
):
    """
    API view for initiating LandingZone validation/moving via SODAR Taskflow.
    NOTE: Not tied to serializer or generic views, as the actual object will not
          be updated here.
    """

    def post(self, request, *args, **kwargs):
        """POST request for initiating landing zone validation/moving"""
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()

        # Validate/move or validate only
        if self.request.get_full_path() == reverse(
            'landingzones:api_submit_validate',
            kwargs={'landingzone': zone.sodar_uuid},
        ):
            validate_only = True
            action_obj = 'validate'
            action_msg = 'validation'

        else:
            validate_only = False
            action_obj = 'move'
            action_msg = 'moving'

        self._validate_zone_obj(zone, STATUS_ALLOW_UPDATE, action_obj)

        try:
            self._submit_validate_move(zone, validate_only)

        except Exception as ex:
            raise APIException(
                'Initiating landing zone {} failed: {}'.format(action_msg, ex)
            )

        return Response(
            {
                'message': 'Landing zone {} initiated'.format(action_msg),
                'sodar_uuid': str(zone.sodar_uuid),
            },
            status=status.HTTP_200_OK,
        )


# TODO: Remove once Metabolomics are using the new view
@fallback_to_auth_basic
class LandingZoneOldListAPIView(APIView):
    """View for returning a landing zone list based on its configuration"""

    # TODO: TBD: Do we also need this to work without a configuration param?

    def get(self, *args, **kwargs):
        from landingzones.plugins import get_zone_config_plugin

        irods_backend = get_backend_api('omics_irods', conn=False)

        if not irods_backend:
            return Response('iRODS backend not enabled', status=500)

        zone_config = self.kwargs['configuration']
        zones = LandingZone.objects.filter(configuration=zone_config)

        if zones.count() == 0:
            return Response('LandingZone not found', status=404)

        config_plugin = get_zone_config_plugin(zones.first())
        ret_data = {}

        for zone in zones:
            ret_data[str(zone.sodar_uuid)] = {
                'title': zone.title,
                'assay': zone.assay.get_name(),
                'user': zone.user.username,
                'status': zone.status,
                'configuration': zone.configuration,
                'irods_path': irods_backend.get_path(zone),
            }

            if config_plugin:
                for field in config_plugin.api_config_data:
                    if field in zone.config_data:
                        ret_data[str(zone.sodar_uuid)][
                            field
                        ] = zone.config_data[field]

        return Response(ret_data, status=200)
