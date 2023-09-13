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
    PermissionDenied,
)
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
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
from projectroles.utils import build_secret

from samplesheets.io import SampleSheetIO
from samplesheets.models import (
    Investigation,
    ISATab,
    IrodsAccessTicket,
    IrodsDataRequest,
    IRODS_REQUEST_STATUS_ACTIVE,
    IRODS_REQUEST_STATUS_FAILED,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.serializers import (
    InvestigationSerializer,
    IrodsAccessTicketSerializer,
    IrodsDataRequestSerializer,
)
from samplesheets.views import (
    IrodsAccessTicketModifyMixin,
    IrodsCollsCreateViewMixin,
    IrodsDataRequestModifyMixin,
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
IRODS_QUERY_ERROR_MSG = 'Exception querying iRODS objects'
IRODS_REQUEST_EX_MSG = 'iRODS data request failed'
IRODS_TICKET_EX_MSG = 'iRODS access ticket failed'
IRODS_TICKET_NO_UPDATE_FIELDS_MSG = 'No fields to update'


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
    - ``comments``: Investigation comments (dict)
    - ``description``: Investigation description (string)
    - ``file_name``: Investigation file name (string)
    - ``identifier``: Locally unique investigation identifier (string)
    - ``irods_status``: Whether iRODS collections for the investigation have
      been created (boolean)
    - ``parser_version``: Version of altamISA used in importing (string)
    - ``project``: Project UUID (string)
    - ``sodar_uuid``: Investigation UUID (string)
    - ``studies``: Study and assay information (dict, using study UUID as key)
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

    **Returns:**

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


class IrodsAccessTicketListAPIView(SODARAPIBaseProjectMixin, ListAPIView):
    """
    List iRODS access tickets for a project.

    **URL:** ``/samplesheets/api/irods/ticket/list/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Query parameters:**

    - ``active`` (boolean, default ``0``)
    """

    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsAccessTicketSerializer

    def get_queryset(self):
        project = self.get_project()
        tickets = IrodsAccessTicket.objects.filter(
            study__investigation__project=project
        )
        active = self.request.query_params.get('active', '0')
        active = bool(int(active))
        if active:
            tickets = [t for t in tickets if t.is_active()]
        return tickets


class IrodsAccessTicketRetrieveAPIView(
    SODARAPIGenericProjectMixin, RetrieveAPIView
):
    """
    Retrieve an iRODS access ticket for a project.

    **URL:** ``/samplesheets/api/irods/ticket/retrieve/{IrodsAccessTicket.sodar_uuid}``

    **Methods:** ``GET``
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'irodsaccessticket'
    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsAccessTicketSerializer
    queryset_project_field = 'study__investigation__project'


class IrodsAccessTicketCreateAPIView(
    IrodsAccessTicketModifyMixin, SODARAPIGenericProjectMixin, CreateAPIView
):
    """
    Create an iRODS access ticket for a project.

    **URL:** ``/samplesheets/api/irods/ticket/create/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Parameters:**

    - ``path``: iRODS path
    - ``label``: Label (string, optional)
    - ``date_expires``: Expiration date (YYYY-MM-DDThh:mm:ssZ, optional)
    """

    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsAccessTicketSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.get_project()
        context['user'] = self.request.user
        return context

    def perform_create(self, serializer):
        """Override perform_create() to create IrodsAccessTicket"""
        irods_backend = get_backend_api('omics_irods')
        try:
            with irods_backend.get_session() as irods:
                ticket = irods_backend.issue_ticket(
                    irods,
                    'read',
                    serializer.validated_data.get('path'),
                    ticket_str=build_secret(16),
                    expiry_date=serializer.validated_data.get('date_expires'),
                )
        except Exception as ex:
            raise ValidationError(
                '{} {}'.format('Creating ' + IRODS_TICKET_EX_MSG + ':', ex)
            )

        serializer.validated_data['ticket'] = ticket.ticket
        serializer.save()
        # Create timeline event
        self.create_timeline_event(serializer.instance, 'create')
        # Add app alerts to owners/delegates
        self.create_app_alerts(serializer.instance, 'create', self.request.user)


class IrodsAccessTicketUpdateAPIView(
    IrodsAccessTicketModifyMixin, SODARAPIGenericProjectMixin, UpdateAPIView
):
    """
    Update an iRODS access ticket for a project.

    **URL:** ``/samplesheets/api/irods/ticket/update/{IrodsAccessTicket.sodar_uuid}``

    **Methods:** ``PUT``, ``PATCH``

    **Parameters:**

    - ``label``: Label (string)
    - ``date_expires``: Expiration date (YYYY-MM-DD)
    """

    lookup_url_kwarg = 'irodsaccessticket'
    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsAccessTicketSerializer
    queryset_project_field = 'study__investigation__project'

    def perform_update(self, serializer):
        """Override perform_update() to update IrodsAccessTicket"""
        if not set(serializer.initial_data) & {'label', 'date_expires'}:
            raise ValidationError(IRODS_TICKET_NO_UPDATE_FIELDS_MSG)
        serializer.save()
        # Create timeline event
        self.create_timeline_event(serializer.instance, 'update')
        # Add app alerts to owners/delegates
        self.create_app_alerts(serializer.instance, 'update', self.request.user)


class IrodsAccessTicketDestroyAPIView(
    IrodsAccessTicketModifyMixin, SODARAPIGenericProjectMixin, DestroyAPIView
):
    """
    Delete an iRODS access ticket for a project.

    **URL:** ``/samplesheets/api/irods/ticket/delete/{IrodsAccessTicket.sodar_uuid}``

    **Methods:** ``DELETE``
    """

    lookup_field = 'sodar_uuid'
    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsAccessTicketSerializer
    queryset_project_field = 'study__investigation__project'

    def perform_destroy(self, instance):
        """Override perform_destroy() to delete IrodsAccessTicket"""
        irods_backend = get_backend_api('omics_irods')
        try:
            with irods_backend.get_session() as irods:
                irods_backend.delete_ticket(irods, instance.ticket)
        except Exception as ex:
            raise ValidationError(
                '{} {}'.format('Deleting ' + IRODS_TICKET_EX_MSG + ':', ex)
            )
        instance.delete()
        # Create timeline event
        self.create_timeline_event(instance, 'delete')
        # Add app alerts to owners/delegates
        self.create_app_alerts(instance, 'delete', self.request.user)


class IrodsDataRequestRetrieveAPIView(
    SODARAPIGenericProjectMixin, RetrieveAPIView
):
    """
    Retrieve a iRODS data request.

    **URL:** ``/samplesheets/api/irods/request/retrieve/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:**

    - ``project``: Project UUID (string)
    - ``action``: Request action (string)
    - ``path``: iRODS path to object or collection (string)
    - ``target_path``: Target path (string, currently unused)
    - ``user``: User initiating request (dict)
    - ``status``: Request status (string)
    - ``status_info``: Request status info (string)
    - ``description``: Request description (string)
    - ``date_created``: Request creation date (datetime)
    - ``sodar_uuid``: Request UUID (string)
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'irodsdatarequest'
    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsDataRequestSerializer


class IrodsDataRequestListAPIView(SODARAPIBaseProjectMixin, ListAPIView):
    """
    List the iRODS data requests for a project.

    If the requesting user is an owner, delegate or superuser, the view lists
    all requests with the status of ACTIVE or FAILED. If called as a
    contributor, returns the user's own requests regardless of the state.

    **URL:** ``/samplesheets/api/irods/requests/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:** List of iRODS data requests (list of dicts)
    """

    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsDataRequestSerializer

    def get_queryset(self):
        project = self.get_project()
        requests = IrodsDataRequest.objects.filter(project=project)
        # For superusers, owners and delegates, display requests from all users
        if self.request.user.is_superuser or project.is_owner_or_delegate(
            self.request.user
        ):
            return requests.filter(
                status__in=[
                    IRODS_REQUEST_STATUS_ACTIVE,
                    IRODS_REQUEST_STATUS_FAILED,
                ]
            )
        return requests.filter(user=self.request.user)


class IrodsDataRequestCreateAPIView(
    IrodsDataRequestModifyMixin, SODARAPIGenericProjectMixin, CreateAPIView
):
    """
    Create an iRODS delete request for a project.

    The request must point to a collection or data object within the sample data
    repository of the project. The user making the request must have the role of
    contributor or above in the project.

    **URL:** ``/samplesheets/api/irods/request/create/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Parameters:**

    - ``path``: iRODS path to object or collection (string)
    - ``description``: Request description (string, optional)
    """

    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsDataRequestSerializer

    def perform_create(self, serializer):
        serializer.save()
        # Create timeline event
        self.add_tl_create(serializer.instance)
        # Add app alerts to owners/delegates
        self.add_alerts_create(serializer.instance.project)


class IrodsDataRequestUpdateAPIView(
    IrodsDataRequestModifyMixin, SODARAPIGenericProjectMixin, UpdateAPIView
):
    """
    Update an iRODS data request for a project.

    **URL:** ``/samplesheets/api/irods/request/update/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``PUT``, ``PATCH``

    **Parameters:**

    - ``path``: iRODS path to object or collection (string)
    - ``description``: Request description
    """

    lookup_url_kwarg = 'irodsdatarequest'
    permission_classes = [IsAuthenticated]
    serializer_class = IrodsDataRequestSerializer

    def perform_update(self, serializer):
        if not self.has_irods_request_update_perms(
            self.request, serializer.instance
        ):
            raise PermissionDenied
        serializer.save()
        # Add timeline event
        self.add_tl_update(serializer.instance)


class IrodsDataRequestDestroyAPIView(
    IrodsDataRequestModifyMixin, SODARAPIGenericProjectMixin, DestroyAPIView
):
    """
    Delete an iRODS data request object.

    This action only deletes the request object and is equvalent to cencelling
    the request. No associated iRODS collections or data objects will be
    deleted.

    **URL:** ``/samplesheets/api/irods/request/delete/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``DELETE``
    """

    lookup_url_kwarg = 'irodsdatarequest'
    permission_classes = [IsAuthenticated]
    serializer_class = IrodsDataRequestSerializer

    def perform_destroy(self, instance):
        if not self.has_irods_request_update_perms(self.request, instance):
            raise PermissionDenied
        instance.delete()
        # Add timeline event
        self.add_tl_delete(instance)
        # Handle project alerts
        self.handle_alerts_deactivate(instance)


class IrodsDataRequestAcceptAPIView(
    IrodsDataRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Accept an iRODS data request for a project.

    Accepting will delete the iRODS collection or data object targeted by the
    request. This action can not  be undone.

    **URL:** ``/samplesheets/api/irods/request/accept/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.manage_sheet'

    def post(self, request, *args, **kwargs):
        """POST request for accepting an iRODS data request"""
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        app_alerts = get_backend_api('appalerts_backend')
        project = self.get_project()
        irods_request = IrodsDataRequest.objects.filter(
            sodar_uuid=self.kwargs.get('irodsdatarequest')
        ).first()

        try:
            self.accept_request(
                irods_request,
                project,
                self.request,
                timeline=timeline,
                taskflow=taskflow,
                app_alerts=app_alerts,
            )
        except Exception as ex:
            raise ValidationError(
                '{} {}'.format('Accepting ' + IRODS_REQUEST_EX_MSG + ':', ex)
            )
        return Response(
            {'detail': 'iRODS data request accepted'}, status=status.HTTP_200_OK
        )


class IrodsDataRequestRejectAPIView(
    IrodsDataRequestModifyMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Reject an iRODS data request for a project.

    This action will set the request status as rejected and keep the targeted
    iRODS collection or data object intact.

    **URL:** ``/samplesheets/api/irods/request/reject/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.manage_sheet'

    def post(self, request, *args, **kwargs):
        """POST request for rejecting an iRODS data request"""
        timeline = get_backend_api('timeline_backend')
        app_alerts = get_backend_api('appalerts_backend')
        project = self.get_project()
        irods_request = IrodsDataRequest.objects.filter(
            sodar_uuid=self.kwargs.get('irodsdatarequest')
        ).first()

        try:
            self.reject_request(
                irods_request,
                project,
                self.request,
                timeline=timeline,
                app_alerts=app_alerts,
            )
        except Exception as ex:
            raise APIException(
                '{} {}'.format('Rejecting ' + IRODS_REQUEST_EX_MSG + ':', ex)
            )
        return Response(
            {'detail': 'iRODS data request rejected'}, status=status.HTTP_200_OK
        )


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


class ProjectIrodsFileListAPIView(SODARAPIBaseProjectMixin, APIView):
    """
    Return a list of files in the project sample data repository.

    **URL:** ``/samplesheets/api/file/list/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Returns:**

    - ``irods_data``: List of iRODS data objects (list of dicts)
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
                {'detail': '{}: {}'.format(IRODS_QUERY_ERROR_MSG, ex)},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(irods_data, status=status.HTTP_200_OK)


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
