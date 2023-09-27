"""REST API views for the irodsinfo app"""

import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.plugins import get_backend_api

from irodsinfo.views import IrodsConfigMixin


logger = logging.getLogger(__name__)


class IrodsEnvRetrieveAPIView(IrodsConfigMixin, APIView):
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
