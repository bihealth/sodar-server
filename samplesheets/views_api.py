"""REST API views for the samplesheets app"""

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import RemoteSite
from projectroles.plugins import get_backend_api
from projectroles.views_api import (
    SODARAPIBaseProjectMixin,
    SODARAPIGenericProjectMixin,
)

from samplesheets.io import SampleSheetIO
from samplesheets.models import Investigation
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.serializers import InvestigationSerializer
from samplesheets.views import (
    IrodsCollsCreateViewMixin,
    SITE_MODE_TARGET,
    REMOTE_LEVEL_READ_ROLES,
)


# API Views --------------------------------------------------------------------


class InvestigationRetrieveAPIView(
    SODARAPIGenericProjectMixin, RetrieveAPIView
):
    """API view for retrieving information of an Investigation with its studies
    and assays"""

    lookup_field = 'project__sodar_uuid'
    permission_required = 'samplesheets.view_sheet'
    serializer_class = InvestigationSerializer


class IrodsCollsCreateAPIView(
    IrodsCollsCreateViewMixin, SODARAPIBaseProjectMixin, APIView
):
    """API view for iRODS collection creation for project"""

    http_method_names = ['post']
    permission_required = 'samplesheets.create_colls'

    def post(self, request, *args, **kwargs):
        """POST request for creating iRODS collections"""
        irods_backend = get_backend_api('omics_irods', conn=False)
        ex_msg = 'Creating iRODS collections failed: '
        investigation = Investigation.objects.filter(
            project__sodar_uuid=self.kwargs.get('project'), active=True
        ).first()

        if not investigation:
            raise ValidationError('{}Investigation not found'.format(ex_msg))

        # TODO: TBD: Also allow updating?
        if investigation.irods_status:
            raise ValidationError(
                '{}iRODS collections already created'.format(ex_msg)
            )

        try:
            self._create_colls(investigation)

        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))

        return Response(
            {
                'detail': 'iRODS collections created',
                'path': irods_backend.get_sample_path(investigation.project),
            },
            status=status.HTTP_200_OK,
        )


# TODO: Temporary HACK, should be replaced by proper API view
class RemoteSheetGetAPIView(APIView):
    """Temporary API view for retrieving the sample sheet as JSON by a target
    site, either as rendered tables or the original ISAtab"""

    permission_classes = (AllowAny,)  # We check the secret in get()/post()

    def get(self, request, **kwargs):
        secret = kwargs['secret']
        isa = request.GET.get('isa')

        try:
            target_site = RemoteSite.objects.get(
                mode=SITE_MODE_TARGET, secret=secret
            )

        except RemoteSite.DoesNotExist:
            return Response('Remote site not found, unauthorized', status=401)

        target_project = target_site.projects.filter(
            project_uuid=kwargs['project']
        ).first()

        if (
            not target_project
            or target_project.level != REMOTE_LEVEL_READ_ROLES
        ):
            return Response(
                'No project access for remote site, unauthorized', status=401
            )

        try:
            investigation = Investigation.objects.get(
                project=target_project.get_project(), active=True
            )

        except Investigation.DoesNotExist:
            return Response(
                'No ISA investigation found for project', status=404
            )

        # All OK so far, return data
        # Rendered tables
        if not isa or int(isa) != 1:
            ret = {'studies': {}}
            tb = SampleSheetTableBuilder()

            # Build study tables
            for study in investigation.studies.all():
                try:
                    tables = tb.build_study_tables(study)

                except Exception as ex:
                    return Response(str(ex), status=500)

                ret['studies'][str(study.sodar_uuid)] = tables

        # Original ISAtab
        else:
            sheet_io = SampleSheetIO()

            try:
                ret = sheet_io.export_isa(investigation)

            except Exception as ex:
                return Response(str(ex), status=500)

        return Response(ret, status=200)
