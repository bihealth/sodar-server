"""REST API views for the irodsinfo app"""

import logging

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.versioning import AcceptHeaderVersioning
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, inline_serializer

# Projectroles dependency
from projectroles.plugins import get_backend_api

from irodsinfo.views import IrodsConfigMixin


logger = logging.getLogger(__name__)


# Local constants
IRODSINFO_API_MEDIA_TYPE = 'application/vnd.bihealth.sodar.irodsinfo+json'
IRODSINFO_API_ALLOWED_VERSIONS = ['1.0']
IRODSINFO_API_DEFAULT_VERSION = '1.0'


class IrodsinfoAPIVersioningMixin:
    """
    Irodsinfo API view versioning mixin for overriding media type and
    accepted versions.
    """

    class IrodsinfoAPIRenderer(JSONRenderer):
        media_type = IRODSINFO_API_MEDIA_TYPE

    class IrodsinfoAPIVersioning(AcceptHeaderVersioning):
        allowed_versions = IRODSINFO_API_ALLOWED_VERSIONS
        default_version = IRODSINFO_API_DEFAULT_VERSION

    renderer_classes = [IrodsinfoAPIRenderer]
    versioning_class = IrodsinfoAPIVersioning


@extend_schema(
    responses={
        '200': inline_serializer(
            'IrodsEnvRetrieveResponse',
            fields={'irods_environment': serializers.JSONField()},
        )
    }
)
class IrodsEnvRetrieveAPIView(
    IrodsConfigMixin, IrodsinfoAPIVersioningMixin, APIView
):
    """
    Retrieve iRODS environment file for the current user.

    **URL:** ``/irods/api/environment``

    **Methods:** ``GET``

    **Returns:**

    - ``irods_environment``: iRODS client environment (dict)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Get iRODS environment file"""
        try:
            irods_backend = get_backend_api('omics_irods')
            if not irods_backend:
                return Response(
                    {'detail': 'iRODS backend not enabled'}, status=404
                )
            env = self.get_irods_client_env(request.user, irods_backend)
            return Response({'irods_environment': env})
        except Exception as ex:
            logger.error('iRODS config retrieval failed: {}'.format(ex))
            return Response(
                {'detail': 'iRODS config retrieval failed'}, status=400
            )
