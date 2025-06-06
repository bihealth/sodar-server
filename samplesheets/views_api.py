"""REST API views for the samplesheets app"""

import logging
import re
import sys

from irods.exception import CAT_NO_ROWS_FOUND
from irods.models import DataObject
from packaging.version import parse as parse_version

from django.conf import settings
from django.urls import reverse

from rest_framework import serializers, status
from rest_framework.exceptions import (
    APIException,
    ParseError,
    ValidationError,
    NotAcceptable,
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
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.versioning import AcceptHeaderVersioning
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, inline_serializer

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import (
    RoleAssignment,
    RemoteSite,
    SODAR_CONSTANTS,
    ROLE_RANKING,
)
from projectroles.plugins import get_backend_api
from projectroles.views_api import (
    SODARAPIBaseProjectMixin,
    SODARAPIGenericProjectMixin,
    SODARPageNumberPagination,
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


# SODAR constants
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']

# Local constants
APP_NAME = 'samplesheets'
SAMPLESHEETS_API_MEDIA_TYPE = 'application/vnd.bihealth.sodar.samplesheets+json'
SAMPLESHEETS_API_ALLOWED_VERSIONS = ['1.0', '1.1']
SAMPLESHEETS_API_DEFAULT_VERSION = '1.1'
HASH_SCHEME_MD5 = 'MD5'
HASH_SCHEME_SHA256 = 'SHA256'
CHECKSUM_RE = {
    HASH_SCHEME_MD5: re.compile(r'^([a-fA-F\d]{32})$'),
    HASH_SCHEME_SHA256: re.compile(r'^([a-fA-F\d]{64})$'),
}
IRODS_QUERY_ERROR_MSG = 'Exception querying iRODS objects'
IRODS_REQUEST_EX_MSG = 'iRODS data request failed'
IRODS_TICKET_EX_MSG = 'iRODS access ticket failed'
IRODS_TICKET_NO_UPDATE_FIELDS_MSG = 'No fields to update'
FILE_EXISTS_RESTRICT_MSG = (
    'File exist query access restricted: user does not have guest access or '
    'above in any project (SHEETS_API_FILE_EXISTS_RESTRICT=True)'
)
FILE_LIST_PAGINATE_VERSION_MSG = 'Pagination not supported in API version 1.0'
HOST_VERSION_ERR_MSG = (
    'Field allowed_hosts requires samplesheets API version 1.1 or above'
)


# Base Classes and Mixins ------------------------------------------------------


class SamplesheetsAPIVersioningMixin:
    """
    Samplesheets API view versioning mixin for overriding media type and
    accepted versions.
    """

    class SamplesheetsAPIRenderer(JSONRenderer):
        media_type = SAMPLESHEETS_API_MEDIA_TYPE

    class SamplesheetsAPIVersioning(AcceptHeaderVersioning):
        allowed_versions = SAMPLESHEETS_API_ALLOWED_VERSIONS
        default_version = SAMPLESHEETS_API_DEFAULT_VERSION

    renderer_classes = [SamplesheetsAPIRenderer]
    versioning_class = SamplesheetsAPIVersioning


# API Views --------------------------------------------------------------------


class InvestigationRetrieveAPIView(
    SamplesheetsAPIVersioningMixin, SODARAPIGenericProjectMixin, RetrieveAPIView
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


@extend_schema(
    responses={
        '200': inline_serializer(
            'IrodsCollsCreateResponse',
            fields={'path': serializers.CharField()},
        ),
    }
)
class IrodsCollsCreateAPIView(
    IrodsCollsCreateViewMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIBaseProjectMixin,
    APIView,
):
    """
    Create iRODS collections for a project.

    Returns ``503`` if the project is currently locked by another operation.

    **URL:** ``/samplesheets/api/irods/collections/create/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Returns:**

    - ``path``: Full iRODS path to the root of created collections (string)
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.create_colls'
    serializer_class = None

    def post(self, request, *args, **kwargs):
        """POST request for creating iRODS collections"""
        irods_backend = get_backend_api('omics_irods')
        taskflow = get_backend_api('taskflow')
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
            if taskflow:
                taskflow.raise_submit_api_exception(ex_msg, ex)
            raise APIException('{}{}'.format(ex_msg, ex))
        return Response(
            {
                'detail': 'iRODS collections created',
                'path': irods_backend.get_sample_path(investigation.project),
            },
            status=status.HTTP_200_OK,
        )


class SheetISAExportAPIView(
    SheetISAExportMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIBaseProjectMixin,
    APIView,
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
    serializer_class = None

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


@extend_schema(
    responses={
        '200': inline_serializer(
            'SheetImportResponse',
            fields={
                'detail': serializers.CharField(),
                'sodar_warnings': serializers.ListField(),
            },
        ),
    }
)
class SheetImportAPIView(
    SheetImportMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIBaseProjectMixin,
    APIView,
):
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
    serializer_class = None

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
        tl_event = self.add_tl_event(project=project, action=action)
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


class IrodsAccessTicketRetrieveAPIView(
    SamplesheetsAPIVersioningMixin, SODARAPIGenericProjectMixin, RetrieveAPIView
):
    """
    Retrieve an iRODS access ticket for a project.

    **URL:** ``/samplesheets/api/irods/ticket/retrieve/{IrodsAccessTicket.sodar_uuid}``

    **Methods:** ``GET``

    **Returns**

    - ``path``: Full iRODS path (string)
    - ``label``: Text label for ticket (string, optional)
    - ``ticket``: Ticket string for accessing the path (string)
    - ``assay``: Assay UUID (string)
    - ``study``: Study UUID (string)
    - ``date_created``: Creation datetime (YYYY-MM-DDThh:mm:ssZ)
    - ``date_expires``: Expiry datetime (YYYY-MM-DDThh:mm:ssZ or null)
    - ``allowed_hosts``: Allowed hosts for ticket access (list)
    - ``user``: UUID of user who created the request (string)
    - ``is_active``: Whether the request is currently active (boolean)
    - ``sodar_uuid``: IrodsAccessTicket UUID (string)

    **Version Changes**:

    - ``1.1``: Add ``allowed_hosts`` field
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'irodsaccessticket'
    permission_required = 'samplesheets.view_tickets'
    serializer_class = IrodsAccessTicketSerializer
    queryset_project_field = 'study__investigation__project'


class IrodsAccessTicketListAPIView(
    SamplesheetsAPIVersioningMixin, SODARAPIBaseProjectMixin, ListAPIView
):
    """
    List iRODS access tickets for a project.

    Supports optional pagination for listing by providing the ``page`` query
    string. This will return results in the Django Rest Framework
    ``PageNumberPagination`` format.

    **URL:** ``/samplesheets/api/irods/ticket/list/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Query parameters:**

    - ``active`` (boolean, optional, default=false)
    - ``page``: Page number for paginated results (int, optional)

    **Returns:** List of ticket dicts, see ``IrodsAccessTicketRetrieveAPIView``
    """

    pagination_class = SODARPageNumberPagination
    permission_required = 'samplesheets.view_tickets'
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


class IrodsAccessTicketCreateAPIView(
    IrodsAccessTicketModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    CreateAPIView,
):
    """
    Create an iRODS access ticket for collection or data object in a project.

    **URL:** ``/samplesheets/api/irods/ticket/create/{Project.sodar_uuid}``

    **Methods:** ``POST``

    **Parameters:**

    - ``path``: Full iRODS path to collection or data object (string)
    - ``label``: Text label for ticket (string, optional)
    - ``date_expires``: Expiration date (YYYY-MM-DDThh:mm:ssZ, optional)
    - ``allowed_hosts``: Allowed hosts for ticket access (list, optional)

    **Returns:** Ticket dict, see ``IrodsAccessTicketRetrieveAPIView``

    **Version Changes**:

    - ``1.1``: Add ``allowed_hosts`` field
    """

    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsAccessTicketSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if sys.argv[1:2] == ['generateschema']:
            return context
        context['project'] = self.get_project()
        context['user'] = self.request.user
        return context

    def create(self, request, *args, **kwargs):
        # If API v1.0, fail if attribute is present, set default if not
        version = parse_version(self.request.version)
        if version < parse_version('1.1'):
            if 'allowed_hosts' in request.data:
                raise ValidationError(HOST_VERSION_ERR_MSG)
            default_hosts = app_settings.get(
                APP_NAME, 'irods_ticket_hosts', project=self.get_project()
            )
            request.data['allowed_hosts'] = [
                h.strip() for h in default_hosts.split(',') if h.strip()
            ]
        return super().create(request, *args, **kwargs)

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
                    date_expires=serializer.validated_data.get('date_expires'),
                    allowed_hosts=serializer.validated_data.get(
                        'allowed_hosts'
                    ),
                )
        except Exception as ex:
            raise ValidationError(
                '{} {}'.format('Creating ' + IRODS_TICKET_EX_MSG + ':', ex)
            )

        serializer.validated_data['ticket'] = ticket.ticket
        serializer.save()
        # Create timeline event
        self.add_tl_event(serializer.instance, 'create')
        # Add app alerts to owners/delegates
        self.create_app_alerts(serializer.instance, 'create', self.request.user)


class IrodsAccessTicketUpdateAPIView(
    IrodsAccessTicketModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    UpdateAPIView,
):
    """
    Update an iRODS access ticket for a project.

    **URL:** ``/samplesheets/api/irods/ticket/update/{IrodsAccessTicket.sodar_uuid}``

    **Methods:** ``PUT``, ``PATCH``

    **Parameters:**

    - ``label``: Label (string)
    - ``date_expires``: Expiration date (YYYY-MM-DDThh:mm:ssZ, optional)
    - ``allowed_hosts``: Allowed hosts for ticket access (list, optional)

    **Returns:** Ticket dict, see ``IrodsAccessTicketRetrieveAPIView``

    **Version Changes**:

    - ``1.1``: Add ``allowed_hosts`` field
    """

    lookup_url_kwarg = 'irodsaccessticket'
    permission_required = 'samplesheets.edit_sheet'
    serializer_class = IrodsAccessTicketSerializer
    queryset_project_field = 'study__investigation__project'

    def update(self, request, *args, **kwargs):
        version = parse_version(self.request.version)
        if version < parse_version('1.1'):
            if 'allowed_hosts' in request.data:
                raise ValidationError(HOST_VERSION_ERR_MSG)
            # Set current value for serializer
            obj = self.get_object()
            request.data['allowed_hosts'] = [
                h.strip() for h in obj.allowed_hosts.split(',') if h.strip()
            ]
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        """Override perform_update() to update IrodsAccessTicket"""
        irods_backend = get_backend_api('omics_irods')
        if not set(serializer.initial_data) & {
            'label',
            'date_expires',
            'allowed_hosts',
        }:
            raise ValidationError(IRODS_TICKET_NO_UPDATE_FIELDS_MSG)
        serializer.save()
        # Update ticket in iRODS
        try:
            with irods_backend.get_session() as irods:
                irods_backend.update_ticket(
                    irods,
                    ticket_str=serializer.instance.ticket,
                    date_expires=serializer.instance.date_expires,
                    allowed_hosts=serializer.validated_data.get(
                        'allowed_hosts'
                    ),
                )
        except Exception as ex:
            raise APIException(
                'Exception updating iRODS access ticket: {}'.format(ex),
            )
        # Add timeline event
        self.add_tl_event(serializer.instance, 'update')
        # Add app alerts to owners/delegates
        self.create_app_alerts(serializer.instance, 'update', self.request.user)


class IrodsAccessTicketDestroyAPIView(
    IrodsAccessTicketModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    DestroyAPIView,
):
    """
    Delete an iRODS access ticket.

    **URL:** ``/samplesheets/api/irods/ticket/delete/{IrodsAccessTicket.sodar_uuid}``

    **Methods:** ``DELETE``
    """

    lookup_field = 'sodar_uuid'
    lookup_url_kwarg = 'irodsaccessticket'
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
        self.add_tl_event(instance, 'delete')
        # Add app alerts to owners/delegates
        self.create_app_alerts(instance, 'delete', self.request.user)


class IrodsDataRequestRetrieveAPIView(
    SamplesheetsAPIVersioningMixin, SODARAPIGenericProjectMixin, RetrieveAPIView
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
    - ``user``: UUID of user initiating request (string)
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


class IrodsDataRequestListAPIView(
    SamplesheetsAPIVersioningMixin, SODARAPIBaseProjectMixin, ListAPIView
):
    """
    List the iRODS data requests for a project.

    If the requesting user is an owner, delegate or superuser, the view lists
    all requests with the status of ACTIVE or FAILED. If called as a
    contributor, returns the user's own requests regardless of the state.

    Supports optional pagination for listing by providing the ``page`` query
    string. This will return results in the Django Rest Framework
    ``PageNumberPagination`` format.

    **URL:** ``/samplesheets/api/irods/requests/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Query parameters:**

    - ``page``: Page number for paginated results (int, optional)

    **Returns:** List of iRODS data requests (list of dicts)
    """

    pagination_class = SODARPageNumberPagination
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
    IrodsDataRequestModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    CreateAPIView,
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
        self.add_tl_event(serializer.instance, 'create')
        # Add app alerts to owners/delegates
        self.add_alerts_create(serializer.instance.project)


class IrodsDataRequestUpdateAPIView(
    IrodsDataRequestModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    UpdateAPIView,
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
        self.add_tl_event(serializer.instance, 'update')


class IrodsDataRequestDestroyAPIView(
    IrodsDataRequestModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIGenericProjectMixin,
    DestroyAPIView,
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
        self.add_tl_event(instance, 'delete')
        # Handle project alerts
        self.handle_alerts_deactivate(instance)


@extend_schema(
    responses={
        '200': inline_serializer(
            'IrodsDataRequestAcceptResponse',
            fields={'detail': serializers.CharField()},
        ),
    }
)
class IrodsDataRequestAcceptAPIView(
    IrodsDataRequestModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIBaseProjectMixin,
    APIView,
):
    """
    Accept an iRODS data request for a project.

    Accepting will delete the iRODS collection or data object targeted by the
    request. This action can not be undone.

    Returns ``503`` if the project is currently locked by another operation.

    **URL:** ``/samplesheets/api/irods/request/accept/{IrodsDataRequest.sodar_uuid}``

    **Methods:** ``POST``
    """

    http_method_names = ['post']
    permission_required = 'samplesheets.manage_sheet'
    serializer_class = None

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
            ex_msg = 'Accepting ' + IRODS_REQUEST_EX_MSG + ': '
            if taskflow:
                taskflow.raise_submit_api_exception(ex_msg, ex, ValidationError)
            raise ValidationError('{}{}'.format(ex_msg, ex))
        return Response(
            {'detail': 'iRODS data request accepted'}, status=status.HTTP_200_OK
        )


@extend_schema(
    responses={
        '200': inline_serializer(
            'IrodsDataRequestRejectResponse',
            fields={'detail': serializers.CharField()},
        ),
    }
)
class IrodsDataRequestRejectAPIView(
    IrodsDataRequestModifyMixin,
    SamplesheetsAPIVersioningMixin,
    SODARAPIBaseProjectMixin,
    APIView,
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
    serializer_class = None

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


@extend_schema(
    responses={
        '200': inline_serializer(
            'SampleDataFileExistsResponse',
            fields={
                'detail': serializers.CharField(),
                'sodar_uuid': serializers.BooleanField(),
            },
        ),
    }
)
class SampleDataFileExistsAPIView(SamplesheetsAPIVersioningMixin, APIView):
    """
    Return status of data object existing in SODAR iRODS by checksum.
    Includes all projects in search regardless of user permissions.

    The checksum is expected as MD5 or SHA256, depending on which is set as the
    hash scheme for the SODAR and iRODS servers.

    If ``SHEETS_API_FILE_EXISTS_RESTRICT`` is set True on the server, this view
    is only accessible by users who have a guest role or above in at least one
    category or project.

    **URL:** ``/samplesheets/api/file/exists``

    **Methods:** ``GET``

    **Parameters:**

    - ``checksum``: MD5 or SHA256 checksum as hex (string)

    **Returns:**

    - ``detail``: String
    - ``status``: Boolean
    """

    http_method_names = ['get']
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        if (
            settings.SHEETS_API_FILE_EXISTS_RESTRICT
            and not request.user.is_superuser
        ):
            roles = RoleAssignment.objects.filter(
                user=request.user,
                role__rank__lte=ROLE_RANKING[PROJECT_ROLE_GUEST],
            )
            if roles.count() == 0:
                raise PermissionDenied(FILE_EXISTS_RESTRICT_MSG)
        if not settings.ENABLE_IRODS:
            raise APIException('iRODS not enabled')
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            raise APIException('iRODS backend not enabled')

        hash_scheme = settings.IRODS_HASH_SCHEME
        c = request.query_params.get('checksum')
        if not c or not re.match(CHECKSUM_RE[hash_scheme], c):
            raise ParseError(f'Invalid {hash_scheme} checksum: "{c}"')
        # If SHA256, convert to base64 with prefix
        if hash_scheme == HASH_SCHEME_SHA256:
            c = irods_backend.get_sha256_base64(c, prefix=True)

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


@extend_schema(
    responses={
        '200': inline_serializer(
            'ProjectIrodsFileListResponse',
            fields={
                'name': serializers.CharField(),
                'type': serializers.CharField(),
                'path': serializers.CharField(),
                'size': serializers.IntegerField(),
                'modify_time': serializers.DateTimeField(),
                'checksum': serializers.CharField(),
            },
        ),
    }
)
class ProjectIrodsFileListAPIView(
    SamplesheetsAPIVersioningMixin, SODARAPIBaseProjectMixin, APIView
):
    """
    Return a list of files in the project sample data repository.

    Supports optional pagination for listing by providing the ``page`` query
    string. This will return results in the Django Rest Framework
    ``PageNumberPagination`` format.

    **URL:** ``/samplesheets/api/file/list/{Project.sodar_uuid}``

    **Methods:** ``GET``

    **Parameters:**

    - ``page``: Page number for paginated results (int, optional)

    **Returns:**

    List of iRODS data objects (list of dicts). Each object dict contains:

    - ``name``: File name
    - ``type``: iRODS item type type (``obj`` for file)
    - ``path``: Full path to file
    - ``size``: Size in bytes
    - ``modify_time``: Datetime of last modification (YYYY-MM-DDThh:mm:ssZ)
    - ``checksum``: Checksum of data object

    **Version Changes**:

    - ``1.1``: Add ``checksum`` field to return data
    - ``1.1``: Add ``page`` parameter for optional pagination
    """

    http_method_names = ['get']
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        if not settings.ENABLE_IRODS:
            raise APIException('iRODS not enabled')
        version = parse_version(request.version)
        page = request.GET.get('page')
        if page and version < parse_version('1.1'):
            raise NotAcceptable(FILE_LIST_PAGINATE_VERSION_MSG)
        elif page:
            page = int(page)

        irods_backend = get_backend_api('omics_irods')
        project = self.get_project()
        path = irods_backend.get_sample_path(project)
        page_size = settings.SODAR_API_PAGE_SIZE
        limit = None
        offset = None
        file_count = None
        if page:
            limit = page_size
            offset = 0 if page == 1 else (page - 1) * page_size
        checksum = True if version >= parse_version('1.1') else False

        try:
            with irods_backend.get_session() as irods:
                obj_list = irods_backend.get_objects(
                    irods,
                    path,
                    limit=limit,
                    offset=offset,
                    api_format=True,
                    checksum=checksum,
                )
                # Get total count for DRF compatible pagination response
                if page:
                    stats = irods_backend.get_stats(irods, path)
                    file_count = stats['file_count']
        except FileNotFoundError as ex:
            raise NotFound('{}: {}'.format(IRODS_QUERY_ERROR_MSG, ex))
        except Exception as ex:
            return Response(
                {'detail': '{}: {}'.format(IRODS_QUERY_ERROR_MSG, ex)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if page:
            url = reverse(
                'samplesheets:api_file_list',
                kwargs={'project': project.sodar_uuid},
            )
            ret = {
                'count': file_count,
                'next': (
                    (url + f'?page={page + 1}')
                    if file_count > page * page_size
                    else None
                ),
                'previous': (url + f'?page={page - 1}') if page > 1 else None,
                'results': obj_list,
            }
        else:
            ret = obj_list
        return Response(ret, status=status.HTTP_200_OK)


# TODO: Temporary HACK, should be replaced by proper API view
@extend_schema(
    responses={
        '200': inline_serializer(
            'RemoteSheetGetResponse',
            fields={'studies': serializers.JSONField()},
        ),
    }
)
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
