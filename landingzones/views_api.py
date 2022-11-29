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
from samplesheets.models import Investigation

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views_api import (
    SODARAPIBaseProjectMixin,
    SODARAPIGenericProjectMixin,
)

from landingzones.models import (
    LandingZone,
    STATUS_ALLOW_UPDATE,
    STATUS_FINISHED,
)
from landingzones.serializers import LandingZoneSerializer
from landingzones.views import (
    ZoneUpdateRequiredPermissionMixin,
    ZoneCreateMixin,
    ZoneDeleteMixin,
    ZoneMoveMixin,
)

# Local helper for authenticating with auth basic
from sodar.users.auth import fallback_to_auth_basic


# Get logger
logger = logging.getLogger(__name__)


# Mixins and Base Views --------------------------------------------------------


class LandingZoneSubmitBaseAPIView(
    ZoneUpdateRequiredPermissionMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Base API view for initiating LandingZone operations via SODAR Taskflow.
    NOTE: Not tied to serializer or generic views, as the actual object will not
          be updated here.
    """

    http_method_names = ['post']

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


# API Views --------------------------------------------------------------------


class LandingZoneListAPIView(SODARAPIGenericProjectMixin, ListAPIView):
    """
    List the landing zones in a project.

    If the user has rights to view all zones, every zone in the project will be
    listed. Otherwise only their own zones appear in the list. Also returns
    finished (meaning moved or deleted) zones if the "finished" parameter is
    set.

    **URL:** ``/landingzones/api/list/{Project.sodar_uuid}?finished={integer}``

    **Methods:** ``GET``

    **Parameters:**

    - ``finished``: Include finished zones if 1 (integer)

    **Returns:** List of landing zone details (see ``LandingZoneRetrieveAPIView``)
    """

    permission_required = 'landingzones.view_zones_own'
    serializer_class = LandingZoneSerializer

    def get_queryset(self):
        """
        Override get_queryset() to return zones based on user perms and
        parameters.
        """
        project = self.get_project()
        include_finished = int(self.request.query_params.get('finished', 0))
        ret = LandingZone.objects.filter(project=project)
        if include_finished != 1:
            ret = ret.exclude(status__in=STATUS_FINISHED)
        if not self.request.user.has_perm(
            'landingzones.view_zones_all', project
        ):
            return ret.filter(user=self.request.user)
        return ret


class LandingZoneRetrieveAPIView(SODARAPIGenericProjectMixin, RetrieveAPIView):
    """
    Retrieve the details of a landing zone.

    **URL:** ``/landingzones/api/retrieve/{LandingZone.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:**

    - ``assay``: Assay UUID (string)
    - ``config_data``: Data for special configuration (JSON)
    - ``configuration``: Special configuration name (string)
    - ``date_modified``: Last modification date of the zone (string)
    - ``description``: Landing zone description (string)
    - ``user_message``: Message displayed to users on successful moving of zone (string)
    - ``irods_path``: Full iRODS path to the landing zone (string)
    - ``project``: Project UUID (string)
    - ``sodar_uuid``: Landing zone UUID (string)
    - ``status``: Current status of the landing zone (string)
    - ``status_info``: Detailed description of the landing zone status (string)
    - ``status_locked``: Whether write access to the zone is currently locked (boolean)
    - ``title``: Full title of the created landing zone (string)
    - ``user``: User who owns the zone (JSON)
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'landingzone'
    serializer_class = LandingZoneSerializer

    def get_permission_required(self):
        """
        Override get_permission_required() to check perms depending on owner.
        """
        obj = self.get_object()
        if not obj:
            return False
        if obj.user == self.request.user:
            return 'landingzones.update_zones_own'
        return 'landingzones.update_zones_all'


class LandingZoneCreateAPIView(
    ZoneCreateMixin, SODARAPIGenericProjectMixin, CreateAPIView
):
    """
    Create a landing zone.

    **URL:** ``/landingzones/api/create/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Parameters:**

    - ``assay``: Assay UUID (string)
    - ``config_data``: Data for special configuration (JSON, optional)
    - ``configuration``: Special configuration (string, optional)
    - ``description``: Landing zone description (string, optional)
    - ``user_message``: Message displayed to users on successful moving of zone (string, optional)
    - ``title``: Suffix for the zone title (string, optional)
    - ``create_colls``: Create expected collections (boolean, optional)
    - ``restrict_colls``: Restrict access to created collections (boolean, optional)

    **Returns:** Landing zone details (see ``LandingZoneRetrieveAPIView``)
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'project'
    permission_required = 'landingzones.add_zones'
    serializer_class = LandingZoneSerializer

    def perform_create(self, serializer):
        """
        Override perform_create() to add timeline event and initiate taskflow.
        """
        ex_msg = 'Creating landing zone failed: '

        # Check taskflow status
        if not get_backend_api('taskflow'):
            raise APIException('{}Taskflow not enabled'.format(ex_msg))

        # Ensure project has investigation with iRODS collections created
        project = self.get_project()
        investigation = Investigation.objects.filter(
            active=True, project=project
        ).first()

        if not investigation:
            raise ValidationError(
                '{}No investigation found for project'.format(ex_msg)
            )
        if not investigation.irods_status:
            raise ValidationError(
                '{}iRODS collections not created for project'.format(ex_msg)
            )

        # If all is OK, go forward with object creation and taskflow submission
        create_colls = serializer.validated_data.pop('create_colls')
        restrict_colls = serializer.validated_data.pop('restrict_colls')
        super().perform_create(serializer)
        try:
            self.submit_create(
                zone=serializer.instance,
                create_colls=create_colls,
                restrict_colls=restrict_colls,
                request=self.request,
            )
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))


class LandingZoneSubmitDeleteAPIView(
    ZoneDeleteMixin, LandingZoneSubmitBaseAPIView
):
    """
    Initiate landing zone deletion.

    Initiates an asynchronous operation. The zone status can be queried using
    ``LandingZoneRetrieveAPIView`` with the returned ``sodar_uuid``.

    **URL:** ``/landingzones/api/submit/delete/{LandingZone.sodar_uuid}``

    **Methods:** ``POST``
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
                'detail': 'Landing zone deletion initiated',
                'sodar_uuid': str(zone.sodar_uuid),
            },
            status=status.HTTP_200_OK,
        )


class LandingZoneSubmitMoveAPIView(ZoneMoveMixin, LandingZoneSubmitBaseAPIView):
    """
    Initiate landing zone validation and/or moving.

    Initiates an asynchronous operation. The zone status can be queried using
    ``LandingZoneRetrieveAPIView`` with the returned ``sodar_uuid``.

    For validating data without moving it to the sample repository, this view
    should be called with ``submit/validate``.

    **URL for Validation:** ``/landingzones/api/submit/validate/{LandingZone.sodar_uuid}``

    **URL for Moving:** ``/landingzones/api/submit/move/{LandingZone.sodar_uuid}``

    **Methods:** ``POST``
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
                'detail': 'Landing zone {} initiated'.format(action_msg),
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

        irods_backend = get_backend_api('omics_irods')
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
