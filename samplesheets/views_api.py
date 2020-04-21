"""REST API views for the samplesheets app"""

from rest_framework import status
from rest_framework.exceptions import APIException, ParseError, ValidationError
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
from samplesheets.models import Investigation, ISATab
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.serializers import InvestigationSerializer
from samplesheets.views import (
    IrodsCollsCreateViewMixin,
    SampleSheetImportMixin,
    SITE_MODE_TARGET,
    REMOTE_LEVEL_READ_ROLES,
)


# API Views --------------------------------------------------------------------


class InvestigationRetrieveAPIView(
    SODARAPIGenericProjectMixin, RetrieveAPIView
):
    """
    Retrieve metadata of an investigation with its studies and assays.

    This view can be used to e.g. retrieve assay UUIDs for landing zone
    operations.

    **URL:** ``/samplesheets/api/investigation/retrieve/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:**

    - ``archive_name``: Original archive name if imported from a zip (string)
    - ``comments``: Investigation comments (JSON)
    - ``description``: Investigation description (string)
    - ``file_name``: Investigation file name (string)
    - ``identifier``: Locally unique investigation identifier (string)
    - ``irods_status``: Whether iRODS collections for the investigation have
      been created (boolean)
    - ``parser_version``: Version of altamISA used in importing (string)
    - ``project``: Project UUID (string)
    - ``sodar_uuid``: Investigation UUID (string)
    - ``studies``: Study and assay information (JSON, using study UUID as key)
    - ``title``: Investigation title (string)
    """

    lookup_field = 'project__sodar_uuid'
    permission_required = 'samplesheets.view_sheet'
    serializer_class = InvestigationSerializer


class IrodsCollsCreateAPIView(
    IrodsCollsCreateViewMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Create iRODS collections for a project.

    **URL:** ``/samplesheets/api/irods/collections/create/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Returns:**

    - ``path``: Full iRODS path to the root of created collections (string)
    """

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


class SampleSheetImportAPIView(
    SampleSheetImportMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Upload sample sheet as separate ISAtab TSV files or a zip archive. Will
    replace existing sheets if valid.

    The request should be in format of ``multipart/form-data``. Content type
    for each file must be provided.

    **URL:** ``/samplesheets/api/import/{Project.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        """Handle POST request for submitting"""
        sheet_io = SampleSheetIO()
        project = self.get_project()
        old_inv = Investigation.objects.filter(
            project=project, active=True
        ).first()
        action = 'replace' if old_inv else 'create'
        zip_file = None

        if len(request.FILES) == 0:
            raise ParseError('No files provided')

        # Zip file handling
        if len(request.FILES) == 1:
            file = request.FILES[next(iter(request.FILES))]

            try:
                zip_file = sheet_io.get_zip_file(file)

            except OSError as ex:
                raise ParseError('Failed to parse zip archive: {}'.format(ex))

            isa_data = sheet_io.get_isa_from_zip(zip_file)

        # Multi-file handling
        else:
            try:
                isa_data = sheet_io.get_isa_from_files(request.FILES.values())

            except Exception as ex:
                raise ParseError('Failed to parse TSV files: {}'.format(ex))

        # Handle import
        tl_event = self.create_timeline_event(
            project=project, replace=True if old_inv else False
        )

        try:
            investigation = sheet_io.import_isa(
                isa_data=isa_data,
                project=project,
                archive_name=zip_file.filename if zip_file else None,
                user=request.user,
                replace=True if old_inv else False,
                replace_uuid=old_inv.sodar_uuid if old_inv else None,
            )

        except Exception as ex:
            self.handle_import_exception(ex, tl_event, ui_mode=False)
            raise APIException(str(ex))

        if tl_event:
            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title,
            )

        # Handle replace
        if old_inv:
            try:
                investigation = self.handle_replace(
                    investigation=investigation,
                    old_inv=old_inv,
                    tl_event=tl_event,
                )
                ex_msg = None

            except Exception as ex:
                ex_msg = str(ex)

            if ex_msg or not investigation:
                raise ParseError(
                    'Sample sheet replacing failed: {}'.format(
                        ex_msg if ex_msg else 'See SODAR error log'
                    )
                )

        # Finalize import
        isa_version = (
            ISATab.objects.filter(investigation_uuid=investigation.sodar_uuid)
            .order_by('-date_created')
            .first()
        )
        self.finalize_import(
            investigation=investigation,
            action=action,
            tl_event=tl_event,
            isa_version=isa_version,
        )

        return Response(
            {
                'detail': 'Sample sheets {}d for project "{}" ({})'.format(
                    action, project.title, project.sodar_uuid
                )
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
