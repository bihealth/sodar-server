"""Ajax API views for the samplesheets app"""

from altamisa.constants import table_headers as th
from datetime import datetime as dt
import json
from packaging import version
import random
import string

from django.conf import settings
from django.db import transaction
from django.middleware.csrf import get_token
from django.urls import reverse

from rest_framework.response import Response

# Projectroles dependency
from projectroles.plugins import get_backend_api
from projectroles.views_ajax import SODARBaseProjectAjaxView

from samplesheets.io import SampleSheetIO
from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    Protocol,
    Process,
    GenericMaterial,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import (
    get_comments,
    build_sheet_config,
    build_display_config,
)
from samplesheets.views import (
    app_settings,
    APP_NAME,
    TARGET_ALTAMISA_VERSION,
    RESULTS_COLL_ID,
    RESULTS_COLL,
    MISC_FILES_COLL_ID,
    MISC_FILES_COLL,
    logger,
)


# Local constants
EDIT_JSON_ATTRS = [
    'characteristics',
    'comments',
    'factor_values',
    'parameter_values',
]
ATTR_HEADER_MAP = {
    'characteristics': th.CHARACTERISTICS,
    'comments': th.COMMENT,
    'factor_values': th.FACTOR_VALUE,
    'parameter_values': th.PARAMETER_VALUE,
}
EDIT_FIELD_MAP = {
    'array design ref': 'array_design_ref',
    'label': 'extract_label',
    'performer': 'performer',
}


class SampleSheetContextAjaxView(SODARBaseProjectAjaxView):
    """View to retrieve sample sheet context data"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        studies = Study.objects.filter(investigation=investigation).order_by(
            'pk'
        )
        irods_backend = get_backend_api('omics_irods', conn=False)

        # Can't import at module root due to circular dependency
        from .plugins import find_study_plugin, find_assay_plugin

        # General context data for Vue app
        ret_data = {
            'configuration': investigation.get_configuration()
            if investigation
            else None,
            'inv_file_name': investigation.file_name.split('/')[-1]
            if investigation
            else None,
            'irods_status': investigation.irods_status
            if investigation
            else None,
            'irods_backend_enabled': (True if irods_backend else False),
            'parser_version': (investigation.parser_version or 'LEGACY')
            if investigation
            else None,
            'parser_warnings': True
            if investigation
            and investigation.parser_warnings
            and 'use_file_names' in investigation.parser_warnings
            else False,
            'irods_webdav_enabled': settings.IRODS_WEBDAV_ENABLED,
            'irods_webdav_url': settings.IRODS_WEBDAV_URL.rstrip('/'),
            'external_link_labels': settings.SHEETS_EXTERNAL_LINK_LABELS,
            'table_height': settings.SHEETS_TABLE_HEIGHT,
            'min_col_width': settings.SHEETS_MIN_COLUMN_WIDTH,
            'max_col_width': settings.SHEETS_MAX_COLUMN_WIDTH,
            'allow_editing': app_settings.get_app_setting(
                APP_NAME, 'allow_editing', project=project
            ),
            'alerts': [],
            'csrf_token': get_token(request),
        }

        if investigation and (
            not investigation.parser_version
            or version.parse(investigation.parser_version)
            < version.parse(TARGET_ALTAMISA_VERSION)
        ):
            ret_data['alerts'].append(
                {
                    'level': 'danger',
                    'text': 'This sample sheet has been imported with an '
                    'old altamISA version (< {}). Please replace the ISAtab '
                    'to enable all features and ensure full '
                    'functionality.'.format(TARGET_ALTAMISA_VERSION),
                }
            )

        # Study info
        ret_data['studies'] = {}

        for s in studies:
            study_plugin = find_study_plugin(investigation.get_configuration())
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
                assay_plugin = find_assay_plugin(
                    a.measurement_type, a.technology_type
                )
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
            'is_superuser': request.user.is_superuser,
        }

        # Overview data
        ret_data['investigation'] = (
            {
                'identifier': investigation.identifier,
                'title': investigation.title,
                'description': investigation.description
                if investigation.description != project.description
                else None,
                'comments': get_comments(investigation),
            }
            if investigation
            else {}
        )

        # Statistics
        ret_data['sheet_stats'] = (
            {
                'study_count': Study.objects.filter(
                    investigation=investigation
                ).count(),
                'assay_count': Assay.objects.filter(
                    study__investigation=investigation
                ).count(),
                'protocol_count': Protocol.objects.filter(
                    study__investigation=investigation
                ).count(),
                'process_count': Process.objects.filter(
                    protocol__study__investigation=investigation
                ).count(),
                'source_count': investigation.get_material_count('SOURCE'),
                'material_count': investigation.get_material_count('MATERIAL'),
                'sample_count': investigation.get_material_count('SAMPLE'),
                'data_count': investigation.get_material_count('DATA'),
            }
            if investigation
            else {}
        )

        ret_data = json.dumps(ret_data)
        return Response(ret_data, status=200)


class SampleSheetStudyTablesAjaxView(SODARBaseProjectAjaxView):
    """View to retrieve study tables built from the sample sheet graph"""

    def get_permission_required(self):
        """Override get_permisson_required() to provide the approrpiate perm"""
        if bool(self.request.GET.get('edit')):
            return 'samplesheets.edit_sheet'

        return 'samplesheets.view_sheet'

    def _get_sheet_config(self, investigation):
        """Get or create sheet configuration for an investigation"""

        sheet_config = app_settings.get_app_setting(
            APP_NAME, 'sheet_config', project=investigation.project
        )

        if not sheet_config:
            logger.debug('No sheet configuration found, building..')
            sheet_config = build_sheet_config(investigation)
            app_settings.set_app_setting(
                APP_NAME,
                'sheet_config',
                sheet_config,
                project=investigation.project,
            )
            logger.info('Sheet configuration built for investigation')

        return sheet_config

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
                APP_NAME, 'display_config_default', project=project,
            )

        # If default display configuration is not found, build it
        if not display_config:
            logger.debug('No default display configuration found, building..')

            if not sheet_config:
                sheet_config = self._get_sheet_config(investigation)

            display_config = build_display_config(investigation, sheet_config)

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
                'Setting display config for user "{}" in project "{}" ({})'.format(
                    user.username, project.title, project.sodar_uuid
                )
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
        timeline = get_backend_api('timeline_backend')
        irods_backend = get_backend_api('omics_irods', conn=False)
        cache_backend = get_backend_api('sodar_cache')
        study = Study.objects.filter(sodar_uuid=self.kwargs['study']).first()

        if not study:
            return Response(
                {
                    'render_error': 'Study not found with UUID "{}", '
                    'unable to render'.format(self.kwargs['study'])
                },
                status=404,
            )

        # Return extra edit mode data
        project = study.investigation.project
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
        if not edit and study.investigation.irods_status and irods_backend:
            # Can't import at module root due to circular dependency
            from .plugins import find_study_plugin
            from .plugins import find_assay_plugin

            # Get study plugin for shortcut data
            study_plugin = find_study_plugin(
                study.investigation.get_configuration()
            )

            if study_plugin:
                shortcuts = study_plugin.get_shortcut_column(
                    study, ret_data['tables']
                )
                ret_data['tables']['study']['shortcuts'] = shortcuts

            # Get assay content if corresponding assay plugin exists
            for a_uuid, a_data in ret_data['tables']['assays'].items():
                assay = Assay.objects.filter(sodar_uuid=a_uuid).first()
                assay_path = irods_backend.get_path(assay)
                a_data['irods_paths'] = []

                # Default shortcuts
                a_data['shortcuts'] = [
                    {
                        'id': RESULTS_COLL_ID,
                        'label': 'Results and Reports',
                        'path': assay_path + '/' + RESULTS_COLL,
                    },
                    {
                        'id': MISC_FILES_COLL_ID,
                        'label': 'Misc Files',
                        'path': assay_path + '/' + MISC_FILES_COLL,
                    },
                ]

                assay_plugin = find_assay_plugin(
                    assay.measurement_type, assay.technology_type
                )

                if assay_plugin:
                    cache_item = cache_backend.get_cache_item(
                        name='irods/rows/{}'.format(a_uuid),
                        app_name=assay_plugin.app_name,
                        project=assay.get_project(),
                    )

                    for row in a_data['table_data']:
                        # Update assay links column
                        path = assay_plugin.get_row_path(
                            row, a_data, assay, assay_path
                        )
                        enabled = True

                        # Set initial state to disabled by cached value
                        if (
                            cache_item
                            and path in cache_item.data['paths']
                            and (
                                not cache_item.data['paths'][path]
                                or cache_item.data['paths'][path] == 0
                            )
                        ):
                            enabled = False

                        a_data['irods_paths'].append(
                            {'path': path, 'enabled': enabled}
                        )
                        # Update row links
                        assay_plugin.update_row(row, a_data, assay)

                    # Add extra table if available
                    a_data['shortcuts'].extend(
                        assay_plugin.get_shortcuts(assay) or []
                    )

                # Check assay shortcut cache and set initial enabled value
                cache_item = cache_backend.get_cache_item(
                    name='irods/shortcuts/assay/{}'.format(a_uuid),
                    app_name=APP_NAME,
                    project=assay.get_project(),
                )

                for i in range(len(a_data['shortcuts'])):
                    if cache_item:
                        a_data['shortcuts'][i]['enabled'] = cache_item.data[
                            'shortcuts'
                        ].get(a_data['shortcuts'][i]['id'])

                    else:
                        a_data['shortcuts'][i]['enabled'] = True

        # Get/build sheet config
        sheet_config = self._get_sheet_config(study.investigation)

        # Get/build display config
        display_config = self._get_display_config(
            study.investigation, request.user, sheet_config
        )

        ret_data['display_config'] = display_config['studies'][
            str(study.sodar_uuid)
        ]

        # Set up editing
        if edit:
            # Get study config
            ret_data['study_config'] = sheet_config['studies'][
                str(study.sodar_uuid)
            ]

            # Set up study edit context
            ret_data['edit_context'] = {'samples': [], 'protocols': []}

            # Add sample info
            for sample in GenericMaterial.objects.filter(
                study=study, item_type='SAMPLE'
            ).order_by('name'):
                ret_data['edit_context']['samples'].append(
                    {'uuid': str(sample.sodar_uuid), 'name': sample.name}
                )

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
                    description='started editing sheets',
                    status_type='OK',
                )

        return Response(ret_data, status=200)


class SampleSheetStudyLinksAjaxView(SODARBaseProjectAjaxView):
    """View to retrieve data for shortcut links from study apps"""

    # TODO: Also do this for assay apps?
    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        study = Study.objects.filter(sodar_uuid=self.kwargs['study']).first()

        # Get study plugin for shortcut data
        from .plugins import find_study_plugin

        study_plugin = find_study_plugin(
            study.investigation.get_configuration()
        )

        if not study_plugin:
            return Response(
                {'message': 'Plugin not found for study'}, status=404
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


class SampleSheetWarningsAjaxView(SODARBaseProjectAjaxView):
    """View to retrieve parser warnings for sample sheets"""

    permission_required = 'samplesheets.view_sheet'

    def get(self, request, *args, **kwargs):
        investigation = Investigation.objects.filter(
            project=self.get_project()
        ).first()

        if not investigation:
            return Response(
                {'message': 'Investigation not found for project'}, status=404
            )

        return Response({'warnings': investigation.parser_warnings}, status=200)


class SampleSheetEditAjaxView(SODARBaseProjectAjaxView):
    """View to edit sample sheet data"""

    permission_required = 'samplesheets.edit_sheet'

    class SheetEditException(Exception):
        pass

    def _raise_ex(self, msg):
        logger.error(msg)
        raise self.SheetEditException(msg)

    @transaction.atomic
    def _update_cell(self, obj, cell, save=False):
        """
        Update a single cell in an object.

        :param obj: GenericMaterial or Process object
        :param cell: Cell update data from the client (dict)
        :param save: If True, save object after successful call (boolean)
        :return: String
        :raise: SheetEditException if the operation fails.
        """
        ok_msg = None
        logger.debug(
            'Editing {} "{}" ({})'.format(
                obj.__class__.__name__, obj.unique_name, obj.sodar_uuid
            )
        )
        # TODO: Provide the original header as one string instead
        header_type = cell['header_type']
        header_name = cell['header_name']

        # Plain fields
        if not header_type and header_name.lower() in EDIT_FIELD_MAP:
            attr_name = EDIT_FIELD_MAP[header_name.lower()]
            attr = getattr(obj, attr_name)

            if isinstance(attr, str):
                setattr(obj, attr_name, cell['value'])

            elif isinstance(attr, dict):
                attr['name'] = cell['value']

                # TODO: Set accession and ontology once editing is allowed

            ok_msg = 'Edited field: {}'.format(attr_name)

        # Name field (special case)
        elif header_type == 'name':
            if len(cell['value']) == 0 and cell.get('item_type') != 'DATA':
                self._raise_ex('Empty name not allowed for non-data node')

            obj.name = cell['value']
            # TODO: Update unique name here if needed
            ok_msg = 'Edited node name: {}'.format(cell['value'])

        # Process name and name type (special case)
        elif header_type == 'process_name':
            obj.name = cell['value']

            if cell['header_name'] in th.PROCESS_NAME_HEADERS:
                obj.name_type = cell['header_name']

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

            obj.protocol = protocol
            ok_msg = 'Edited protocol ref: "{}" ({})'.format(
                cell['value'], cell['uuid_ref']
            )

        # Performer (special case)
        elif header_type == 'performer':
            obj.performer = cell['value']

        # Perform date (special case)
        elif header_type == 'perform_date':
            if cell['value']:
                try:
                    obj.perform_date = dt.strptime(cell['value'], '%Y-%m-%d')

                except ValueError as ex:
                    self._raise_ex(ex)

            else:
                obj.perform_date = None

        # JSON Attributes
        elif header_type in EDIT_JSON_ATTRS:
            attr = getattr(obj, header_type)

            # TODO: Is this actually a thing nowadays?
            if isinstance(attr[header_name], str):
                attr[header_name] = cell['value']

            elif isinstance(attr[header_name], dict):
                # TODO: Ontology value and list support
                attr[header_name]['value'] = cell['value']

                # TODO: Support ontology ref in unit
                if 'unit' not in attr[header_name] or isinstance(
                    attr[header_name]['unit'], str
                ):
                    attr[header_name]['unit'] = cell.get('unit')

                elif isinstance(attr[header_name]['unit'], dict):
                    attr[header_name]['unit']['name'] = cell.get('unit')

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
            obj.save()

            if ok_msg:
                logger.debug(ok_msg)

        return ok_msg

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
    def _get_unique_name(cls, study, assay, name, item_type=None):
        """
        Return unique name for a node.

        :param study: Study object
        :param assay: Assay object
        :param name: Display name for material
        :param item_type: Item type for materials (string)
        :return: String
        """

        # HACK: This will of course not work on empty tables..
        # TODO: Refactor once we allow creating sheets from scratch
        study_id = study.arcs[0][0].split('-')[1][1:]
        assay_id = 0

        if assay and study.assays.all().count() > 1:
            assay_id = sorted([a.file_name for a in study.assays.all()]).index(
                assay.file_name
            )

        return 'p{}-s{}-{}{}{}-{}'.format(
            study.investigation.project.pk,
            study_id,
            'a{}-'.format(assay_id) if assay else '',
            '{}-'.format(item_type.lower()) if item_type else '',
            name,
            ''.join(
                random.SystemRandom().choice(string.ascii_lowercase)
                for _ in range(8)
            ),
        )

    @classmethod
    def _add_node_attr(cls, node_obj, cell):
        """
        Add common node attribute from cell in a new row node.

        :param node_obj: GenericMaterial or Process
        :param cell: Dict
        """
        header_name = cell['header_name']
        header_type = cell['header_type']

        if header_type in EDIT_JSON_ATTRS:
            attr = getattr(node_obj, header_type)
            # Check if we have ontology refs and alter value
            h_idx = node_obj.headers.index(
                '{}[{}]'.format(ATTR_HEADER_MAP[header_type], header_name)
            )

            if (
                h_idx
                and h_idx < len(node_obj.headers) - 1
                and node_obj.headers[h_idx + 1]
                in [th.TERM_SOURCE_REF, th.TERM_ACCESSION_NUMBER]
                and not isinstance(cell['value'], dict)
            ):
                attr[header_name] = {
                    'value': {
                        'name': cell.get('value'),
                        'accession': None,
                        'ontology_name': None,
                    }
                }

            else:
                attr[header_name] = {'value': cell['value']}

            # TODO: Support ontology ref in unit for real
            if (
                h_idx < len(node_obj.headers) - 2
                and node_obj.headers[h_idx + 1] == 'Unit'
                and node_obj.headers[h_idx + 2]
                in [th.TERM_SOURCE_REF, th.TERM_ACCESSION_NUMBER]
            ):
                attr[header_name]['unit'] = {
                    'name': cell.get('unit'),
                    'ontology_name': None,
                    'accession': None,
                }

            elif (
                h_idx < len(node_obj.headers) - 2
                and node_obj.headers[h_idx + 1] == 'Unit'
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

                iter_idx += 1

            if prev_old_uuid:
                logger.debug(
                    'Collapse: Found previous named node "{}"'.format(
                        comp_row[iter_idx - 1]['value']
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
                            'Collapse: Found next named node "{}"'.format(
                                comp_row[iter_idx]['value']
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
        sheet_io = SampleSheetIO()
        study = Study.objects.filter(sodar_uuid=row['study']).first()
        assay = None
        row_arcs = []
        parent = study

        if row['assay']:
            assay = Assay.objects.filter(sodar_uuid=row['assay']).first()
            parent = assay

        logger.debug(
            'Inserting row in {} "{}" ({})'.format(
                parent.__class__.__name__,
                parent.get_display_name(),
                parent.sodar_uuid,
            )
        )

        node_objects = []
        node_count = 0
        obj_kwargs = {}
        collapse = False
        comp_table = None

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

            ################
            # Existing Node
            ################

            if node['cells'][0].get('uuid'):
                new_node = False
                node_obj = None
                # Could also use eval() but it's unsafe
                if node['cells'][0]['obj_cls'] == 'GenericMaterial':
                    node_obj = GenericMaterial.objects.filter(
                        sodar_uuid=node['cells'][0]['uuid']
                    ).first()

                elif node['cells'][0]['obj_cls'] == 'Process':
                    node_obj = Process.objects.filter(
                        sodar_uuid=node['cells'][0]['obj_cls']
                    ).first()

                if not node_obj:
                    self._raise_ex(
                        '{} not found (UUID={})'.format(
                            node['cells'][0]['obj_cls'],
                            node['cells'][0]['uuid'],
                        )
                    )

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

            elif node['cells'][0]['obj_cls'] == 'Process':
                new_node = True
                name = self._get_name(node)
                protocol = None
                unique_name = (
                    self._get_unique_name(study, assay, name) if name else None
                )

                # TODO: Can we trust that the protocol always comes first?
                if node['cells'][0]['header_type'] == 'protocol':
                    protocol = Protocol.objects.filter(
                        sodar_uuid=node['cells'][0]['uuid_ref']
                    ).first()

                    if not name:
                        unique_name = self._get_unique_name(
                            study, assay, protocol.name
                        )

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

            else:
                new_node = True
                name_id = node['cells'][0]['value']

                if not name_id:
                    name_id = node['headers'][0]

                obj_kwargs = {
                    'item_type': node['cells'][0]['item_type'],
                    'name': node['cells'][0]['value'],
                    'unique_name': self._get_unique_name(
                        study, assay, name_id, node['cells'][0]['item_type'],
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

        parent.arcs += row_arcs
        logger.debug('Row Arcs: {}'.format(row_arcs))
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
        ok_data = {'message': 'ok'}
        new_row = request.data.get('new_row', None)
        updated_cells = request.data.get('updated_cells', [])

        ################
        # Row Inserting
        ################
        if new_row:
            logger.debug('Row insert: {}'.format(json.dumps(new_row)))

            try:
                ok_data['node_uuids'] = self._insert_row(new_row)
                logger.debug('node_uuids={}'.format(ok_data['node_uuids']))

            except self.SheetEditException as ex:
                return Response({'message': str(ex)}, status=500)

        #######################
        # Single Cell Updating
        #######################
        for cell in updated_cells:
            logger.debug('Cell update: {}'.format(cell))
            obj_cls = (
                GenericMaterial
                if cell['obj_cls'] == 'GenericMaterial'
                else Process
            )
            obj = obj_cls.objects.filter(sodar_uuid=cell['uuid']).first()
            # TODO: Make sure given object actually belongs in project etc.

            if not obj:
                err_msg = 'Object not found: {} ({})'.format(
                    cell['uuid'], cell['obj_cls']
                )
                logger.error(err_msg)

                # TODO: Return list of errors when processing in batch
                return Response({'message': err_msg}, status=500)

            # Update cell, save immediately (now we are only editing one cell)
            try:
                self._update_cell(obj, cell, save=True)

            except self.SheetEditException as ex:
                return Response({'message': str(ex)}, status=500)

        # TODO: Log edits in timeline here, once saving in bulk
        return Response(ok_data, status=200)


class SampleSheetEditFinishAjaxView(SODARBaseProjectAjaxView):
    """View for finishing editing and saving an ISAtab copy of the current
    sample sheet"""

    permission_required = 'samplesheets.edit_sheet'

    def post(self, request, *args, **kwargs):
        updated = request.data.get('updated')
        log_msg = 'Finish editing: '

        if not updated:
            logger.info(log_msg + 'nothing updated')
            return Response({'message': 'ok'}, status=200)  # Nothing to do

        timeline = get_backend_api('timeline_backend')
        isa_version = None
        sheet_io = SampleSheetIO()
        project = self.get_project()
        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        export_ex = None

        try:
            isa_data = sheet_io.export_isa(investigation)

            # Save sheet config with ISATab version
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
            )

        except Exception as ex:
            logger.error(
                log_msg + 'Unable to export sheet to ISAtab: {}'.format(ex)
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
                    obj=isa_version, label='isatab', name=isa_version.get_name()
                )

        if not export_ex:
            logger.info(
                log_msg + 'Saved ISATab "{}"'.format(isa_version.get_name())
            )
            return Response({'message': 'ok'}, status=200)

        return Response({'message': export_ex}, status=500)


class SampleSheetManageAjaxView(SODARBaseProjectAjaxView):
    """View to manage sample sheet editing configuration"""

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
                return Response({'message': msg}, status=500)

            if not is_name and (
                field['config']['name'] != og_config['name']
                or (
                    og_config.get('type')
                    and field['config']['type'] != og_config['type']
                )
            ):
                msg = 'Fields do not match ({})'.format(debug_info)
                logger.error(msg)
                return Response({'message': msg}, status=500)

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

        return Response({'message': 'ok'}, status=200)


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
