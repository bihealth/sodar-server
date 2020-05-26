"""Ajax API views for the samplesheets app"""

import json
from packaging import version

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

    @transaction.atomic
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
            ret_data['study_config'] = sheet_config['studies'][
                str(study.sodar_uuid)
            ]

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

    # TODO: Update to support name columns

    permission_required = 'samplesheets.edit_sheet'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        updated_cells = request.data.get('updated_cells') or []

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
                logger.error(
                    'No {} found with UUID={}'.format(
                        cell['obj_cls'], cell['uuid']
                    )
                )
                # TODO: Return list of errors when processing in batch
                return Response(
                    {
                        'message': 'Object not found: {} ({})'.format(
                            cell['uuid'], cell['obj_cls']
                        )
                    },
                    status=500,
                )

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

                obj.save()
                logger.debug('Edited field: {}'.format(attr_name))

            # Name field (special case)
            elif header_type == 'name':
                if len(cell['value']) == 0:
                    logger.error('Empty name not allowed for node')
                    return Response({'message': 'failed'}, status=500)

                obj.name = cell['value']
                # TODO: Update unique name here if needed
                obj.save()
                logger.debug('Edited node name: {}'.format(cell['value']))

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

                obj.save()
                logger.debug(
                    'Edited JSON attribute: {}[{}]'.format(
                        header_type, header_name
                    )
                )

            else:
                logger.error(
                    'Editing not implemented '
                    '(header_type={}; header_name={}'.format(
                        header_type, header_name
                    )
                )
                return Response({'message': 'failed'}, status=500)

        # TODO: Log edits in timeline here, once saving in bulk

        return Response({'message': 'ok'}, status=200)


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

    permission_required = 'samplesheets.manage_sheet'

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
                or field['config']['type'] != og_config['type']
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

                if c['format'] == 'select':
                    c.pop('regex', None)

                else:  # Select
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
