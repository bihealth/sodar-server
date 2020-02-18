"""REST API views for the samplesheets app"""

from django.core.exceptions import ImproperlyConfigured

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import BasePermission, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.models import RemoteSite
from projectroles.plugins import get_backend_api
from projectroles.views import (
    ProjectAccessMixin,
    SODARAPIRenderer,
    SODARAPIVersioning,
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


# Base Views and Mixins --------------------------------------------------------


# TODO: Move to sodar_core
class SODARAPIProjectPermission(ProjectAccessMixin, BasePermission):
    """
    Mixin for providing a basic project permission checking for API views
    with a single permission_required attribute. Also works with Knox token
    based views.

    This must be used in the permission_classes attribute in order for token
    authentication to work.

    NOTE: Requires implementing either permission_required or
          get_permission_required() in the view
    """

    def has_permission(self, request, view):
        """
        Override has_permission() for checking auth and  project permission
        """
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(view, 'permission_required') and (
            not hasattr(view, 'get_permission_required')
            or not callable(getattr(view, 'get_permission_required', None))
        ):
            raise ImproperlyConfigured(
                '{0} is missing the permission_required attribute. '
                'Define {0}.permission_required, or override '
                '{0}.get_permission_required().'.format(view.__class__.__name__)
            )

        elif hasattr(view, 'permission_required'):
            perm = view.permission_required

        else:
            perm = view.get_permission_required()

        # This may return an iterable, but we are only interested in one perm
        if isinstance(perm, (list, tuple)) and len(perm) > 0:
            # TODO: TBD: Raise exception / log warning if given multiple perms?
            perm = perm[0]

        return request.user.has_perm(
            perm, self.get_project(request=request, kwargs=view.kwargs)
        )


# TODO: Move this to sodar_core
class SODARAPIBaseMixin:
    """Base SODAR API mixin to be used by external SODAR Core based sites"""

    renderer_classes = [SODARAPIRenderer]
    versioning_class = SODARAPIVersioning


# TODO: Move this to sodar_core
class SODARAPIBaseProjectMixin(SODARAPIBaseMixin):
    """
    API view mixin for the base DRF APIView class with project permission
    checking, but without serializers and other generic view functionality.
    """

    permission_classes = [SODARAPIProjectPermission]


# TODO: Move this to sodar_core
# TODO: Combine with SODARAPIBaseProjectMixin? Is this needed on its own?
class SODARAPIGenericViewProjectMixin(
    ProjectAccessMixin, SODARAPIBaseProjectMixin
):
    """
    API view mixin for generic DRF API views with serializers, SODAR
    project context and permission checkin.

    NOTE: Unless overriding permission_classes with their own implementation,
          the user MUST supply a permission_required attribute.

    NOTE: Replace lookup_url_kwarg with your view's url kwarg (SODAR project
          compatible model name in lowercase)

    NOTE: If the lookup is done via the project object, change lookup_field into
          "sodar_uuid"
    """

    lookup_field = 'project__sodar_uuid'
    lookup_url_kwarg = 'project'  # Replace with relevant model

    def get_serializer_context(self, *args, **kwargs):
        result = super().get_serializer_context(*args, **kwargs)
        result['project'] = self.get_project(request=result['request'])
        return result

    def get_queryset(self):
        return self.__class__.serializer_class.Meta.model.objects.filter(
            project=self.get_project()
        )


class SheetSubmitBaseAPIView(SODARAPIBaseProjectMixin, APIView):
    """
    Base API view for initiating sample sheet operations via SODAR Taskflow.
    NOTE: Not tied to serializer or generic views, as the actual object will not
          be updated here.
    """

    http_method_names = ['post']


# API Views --------------------------------------------------------------------


class InvestigationRetrieveAPIView(
    SODARAPIGenericViewProjectMixin, RetrieveAPIView
):
    """API view for retrieving information of an Investigation with its studies
    and assays"""

    permission_required = 'samplesheets.view_sheet'
    serializer_class = InvestigationSerializer


class IrodsCollsCreateAPIView(
    IrodsCollsCreateViewMixin, SheetSubmitBaseAPIView
):
    """API view for iRODS collection creation for project"""

    permission_required = 'samplesheets.create_dirs'

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
