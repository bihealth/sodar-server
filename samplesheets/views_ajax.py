"""Ajax API views for the samplesheets app"""

import json

from altamisa.constants import table_headers as th
from datetime import datetime as dt
from packaging import version

from django.conf import settings
from django.db import transaction
from django.middleware.csrf import get_token
from django.urls import reverse

from rest_framework.response import Response

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS
from projectroles.models import RoleAssignment
from projectroles.plugins import get_backend_api
from projectroles.views_ajax import SODARBaseProjectAjaxView

# Irodsbackend dependency
from irodsbackend.views import BaseIrodsAjaxView

from samplesheets.io import SampleSheetIO
from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    Protocol,
    Process,
    GenericMaterial,
    IrodsDataRequest,
    ISATab,
)
from samplesheets.rendering import (
    SampleSheetTableBuilder,
    MODEL_JSON_ATTRS,
)
from samplesheets.sheet_config import SheetConfigAPI
from samplesheets.utils import (
    get_comments,
    get_unique_name,
    get_node_obj,
    get_webdav_url,
)
from samplesheets.views import (
    IrodsRequestModifyMixin,
    app_settings,
    APP_NAME,
    TARGET_ALTAMISA_VERSION,
    logger,
)


conf_api = SheetConfigAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']

# Local constants
EDIT_FIELD_MAP = {
    'array design ref': 'array_design_ref',
    'label': 'extract_label',
    'performer': 'performer',
}

ALERT_ACTIVE_REQS = (
    'Active iRODS delete requests in this project require your attention. '
    '<a href="{url}">See request list for details</a>.'
)
ERROR_NOT_IN_PROJECT = 'Collection does not belong to project'
ERROR_NOT_FOUND = 'Collection not found'
ERROR_NO_AUTH = 'User not authorized for iRODS collection'


# Base Ajax View Classes and Mixins --------------------------------------------


class BaseSheetEditAjaxView(SODARBaseProjectAjaxView):
    """Base ajax view for editing sample sheet data"""

    permission_required = 'samplesheets.edit_sheet'
    ok_data = {'detail': 'ok'}

    class SheetEditException(Exception):
        pass

    def _raise_ex(self, msg):
        logger.error(msg)
        raise self.SheetEditException(msg)

    @classmethod
    def _get_attr_value(cls, node_obj, cell, header_name, header_type):
        """
        Get node object attribute value in a format saveable into the database.

        :param node_obj: GenericMaterial or Process object
        :param cell: Cell update data from the client (dict)
        :param header_name: Header name (string)
        :param header_type: Header type (string)
        :return: String, dict or list
        """
        if isinstance(cell['value'], list) and len(cell['value']) == 1:
            val = cell['value'][0]
        # Handle empty list
        elif isinstance(cell['value'], list) and len(cell['value']) == 0:
            val = None
            if node_obj.is_ontology_field(header_name, header_type):
                val = {
                    'name': None,
                    'accession': None,
                    'ontology_name': None,
                }
        else:
            val = cell['value']
        return val

    @classmethod
    def _get_ontology_names(cls, cells=None, nodes=None):
        """
        Return unique ontology names from ontology field in a list of nodes.

        :param cells: List of dicts
        :param nodes: List of dicts
        :return: List
        """
        if not cells and not nodes:
            raise ValueError('Must define either cells or nodes')
        if not cells:
            cells = []
            for n in nodes:
                cells += n['cells']
        ret = []
        for c in cells:
            if (
                c.get('value')
                and isinstance(c['value'], list)
                and len(c['value']) > 0
                and isinstance(c['value'][0], dict)
            ):
                for t in c['value']:
                    o_name = t.get('ontology_name')
                    if o_name and o_name not in ret:
                        ret.append(o_name)
        logger.debug('Ontologies in edit data: {}'.format(', '.join(ret)))
        return ret

    @classmethod
    @transaction.atomic
    def _update_ontology_refs(cls, investigation, edit_names):
        """
        Update investigation ontology refs, adding references to ontologies
        currently missing.

        :param investigation: Investigation object
        :param edit_names: Ontology names from editing (list)
        """
        # TODO: Implement removal of unused ontologies (see issue #967)
        # TODO: Update existing refs for SODAR ontology data?
        ontology_backend = get_backend_api('ontologyaccess_backend')
        if not ontology_backend:
            logger.error(
                'Ontologyaccess backend not enabled, unable to update '
                'ontology refs'
            )
            return

        i_names = [
            o['name']
            for o in investigation.ontology_source_refs
            if o.get('name')
        ]
        sodar_obos = ontology_backend.get_obo_dict(key='name')
        updated = False

        for o_name in edit_names:
            if o_name not in i_names and o_name:
                logger.debug(
                    'Inserting ontology reference for "{}"'.format(o_name)
                )
                if o_name not in sodar_obos.keys():
                    logger.warning(
                        'Ontology "{}" not imported to SODAR, unable to '
                        'update ontology reference'.format(o_name)
                    )
                    continue
                investigation.ontology_source_refs.append(
                    {
                        'file': sodar_obos[o_name]['file'],
                        'name': o_name,
                        'version': sodar_obos[o_name]['data_version'] or '',
                        'description': sodar_obos[o_name]['title'],
                        'comments': [],
                        'headers': [
                            'Term Source Name',
                            'Term Source File',
                            'Term Source Version',
                            'Term Source Description',
                        ],
                    }
                )
                updated = True
                logger.debug(
                    'Inserted ontology reference for "{}" '
                    '(investigation={})'.format(
                        o_name, investigation.sodar_uuid
                    )
                )

        if updated:
            investigation.save()
            logger.info(
                'Ontology references updated (investigation={})'.format(
                    investigation.sodar_uuid
                )
            )
        else:
            logger.debug(
                'No updates for ontology references '
                '(investigation={})'.format(investigation.sodar_uuid)
            )


class EditConfigMixin:
    """Mixin class to check if user can edit config"""

    @classmethod
    def _can_edit_config(cls, user, project):
        if user.is_superuser:
            return True
        edit_config_min_role = app_settings.get_app_setting(
            APP_NAME, 'edit_config_min_role', project=project
        )
        assignment = RoleAssignment.objects.get_assignment(user, project)
        role_order = [
            SODAR_CONSTANTS['PROJECT_ROLE_OWNER'],
            SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE'],
            SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR'],
            SODAR_CONSTANTS['PROJECT_ROLE_GUEST'],
        ]
        if not assignment:
            return False
        return role_order.index(assignment.role.name) <= role_order.index(
            edit_config_min_role
        )


class SheetVersionMixin:
    """Mixin for sheet version saving"""

    @classmethod
    def save_version(cls, investigation, request, description=None):
        """
        Save current version of an investigation as ISA-Tab into the database.

        :param investigation: Investigation object
        :param request: HTTP request
        :param description: Version description (string, optional)
        :return: ISATab object
        :raise: Exception if ISA-Tab saving fails
        """
        sheet_io = SampleSheetIO()
        project = investigation.project
        isa_data = sheet_io.export_isa(investigation)
        # Save sheet config with ISA-Tab version
        isa_data['sheet_config'] = app_settings.get_app_setting(
            APP_NAME, 'sheet_config', project=project
        )
        isa_version = sheet_io.save_isa(
            project=project,
            inv_uuid=investigation.sodar_uuid,
            isa_data=isa_data,
            tags=['EDIT'],
            user=request.user,
            archive_name=investigation.archive_name,
            description=description,
        )
        return isa_version


# Ajax Views -------------------------------------------------------------------


class SheetContextAjaxView(EditConfigMixin, SODARBaseProjectAjaxView):
    """View to retrieve sample sheet context data"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        inv = Investigation.objects.filter(project=project, active=True).first()
        studies = Study.objects.filter(investigation=inv).order_by('pk')
        irods_backend = get_backend_api('omics_irods', conn=False)

        # General context data for Vue app
        ret_data = {
            'configuration': None,
            'inv_file_name': None,
            'irods_status': None,
            'irods_backend_enabled': (True if irods_backend else False),
            'parser_version': None,
            'parser_warnings': False,
            'irods_webdav_enabled': settings.IRODS_WEBDAV_ENABLED,
            'irods_webdav_url': get_webdav_url(project, request.user),
            'external_link_labels': settings.SHEETS_EXTERNAL_LINK_LABELS,
            'table_height': settings.SHEETS_TABLE_HEIGHT,
            'min_col_width': settings.SHEETS_MIN_COLUMN_WIDTH,
            'max_col_width': settings.SHEETS_MAX_COLUMN_WIDTH,
            'allow_editing': app_settings.get_app_setting(
                APP_NAME, 'allow_editing', project=project
            ),
            'alerts': [],
            'csrf_token': get_token(request),
            'investigation': {},
            'user_uuid': str(request.user.sodar_uuid)
            if hasattr(request.user, 'sodar_uuid')
            else None,
            'sheet_sync_enabled': app_settings.get_app_setting(
                APP_NAME, 'sheet_sync_enable', project=project
            ),
        }

        if inv:
            inv_data = {
                'configuration': inv.get_configuration(),
                'inv_file_name': inv.file_name.split('/')[-1],
                'irods_status': inv.irods_status,
                'parser_version': inv.parser_version or 'LEGACY',
                'parser_warnings': True
                if inv.parser_warnings
                and 'use_file_names' in inv.parser_warnings
                else False,
                'investigation': {
                    'identifier': inv.identifier,
                    'title': inv.title,
                    'description': inv.description
                    if inv.description != project.description
                    else None,
                    'comments': get_comments(inv),
                },
            }
            ret_data.update(inv_data)

        # Parser alert
        if inv and (
            not inv.parser_version
            or version.parse(inv.parser_version)
            < version.parse(TARGET_ALTAMISA_VERSION)
        ):
            ret_data['alerts'].append(
                {
                    'level': 'danger',
                    'html': 'This sample sheet has been imported with an '
                    'old altamISA version (< {}). Please replace the ISA-Tab '
                    'to enable all features and ensure full '
                    'functionality.'.format(TARGET_ALTAMISA_VERSION),
                }
            )

        # iRODS data request alert
        if (
            inv
            and inv.irods_status
            and (
                self.request.user.is_superuser
                or project.is_owner_or_delegate(self.request.user)
            )
        ):
            irods_req_count = IrodsDataRequest.objects.filter(
                project=project, status__in=['ACTIVE', 'FAILED']
            ).count()
            if irods_req_count > 0:
                ret_data['alerts'].append(
                    {
                        'level': 'info',
                        'html': ALERT_ACTIVE_REQS.format(
                            url=reverse(
                                'samplesheets:irods_requests',
                                kwargs={'project': project.sodar_uuid},
                            )
                        ),
                    }
                )

        # Study info
        ret_data['studies'] = {}

        for s in studies:
            study_plugin = s.get_plugin()
            ret_data['studies'][str(s.sodar_uuid)] = {
                'display_name': s.get_display_name(),
                'identifier': s.identifier,
                'description': s.description,
                'comments': get_comments(s),
                'irods_path': irods_backend.get_path(s)
                if irods_backend
                else None,
                'table_url': request.build_absolute_uri(
                    reverse(
                        'samplesheets:ajax_study_tables',
                        kwargs={'study': str(s.sodar_uuid)},
                    )
                ),
                'plugin': study_plugin.title if study_plugin else None,
                'assays': {},
            }

            # Set up assay data
            for a in s.assays.all().order_by('pk'):
                assay_plugin = a.get_plugin()
                ret_data['studies'][str(s.sodar_uuid)]['assays'][
                    str(a.sodar_uuid)
                ] = {
                    'name': a.get_name(),
                    'display_name': a.get_display_name(),
                    'irods_path': irods_backend.get_path(a)
                    if irods_backend
                    else None,
                    'display_row_links': assay_plugin.display_row_links
                    if assay_plugin
                    else True,
                    'plugin': assay_plugin.title if assay_plugin else None,
                }

        # Permissions for UI elements (will be checked on request)
        ret_data['perms'] = {
            'edit_sheet': request.user.has_perm(
                'samplesheets.edit_sheet', project
            ),
            'manage_sheet': request.user.has_perm(
                'samplesheets.manage_sheet', project
            ),
            'create_colls': request.user.has_perm(
                'samplesheets.create_colls', project
            ),
            'export_sheet': request.user.has_perm(
                'samplesheets.export_sheet', project
            ),
            'delete_sheet': request.user.has_perm(
                'samplesheets.delete_sheet', project
            ),
            'view_versions': request.user.has_perm(
                'samplesheets.view_versions', project
            ),
            'edit_config': self._can_edit_config(request.user, project),
            'is_superuser': request.user.is_superuser,
        }

        # Statistics
        ret_data['sheet_stats'] = (
            {
                'study_count': Study.objects.filter(investigation=inv).count(),
                'assay_count': Assay.objects.filter(
                    study__investigation=inv
                ).count(),
                'protocol_count': Protocol.objects.filter(
                    study__investigation=inv
                ).count(),
                'process_count': Process.objects.filter(
                    protocol__study__investigation=inv
                ).count(),
                'source_count': inv.get_material_count('SOURCE'),
                'material_count': inv.get_material_count('MATERIAL'),
                'sample_count': inv.get_material_count('SAMPLE'),
                'data_count': inv.get_material_count('DATA'),
            }
            if inv
            else {}
        )

        ret_data = json.dumps(ret_data)
        # logger.debug('SODAR Context: {}'.format(ret_data))
        return Response(ret_data, status=200)


class StudyTablesAjaxView(SODARBaseProjectAjaxView):
    """View to retrieve study tables built from the sample sheet graph"""

    def get_permission_required(self):
        """Override get_permisson_required() to provide the approrpiate perm"""
        if bool(self.request.GET.get('edit')):
            return 'samplesheets.edit_sheet'

        return 'samplesheets.view_sheet'

    def _get_display_config(self, investigation, user, sheet_config=None):
        """Get or create display configuration for an investigation"""
        project = investigation.project
        user_config_found = True

        # Get user display config
        display_config = app_settings.get_app_setting(
            APP_NAME, 'display_config', project=project, user=user
        )
        # Get default configuration if user config is not found
        if not display_config:
            user_config_found = False
            logger.debug(
                'No display configuration found for user "{}", '
                'using default..'.format(user.username)
            )
            display_config = app_settings.get_app_setting(
                APP_NAME,
                'display_config_default',
                project=project,
            )

        # If default display configuration is not found, build it
        if not display_config:
            logger.debug('No default display configuration found, building..')
            if not sheet_config:
                sheet_config = conf_api.get_sheet_config(investigation)
            display_config = conf_api.build_display_config(
                investigation, sheet_config
            )
            logger.debug(
                'Setting default display config for project "{}" ({})'.format(
                    project.title, project.sodar_uuid
                )
            )
            app_settings.set_app_setting(
                APP_NAME,
                'display_config_default',
                display_config,
                project=project,
            )

        if not user_config_found:
            logger.debug(
                'Setting display config for user "{}" in project "{}" '
                '({})'.format(user.username, project.title, project.sodar_uuid)
            )
            app_settings.set_app_setting(
                APP_NAME,
                'display_config',
                display_config,
                project=project,
                user=user,
            )

        return display_config

    def get(self, request, *args, **kwargs):
        from samplesheets.plugins import get_irods_content

        timeline = get_backend_api('timeline_backend')
        irods_backend = get_backend_api('omics_irods', conn=False)
        study = Study.objects.filter(sodar_uuid=self.kwargs['study']).first()
        if not study:
            return Response(
                {
                    'render_error': 'Study not found with UUID "{}", '
                    'unable to render'.format(self.kwargs['study'])
                },
                status=404,
            )

        inv = study.investigation
        project = inv.project
        # Return extra edit mode data
        edit = bool(request.GET.get('edit'))
        allow_editing = app_settings.get_app_setting(
            APP_NAME, 'allow_editing', project=project
        )

        if edit and not allow_editing:
            return Response(
                {
                    'render_error': 'Editing not allowed in the project, '
                    'unable to render'
                },
                status=403,
            )

        ret_data = {'study': {'display_name': study.get_display_name()}}
        tb = SampleSheetTableBuilder()

        try:
            ret_data['tables'] = tb.build_study_tables(study, edit=edit)
        except Exception as ex:
            # Raise if we are in debug mode
            if settings.DEBUG:
                raise ex
            # TODO: Log error
            ret_data['render_error'] = str(ex)
            return Response(ret_data, status=200)

        # Get iRODS content if NOT editing and collections have been created
        if not edit:
            ret_data = get_irods_content(inv, study, irods_backend, ret_data)

        # Get/build sheet config
        sheet_config = conf_api.get_sheet_config(inv)

        # Get/build display config
        if request.user and request.user.is_authenticated:
            display_config = self._get_display_config(
                inv, request.user, sheet_config
            )
            ret_data['display_config'] = display_config['studies'][
                str(study.sodar_uuid)
            ]

        # Set up editing
        if edit:
            ontology_backend = get_backend_api('ontologyaccess_backend')
            # Get study config
            ret_data['study_config'] = sheet_config['studies'][
                str(study.sodar_uuid)
            ]
            # Set up study edit context
            ret_data['edit_context'] = {
                'sodar_ontologies': ontology_backend.get_obo_dict(key='name')
                if ontology_backend
                else {},
                'samples': {},
                'protocols': [],
            }
            # Add sample info
            s_assays = {}

            for assay in study.assays.all().order_by('pk'):
                a_uuid = str(assay.sodar_uuid)
                for n in [a[0] for a in assay.arcs]:
                    if '-sample-' in n:
                        if n not in s_assays:
                            s_assays[n] = []
                        if a_uuid not in s_assays[n]:
                            s_assays[n].append(a_uuid)

            for sample in GenericMaterial.objects.filter(
                study=study, item_type='SAMPLE'
            ).order_by('name'):
                ret_data['edit_context']['samples'][str(sample.sodar_uuid)] = {
                    'name': sample.name,
                    'assays': s_assays[sample.unique_name]
                    if sample.unique_name in s_assays
                    else [],
                }

            # Add Protocol info
            for protocol in Protocol.objects.filter(study=study).order_by(
                'name'
            ):
                ret_data['edit_context']['protocols'].append(
                    {'uuid': str(protocol.sodar_uuid), 'name': protocol.name}
                )

            if timeline:
                timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=request.user,
                    event_name='sheet_edit_start',
                    description='start editing sheets',
                    status_type='OK',
                )

        return Response(ret_data, status=200)


class StudyLinksAjaxView(SODARBaseProjectAjaxView):
    """View to retrieve data for shortcut links from study apps"""

    # TODO: Also do this for assay apps?
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        study = Study.objects.filter(sodar_uuid=self.kwargs['study']).first()
        study_plugin = study.get_plugin()
        if not study_plugin:
            return Response(
                {'detail': 'Plugin not found for study'}, status=404
            )
        ret_data = {'study': {'display_name': study.get_display_name()}}
        tb = SampleSheetTableBuilder()
        try:
            study_tables = tb.build_study_tables(study)
        except Exception as ex:
            # TODO: Log error
            ret_data['render_error'] = str(ex)
            return Response(ret_data, status=200)
        ret_data = study_plugin.get_shortcut_links(
            study, study_tables, **request.GET
        )
        return Response(ret_data, status=200)


class SheetWarningsAjaxView(SODARBaseProjectAjaxView):
    """View to retrieve parser warnings for sample sheets"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        inv = Investigation.objects.filter(project=self.get_project()).first()
        if not inv:
            return Response(
                {'detail': 'Investigation not found for project'}, status=404
            )
        logger.debug(
            'Parser Warnings: {}'.format(json.dumps(inv.parser_warnings))
        )
        return Response({'warnings': inv.parser_warnings}, status=200)


class SheetCellEditAjaxView(BaseSheetEditAjaxView):
    """Ajax view to edit sample sheet cells"""

    @transaction.atomic
    def _update_cell(self, node_obj, cell, save=False):
        """
        Update a single cell in an object.

        :param node_obj: GenericMaterial or Process object
        :param cell: Cell update data from the client (dict)
        :param save: If True, save object after successful call (boolean)
        :return: String
        :raise: SheetEditException if the operation fails.
        """
        ok_msg = None
        logger.debug(
            'Editing {} "{}" ({})'.format(
                node_obj.__class__.__name__,
                node_obj.unique_name,
                node_obj.sodar_uuid,
            )
        )
        # TODO: Provide the original header as one string instead
        header_type = cell['header_type']
        header_name = cell['header_name']

        # Plain fields
        if not header_type and header_name.lower() in EDIT_FIELD_MAP:
            attr_name = EDIT_FIELD_MAP[header_name.lower()]
            attr = getattr(node_obj, attr_name)
            if isinstance(attr, str):
                setattr(node_obj, attr_name, cell['value'])
            elif isinstance(attr, dict):
                attr['name'] = cell['value']
                # TODO: Set accession and ontology once editing is allowed
            ok_msg = 'Edited field: {}'.format(attr_name)

        # Name field (special case)
        elif header_type == 'name':
            if len(cell['value']) == 0 and cell.get('item_type') != 'DATA':
                self._raise_ex('Empty name not allowed for non-data node')
            node_obj.name = cell['value']
            # TODO: Update unique name here if needed
            ok_msg = 'Edited node name: {}'.format(cell['value'])

        # Process name and name type (special case)
        elif header_type == 'process_name':
            node_obj.name = cell['value']
            if cell['header_name'] in th.PROCESS_NAME_HEADERS:
                node_obj.name_type = cell['header_name']
            ok_msg = 'Edited process name: {}{}'.format(
                cell['value'],
                ' ({})'.format(cell['header_name'])
                if cell['header_name'] in th.PROCESS_NAME_HEADERS
                else '',
            )

        # Protocol field (special case)
        elif header_type == 'protocol':
            protocol = Protocol.objects.filter(
                sodar_uuid=cell['uuid_ref']
            ).first()
            if not protocol:
                self._raise_ex(
                    'Protocol not found: "{}" ({})'.format(
                        cell['value'], cell['uuid_ref']
                    )
                )
            node_obj.protocol = protocol
            ok_msg = 'Edited protocol ref: "{}" ({})'.format(
                cell['value'], cell['uuid_ref']
            )

        # Performer (special case)
        elif header_type == 'performer':
            node_obj.performer = cell['value']

        # Perform date (special case)
        elif header_type == 'perform_date':
            if cell['value']:
                try:
                    node_obj.perform_date = dt.strptime(
                        cell['value'], '%Y-%m-%d'
                    )
                except ValueError as ex:
                    self._raise_ex(ex)
            else:
                node_obj.perform_date = None

        # Extract label (special case)
        elif header_type == 'extract_label':
            node_obj.extract_label = cell['value']

        # JSON Attributes
        elif header_type in MODEL_JSON_ATTRS:
            attr = getattr(node_obj, header_type)
            # TODO: Is this actually a thing nowadays?
            if isinstance(attr[header_name], str):
                attr[header_name] = cell['value']
            else:
                attr[header_name]['value'] = self._get_attr_value(
                    node_obj, cell, header_name, header_type
                )
                # TODO: Support ontology ref in unit
                if node_obj.has_ontology_unit(
                    header_name, header_type
                ) and isinstance(attr[header_name]['unit'], dict):
                    attr[header_name]['unit']['name'] = cell.get('unit')
                elif node_obj.has_unit(header_name, header_type):
                    attr[header_name]['unit'] = cell.get('unit')
            ok_msg = 'Edited JSON attribute: {}[{}]'.format(
                header_type, header_name
            )

        else:
            self._raise_ex(
                'Editing not implemented '
                '(header_type={}; header_name={})'.format(
                    header_type, header_name
                )
            )

        if save:
            node_obj.save()
            if ok_msg:
                logger.debug(ok_msg)

        return ok_msg

    def post(self, request, *args, **kwargs):
        inv = Investigation.objects.filter(
            project=self.get_project(), active=True
        ).first()
        updated_cells = request.data.get('updated_cells', [])

        for cell in updated_cells:
            logger.debug('Cell update: {}'.format(cell))
            node_obj = get_node_obj(sodar_uuid=cell['uuid'])
            # TODO: Make sure given object actually belongs in project etc.
            if not node_obj:
                err_msg = 'Object not found: {} ({})'.format(
                    cell['uuid'], cell['obj_cls']
                )
                logger.error(err_msg)
                # TODO: Return list of errors when processing in batch
                return Response({'detail': err_msg}, status=500)

            # Update cell, save immediately (now we are only editing one cell)
            try:
                self._update_cell(node_obj, cell, save=True)
            except self.SheetEditException as ex:
                return Response({'detail': str(ex)}, status=500)

        # Update investigation ontology refs
        if updated_cells:
            try:
                self._update_ontology_refs(
                    inv, self._get_ontology_names(cells=updated_cells)
                )
            except Exception as ex:
                return Response({'detail': str(ex)}, status=500)

        # TODO: Log edits in timeline here, once saving in bulk
        return Response(self.ok_data, status=200)


class SheetRowInsertAjaxView(BaseSheetEditAjaxView):
    """Ajax view for inserting rows into sample sheets"""

    @classmethod
    def _get_name(cls, node):
        """
        Return non-unique name for a node retrieved from the editor for a new
        row, or None if the name does not exist.

        :param node: Dict
        :return: String or None
        """
        if node['cells'][0]['obj_cls'] == 'Process':
            for cell in node['cells']:
                if cell['header_type'] == 'process_name':
                    return cell['value']
        else:  # Material
            return node['cells'][0]['value']

    @classmethod
    def _add_node_attr(cls, node_obj, cell):
        """
        Add common node attribute from cell in a new row node.

        :param node_obj: GenericMaterial or Process
        :param cell: Dict
        """
        header_name = cell['header_name']
        header_type = cell['header_type']

        if header_type in MODEL_JSON_ATTRS:
            attr = getattr(node_obj, header_type)
            # Check if we have ontology refs and alter value
            attr[header_name] = {
                'value': cls._get_attr_value(
                    node_obj, cell, header_name, header_type
                )
            }
            # TODO: Support ontology ref in unit for real
            if node_obj.has_ontology_unit(header_name, header_type):
                attr[header_name]['unit'] = {
                    'name': cell.get('unit'),
                    'ontology_name': None,
                    'accession': None,
                }
            elif (
                node_obj.has_unit(header_name, header_type)
                and cell.get('unit') != ''
            ):
                attr[header_name]['unit'] = cell.get('unit')
            else:
                attr[header_name]['unit'] = None
            logger.debug(
                'Set {}: {} = {}'.format(
                    header_type, header_name, attr[header_name]
                )
            )

        elif header_type == 'performer' and cell['value']:
            node_obj.performer = cell['value']
            logger.debug('Set performer: {}'.format(node_obj.performer))

        elif header_type == 'perform_date' and cell['value']:
            node_obj.perform_date = dt.strptime(cell['value'], '%Y-%m-%d')
            logger.debug('Set perform date: {}'.format(cell['value']))

        elif header_type == 'extract_label':
            node_obj.extract_label = cell['value']

    @classmethod
    def _collapse_process(cls, row_nodes, node, node_idx, comp_table, node_obj):
        """
        Collapse process into an existing one.

        :param row_nodes: List of dicts from editor UI
        :param node: Dict from editor UI
        :param comp_table: Study/assay table generated by
                           SampleSheetTableBuilder (dict)
        :param node_obj: Unsaved Process object
        :return: UUID of collapsed process (String or None)
        """
        # First get the UUIDs of existing nodes in the current row
        prev_new_uuid = None
        next_new_uuid = None
        iter_idx = 0

        while iter_idx < node_idx:
            if cls._get_name(row_nodes[iter_idx]):
                prev_new_uuid = row_nodes[iter_idx]['cells'][0].get('uuid')
            iter_idx += 1
        if not prev_new_uuid:
            logger.debug(
                'Collapse: Previous named node in current row not found'
            )
            return None

        iter_idx = node_idx + 1
        while not next_new_uuid and iter_idx < len(row_nodes):
            if cls._get_name(row_nodes[iter_idx]):
                next_new_uuid = row_nodes[iter_idx]['cells'][0].get('uuid')
            iter_idx += 1
        if not next_new_uuid:
            logger.debug('Collapse: Next named node in current row not found')
            return None

        # HACK: Get actual cell index
        col_idx = int(node['cells'][0]['header_field'][3:])

        for comp_row in comp_table['table_data']:
            iter_idx = 0
            same_protocol = False
            prev_old_uuid = None
            prev_old_name = None
            next_old_uuid = None

            # TODO: Can we trust that the protocol always comes first in node?
            if (
                not node_obj.protocol
                or comp_row[col_idx]['value'] == node_obj.protocol.name
            ):
                same_protocol = True

            while iter_idx < col_idx:
                if (
                    comp_table['field_header'][iter_idx]['type']
                    in ['name', 'process_name']
                    and comp_row[iter_idx]['value']
                ):
                    prev_old_uuid = comp_row[iter_idx]['uuid']
                    prev_old_name = comp_row[iter_idx]['value']
                iter_idx += 1

            if prev_old_uuid:
                logger.debug(
                    'Collapse: Found previous named node "{}" (UUID={})'.format(
                        prev_old_name, prev_old_uuid
                    )
                )
                iter_idx = col_idx + 1

                while not next_old_uuid and iter_idx < len(comp_row):
                    if (
                        comp_table['field_header'][iter_idx]['type']
                        in ['name', 'process_name']
                        and comp_row[iter_idx]['uuid']
                        != comp_row[col_idx]['uuid']
                        and comp_row[iter_idx]['value']
                    ):
                        next_old_uuid = comp_row[iter_idx]['uuid']
                        logger.debug(
                            'Collapse: Found next named node "{}" '
                            '(UUID={})'.format(
                                comp_row[iter_idx]['value'], next_old_uuid
                            )
                        )
                        break
                    iter_idx += 1

            if (
                prev_old_uuid
                and next_old_uuid
                and same_protocol
                and (prev_old_uuid == prev_new_uuid)
                and (next_old_uuid == next_new_uuid)
            ):
                logger.debug('Collapse: Comparing process objects..')
                collapse_uuid = comp_row[col_idx]['uuid']
                comp_obj = Process.objects.get(sodar_uuid=collapse_uuid)
                # Compare parameters
                # TODO: Compare other fields once supported
                if node_obj.parameter_values != comp_obj.parameter_values:
                    logger.debug('Collapse: Parameter values do not match')
                elif node_obj.performer != comp_obj.performer:
                    logger.debug('Collapse: Performer does not match')
                elif node_obj.perform_date != comp_obj.perform_date:
                    logger.debug('Collapse: Perform date does not match')
                else:
                    logger.debug('Collapse: Match found')
                    return collapse_uuid

            logger.debug('Collapse: Identical process not found')

    @transaction.atomic
    def _insert_row(self, row):
        """
        Insert row into a sample sheet.

        :param row: Dict from the UI
        :raise: SheetEditException if the operation fails.
        """
        sheet_io = SampleSheetIO()
        study = Study.objects.filter(sodar_uuid=row['study']).first()
        assay = None
        row_arcs = []
        parent = study
        if row['assay']:
            assay = Assay.objects.filter(sodar_uuid=row['assay']).first()
            parent = assay
        node_objects = []
        node_count = 0
        obj_kwargs = {}
        collapse = False
        comp_table = None
        logger.debug(
            'Inserting row in {} "{}" ({})'.format(
                parent.__class__.__name__,
                parent.get_display_name(),
                parent.sodar_uuid,
            )
        )

        # Check if we'll need to consider collapsing of unnamed nodes
        if len([n for n in row['nodes'] if not self._get_name(n)]) > 0:
            logger.debug('Unnamed node(s) in row, will attempt collapsing')
            collapse = True
            tb = SampleSheetTableBuilder()
            try:
                comp_study = tb.build_study_tables(
                    Study.objects.filter(sodar_uuid=row['study']).first(),
                    edit=True,
                )
            except Exception as ex:
                self._raise_ex(
                    'Error building tables for collapsing: {}'.format(ex)
                )
            if not assay:
                comp_table = comp_study['study']
            else:
                comp_table = comp_study['assays'][str(assay.sodar_uuid)]

        # Retrieve/build row nodes
        for node in row['nodes']:
            # logger.debug('Node headers: {}'.format(node['headers']))  # DEBUG
            name = self._get_name(node)
            new_node = True
            node_obj = None
            obj_cls = node['cells'][0]['obj_cls']
            uuid = node['cells'][0].get('uuid')

            ################
            # Existing Node
            ################

            if uuid:
                # Could also use eval() but it's unsafe
                node_obj = get_node_obj(sodar_uuid=uuid)
                if not node_obj:
                    self._raise_ex(
                        '{} not found (UUID={})'.format(obj_cls, uuid)
                    )
            # Named process is a special case
            # TODO: Also check column!
            elif obj_cls == 'Process' and name:
                node_obj = Process.objects.filter(
                    study=study, assay=assay, name=name
                ).first()

            if node_obj:
                new_node = False
                logger.debug(
                    'Node {}: Existing {} {}'.format(
                        node_count,
                        node_obj.__class__.__name__,
                        node_obj.sodar_uuid,
                    )
                )

            ##############
            # New Process
            ##############

            if not node_obj and obj_cls == 'Process':
                protocol = None
                unique_name = (
                    get_unique_name(study, assay, name) if name else None
                )

                # TODO: Can we trust that the protocol always comes first?
                if node['cells'][0]['header_type'] == 'protocol':
                    protocol = Protocol.objects.filter(
                        sodar_uuid=node['cells'][0]['uuid_ref']
                    ).first()
                    if not protocol:
                        self._raise_ex(
                            'Protocol not found with UUID={}'.format(
                                node['cells'][0]['uuid_ref']
                            )
                        )
                    unique_name = get_unique_name(study, assay, protocol.name)

                if not name and not protocol:
                    self._raise_ex(
                        'Protocol and name both missing from process'
                    )

                # NOTE: We create the object in memory regardless of collapse
                obj_kwargs = {
                    'name': name,
                    'unique_name': unique_name,
                    'name_type': None,
                    'protocol': protocol,
                    'study': study,
                    'assay': assay,
                    'performer': '' if 'Performer' in node['headers'] else None,
                    'perform_date': None,
                    'headers': node['headers'],
                }

                # Add name_type if found in headers
                for h in node['headers']:
                    if h in th.PROCESS_NAME_HEADERS:
                        obj_kwargs['name_type'] = h
                        break

                # TODO: array_design_ref
                # TODO: first_dimension
                # TODO: second_dimension
                node_obj = Process(**obj_kwargs)

            ###############
            # New Material
            ###############

            elif not node_obj and obj_cls == 'GenericMaterial':
                name_id = node['cells'][0]['value']
                if not name_id:
                    name_id = node['headers'][0]
                obj_kwargs = {
                    'item_type': node['cells'][0]['item_type'],
                    'name': node['cells'][0]['value'],
                    'unique_name': get_unique_name(
                        study,
                        assay,
                        name_id,
                        node['cells'][0]['item_type'],
                    ),
                    'study': study,
                    'assay': assay,
                    'material_type': node['headers'][0],
                    'factor_values': {},
                    'headers': node['headers'],
                }
                # TODO: extra_material_type
                # TODO: extract_label
                # TODO: alt_names
                node_obj = GenericMaterial(**obj_kwargs)

            ###################################
            # Fill New Node / Collapse Process
            ###################################

            if new_node:
                # Add common attributes
                for cell in node['cells'][1:]:
                    self._add_node_attr(node_obj, cell)

                collapse_uuid = None
                if (
                    node_obj.__class__ == Process
                    and not node_obj.name
                    and collapse
                    and node_count > 0
                ):
                    logger.debug('Unnamed process, attempting to collapse..')
                    collapse_uuid = self._collapse_process(
                        row['nodes'], node, node_count, comp_table, node_obj
                    )

                if collapse_uuid:  # Collapse successful
                    node_obj = Process.objects.get(sodar_uuid=collapse_uuid)
                    logger.debug(
                        'Node {}: Collapsed with existing {} {}'.format(
                            node_count,
                            node_obj.__class__.__name__,
                            node_obj.sodar_uuid,
                        )
                    )
                else:
                    node_obj.save()
                    logger.debug(
                        'Node {}: Created {} {}: {}'.format(
                            node_count,
                            node_obj.__class__.__name__,
                            node_obj.sodar_uuid,
                            obj_kwargs,
                        )
                    )

            node_objects.append(node_obj)
            node_count += 1

        # Build arcs
        for i in range(0, len(node_objects) - 1):
            row_arcs.append(
                [node_objects[i].unique_name, node_objects[i + 1].unique_name]
            )

        logger.debug('Row Arcs: {}'.format(row_arcs))

        # Add new arcs to parent
        for a in row_arcs:
            if a not in parent.arcs:
                parent.arcs.append(a)

        parent.save()

        # Attempt to export investigation with altamISA
        try:
            sheet_io.export_isa(study.investigation)
        except Exception as ex:
            self._raise_ex('altamISA Error: {}'.format(ex))

        logger.debug('Inserting row OK')
        # Return node UUIDs if successful
        return [str(o.sodar_uuid) for o in node_objects]

    def post(self, request, *args, **kwargs):
        inv = Investigation.objects.filter(
            project=self.get_project(), active=True
        ).first()
        new_row = request.data.get('new_row', None)
        if new_row:
            logger.debug('Row insert: {}'.format(json.dumps(new_row)))
            try:
                self.ok_data['node_uuids'] = self._insert_row(new_row)
                logger.debug('node_uuids={}'.format(self.ok_data['node_uuids']))
                # Update investigation ontology refs
                try:
                    self._update_ontology_refs(
                        inv, self._get_ontology_names(nodes=new_row['nodes'])
                    )
                except Exception as ex:
                    return Response({'detail': str(ex)}, status=500)
            except Exception as ex:
                return Response({'detail': str(ex)}, status=500)
        return Response(self.ok_data, status=200)


class SheetRowDeleteAjaxView(BaseSheetEditAjaxView):
    """Ajax view for deleting rows from sample sheets"""

    def _delete_node(self, node):
        """
        Delete node object from the database

        :param node: Dict
        """
        if node['obj'].id:  # It's possible we already deleted thit
            logger.debug(
                'Deleting node: {} {} (UUID={})'.format(
                    node['obj'].__class__.__name__,
                    node['unique_name'],
                    node['uuid'],
                )
            )
            node['obj'].delete()

    @transaction.atomic
    def _delete_row(self, row):
        """
        Delete row from a study/assay table. Also delete node objects from the
        database if unused after the row deletion.

        :param row: Dict from the UI
        :raise: SheetEditException if the operation fails.
        """
        tb = SampleSheetTableBuilder()
        sheet_io = SampleSheetIO()
        study = Study.objects.filter(sodar_uuid=row['study']).first()
        parent = study
        ui_nodes = row['nodes']
        sample_obj = None

        for node in ui_nodes:
            if node['obj_cls'] == 'GenericMaterial':
                node_obj = GenericMaterial.objects.filter(
                    sodar_uuid=node['uuid']
                ).first()
            else:
                node_obj = Process.objects.filter(
                    sodar_uuid=node['uuid']
                ).first()

            if not node_obj:
                self._raise_ex(
                    '{} not found (UUID={})'.format(
                        node['obj_cls'], node['uuid']
                    )
                )

            node['obj'] = node_obj
            node['unique_name'] = node_obj.unique_name
            if (
                node_obj.__class__ == GenericMaterial
                and node_obj.item_type == 'SAMPLE'
            ):
                sample_obj = node_obj

        if row['assay']:
            assay = Assay.objects.filter(sodar_uuid=row['assay']).first()
            parent = assay

        # Check for invalid deletion attempts we can detect at this point
        if parent == study:
            for s_assay in study.assays.all():
                if sample_obj.unique_name in [a[0] for a in s_assay.arcs]:
                    self._raise_ex(
                        'Sample used in assay(s), can not delete row from study'
                    )

        logger.debug(
            'Deleting row from {} "{}" ({})'.format(
                parent.__class__.__name__,
                parent.get_display_name(),
                parent.sodar_uuid,
            )
        )

        # Build reference table
        ref_study = Study.objects.get(sodar_uuid=row['study'])  # See issue #902
        study_nodes = ref_study.get_nodes()
        all_refs = tb.build_study_reference(ref_study, study_nodes)
        sample_idx = tb.get_sample_idx(all_refs)
        arc_del_count = 0

        if parent == study:
            table_refs = tb.get_study_refs(all_refs, sample_idx)
        else:
            assay_id = 0
            for a in study.assays.all().order_by('pk'):
                if parent == a:
                    break
                assay_id += 1
            table_refs = tb.get_assay_refs(
                all_refs, assay_id, sample_idx, study_cols=False
            )
            sample_idx = 0  # Set to 0 for further checks against the table

        for i in range(1, len(ui_nodes)):
            arc_count = 0
            node1_name = ui_nodes[i - 1]['unique_name']
            node2_name = ui_nodes[i]['unique_name']
            node1_count = 0
            node2_count = 0

            for ref_row in table_refs:
                if ref_row[i - 1] == node1_name and ref_row[i] == node2_name:
                    arc_count += 1
                if ref_row[i - 1] == node1_name:
                    node1_count += 1
                if ref_row[i] == node2_name:
                    node2_count += 1

            if arc_count == 1:
                logger.debug(
                    'Deleting arc: {} / {}'.format(node1_name, node2_name)
                )
                parent.arcs.remove([node1_name, node2_name])
                parent.save()
                if node1_count == 1 and (
                    parent == study or i - 1 != sample_idx
                ):
                    self._delete_node(ui_nodes[i - 1])
                if node2_count == 1 and (
                    parent == study or i - 1 != sample_idx
                ):
                    self._delete_node(ui_nodes[i])
                arc_del_count += 1

        if arc_del_count == 0:
            self._raise_ex('Did not find arcs to remove')

        study.investigation.save()

        # Attempt to export investigation with altamISA
        try:
            sheet_io.export_isa(study.investigation)
        except Exception as ex:
            self._raise_ex('altamISA Error: {}'.format(ex))

        logger.debug('Deleting row OK')

    def post(self, request, *args, **kwargs):
        del_row = request.data.get('del_row', None)
        if del_row:
            logger.debug('Row delete: {}'.format(json.dumps(del_row)))
            try:
                self._delete_row(del_row)
            except self.SheetEditException as ex:
                return Response({'detail': str(ex)}, status=500)
        return Response(self.ok_data, status=200)


class SheetVersionSaveAjaxView(SheetVersionMixin, SODARBaseProjectAjaxView):
    """Ajax view for saving current sample sheet version as ISATab backup"""

    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        log_msg = 'Save sheet version: '
        isa_version = None
        project = self.get_project()
        inv = Investigation.objects.filter(project=project, active=True).first()
        export_ex = None

        try:
            isa_version = self.save_version(
                inv, request, request.data.get('description') or None
            )
        except Exception as ex:
            logger.error(
                log_msg + 'Unable to export sheet to ISA-Tab: {}'.format(ex)
            )
            export_ex = str(ex)

        if timeline:
            tl_status = 'FAILED' if export_ex else 'OK'
            tl_desc = 'save sheet version'
            if not export_ex and isa_version:
                tl_desc += ' as {isatab}'
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=request.user,
                event_name='sheet_version_save',
                description=tl_desc,
                status_type=tl_status,
                status_desc=export_ex if tl_status == 'FAILED' else None,
            )
            if not export_ex and isa_version:
                tl_event.add_object(
                    obj=isa_version,
                    label='isatab',
                    name=isa_version.get_full_name(),
                )

        if not export_ex and isa_version:
            return Response({'detail': 'ok'}, status=200)

        return Response({'detail': export_ex}, status=500)


class SheetEditFinishAjaxView(SheetVersionMixin, SODARBaseProjectAjaxView):
    """
    View for finishing editing and saving an ISA-Tab copy of the current
    sample sheet.
    """

    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        log_msg = 'Finish editing: '
        updated = request.data.get('updated')
        if not updated:
            logger.info(log_msg + 'nothing updated')
            return Response({'detail': 'ok'}, status=200)  # Nothing to do

        timeline = get_backend_api('timeline_backend')
        isa_version = None
        project = self.get_project()
        inv = Investigation.objects.filter(project=project, active=True).first()
        export_ex = None

        if not request.data.get('version_saved'):
            try:
                isa_version = self.save_version(inv, request)
            except Exception as ex:
                logger.error(
                    log_msg + 'Unable to export sheet to ISA-Tab: {}'.format(ex)
                )
                export_ex = str(ex)

        if timeline:
            tl_status = 'FAILED' if export_ex else 'OK'
            tl_desc = 'finish editing sheets '
            if not updated:
                tl_desc += '(no updates)'
            elif not export_ex and isa_version:
                tl_desc += 'and save version as {isatab}'
            else:
                tl_desc += '(saving version failed)'
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=request.user,
                event_name='sheet_edit_finish',
                description=tl_desc,
                status_type=tl_status,
                status_desc=export_ex if tl_status == 'FAILED' else None,
            )
            if not export_ex and isa_version:
                tl_event.add_object(
                    obj=isa_version,
                    label='isatab',
                    name=isa_version.get_full_name(),
                )

        if not export_ex:
            if isa_version:
                logger.info(
                    log_msg
                    + 'Saved ISA-Tab "{}"'.format(isa_version.get_full_name())
                )
            inv.save()  # Update date_modified
            return Response({'detail': 'ok'}, status=200)

        return Response({'detail': export_ex}, status=500)


class SheetEditConfigAjaxView(EditConfigMixin, SODARBaseProjectAjaxView):
    """View to update sample sheet editing configuration"""

    # NOTE: Currently not requiring manage_sheet perm (see issue #880)
    permission_required = 'samplesheets.edit_sheet'

    # TODO: Add node name for logging/timeline
    def post(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        project = self.get_project()
        fields = request.data.get('fields')
        sheet_config = app_settings.get_app_setting(
            APP_NAME, 'sheet_config', project=project
        )

        if not self._can_edit_config(request.user, project):
            return Response(
                {'detail': 'User not allowed to modify column config'},
                status=403,
            )

        for field in fields:
            logger.debug('Field config: {}'.format(field))
            s_uuid = field['study']
            a_uuid = field['assay']
            n_idx = field['node_idx']
            f_idx = field['field_idx']
            is_name = True if field['config']['name'] == 'Name' else False
            debug_info = 'study="{}"; assay="{}"; n={}; f={})'.format(
                s_uuid, a_uuid, n_idx, f_idx
            )

            try:
                if a_uuid:
                    og_config = sheet_config['studies'][s_uuid]['assays'][
                        a_uuid
                    ]['nodes'][n_idx]['fields'][f_idx]
                else:
                    og_config = sheet_config['studies'][s_uuid]['nodes'][n_idx][
                        'fields'
                    ][f_idx]
            except Exception as ex:
                msg = 'Unable to access config field ({}): {}'.format(
                    debug_info, ex
                )
                logger.error(msg)
                return Response({'detail': msg}, status=500)

            if not is_name and (
                field['config']['name'] != og_config['name']
                or (
                    og_config.get('type')
                    and field['config']['type'] != og_config['type']
                )
            ):
                msg = 'Fields do not match ({})'.format(debug_info)
                logger.error(msg)
                return Response({'detail': msg}, status=500)

            # Cleanup data
            c = field['config']

            if not is_name:
                if c['format'] != 'integer':
                    c.pop('range', None)
                    c.pop('unit', None)
                    c.pop('unit_default', None)
                elif 'range' in c and not c['range'][0] and not c['range'][1]:
                    c.pop('range', None)
                if c['format'] in ['protocol', 'select']:
                    c.pop('regex', None)
                if c['format'] != 'select':
                    c.pop('options', None)

            if a_uuid:
                sheet_config['studies'][s_uuid]['assays'][a_uuid]['nodes'][
                    n_idx
                ]['fields'][f_idx] = c
            else:
                sheet_config['studies'][s_uuid]['nodes'][n_idx]['fields'][
                    f_idx
                ] = c

            app_settings.set_app_setting(
                APP_NAME, 'sheet_config', sheet_config, project=project
            )
            logger.info(
                'Updated field config for "{}" ({}) in {} {}'.format(
                    c['name'],
                    'name' if is_name else c.get('type'),
                    'assay' if a_uuid else 'study',
                    a_uuid if a_uuid else s_uuid,
                )
            )

            # TODO: Update default display config (and user configurations?)

            if timeline:
                if a_uuid:
                    tl_obj = Assay.objects.filter(sodar_uuid=a_uuid).first()
                else:
                    tl_obj = Study.objects.filter(sodar_uuid=s_uuid).first()
                tl_label = tl_obj.__class__.__name__.lower()
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=request.user,
                    event_name='field_update',
                    description='update field configuration for "{}" '
                    'in {{{}}}'.format(c['name'].title(), tl_label),
                    status_type='OK',
                    extra_data={'config': c},
                )
                tl_event.add_object(
                    obj=tl_obj, label=tl_label, name=tl_obj.get_display_name()
                )

        # TODO: Update investigation ontology reference, return list
        return Response({'detail': 'ok'}, status=200)


class StudyDisplayConfigAjaxView(SODARBaseProjectAjaxView):
    """View to update sample sheet display configuration for a study"""

    permission_required = 'samplesheets.view_sheet'

    def post(self, request, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        study_uuid = self.kwargs.get('study')
        study = Study.objects.filter(sodar_uuid=study_uuid).first()
        if not study:
            return Response({'detail': 'Study not found'}, status=404)
        project = study.investigation.project
        study_config = request.data.get('study_config')
        if not study_config:
            return Response(
                {'detail': 'No study configuration provided'}, status=400
            )

        # Set current configuration as default if selected
        set_default = request.data.get('set_default')
        ret_default = False

        if set_default:
            default_config = app_settings.get_app_setting(
                APP_NAME, 'display_config_default', project=project
            )
            default_config['studies'][study_uuid] = study_config
            ret_default = app_settings.set_app_setting(
                APP_NAME,
                'display_config_default',
                project=project,
                value=default_config,
            )

            if timeline and ret_default:
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=request.user,
                    event_name='display_update',
                    description='update default column display configuration '
                    'for {study}',
                    status_type='OK',
                )
                tl_event.add_object(
                    obj=study, label='study', name=study.get_display_name()
                )

        # Get user display config
        display_config = app_settings.get_app_setting(
            APP_NAME, 'display_config', project=project, user=request.user
        )
        display_config['studies'][study_uuid] = study_config
        ret = app_settings.set_app_setting(
            APP_NAME,
            'display_config',
            project=project,
            user=request.user,
            value=display_config,
        )
        return Response(
            {'detail': 'ok' if ret or ret_default else 'Nothing to update'},
            status=200,
        )


class IrodsRequestCreateAjaxView(
    IrodsRequestModifyMixin, SODARBaseProjectAjaxView
):
    """Ajax view for creating an iRODS data request"""

    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        project = self.get_project()
        path = request.data.get('path')

        # Create database object
        old_request = IrodsDataRequest.objects.filter(
            path=path, status__in=['ACTIVE', 'FAILED']
        ).first()
        if old_request:
            return Response(
                {'detail': 'active request for path already exists'}, status=400
            )

        irods_request = IrodsDataRequest.objects.create(
            path=path,
            user=request.user,
            project=project,
            description='Request created via Ajax API',
        )

        # Create timeline event
        self.add_tl_create(irods_request)
        # Add app alerts to owners/delegates
        self.add_alerts_create(project)
        return Response(
            {
                'detail': 'ok',
                'status': irods_request.status,
                'user': str(request.user.sodar_uuid),
            },
            status=200,
        )


class IrodsRequestDeleteAjaxView(
    IrodsRequestModifyMixin, SODARBaseProjectAjaxView
):
    """Ajax view for deleting an iRODS data request"""

    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        # Delete database object
        irods_request = IrodsDataRequest.objects.filter(
            path=request.data.get('path'),
            status__in=['ACTIVE', 'FAILED'],
        ).first()
        if not irods_request:
            return Response({'detail': 'Request not found'}, status=404)
        if not (
            request.user.is_superuser or request.user == irods_request.user
        ):
            return Response(
                {'detail': 'User not allowed to delete request'}, status=403
            )

        # Add timeline event
        self.add_tl_delete(irods_request)
        # Handle project alerts
        self.handle_alerts_deactivate(irods_request)
        irods_request.delete()
        return Response(
            {
                'detail': 'ok',
                'status': None,
                'user': None,
            },
            status=200,
        )


class IrodsObjectListAjaxView(BaseIrodsAjaxView):
    """View for listing data objects in iRODS recursively"""

    permission_required = 'samplesheets.view_sheet'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = None
        self.path = None

    def get(self, request, *args, **kwargs):
        try:
            irods_backend = get_backend_api('omics_irods')
        except Exception as ex:
            return Response({'detail': str(ex)}, status=400)
        # Get files
        try:
            ret_data = irods_backend.get_objects(self.path)
        except Exception as ex:
            return Response({'detail': str(ex)}, status=400)
        for data_obj in ret_data.get('irods_data', []):
            obj = IrodsDataRequest.objects.filter(
                path=data_obj['path'], status__in=['ACTIVE', 'FAILED']
            ).first()
            data_obj['irods_request_status'] = obj.status if obj else None
            data_obj['irods_request_user'] = (
                str(obj.user.sodar_uuid) if obj else None
            )
        return Response(ret_data, status=200)


class SheetVersionCompareAjaxView(SODARBaseProjectAjaxView):
    """View for listing data objects in iRODS recursively"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = None
        self.path = None

    permission_required = 'samplesheets.edit_sheet'

    def get(self, request, *args, **kwargs):
        category = request.GET.get('category')
        filename = request.GET.get('filename')
        try:
            source = ISATab.objects.get(sodar_uuid=request.GET.get('source'))
            target = ISATab.objects.get(sodar_uuid=request.GET.get('target'))
        except ISATab.DoesNotExist:
            return Response(
                {'detail': 'Sample sheet version(s) not found.'}, status=500
            )

        ret_data = {}

        # If category and filename are given, only return diff data for one file
        if category and filename:
            ret_data = [
                [
                    line.split('\t')
                    for line in source.data.get(category, {})
                    .get(filename, {})
                    .get('tsv', '')
                    .replace('"', '')
                    .split('\n')
                ],
                [
                    line.split('\t')
                    for line in target.data.get(category, {})
                    .get(filename, {})
                    .get('tsv', '')
                    .replace('"', '')
                    .split('\n')
                ],
            ]
            return Response(ret_data, status=200)

        # If filename and/or category are missing, generate diff for
        # the whole samplesheet
        categories = ('studies', 'assays')

        for category in categories:
            ret_data[category] = {}

        for category in categories:
            for filename, data in source.data.get(category, {}).items():
                ret_data[category][filename] = [
                    [
                        line.split('\t')
                        for line in data['tsv'].replace('"', '').split('\n')
                    ],
                    [
                        line.split('\t')
                        for line in target.data.get(category, {})
                        .get(filename, {})
                        .get('tsv', '')
                        .replace('"', '')
                        .split('\n')
                    ],
                ]

        for category in categories:
            for filename, data in target.data.get(category, {}).items():
                if filename not in ret_data[category]:
                    ret_data[category][filename] = [
                        [
                            line.split('\t')
                            for line in data['tsv'].replace('"', '').split('\n')
                        ],
                        [
                            line.split('\t')
                            for line in target.data.get(category, {})
                            .get(filename, {})
                            .get('tsv', '')
                            .replace('"', '')
                            .split('\n')
                        ],
                    ]

        return Response(ret_data, status=200)
