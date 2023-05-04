"""REST API views for the samplesheets app"""

import logging
import re

from irods.exception import CAT_NO_ROWS_FOUND
from irods.models import DataObject

from django.conf import settings
from django.urls import reverse

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ParseError,
    ValidationError,
    NotFound,
)
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import RemoteSite
from projectroles.plugins import get_backend_api
from projectroles.views_api import (
    SODARAPIBaseMixin,
    SODARAPIBaseProjectMixin,
    SODARAPIGenericProjectMixin,
)

from samplesheets.io import SampleSheetIO
from samplesheets.models import Investigation, ISATab, IrodsDataRequest
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.serializers import (
    InvestigationSerializer,
)
from samplesheets.views import (
    IrodsCollsCreateViewMixin,
    IrodsRequestModifyMixin,
    SheetImportMixin,
    SheetISAExportMixin,
    SITE_MODE_TARGET,
    REMOTE_LEVEL_READ_ROLES,
)


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
table_builder = SampleSheetTableBuilder()


MD5_RE = re.compile(r'([a-fA-F\d]{32})')
APP_NAME = 'samplesheets'
IRODS_ERROR_MSG = 'Exception querying iRODS objects:'


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
        irods_backend = get_backend_api('omics_irods')
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
            self.create_colls(investigation, request)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS collections created',
                'path': irods_backend.get_sample_path(investigation.project),
            },
            status=status.HTTP_200_OK,
        )


class IrodsDataRequestListAPIView(
    IrodsRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    List iRODS data requests for a project.

    **URL:** ``/samplesheets/api/irods/requests/{Project.sodar_uuid}``

    **Methods:** ``GET``
    """

    http_method_names = ['get']
    permission_required = 'samplesheets.edit_sheet'

    def get(self, request, *args, **kwargs):
        """GET request for listing iRODS data requests"""
        irods_backend = get_backend_api('omics_irods')
        ex_msg = 'Listing iRODS data requests failed: '
        investigation = Investigation.objects.filter(
            project__sodar_uuid=self.kwargs.get('project'), active=True
        ).first()
        if not investigation:
            raise ValidationError('{}Investigation not found'.format(ex_msg))
        try:
            requests = irods_backend.get_data_requests(investigation.project)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS data requests listed',
                'requests': requests,
            },
            status=status.HTTP_200_OK,
        )


class IrodsRequestCreateAPIView(
    IrodsRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Create an iRODS data request for a project.

    **URL:** ``/samplesheets/api/irods/request/create/{Project.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        """POST request for creating an iRODS data request"""
        ex_msg = 'Creating iRODS data request failed: '
        investigation = Investigation.objects.filter(
            project__sodar_uuid=self.kwargs.get('project'), active=True
        ).first()
        if not investigation:
            raise ValidationError('{}Investigation not found'.format(ex_msg))
        try:
            self.create_request(investigation, request)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS data request created',
                'request': request,
            },
            status=status.HTTP_200_OK,
        )


class IrodsRequestUpdateAPIView(
    IrodsRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Update an iRODS data request for a project.

    **URL:** ``/samplesheets/api/irods/request/update/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        """POST request for updating an iRODS data request"""
        ex_msg = 'Updating iRODS data request failed: '
        request = IrodsDataRequest.objects.filter(
            sodar_uuid=self.kwargs.get('irodsdatarequest')
        ).first()
        if not request:
            raise ValidationError('{}Request not found'.format(ex_msg))
        try:
            self.update_request(request, request)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS data request updated',
                'request': request,
            },
            status=status.HTTP_200_OK,
        )


class IrodsRequestDeleteAPIView(
    IrodsRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Delete an iRODS data request for a project.

    **URL:** ``/samplesheets/api/irods/request/delete/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``DELETE``
    """

    http_method_names = ['delete']
    permission_required = 'samplesheets.delete_sheet'

    def delete(self, request, *args, **kwargs):
        """DELETE request for deleting an iRODS data request"""
        ex_msg = 'Deleting iRODS data request failed: '
        request = IrodsDataRequest.objects.filter(
            sodar_uuid=self.kwargs.get('irodsdatarequest')
        ).first()
        if not request:
            raise ValidationError('{}Request not found'.format(ex_msg))
        try:
            self.delete_request(request, request)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS data request deleted',
            },
            status=status.HTTP_200_OK,
        )


class IrodsRequestAcceptAPIView(
    IrodsRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Accept an iRODS data request for a project.

    **URL:** ``/samplesheets/api/irods/request/accept/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.manage_sheet'

    def post(self, request, *args, **kwargs):
        """POST request for accepting an iRODS data request"""
        ex_msg = 'Accepting iRODS data request failed: '
        request = IrodsDataRequest.objects.filter(
            sodar_uuid=self.kwargs.get('irodsdatarequest')
        ).first()
        if not request:
            raise ValidationError('{}Request not found'.format(ex_msg))
        try:
            self.accept_request(request, request)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS data request accepted',
                'paths': request.paths,
            },
            status=status.HTTP_200_OK,
        )


class IrodsRequestRejectAPIView(
    IrodsRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Reject an iRODS data request for a project.

    **URL:** ``/samplesheets/api/irods/request/reject/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.manage_sheet'

    def post(self, request, *args, **kwargs):
        """POST request for rejecting an iRODS data request"""
        ex_msg = 'Rejecting iRODS data request failed: '
        request = IrodsDataRequest.objects.filter(
            sodar_uuid=self.kwargs.get('irodsdatarequest')
        ).first()
        if not request:
            raise ValidationError('{}Request not found'.format(ex_msg))
        try:
            self.reject_request(request, request)
        except Exception as ex:
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS data request rejected',
            },
            status=status.HTTP_200_OK,
        )


class SheetISAExportAPIView(
    SheetISAExportMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Export sample sheets as ISA-Tab TSV files, either packed in a zip archive or
    wrapped in a JSON structure.

    **URL for zip export:** ``/samplesheets/api/export/zip/{Project.sodar_uuid}``

    **URL for JSON export:** ``/samplesheets/api/export/json/{Project.sodar_uuid}``

    **Methods:** ``GET``
    """

    http_method_names = ['get']
    permission_required = 'samplesheets.export_sheet'

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        if not investigation:
            raise NotFound()

        export_format = 'json'
        if self.request.get_full_path() == reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': project.sodar_uuid},
        ):
            export_format = 'zip'

        try:
            return self.get_isa_export(project, request, export_format)
        except Exception as ex:
            raise APIException('Unable to export ISA-Tab: {}'.format(ex))


class SheetImportAPIView(SheetImportMixin, SODARAPIBaseProjectMixin, APIView):
    """
    Upload sample sheet as separate ISA-Tab TSV files or a zip archive. Will
    replace existing sheets if valid.

    The request should be in format of ``multipart/form-data``. Content type
    for each file must be provided.

    **URL:** ``/samplesheets/api/import/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Return:**

    - ``detail``: Detail of project success (string)
    - ``sodar_warnings``: SODAR import issue warnings (list of srings, optional)
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        """Handle POST request for submitting"""
        project = self.get_project()
        if app_settings.get(APP_NAME, 'sheet_sync_enable', project):
            raise ValidationError(
                'Sheet synchronization enabled in project: import not allowed'
            )
        sheet_io = SampleSheetIO()
        old_inv = Investigation.objects.filter(
            project=project, active=True
        ).first()
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
        action = 'replace' if old_inv else 'create'
        tl_event = self.create_timeline_event(project=project, action=action)
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

        if tl_event:
            tl_event.add_object(
                obj=investigation,
                label='investigation',
                name=investigation.title,
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
        ret_data = {
            'detail': 'Sample sheets {}d for project {}'.format(
                action, project.get_log_title()
            )
        }
        no_plugin_assays = self.get_assays_without_plugins(investigation)
        if no_plugin_assays:
            ret_data['sodar_warnings'] = [
                self.get_assay_plugin_warning(a) for a in no_plugin_assays
            ]
        return Response(ret_data, status=status.HTTP_200_OK)


class SampleDataFileExistsAPIView(SODARAPIBaseMixin, APIView):
    """
    Return status of data object existing in SODAR iRODS by MD5 checksum.
    Includes all projects in search regardless of user permissions.

    **URL:** ``/samplesheets/api/file/exists``

    **Methods:** ``GET``

    **Parameters:**

    - ``checksum``: MD5 checksum (string)

    **Returns:**

    - ``detail``: String
    - ``status``: Boolean
    """

    http_method_names = ['get']
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        if not settings.ENABLE_IRODS:
            raise APIException('iRODS not enabled')
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            raise APIException('iRODS backend not enabled')
        c = request.query_params.get('checksum')
        if not c or not re.match(MD5_RE, c):
            raise ParseError('Invalid MD5 checksum: "{}"'.format(c))

        ret = {'detail': 'File does not exist', 'status': False}
        sql = (
            'SELECT DISTINCT ON (data_id) data_name '
            'FROM r_data_main JOIN r_coll_main USING (coll_id) '
            'WHERE (coll_name LIKE \'%/{coll}\' '
            'OR coll_name LIKE \'%/{coll}/%\') '
            'AND r_data_main.data_checksum = \'{sum}\''.format(
                coll=settings.IRODS_SAMPLE_COLL, sum=c
            )
        )
        # print('QUERY: {}'.format(sql))  # DEBUG
        columns = [DataObject.name]
        try:
            with irods_backend.get_session() as irods:
                query = irods_backend.get_query(irods, sql, columns)
                try:
                    results = query.get_results()
                    if sum(1 for _ in results) > 0:
                        ret['detail'] = 'File exists'
                        ret['status'] = True
                except CAT_NO_ROWS_FOUND:
                    pass  # No results, this is OK
                except Exception as ex:
                    logger.error(
                        '{} iRODS query exception: {}'.format(
                            self.__class__.__name__, ex
                        )
                    )
                    raise APIException(
                        'iRODS query exception, please contact an admin if '
                        'issue persists'
                    )
                finally:
                    query.remove()
        except Exception as ex:
            return Response(
                {'detail': 'Unable to connect to iRODS: {}'.format(ex)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(ret, status=status.HTTP_200_OK)


# TODO: Temporary HACK, should be replaced by proper API view
class RemoteSheetGetAPIView(APIView):
    """
    Temporary API view for retrieving the sample sheet as JSON by a target
    site, either as rendered tables or the original ISA-Tab.
    """

    permission_classes = (AllowAny,)  # We check the secret in get()/post()

    def get(self, request, **kwargs):
        secret = kwargs['secret']
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
        isa = request.GET.get('isa')
        # Rendered tables
        if not isa or int(isa) != 1:
            ret = {'studies': {}}
            # Get/build study tables
            for study in investigation.studies.all():
                try:
                    tables = table_builder.get_study_tables(study)
                except Exception as ex:
                    return Response(str(ex), status=500)
                ret['studies'][str(study.sodar_uuid)] = tables
        # Original ISA-Tab
        else:
            sheet_io = SampleSheetIO()
            try:
                ret = sheet_io.export_isa(investigation)
            except Exception as ex:
                return Response(str(ex), status=500)
        return Response(ret, status=200)


class ProjectIrodsFileListAPIView(SODARAPIBaseProjectMixin, APIView):
    """
    Return a list of files in the project's sample data repository.

    **URL:** ``/samplesheets/api/file/list/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:**

    - ``irods_data``: List of iRODS data objects
    """

    http_method_names = ['get']
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        if not settings.ENABLE_IRODS:
            raise APIException('iRODS not enabled')
        irods_backend = get_backend_api('omics_irods')
        project = self.get_project()
        path = irods_backend.get_sample_path(project)
        try:
            with irods_backend.get_session() as irods:
                irods_data = irods_backend.get_objects(irods, path)
        except Exception as ex:
            return Response(
                {'detail': '{} {}'.format(IRODS_ERROR_MSG, ex)},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(irods_data, status=status.HTTP_200_OK)
