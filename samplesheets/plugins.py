"""App plugin and sub-app plugin points for the samplesheets app"""

import logging
import os
import re
import time

from copy import deepcopy
from irods.exception import NetworkException
from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse

from djangoplugins.point import PluginPoint

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import (
    ProjectAppPluginPoint,
    ProjectModifyPluginMixin,
    get_backend_api,
)
from projectroles.utils import build_secret

from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    GenericMaterial,
    ISATab,
    IrodsAccessTicket,
    IrodsDataRequest,
    ISA_META_ASSAY_PLUGIN,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.urls import urlpatterns
from samplesheets.utils import (
    get_isa_field_name,
    get_sheets_url,
)
from samplesheets.views import (
    IrodsCollsCreateViewMixin,
    RESULTS_COLL,
    MISC_FILES_COLL,
    TRACK_HUBS_COLL,
    RESULTS_COLL_ID,
    MISC_FILES_COLL_ID,
    APP_NAME,
)


app_settings = AppSettingAPI()
logger = logging.getLogger(__name__)
table_builder = SampleSheetTableBuilder()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']

# Local constants
SHEETS_INFO_SETTINGS = [
    'SHEETS_ALLOW_CRITICAL',
    'SHEETS_CONFIG_VERSION',
    'SHEETS_ENABLE_CACHE',
    'SHEETS_ENABLE_STUDY_TABLE_CACHE',
    'SHEETS_EXTERNAL_LINK_PATH',
    'SHEETS_IRODS_LIMIT',
    'SHEETS_IRODS_REQUEST_PAGINATION',
    'SHEETS_IRODS_TICKET_PAGINATION',
    'SHEETS_MAX_COLUMN_WIDTH',
    'SHEETS_MIN_COLUMN_WIDTH',
    'SHEETS_ONTOLOGY_URL_SKIP',
    'SHEETS_SYNC_INTERVAL',
    'SHEETS_VERSION_PAGINATION',
    'SHEETS_IGV_OMIT_BAM',
    'SHEETS_IGV_OMIT_VCF',
]
MATERIAL_SEARCH_TYPES = ['source', 'sample']
SKIP_MSG_NO_INV = 'No investigation for project'
SKIP_MSG_NO_COLLS = 'Investigation collections not created in iRODS'
IGV_DEFAULT_GENOME = 'b37_1kg'
SYNC_URL_RE = (
    r'/samplesheets/sync/[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]'
    r'{3}-?[a-f0-9]{12}'
)


# Samplesheets project app plugin ----------------------------------------------


class ProjectAppPlugin(
    IrodsCollsCreateViewMixin,
    ProjectModifyPluginMixin,
    ProjectAppPluginPoint,
):
    """Plugin for registering app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'samplesheets'

    #: Title (used in templates)
    title = 'Sample Sheets'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    #: App settings definition
    app_settings = {
        'allow_editing': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'BOOLEAN',
            'label': 'Allow sample sheet editing',
            'description': 'Allow editing of project sample sheets by '
            'authorized users',
            'user_modifiable': True,
            'default': True,
        },
        'display_config': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT_USER'],
            'type': 'JSON',
            'label': 'Sample sheet display configuration',
            'description': 'User specific JSON configuration for column '
            'display in project sample sheets',
        },
        'display_config_default': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'JSON',
            'label': 'Default sample sheet display configuration',
            'description': 'Default JSON configuration for column display in '
            'project sample sheets',
            'user_modifiable': False,
        },
        'sheet_config': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'JSON',
            'label': 'Sample sheet editing configuration',
            'description': 'JSON configuration for sample sheet editing',
            'user_modifiable': False,
        },
        'edit_config_min_role': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'STRING',
            'options': [
                'superuser',
                SODAR_CONSTANTS['PROJECT_ROLE_OWNER'],
                SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE'],
                SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR'],
            ],
            'default': SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR'],
            'label': 'Minimum role for column configuration editing',
            'description': 'Allow per-project restriction of column '
            'configuration updates',
            'user_modifiable': True,
        },
        'sheet_sync_enable': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'BOOLEAN',
            'default': False,
            'label': 'Enable sheet synchronization',
            'description': 'Enable sheet synchronization from a source project',
            'user_modifiable': True,
        },
        'sheet_sync_url': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'STRING',
            'label': 'URL for sheet synchronization',
            'default': '',
            'description': 'REST API URL for sheet synchronization',
            'user_modifiable': True,
        },
        'sheet_sync_token': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'STRING',
            'label': 'Token for sheet synchronization',
            'default': '',
            'description': 'Access token for sheet synchronization in the '
            'source project',
            'user_modifiable': True,
        },
        'sheet_table_height': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_USER'],
            'type': 'INTEGER',
            'label': 'Sample sheet table height',
            'options': [250, 400, 600, 800],
            'default': 400,
            'description': 'Maximum display height for study and assay tables '
            'in pixels',
            'user_modifiable': True,
        },
        'public_access_ticket': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'STRING',
            'label': 'iRODS public access ticket',
            'default': '',
            'description': 'iRODS ticket for read-only anonymous sample data '
            'access, used with projects allowing public guest access',
            'user_modifiable': False,
        },
        'igv_genome': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'STRING',
            'label': 'IGV session genome',
            'default': IGV_DEFAULT_GENOME,
            'description': 'Genome used in generating IGV session files for '
            'the project. The name needs to be in a format accepted by IGV. '
            'Affects cancer and germline projects.',
            'user_modifiable': True,
        },
        'igv_omit_bam': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'STRING',
            'label': 'BAM and CRAM paths to omit from IGV sessions',
            'default': ', '.join(settings.SHEETS_IGV_OMIT_BAM),
            'description': 'Comma-separated list of iRODS path glob patterns '
            'for omitting BAM and CRAM files from IGV sessions and study '
            'shortcuts. Overrides site-wide setting, affects cancer and '
            'germline projects. Update sheet cache after updating this value.',
            'user_modifiable': True,
        },
        'igv_omit_vcf': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'STRING',
            'label': 'VCF paths to omit from IGV sessions',
            'default': ', '.join(settings.SHEETS_IGV_OMIT_VCF),
            'description': 'Comma-separated list of iRODS path glob patterns '
            'for omitting VCF files from IGV sessions and study shortcuts. '
            'Overrides site-wide setting, affects cancer and germline '
            'projects. Update sheet cache after updating this value.',
            'user_modifiable': True,
        },
    }

    #: Iconify icon
    icon = 'mdi:flask'

    #: Entry point URL ID (must take project sodar_uuid as "project" argument)
    entry_point_url_id = 'samplesheets:project_sheets'

    #: Description string
    description = (
        'Study design metadata with access to assay data files in iRODS'
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
            'ordering': 30,
            'align': 'center',
        },
        'files': {
            'title': 'Files',
            'width': 70,
            'description': None,
            'active': True,
            'ordering': 20,
            'align': 'center',
        },
    }

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = SHEETS_INFO_SETTINGS

    def get_object_link(self, model_str, uuid):
        """
        Return URL for referring to a object used by the app, along with a
        label to be shown to the user for linking.

        :param model_str: Object class (string)
        :param uuid: sodar_uuid of the referred object
        :return: Dict or None if not found
        """
        obj = self.get_object(eval(model_str), uuid)
        if not obj:
            return None
        if obj.__class__ == IrodsAccessTicket:
            return {
                'url': reverse(
                    'samplesheets:irods_tickets',
                    kwargs={'project': obj.get_project().sodar_uuid},
                ),
                'label': obj.get_display_name(),
            }
        if obj.__class__ in [Investigation, Study, Assay]:
            return {
                'url': obj.get_url(),
                'label': obj.title
                if obj.__class__ == Investigation
                else obj.get_display_name(),
            }
        url_kwargs = {'project': obj.project.sodar_uuid}
        if obj.__class__ == ISATab:
            return {
                'url': reverse('samplesheets:versions', kwargs=url_kwargs),
                'label': obj.get_full_name(),
            }
        elif obj.__class__ == IrodsDataRequest:
            return {
                'url': reverse(
                    'samplesheets:irods_requests', kwargs=url_kwargs
                ),
                'label': obj.get_display_name(),
            }

    @classmethod
    def _get_search_materials(cls, search_terms, user, keywords, item_types):
        """Return materials for search results"""
        ret = []
        materials = GenericMaterial.objects.find(
            search_terms, keywords, item_types=item_types
        )
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

    @classmethod
    def _get_search_files(cls, search_terms, user, irods_backend):
        """Return iRODS files for search results"""
        ret = []
        try:
            with irods_backend.get_session() as irods:
                obj_list = irods_backend.get_objects(
                    irods=irods,
                    path=irods_backend.get_projects_path(),
                    name_like=search_terms,
                    limit=settings.SHEETS_IRODS_LIMIT,
                )
        # Skip rest if no data objects were found or iRODS is unreachable
        except (FileNotFoundError, NetworkException):
            return ret

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

        for o in obj_list:
            project_uuid = irods_backend.get_uuid_from_path(
                o['path'], obj_type='project'
            )
            sample_subpath = '/{}/{}/'.format(
                project_uuid, settings.IRODS_SAMPLE_COLL
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

            ret.append(
                {
                    'name': o['name'],
                    'type': 'file',
                    'project': project,
                    'study': study,
                    'assays': [assay] if assay else None,
                    'irods_path': o['path'],
                }
            )
            if len(ret) == settings.SHEETS_IRODS_LIMIT:
                break

        if ret:
            ret.sort(key=lambda x: x['name'].lower())
        return ret

    def search(self, search_terms, user, search_type=None, keywords=None):
        """
        Return app items based on one or more search terms, user, optional type
        and optional keywords.

        :param search_terms: Search terms to be joined with the OR operator
                             (list of strings)
        :param user: User object for user initiating the search
        :param search_type: String
        :param keywords: List (optional)
        :return: Dict
        """
        irods_backend = get_backend_api('omics_irods')
        results = {}
        # Materials
        if not search_type or search_type in MATERIAL_SEARCH_TYPES:
            item_types = ['SOURCE', 'SAMPLE']
            if search_type in MATERIAL_SEARCH_TYPES:
                item_types = [search_type.upper()]
            results['materials'] = {
                'title': 'Sources and Samples',
                'search_types': ['source', 'sample'],
                'items': self._get_search_materials(
                    search_terms, user, keywords, item_types
                ),
            }
        # iRODS files
        if irods_backend and (not search_type or search_type == 'file'):
            results['files'] = {
                'title': 'Sample Files in iRODS',
                'search_types': ['file'],
                'items': self._get_search_files(
                    search_terms, user, irods_backend
                ),
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

        if column_id == 'sheets':
            if investigation:
                return (
                    '<a href="{}" title="View project sample sheets">'
                    # 'data-toggle="tooltip" data-placement="top">'
                    '<i class="iconify text-primary" '
                    'data-icon="mdi:flask"></i></a>'.format(
                        get_sheets_url(project)
                    )
                )
            elif user.has_perm(
                'samplesheets.edit_sheet', project
            ) and not app_settings.get(APP_NAME, 'sheet_sync_enable', project):
                return (
                    '<a href="{}" title="Import sample sheet into project">'
                    # 'data-toggle="tooltip" data-placement="top">'
                    '<i class="iconify text-primary" '
                    'data-icon="mdi:plus-thick"></i></a>'.format(
                        reverse(
                            'samplesheets:import',
                            kwargs={'project': project.sodar_uuid},
                        )
                    )
                )
            else:
                return (
                    '<i class="iconify text-muted" data-icon="mdi:flask" '
                    'title="No sample sheets in project"></i>'
                    # 'data-toggle="tooltip" data-placement="top"></i>'
                )

        elif column_id == 'files':
            irods_backend = get_backend_api('omics_irods')
            if (
                irods_backend
                and investigation
                and investigation.irods_status
                and settings.IRODS_WEBDAV_ENABLED
            ):
                return (
                    '<a href="{}" target="_blank" '
                    'title="View project sample files in iRODS">'
                    # 'data-toggle="tooltip" data-placement="top">'
                    '<i class="iconify text-primary" '
                    'data-icon="mdi:folder-open"></i></a>'.format(
                        settings.IRODS_WEBDAV_URL
                        + irods_backend.get_sample_path(project)
                    )
                )
            return (
                '<i class="iconify text-muted" '
                'data-icon="mdi:folder-open" title="{}" '
                # 'data-toggle="tooltip" data-placement="top" '
                '></i>'.format(
                    'No project sample files in iRODS'
                    if settings.IRODS_WEBDAV_URL
                    else 'iRODS WebDAV unavailable'
                )
            )

    def validate_form_app_settings(self, app_settings, project=None, user=None):
        """
        Validate app settings form data and return a dict of errors.

        :param app_settings: Dict of app settings
        :param project: Project object or None
        :param user: User object
        :return: dict in format of {setting_name: 'Error string'}
        """
        ret = {}
        # Ensure all sheet sync settings are set if sync is enabled
        if project and app_settings.get('sheet_sync_enable') is not None:
            enable = app_settings['sheet_sync_enable']
            msg = 'must be set if sheet sync is enabled'
            if enable and not app_settings['sheet_sync_token']:
                ret['sheet_sync_token'] = 'Token ' + msg
            if enable and not app_settings['sheet_sync_url']:
                ret['sheet_sync_url'] = 'URL ' + msg
        # Validate sync URL
        if project and app_settings.get('sheet_sync_url'):
            try:
                urlparse(app_settings['sheet_sync_url'])
            except Exception:
                ret['sheet_sync_url'] = 'Invalid URL'
            if 'sheet_sync_url' not in ret and not re.findall(
                SYNC_URL_RE, app_settings['sheet_sync_url']
            ):
                ret[
                    'sheet_sync_url'
                ] = 'URL does not point to a sheet sync endpoint'
        return ret

    # Project Modify API Implementation ----------------------------------------

    @classmethod
    def _update_public_access(cls, project, taskflow, irods_backend):
        """
        Update project public access.

        :param project: Project object
        :param taskflow: Taskflowbackend API object
        :param irods_backend: Irodsbackend API object
        :raise: Exception if DEBUG==True and a taskflow error is encountered
        """
        sample_path = irods_backend.get_sample_path(project)
        ticket_str = app_settings.get(
            APP_NAME, 'public_access_ticket', project=project
        )
        if (
            not ticket_str
            and project.public_guest_access
            and settings.PROJECTROLES_ALLOW_ANONYMOUS
        ):
            ticket_str = build_secret(16)

        flow_data = {
            'access': project.public_guest_access,
            'path': sample_path,
            'ticket_str': ticket_str,
        }
        try:
            taskflow.submit(
                project=project,
                flow_name='public_access_update',
                flow_data=flow_data,
            )
        except Exception as ex:
            logger.error('Public status update taskflow failed: {}'.format(ex))
            if settings.DEBUG:
                raise ex

        # Update/delete ticket in project settings
        if (
            project.public_guest_access
            and settings.PROJECTROLES_ALLOW_ANONYMOUS
        ):
            app_settings.set(
                APP_NAME,
                'public_access_ticket',
                ticket_str,
                project=project,
            )
        else:
            app_settings.delete(
                APP_NAME, 'public_access_ticket', project=project
            )

    def perform_project_modify(
        self,
        project,
        action,
        project_settings,
        old_data=None,
        old_settings=None,
        request=None,
    ):
        """
        Perform additional actions to finalize project creation or update.

        :param project: Current project object (Project)
        :param action: Action to perform (CREATE or UPDATE)
        :param project_settings: Project app settings (dict)
        :param old_data: Old project data in case of an update (dict or None)
        :param old_settings: Old app settings in case of update (dict or None)
        :param request: Request object or None
        """
        taskflow = get_backend_api('taskflow')
        irods_backend = get_backend_api('omics_irods')

        # Check for conditions and skip if not met
        def _skip(msg):
            logger.debug('Skipping: {}'.format(msg))

        if not taskflow or not irods_backend:
            return _skip(
                'Backends not enabled: taskflow={}; omics_irods={}'.format(
                    taskflow is not None,
                    irods_backend is not None,
                )
            )
        if action == PROJECT_ACTION_CREATE:
            return _skip('Project newly created, no Investigation available')
        if project.public_guest_access == old_data.get('public_guest_access'):
            return _skip('Public guest access unchanged')
        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        if not investigation:
            return _skip(SKIP_MSG_NO_INV)
        if not investigation.irods_status:
            return _skip(SKIP_MSG_NO_COLLS)

        # Submit flow
        logger.info(
            'Setting project public access status for {} to: {} '.format(
                project.get_log_title(), project.public_guest_access
            )
        )
        self._update_public_access(project, taskflow, irods_backend)
        logger.info('Public access status updated')

    # NOTE: No reverting from API needed as this always gets called last

    def perform_project_sync(self, project):
        """
        Synchronize existing projects to ensure related data exists when the
        syncmodifyapi management comment is called. Should mostly be used in
        development when the development databases have been e.g. modified or
        recreated.

        :param project: Current project object (Project)
        """
        taskflow = get_backend_api('taskflow')
        irods_backend = get_backend_api('omics_irods')

        # Set up investigation collections
        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        if not investigation:
            logger.debug('Skipping: {}'.format(SKIP_MSG_NO_INV))
            return
        if investigation.irods_status:
            logger.info('Syncing iRODS sample data collections..')
            self.create_colls(investigation, sync=True)

        # Sync public guest access
        if not investigation.irods_status:
            logger.debug('Skipping: {}'.format(SKIP_MSG_NO_COLLS))
            return
        self._update_public_access(project, taskflow, irods_backend)

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        :raise: Exception if required backends (sodar_cache and omics_irods)
                are not found.
        """
        # NOTE: This will not sync cached study render tables, they are created
        #       synchronously upon access if not up-to-date. To sync the cache
        #       for all study tables, use the syncstudytables command.
        cache_backend = get_backend_api('sodar_cache')
        irods_backend = get_backend_api('omics_irods')
        if not cache_backend or not irods_backend:
            backends = {
                'cache_backend': cache_backend,
                'irods_backend': irods_backend,
            }
            raise Exception(
                'Required backend(s) not found: {}'.format(', ').join(
                    [b for b in backends.keys() if not backends[b]]
                )
            )

        # Study sub-app plugins
        for study_plugin in SampleSheetStudyPluginPoint.get_plugins():
            study_plugin.update_cache(name, project, user)

        # Assay shortcuts
        projects = (
            [project]
            if project
            else Project.objects.filter(type=PROJECT_TYPE_PROJECT)
        )
        assays = Assay.objects.filter(
            study__investigation__project__in=projects,
            study__investigation__irods_status=True,
        )

        with irods_backend.get_session() as irods:
            for assay in assays:
                item_name = 'irods/shortcuts/assay/{}'.format(assay.sodar_uuid)
                assay_path = irods_backend.get_path(assay)
                assay_plugin = assay.get_plugin()
                # Default assay shortcuts
                cache_data = {
                    'shortcuts': {
                        'results_reports': irods.collections.exists(
                            assay_path + '/' + RESULTS_COLL
                        ),
                        'misc_files': irods.collections.exists(
                            assay_path + '/' + MISC_FILES_COLL
                        ),
                    }
                }
                # Plugin assay shortcuts
                if assay_plugin:
                    plugin_shortcuts = assay_plugin.get_shortcuts(assay) or []
                    for sc in plugin_shortcuts:
                        cache_data['shortcuts'][
                            sc['id']
                        ] = irods.collections.exists(sc['path'])
                cache_data['shortcuts']['track_hubs'] = [
                    c.path
                    for c in irods_backend.get_child_colls(
                        irods, os.path.join(assay_path, TRACK_HUBS_COLL)
                    )
                ]
                cache_backend.set_cache_item(
                    name=item_name,
                    app_name='samplesheets',
                    user=user,
                    data=cache_data,
                    project=assay.get_project(),
                )

        # Assay sub-app plugins
        for assay_plugin in SampleSheetAssayPluginPoint.get_plugins():
            assay_plugin.update_cache(name, project, user)


# Samplesheets study sub-app plugin --------------------------------------------


class SampleSheetStudyPluginPoint(PluginPoint):
    """Plugin point for registering study-level samplesheet sub-apps"""

    #: Name (used in code and as unique idenfitier)
    # TODO: Implement this in your study plugin
    # TODO: Recommended in form of samplesheets_study_configname
    # name = 'samplesheets_study_'

    #: Title (used in templates)
    # TODO: Implement this in your study plugin
    # title = 'Sample Sheets X Study App'

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

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        # TODO: Implement this in your app plugin
        return None


def get_study_plugin(plugin_name):
    """
    Return active study plugin.

    :param plugin_name: Plugin name (string)
    :return: SampleSheetStudyPlugin object or None if not found
    """
    try:
        return SampleSheetStudyPluginPoint.get_plugin(plugin_name)
    except SampleSheetStudyPluginPoint.DoesNotExist:
        return None


# Samplesheets assay sub-app plugin --------------------------------------------


class SampleSheetAssayPluginPoint(PluginPoint):
    """Plugin point for registering assay-level samplesheet sub-apps"""

    #: Name (used in code and as unique idenfitier)
    # TODO: Implement this in your assay plugin
    # TODO: Recommended in form of samplesheets_assay_name
    # name = 'samplesheets_assay_'

    #: Title
    # TODO: Implement this in your assay plugin
    # title = 'Sample Sheets X Assay App'

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
        Helper for getting the assay path.

        :param assay: Assay object
        :return: Full iRODS path for the assay
        """
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            return None
        return irods_backend.get_path(assay)

    def get_row_path(self, row, table, assay, assay_path):
        """
        Return iRODS path for an assay row in a sample sheet. If None,
        display default path.

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
        Update render table row with e.g. links. Return the modified row.

        :param row: Original row (list of dicts)
        :param table: Full table (list of lists)
        :param assay: Assay object
        :return: List of dicts
        """
        # TODO: Implement this in your assay plugin
        raise NotImplementedError('Implement update_row() in your assay plugin')

    def get_shortcuts(self, assay):
        """
        Return assay iRODS shortcuts.

        :param assay: Assay object
        :return: List or None
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

    # Common cache update utilities --------------------------------------

    def _update_cache_rows(self, app_name, name=None, project=None, user=None):
        """
        Update cache for row-based iRODS links using get_row_path().

        :param app_name: Application name (string)
        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        if name and (
            name.split('/')[0] != 'irods' or name.split('/')[1] != 'rows'
        ):
            return
        try:
            cache_backend = get_backend_api('sodar_cache')
            irods_backend = get_backend_api('omics_irods')
        except Exception:
            return
        if not cache_backend or not irods_backend:
            return

        projects = (
            [project]
            if project
            else Project.objects.filter(type=PROJECT_TYPE_PROJECT)
        )
        all_assays = Assay.objects.filter(
            study__investigation__project__in=projects,
            study__investigation__irods_status=True,
        )
        config_assays = []

        # Filter assays by measurement and technology type, or plugin override
        for assay in all_assays:
            search_fields = {
                'measurement_type': get_isa_field_name(assay.measurement_type),
                'technology_type': get_isa_field_name(assay.technology_type),
            }
            if (
                assay.comments.get(ISA_META_ASSAY_PLUGIN) == self.name
                or search_fields in self.assay_fields
            ):
                config_assays.append(assay)

        # Iterate through studies so we don't have to rebuild too many tables
        studies = list(set([a.study for a in config_assays]))

        # Get assay paths
        for study in studies:
            study_tables = table_builder.get_study_tables(study)
            for assay in [a for a in study.assays.all() if a in config_assays]:
                assay_table = study_tables['assays'][str(assay.sodar_uuid)]
                assay_path = irods_backend.get_path(assay)
                row_paths = []
                item_name = 'irods/rows/{}'.format(assay.sodar_uuid)

                for row in assay_table['table_data']:
                    path = self.get_row_path(
                        row, assay_table, assay, assay_path
                    )
                    if path and path not in row_paths:
                        row_paths.append(path)

                # Build cache for paths
                cache_data = {'paths': {}}
                with irods_backend.get_session() as irods:
                    for path in row_paths:
                        try:
                            cache_data['paths'][
                                path
                            ] = irods_backend.get_object_stats(irods, path)
                        except FileNotFoundError:
                            cache_data['paths'][path] = None
                cache_backend.set_cache_item(
                    name=item_name,
                    app_name=app_name,
                    user=user,
                    data=cache_data,
                    project=assay.get_project(),
                )


def get_assay_plugin(plugin_name):
    """
    Return active assay plugin.

    :param plugin_name: Plugin name (string)
    :return: SampleSheetAssayPlugin object or None if not found
    """
    try:
        return SampleSheetAssayPluginPoint.get_plugin(plugin_name)
    except SampleSheetAssayPluginPoint.DoesNotExist:
        return None


def get_irods_content(inv, study, irods_backend, ret_data):
    """
    Return iRODS content for a study.

    :param inv: Investigation objet
    :param study: Study object
    :param irods_backend: irodsbackend API object
    :param ret_data: Return data to be modified (dict)
    :return: Dict
    """
    cache_backend = get_backend_api('sodar_cache')
    ret_data = deepcopy(ret_data)
    if not (inv.irods_status and irods_backend):
        return ret_data
    logger.debug('Retrieving iRODS content..')
    time_start = time.time()

    # Get study content if plugin is found
    study_plugin = study.get_plugin()
    if study_plugin:
        logger.debug(
            'Retrieving study shortcuts for study "{}" (plugin={})..'.format(
                study.get_display_name(), study_plugin.name
            )
        )
        shortcuts = study_plugin.get_shortcut_column(study, ret_data['tables'])
        ret_data['tables']['study']['shortcuts'] = shortcuts
    else:
        logger.debug('Study plugin not found')

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
                'assay_plugin': False,
            },
            {
                'id': MISC_FILES_COLL_ID,
                'label': 'Misc Files',
                'path': assay_path + '/' + MISC_FILES_COLL,
                'assay_plugin': False,
            },
        ]

        assay_plugin = assay.get_plugin()
        if assay_plugin:
            logger.debug(
                'Retrieving assay shortcuts for assay "{}" '
                '(plugin={})..'.format(
                    assay.get_display_name(), assay_plugin.name
                )
            )
            cache_item = cache_backend.get_cache_item(
                name='irods/rows/{}'.format(a_uuid),
                app_name=assay_plugin.app_name,
                project=assay.get_project(),
            )

            for row in a_data['table_data']:
                # Update assay links column
                path = assay_plugin.get_row_path(row, a_data, assay, assay_path)
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
                a_data['irods_paths'].append({'path': path, 'enabled': enabled})
                # Update row links
                assay_plugin.update_row(row, a_data, assay)

            # Add visual notification to all shortcuts coming from assay plugin
            assay_shortcuts = assay_plugin.get_shortcuts(assay) or []
            for a in assay_shortcuts:
                a['icon'] = 'mdi:puzzle'
                a['title'] = 'Defined in assay plugin'
                a['assay_plugin'] = True
            # Add extra table if available
            a_data['shortcuts'].extend(assay_shortcuts)
        else:
            logger.debug('Assay plugin not found')

        # Check assay shortcut cache and set initial enabled value
        cache_item = cache_backend.get_cache_item(
            name='irods/shortcuts/assay/{}'.format(a_uuid),
            app_name=APP_NAME,
            project=assay.get_project(),
        )

        # Add track hub shortcuts
        logger.debug('Setting up track hub shortcuts..')
        track_hubs = (
            cache_item and cache_item.data['shortcuts'].get('track_hubs')
        ) or []
        for i, track_hub in enumerate(track_hubs):
            tickets = IrodsAccessTicket.active_objects.filter(
                path=track_hub
            ) or IrodsAccessTicket.objects.filter(path=track_hub)
            ticket = tickets and tickets.first()
            a_data['shortcuts'].append(
                {
                    'id': 'track_hub_%d' % i,
                    'label': os.path.basename(track_hub),
                    'icon': 'mdi:road',
                    'title': 'Track Hub',
                    'assay_plugin': False,
                    'path': track_hub,
                    'extra_links': [
                        {
                            'url': ticket.get_webdav_link(),
                            'icon': 'mdi:ticket',
                            'id': 'ticket_access_%d' % i,
                            'class': 'sodar-irods-ticket-access-%d-btn' % i,
                            'title': ' iRODS Access Ticket',
                            'enabled': ticket.is_active(),
                        }
                    ]
                    if ticket
                    else [],
                }
            )
        for i in range(len(a_data['shortcuts'])):
            if cache_item:
                a_data['shortcuts'][i]['enabled'] = cache_item.data[
                    'shortcuts'
                ].get(a_data['shortcuts'][i]['id'])
            else:
                a_data['shortcuts'][i]['enabled'] = True
    logger.debug(
        'iRODS content retrieved ({:.1f}s)'.format(time.time() - time_start)
    )
    return ret_data
