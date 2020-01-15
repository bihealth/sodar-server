from django.conf import settings
from django.urls import reverse

from djangoplugins.point import PluginPoint
from irods.exception import NetworkException

# Projectroles dependency
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint, get_backend_api

from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    GenericMaterial,
    ISATab,
)
from samplesheets.urls import urlpatterns
from samplesheets.utils import (
    get_sample_dirs,
    get_isa_field_name,
    get_sheets_url,
)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']


# Samplesheets project app plugin ----------------------------------------------


class ProjectAppPlugin(ProjectAppPluginPoint):
    """Plugin for registering app with Projectroles"""

    # Properties required by django-plugins ------------------------------

    #: Name (slug-safe, used in URLs)
    name = 'samplesheets'

    #: Title (used in templates)
    title = 'Sample Sheets'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    # Properties defined in ProjectAppPluginPoint -----------------------

    #: App settings definition
    app_settings = {
        'allow_editing': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'BOOLEAN',
            'label': 'Allow Sample Sheet Editing',
            'description': 'Allow editing of projet sample sheets by '
            'authorized users',
            'user_modifiable': True,
            'default': False,
        },
        'sheet_config': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'JSON',
            'label': 'Sample Sheet Configuration',
            'description': 'JSON configuration for sample sheet editing',
            'user_modifiable': False,
        },
    }

    #: FontAwesome icon ID string
    icon = 'flask'

    #: Entry point URL ID (must take project sodar_uuid as "project" argument)
    entry_point_url_id = 'samplesheets:project_sheets'

    #: Description string
    description = (
        'Sample sheets contain your donors/patients, samples, and '
        'links to assays (such as NGS data), with ISA-Tools '
        'compatibility'
    )

    #: Required permission for accessing the app
    app_permission = 'samplesheets.view_sheet'

    #: Enable or disable general search from project title bar
    search_enable = True

    #: List of search object types for the app
    search_types = ['source', 'sample', 'file']

    #: Search results template
    search_template = 'samplesheets/_search_results.html'

    #: App card template for the project details page
    details_template = 'samplesheets/_details_card.html'

    #: App card title for the project details page
    details_title = 'Sample Sheets Overview'

    #: Position in plugin ordering
    plugin_ordering = 10

    #: Project list columns
    project_list_columns = {
        'sheets': {
            'title': 'Sheets',
            'width': 70,
            'description': None,
            'active': True,
            'align': 'center',
        },
        'data': {
            'title': 'Data',
            'width': 70,
            'description': None,
            'active': True,
            'align': 'center',
        },
    }

    def get_taskflow_sync_data(self):
        """
        Return data for syncing taskflow operations
        :return: List of dicts or None
        """
        sync_flows = []

        # NOTE: This only syncs previously created dirs
        for investigation in Investigation.objects.filter(irods_status=True):
            flow = {
                'flow_name': 'sheet_dirs_create',
                'project_uuid': investigation.project.sodar_uuid,
                'flow_data': {'dirs': get_sample_dirs(investigation)},
            }
            sync_flows.append(flow)

        return sync_flows

    def get_object_link(self, model_str, uuid):
        """
        Return URL for referring to a object used by the app, along with a
        label to be shown to the user for linking.
        :param model_str: Object class (string)
        :param uuid: sodar_uuid of the referred object
        :return: Dict or None if not found
        """
        obj = self.get_object(eval(model_str), uuid)

        if obj and obj.__class__ in [Investigation, Study, Assay]:
            return {
                'url': get_sheets_url(obj),
                'label': obj.title
                if obj.__class__ == Investigation
                else obj.get_display_name(),
            }

        elif obj and obj.__class__ == ISATab:
            return {
                'url': reverse(
                    'samplesheets:versions',
                    kwargs={'project': obj.project.sodar_uuid},
                ),
                'label': obj.get_name(),
            }

    def search(self, search_term, user, search_type=None, keywords=None):
        """
        Return app items based on a search term, user, optional type and
        optional keywords
        :param search_term: String
        :param user: User object for user initiating the search
        :param search_type: String
        :param keywords: List (optional)
        :return: Dict
        """
        irods_backend = get_backend_api('omics_irods')
        results = {}

        # Materials
        def get_materials(materials):
            ret = []

            for m in materials:
                if user.has_perm('samplesheets.view_sheet', m.get_project()):
                    if m.item_type == 'SAMPLE':
                        assays = m.get_sample_assays()

                    else:
                        assays = [m.assay]

                    ret.append(
                        {
                            'name': m.name,
                            'type': m.item_type,
                            'project': m.get_project(),
                            'study': m.study,
                            'assays': assays,
                        }
                    )

            return ret

        material_items = []

        if not search_type or search_type == 'source':
            material_items += get_materials(
                GenericMaterial.objects.find(
                    search_term, keywords, item_type='SOURCE'
                )
            )

        if not search_type or search_type == 'sample':
            material_items += get_materials(
                GenericMaterial.objects.find(
                    search_term, keywords, item_type='SAMPLE'
                )
            )

        if material_items:
            material_items.sort(key=lambda x: x['name'].lower())

        results['materials'] = {
            'title': 'Sources and Samples',
            'search_types': ['source', 'sample'],
            'items': material_items,
        }

        # iRODS files
        file_items = []

        if irods_backend and (not search_type or search_type == 'file'):
            try:
                obj_data = irods_backend.get_objects(
                    path='/{}/projects'.format(settings.IRODS_ZONE),
                    name_like=search_term,
                    limit=settings.SHEETS_IRODS_LIMIT,
                )

            # Skip rest if no data objects were found or iRODS is unreachable
            except (FileNotFoundError, NetworkException):
                return results

            projects = {
                str(p.sodar_uuid): p
                for p in Project.objects.filter(type=PROJECT_TYPE_PROJECT)
                if user.has_perm('samplesheets.view_sheet', p)
            }
            studies = {
                str(s.sodar_uuid): s
                for s in Study.objects.filter(
                    investigation__project__in=projects.values()
                )
            }
            assays = {
                str(a.sodar_uuid): a
                for a in Assay.objects.filter(study__in=studies.values())
            }

            for o in obj_data['data_objects']:
                project_uuid = irods_backend.get_uuid_from_path(
                    o['path'], obj_type='project'
                )
                sample_subpath = '/{}/{}/'.format(
                    project_uuid, settings.IRODS_SAMPLE_DIR
                )

                if sample_subpath not in o['path']:
                    continue  # Skip files not in sample data repository

                try:
                    project = projects[project_uuid]
                    study = studies[
                        irods_backend.get_uuid_from_path(
                            o['path'], obj_type='study'
                        )
                    ]
                    assay = assays[
                        irods_backend.get_uuid_from_path(
                            o['path'], obj_type='assay'
                        )
                    ]

                except KeyError:
                    continue  # Skip file if the project/etc is not found

                file_items.append(
                    {
                        'name': o['name'],
                        'type': 'file',
                        'project': project,
                        'study': study,
                        'assays': [assay] if assay else None,
                        'irods_path': o['path'],
                    }
                )

                if len(file_items) == settings.SHEETS_IRODS_LIMIT:
                    break

        if file_items:
            file_items.sort(key=lambda x: x['name'].lower())

        results['files'] = {
            'title': 'Sample Files in iRODS',
            'search_types': ['file'],
            'items': file_items,
        }

        return results

    def get_project_list_value(self, column_id, project, user):
        """
        Return a value for the optional additional project list column specific
        to a project.

        :param column_id: ID of the column (string)
        :param project: Project object
        :param user: User object (current user)
        :return: String (may contain HTML), integer or None
        """
        investigation = Investigation.objects.filter(project=project).first()

        if column_id == 'sheets' and investigation:
            return (
                '<a href="{}" title="{}" data-toggle="tooltip" '
                'data-placement="top"><i class="fa fa-list-alt text-primary">'
                '</i></a>'.format(
                    reverse(
                        'samplesheets:project_sheets',
                        kwargs={'project': project.sodar_uuid},
                    ),
                    'View project sample sheets',
                )
            )

        elif (
            column_id == 'data'
            and settings.IRODS_WEBDAV_ENABLED
            and investigation
            and investigation.irods_status
        ):
            irods_backend = get_backend_api('omics_irods')
            return (
                (
                    '<a href="{}" target="_blank" title="{}" '
                    'data-toggle="tooltip" data-placement="top">'
                    '<i class="fa fa-folder-open '
                    'text-primary"></i></a>'.format(
                        settings.IRODS_WEBDAV_URL
                        + irods_backend.get_sample_path(project),
                        'View project sample data in iRODS',
                    )
                )
                if irods_backend
                else None
            )

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend or not irods_backend.test_connection():
            return

        for study_plugin in SampleSheetStudyPluginPoint.get_plugins():
            study_plugin.update_cache(name, project, user)

        for assay_plugin in SampleSheetAssayPluginPoint.get_plugins():
            assay_plugin.update_cache(name, project, user)


# Samplesheets study sub-app plugin --------------------------------------------


class SampleSheetStudyPluginPoint(PluginPoint):
    """Plugin point for registering study-level samplesheet sub-apps"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    # TODO: Implement this in your study plugin
    # TODO: Recommended in form of samplesheets_study_configname
    # name = 'samplesheets_study_'

    #: Title (used in templates)
    # TODO: Implement this in your study plugin
    # title = 'Sample Sheets X Study App'

    # Properties defined in SampleSheetStudyPluginPoint ------------------

    #: Configuration name (used to identify plugin by study)
    # TODO: Implement this in your study plugin
    config_name = ''

    #: Description string
    # TODO: Implement this in your study plugin
    description = 'TODO: Write a description for your study plugin'

    #: Required permission for accessing the plugin
    # TODO: Implement this in your study plugin (can be None)
    # TODO: TBD: Do we need this?
    permission = None

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        # TODO: Implement this in your app plugin
        return None

    def get_shortcut_column(self, study, study_tables):
        """
        Return structure containing links for an extra study table links column.

        :param study: Study object
        :param study_tables: Rendered study tables (dict)
        :return: Dict
        """
        # TODO: Implement this in your study plugin
        return None

    def get_shortcut_links(self, study, study_tables, **kwargs):
        """
        Return links for shortcut modal.

        :param study: Study object
        :param study_tables: Rendered study tables (dict)
        :return: Dict
        """
        return None


def get_study_plugin(plugin_name):
    """
    Return active study plugin
    :param plugin_name: Plugin name (string)
    :return: SampleSheetStudyPlugin object or None if not found
    """
    try:
        return SampleSheetStudyPluginPoint.get_plugin(plugin_name)

    except SampleSheetStudyPluginPoint.DoesNotExist:
        return None


def find_study_plugin(config_name):
    """
    Find active study plugin with a config name
    :param config_name: Configuration name (string)
    :return: SampleSheetStudyPlugin object or None if not found
    """
    for plugin in SampleSheetStudyPluginPoint.get_plugins():
        if plugin.config_name == config_name:
            return plugin

    return None


# Samplesheets assay sub-app plugin --------------------------------------------


class SampleSheetAssayPluginPoint(PluginPoint):
    """Plugin point for registering assay-level samplesheet sub-apps"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    # TODO: Implement this in your assay plugin
    # TODO: Recommended in form of samplesheets_assay_name
    # name = 'samplesheets_assay_'

    #: Title
    # TODO: Implement this in your assay plugin
    # title = 'Sample Sheets X Assay App'

    # Properties defined in SampleSheetAssayPluginPoint ------------------

    #: App name for dynamic reference to app in e.g. caching
    # TODO: Rename plugin.name to APP_NAME?
    # TODO: Implement this in your assay plugin
    app_name = None

    #: Identifying assay fields (used to identify plugin by assay)
    # TODO: Implement this in your assay plugin, example below
    assay_fields = [{'measurement_type': 'x', 'technology_type': 'y'}]

    #: Description string
    # TODO: Implement this in your assay plugin
    description = 'TODO: Write a description for your assay plugin'

    #: Template for assay addition (Study object as "study" in context)
    # TODO: Rename this in your assay plugin (can be None)
    assay_template = 'samplesheets_assay_name/_assay.html'

    #: Required permission for accessing the plugin
    # TODO: Implement this in your assay plugin (can be None)
    # TODO: TBD: Do we need this?
    permission = None

    #: Toggle displaying of row-based iRODS links in the assay table
    # TODO: Implement this in your assay plugin
    display_row_links = True

    def get_assay_path(self, assay):
        """
        Helper for getting the assay path
        :param assay: Assay object
        :return: Full iRODS path for the assay
        """
        irods_backend = get_backend_api('omics_irods')

        if not irods_backend:
            return None

        return irods_backend.get_path(assay)

    def get_row_path(self, row, table, assay, assay_path):
        """Return iRODS path for an assay row in a sample sheet. If None,
        display default directory.
        :param row: List of dicts (a row returned by SampleSheetTableBuilder)
        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :param assay_path: Root path for assay
        :return: String with full iRODS path or None
        """
        # TODO: Implement this in your assay plugin if display_row_links=True
        return None

    def update_row(self, row, table, assay):
        """
        Update render table row with e.g. links. Return the modified row
        :param row: Original row (list of dicts)
        :param table: Full table (list of lists)
        :param assay: Assay object
        :return: List of dicts
        """
        # TODO: Implement this in your assay plugin
        raise NotImplementedError('Implement update_row() in your assay plugin')

    def get_extra_table(self, table, assay):
        """
        Return data for an extra content/shortcut table.

        :param table: Full table with headers (dict returned by
                      SampleSheetTableBuilder)
        :param assay: Assay object
        :return: Dict or None
        """
        # TODO: Implement this in your app plugin
        return None

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        # TODO: Implement this in your app plugin
        return None


def get_assay_plugin(plugin_name):
    """
    Return active assay plugin
    :param plugin_name: Plugin name (string)
    :return: SampleSheetAssayPlugin object or None if not found
    """
    try:
        return SampleSheetAssayPluginPoint.get_plugin(plugin_name)

    except SampleSheetAssayPluginPoint.DoesNotExist:
        return None


def find_assay_plugin(measurement_type, technology_type):
    """
    Find active assay plugin with a measurement type and technology type
    :param measurement_type: Measurement type (string or ontology dict)
    :param technology_type: Technology type (string or ontology dict)
    :return: SampleSheetAssayPlugin object or None if not found
    """

    # TODO: Log warning if there are multiple plugins found?

    search_fields = {
        'measurement_type': get_isa_field_name(measurement_type),
        'technology_type': get_isa_field_name(technology_type),
    }

    for plugin in SampleSheetAssayPluginPoint.get_plugins():
        if search_fields in plugin.assay_fields:
            return plugin

    return None
