"""REST API views for the landingzones app"""

import logging
import sys

from django.conf import settings
from django.urls import reverse

from rest_framework import serializers, status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    CreateAPIView,
    UpdateAPIView,
)
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.versioning import AcceptHeaderVersioning
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, inline_serializer

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views_api import (
    SODARAPIBaseProjectMixin,
    SODARAPIGenericProjectMixin,
    SODARPageNumberPagination,
)

# Samplesheets dependency
from samplesheets.models import Investigation

from landingzones.constants import (
    STATUS_ALLOW_UPDATE,
    STATUS_FINISHED,
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
)
from landingzones.models import LandingZone
from landingzones.serializers import LandingZoneSerializer
from landingzones.views import (
    ZoneModifyPermissionMixin,
    ZoneModifyMixin,
    ZoneDeleteMixin,
    ZoneMoveMixin,
    ZONE_UPDATE_FIELDS,
    ZONE_VALIDATE_LIMIT_MSG,
)


logger = logging.getLogger(__name__)


# Local constants
LANDINGZONES_API_MEDIA_TYPE = 'application/vnd.bihealth.sodar.landingzones+json'
LANDINGZONES_API_ALLOWED_VERSIONS = ['1.0']
LANDINGZONES_API_DEFAULT_VERSION = '1.0'
ZONE_NO_COLLS_MSG = 'iRODS collections not created for project'


# Mixins and Base Views --------------------------------------------------------


class LandingzonesAPIVersioningMixin:
    """
    Landingzones API view versioning mixin for overriding media type and
    accepted versions.
    """

    class LandingzonesAPIRenderer(JSONRenderer):
        media_type = LANDINGZONES_API_MEDIA_TYPE

    class LandingzonesAPIVersioning(AcceptHeaderVersioning):
        allowed_versions = LANDINGZONES_API_ALLOWED_VERSIONS
        default_version = LANDINGZONES_API_DEFAULT_VERSION

    renderer_classes = [LandingzonesAPIRenderer]
    versioning_class = LandingzonesAPIVersioning


class ZoneSubmitBaseAPIView(
    ZoneModifyPermissionMixin,
    LandingzonesAPIVersioningMixin,
    SODARAPIBaseProjectMixin,
    APIView,
):
    """
    Base API view for initiating LandingZone operations via SODAR Taskflow.
    NOTE: Not tied to serializer or generic views, as the actual object will not
          be updated here.
    """

    http_method_names = ['post']
    serializer_class = None  # Need to explicitly set this None for spectacular

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


class ZoneListAPIView(
    LandingzonesAPIVersioningMixin, SODARAPIGenericProjectMixin, ListAPIView
):
    """
    List the landing zones in a project.

    If the user has rights to view all zones, every zone in the project will be
    listed. Otherwise only their own zones appear in the list. Also returns
    finished (meaning moved or deleted) zones if the "finished" parameter is
    set.

    Supports optional pagination for listing by providing the ``page`` query
    string. This will return results in the Django Rest Framework
    ``PageNumberPagination`` format.

    **URL:** ``/landingzones/api/list/{Project.sodar_uuid}?finished={integer}``

    **Methods:** ``GET``

    **Parameters:**

    - ``finished``: Include finished zones if 1 (integer)
    - ``page``: Page number for paginated results (int, optional)

    **Returns:** List of landing zone details (see ``ZoneRetrieveAPIView``)
    """

    pagination_class = SODARPageNumberPagination
    permission_required = 'landingzones.view_zone_own'
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
            'landingzones.view_zone_all', project
        ):
            return ret.filter(user=self.request.user)
        return ret


class ZoneRetrieveAPIView(
    LandingzonesAPIVersioningMixin, SODARAPIGenericProjectMixin, RetrieveAPIView
):
    """
    Retrieve the details of a landing zone.

    **URL:** ``/landingzones/api/retrieve/{LandingZone.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:**

    - ``assay``: Assay UUID (string)
    - ``config_data``: Data for special configuration (dict)
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
    - ``user``: UUID of user who owns the zone (string)
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
            return 'landingzones.view_zone_own'
        return 'landingzones.view_zone_all'


class ZoneCreateAPIView(
    ZoneModifyMixin,
    LandingzonesAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    CreateAPIView,
):
    """
    Create a landing zone.

    Returns ``503`` if an investigation for the project is not found or project
    iRODS collections have not been created.

    **URL:** ``/landingzones/api/create/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Parameters:**

    - ``assay``: Assay UUID (string)
    - ``config_data``: Data for special configuration (dict, optional)
    - ``configuration``: Special configuration (string, optional)
    - ``description``: Landing zone description (string, optional)
    - ``user_message``: Message displayed to users on successful moving of zone (string, optional)
    - ``title``: Suffix for the zone title (string, optional)
    - ``create_colls``: Create expected collections (boolean, optional)
    - ``restrict_colls``: Restrict access to created collections (boolean, optional)

    **Returns:** Landing zone details (see ``ZoneRetrieveAPIView``)
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'project'
    permission_required = 'landingzones.create_zone'
    serializer_class = LandingZoneSerializer

    @classmethod
    def _raise_503(cls, msg):
        ex = APIException(msg)
        ex.status_code = 503
        raise ex

    def post(self, request, *args, **kwargs):
        project = self.get_project()
        try:
            self.check_create_limit(project)
        except Exception as ex:
            raise PermissionDenied(ex)
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Override perform_create() to add timeline event and initiate taskflow.
        """
        ex_prefix = 'Creating landing zone failed: '
        # Check taskflow status
        if not get_backend_api('taskflow'):
            self._raise_503('{}Taskflow not enabled'.format(ex_prefix))

        # Ensure project has investigation with iRODS collections created
        project = self.get_project()
        investigation = Investigation.objects.filter(
            active=True, project=project
        ).first()
        # NOTE: Lack of investigation is already caught in serializer
        if not investigation.irods_status:
            self._raise_503('{}{}'.format(ex_prefix, ZONE_NO_COLLS_MSG))

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
            raise APIException('{}{}'.format(ex_prefix, ex))


class ZoneUpdateAPIView(
    ZoneModifyMixin,
    LandingzonesAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    UpdateAPIView,
):
    """
    Update a landing zone description and user message.

    **URL:** ``/landingzones/api/update/{LandingZone.sodar_uuid}``

    **Methods:** ``PATCH``, ``PUT``

    **Parameters:**

    - ``description``: Landing zone description (string, optional)
    - ``user_message``: Message displayed to users on successful moving of zone (string, optional)

    **Returns:** Landing zone details (see ``ZoneRetrieveAPIView``)
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'landingzone'
    permission_required = 'landingzones.update_zone_all'
    serializer_class = LandingZoneSerializer

    def get_serializer_context(self, *args, **kwargs):
        context = super().get_serializer_context(*args, **kwargs)
        if sys.argv[1:2] == ['generateschema']:
            return context
        landing_zone = self.get_object()
        context['assay'] = landing_zone.assay.sodar_uuid
        return context

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def _validate_update_fields(self, serializer):
        """
        Validate that only allowed fields are updated.
        """
        for field in serializer.validated_data.keys():
            if field not in ZONE_UPDATE_FIELDS:
                return False
        return True

    def perform_update(self, serializer):
        """
        Override perform_update() to add timeline event and initiate taskflow.
        """
        ex_msg = 'Updating landing zone failed: '
        # Check that only allowed fields are updated
        if not self._validate_update_fields(serializer):
            # Should raise 400 Bad Request
            raise ValidationError('{}Invalid update fields'.format(ex_msg))
        # If all is OK, go forward with object update and taskflow submission
        super().perform_update(serializer)
        try:
            self.update_zone(zone=serializer.instance, request=self.request)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))


@extend_schema(
    responses={
        '200': inline_serializer(
            'ZoneSubmitDeleteResponse',
            fields={
                'detail': serializers.CharField(),
                'sodar_uuid': serializers.UUIDField(),
            },
        ),
    }
)
class ZoneSubmitDeleteAPIView(ZoneDeleteMixin, ZoneSubmitBaseAPIView):
    """
    Initiate landing zone deletion.

    Initiates an asynchronous operation. The zone status can be queried using
    ``ZoneRetrieveAPIView`` with the returned ``sodar_uuid``.

    **URL:** ``/landingzones/api/submit/delete/{LandingZone.sodar_uuid}``

    **Methods:** ``POST``
    """

    zone_action = 'delete'

    def post(self, request, *args, **kwargs):
        """POST request for initiating landing zone deletion"""
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()
        self._validate_zone_obj(zone, STATUS_ALLOW_UPDATE, 'delete')
        try:
            self.submit_delete(zone)
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


@extend_schema(
    responses={
        '200': inline_serializer(
            'ZoneSubmitMoveResponse',
            fields={
                'detail': serializers.CharField(),
                'sodar_uuid': serializers.UUIDField(),
            },
        ),
    }
)
class ZoneSubmitMoveAPIView(ZoneMoveMixin, ZoneSubmitBaseAPIView):
    """
    Initiate landing zone validation and/or moving.

    Initiates an asynchronous operation. The zone status can be queried using
    ``ZoneRetrieveAPIView`` with the returned ``sodar_uuid``.

    For validating data without moving it to the sample repository, this view
    should be called with ``submit/validate``.

    Returns ``503`` if the project is currently locked by another operation or
    if the concurrent validation limit for the project has been reached.

    **URL for Validation:** ``/landingzones/api/submit/validate/{LandingZone.sodar_uuid}``

    **URL for Moving:** ``/landingzones/api/submit/move/{LandingZone.sodar_uuid}``

    **Methods:** ``POST``
    """

    zone_action = 'move'

    def post(self, request, *args, **kwargs):
        """POST request for initiating landing zone validation/moving"""
        taskflow = get_backend_api('taskflow')
        zone = LandingZone.objects.filter(
            sodar_uuid=self.kwargs['landingzone']
        ).first()

        # Check limit
        valid_count = LandingZone.objects.filter(
            project=zone.project,
            status__in=[ZONE_STATUS_PREPARING, ZONE_STATUS_VALIDATING],
        ).count()
        valid_limit = settings.LANDINGZONES_ZONE_VALIDATE_LIMIT or 1
        if valid_count >= valid_limit:
            ex = APIException(ZONE_VALIDATE_LIMIT_MSG)
            ex.status_code = 503
            raise ex

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
            self.submit_validate_move(zone, validate_only)
        except Exception as ex:
            ex_msg = 'Initiating landing zone {} failed: '.format(action_msg)
            if taskflow:
                taskflow.raise_submit_api_exception(ex_msg, ex)
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'Landing zone {} initiated'.format(action_msg),
                'sodar_uuid': str(zone.sodar_uuid),
            },
            status=status.HTTP_200_OK,
        )
