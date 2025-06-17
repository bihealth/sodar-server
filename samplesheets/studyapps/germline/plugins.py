"""BIH germline config study app plugin for samplesheets"""

import logging

from django.conf import settings
from django.contrib import auth
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from samplesheets.models import Investigation, Study, GenericMaterial
from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.studyapps.germline.utils import (
    get_pedigree_file_path,
    get_families,
    get_family_sources,
)
from samplesheets.studyapps.utils import (
    get_igv_omit_list,
    check_igv_file_suffix,
    check_igv_file_path,
    get_igv_session_url,
    get_igv_irods_url,
)
from samplesheets.utils import get_index_by_header


logger = logging.getLogger(__name__)
table_builder = SampleSheetTableBuilder()
User = auth.get_user_model()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.studyapps.germline'


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for germline studies in sample sheets"""

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_germline'

    #: Title (used in templates)
    title = 'Sample Sheets Germline Study Plugin'

    #: Configuration name
    config_name = 'bih_germline'

    #: Description string
    description = 'Sample sheets germline study app'

    #: Required permission for accessing the plugin
    permission = None

    def get_shortcut_column(self, study, study_tables):
        """
        Return structure containing links for an extra study table links column.

        :param study: Study object
        :param study_tables: Rendered study tables (dict)
        :return: Dict or None if not found
        """
        cache_backend = get_backend_api('sodar_cache')
        cache_item = None
        # Get iRODS URLs from cache if it's available
        if cache_backend:
            cache_item = cache_backend.get_cache_item(
                app_name=APP_NAME,
                name='irods/{}'.format(study.sodar_uuid),
                project=study.get_project(),
            )

        ret = {
            'schema': {
                'igv': {
                    'type': 'link',
                    'icon': 'mdi:open-in-new',
                    'title': 'Open IGV session file for pedigree in IGV',
                },
                'files': {
                    'type': 'modal',
                    'icon': 'mdi:folder-open-outline',
                    'title': 'View links to pedigree BAM/CRAM, VCF and IGV '
                    'session files',
                },
            },
            'data': [],
        }

        # NOTE: This expects that the first field named "family" is the one..
        family_idx = get_index_by_header(study_tables['study'], 'family')
        igv_urls = {}
        id_idx = 0  # Default is the source name
        query_key = 'source'  # Default is source
        study_sources = study.get_sources()
        # Group by family
        if family_idx and study_tables['study']['col_values'][family_idx] == 1:
            logger.debug('Grouping by family')
            id_idx = family_idx
            query_key = 'family'
            source_lookup = {}
            for source in study_sources:
                family = None
                if source.characteristics.get(
                    'Family'
                ) and source.characteristics['Family'].get('value'):
                    family = source.characteristics['Family']['value']
                if family and family not in source_lookup:
                    source_lookup[family] = source
            for family in get_families(study):
                igv_urls[family] = get_igv_session_url(
                    source_lookup[family], APP_NAME
                )
        # Else group by source
        else:
            logger.debug('Grouping by source')
            for source in study_sources:
                igv_urls[source.name] = get_igv_session_url(source, APP_NAME)
        if not igv_urls:
            return ret  # Nothing else to do

        logger.debug('Set shortcut column data..')
        for row in study_tables['study']['table_data']:
            ped_id = row[id_idx]['value']
            source_id = row[0]['value']
            enabled = True
            # Fix potential crash due to pedigree mapping failure (issue #589)
            igv_url = igv_urls[ped_id] if ped_id in igv_urls else None
            # Set initial state based on URL and cache
            if not igv_url or (
                cache_item
                and not cache_item.data['bam'].get(source_id)
                and not cache_item.data['vcf'].get(ped_id)
            ):
                enabled = False
            ret['data'].append(
                {
                    'igv': {
                        'url': igv_url if igv_url else '#',
                        'enabled': enabled,
                    },
                    'files': {
                        'query': {'key': query_key, 'value': ped_id},
                        'enabled': enabled,
                    },
                }
            )
        return ret

    def get_shortcut_links(self, study, study_tables, **kwargs):
        """
        Return links for shortcut modal.

        :param study: Study object
        :param study_tables: Rendered study tables (dict)
        :return: Dict or None
        """
        cache_backend = get_backend_api('sodar_cache')
        cache_item = None
        query_id = None
        find_by_source = False

        if 'family' in kwargs:
            query_id = kwargs['family'][0]
        elif 'source' in kwargs:
            query_id = kwargs['source'][0]
            find_by_source = True
        if not query_id:  # This should not happen..
            return None

        webdav_url = settings.IRODS_WEBDAV_URL
        ret = {
            'title': 'Pedigree-Wise Links for {}'.format(query_id),
            'data': {
                'session': {'title': 'IGV Session File', 'files': []},
                'bam': {'title': 'BAM/CRAM Files', 'files': []},
                'vcf': {'title': 'VCF File', 'files': []},
            },
        }

        if find_by_source:
            sources = GenericMaterial.objects.filter(study=study, name=query_id)
        else:
            sources = get_family_sources(study, query_id)

        # Get iRODS URLs from cache if it's available
        if cache_backend:
            cache_item = cache_backend.get_cache_item(
                app_name=APP_NAME,
                name='irods/{}'.format(study.sodar_uuid),
                project=study.get_project(),
            )

        # BAM/CRAM links
        for source in sources:
            # Use cached value if present
            if cache_item and source.name in cache_item.data['bam']:
                bam_path = cache_item.data['bam'][source.name]
            else:  # Else query iRODS
                bam_path = get_pedigree_file_path(
                    file_type='bam', source=source, study_tables=study_tables
                )
            if bam_path:
                ret['data']['bam']['files'].append(
                    {
                        'label': source.name,
                        'url': webdav_url + bam_path,
                        'title': 'Download BAM/CRAM file',
                        'extra_links': [
                            {
                                'label': 'Add BAM/CRAM file to IGV',
                                'icon': 'mdi:plus-thick',
                                'url': get_igv_irods_url(bam_path, merge=True),
                            }
                        ],
                    }
                )

        # VCF link
        if (
            cache_item
            and query_id in cache_item.data['vcf']
            and cache_item.data['vcf'][query_id]
        ):
            vcf_path = cache_item.data['vcf'][query_id]
        else:
            vcf_path = get_pedigree_file_path(
                file_type='vcf',
                source=sources.first(),
                study_tables=study_tables,
            )
        if vcf_path:
            ret['data']['vcf']['files'].append(
                {
                    'label': query_id,
                    'url': webdav_url + vcf_path,
                    'title': 'Download VCF file',
                    'extra_links': [
                        {
                            'label': 'Add VCF file to IGV',
                            'icon': 'mdi:plus-thick',
                            'url': get_igv_irods_url(vcf_path, merge=True),
                        }
                    ],
                }
            )

        # Session file link (only make available if other files exist)
        if (
            len(ret['data']['bam']['files']) > 0
            or len(ret['data']['vcf']['files']) > 0
        ):
            ret['data']['session']['files'].append(
                {
                    'label': 'Download session file',
                    'url': reverse(
                        'samplesheets.studyapps.germline:igv',
                        kwargs={'genericmaterial': sources.first().sodar_uuid},
                    ),
                    'title': None,
                    'extra_links': [
                        {
                            'label': 'Open session file in IGV '
                            '(replace current)',
                            'icon': 'mdi:open-in-new',
                            'url': get_igv_session_url(
                                sources.first(), APP_NAME, merge=False
                            ),
                        },
                        {
                            'label': 'Merge into current IGV session',
                            'icon': 'mdi:plus-thick',
                            'url': get_igv_session_url(
                                sources.first(), APP_NAME, merge=True
                            ),
                        },
                    ],
                }
            )
        return ret

    @classmethod
    def _update_study_cache(cls, study, user, cache_backend, irods_backend):
        """
        Update germline study app cache for a single study.

        :param study: Study object
        :param user: User object or None
        :param cache_backend: Sodarcache backend object
        :param irods_backend: Irodsbackend object
        """
        item_name = 'irods/{}'.format(study.sodar_uuid)
        bam_paths = {}
        vcf_paths = {}
        # Get/build render tables
        study_tables = table_builder.get_study_tables(study)

        # Pre-fetch study objects to eliminate redundant queries
        obj_len = 0
        study_objs = None
        try:
            logger.debug('Querying for study objects in iRODS..')
            with irods_backend.get_session() as irods:
                study_objs = irods_backend.get_objects(
                    irods, irods_backend.get_path(study)
                )
            obj_len = len(study_objs)
            logger.debug(
                'Query returned {} data object{}'.format(
                    obj_len, 's' if obj_len != 1 else ''
                )
            )
        except FileNotFoundError:
            logger.debug('No data objects found')
        except Exception as ex:
            logger.error('Error querying for study objects: {}'.format(ex))

        project = study.get_project()
        bam_omit_list = get_igv_omit_list(project, 'bam')
        vcf_omit_list = get_igv_omit_list(project, 'vcf')

        for assay in study.assays.all():
            skip_msg = 'skipping pedigree file path search: "{}" ({})'.format(
                assay.get_display_name(), assay.sodar_uuid
            )
            assay_plugin = assay.get_plugin()
            if not assay_plugin:
                logger.warning(f'No plugin for assay, {skip_msg}')
                continue
            assay_table = study_tables['assays'][str(assay.sodar_uuid)]
            assay_path = irods_backend.get_path(assay)
            fam_idx = get_index_by_header(assay_table, 'family')
            row_idx = 0
            for row in assay_table['table_data']:
                source_name = row[0]['value']
                if source_name not in bam_paths:
                    bam_paths[source_name] = []
                # Add BAM/CRAM objects
                path = assay_plugin.get_row_path(
                    row, assay_table, assay, assay_path
                )
                # Skip if path was not found
                if not path:
                    logger.warning(
                        f'No path returned by get_row_path() for row '
                        f'{row_idx}, {skip_msg}'
                    )
                    row_idx += 1
                    continue
                if obj_len > 0 and path not in bam_paths[source_name]:
                    bam_paths[source_name] += [
                        o['path']
                        for o in study_objs
                        if o['path'].startswith(path + '/')
                        and check_igv_file_suffix(o['name'], 'bam')
                        and check_igv_file_path(o['path'], bam_omit_list)
                    ]
                # Add VCF objects
                if fam_idx and row[fam_idx].get('value'):
                    vcf_query_id = row[fam_idx]['value']
                else:  # If family column isn't present/filled, use source name
                    vcf_query_id = source_name
                if vcf_query_id not in vcf_paths:
                    vcf_paths[vcf_query_id] = []
                if obj_len > 0 and path not in vcf_paths[vcf_query_id]:
                    vcf_paths[vcf_query_id] += [
                        o['path']
                        for o in study_objs
                        if o['path'].startswith(path + '/')
                        and o['name'].lower().endswith('vcf.gz')
                        and check_igv_file_path(o['path'], vcf_omit_list)
                    ]
                row_idx += 1

        # Update data
        # NOTE: We get the last file name, assuming files are named by date
        updated_data = {
            'bam': {
                k: (
                    sorted(v, key=lambda x: x.split('/')[-1], reverse=True)[0]
                    if v and len(v) > 0
                    else None
                )
                for k, v in bam_paths.items()
            },
            'vcf': {
                k: (
                    sorted(v, key=lambda x: x.split('/')[-1], reverse=True)[0]
                    if v and len(v) > 0
                    else None
                )
                for k, v in vcf_paths.items()
            },
        }
        cache_backend.set_cache_item(
            name=item_name,
            app_name=APP_NAME,
            user=user,
            data=updated_data,
            project=study.investigation.project,
        )

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        # Expected name: "irods/{study_uuid}"
        if name and name.split('/')[0] != 'irods':
            logger.debug('Unknown cache item name "{}", skipping'.format(name))
            return
        cache_backend = get_backend_api('sodar_cache')
        irods_backend = get_backend_api('omics_irods')
        projects = (
            [project]
            if project
            else Project.objects.filter(type=PROJECT_TYPE_PROJECT)
        )

        for project in projects:
            investigation = Investigation.objects.filter(
                project=project, active=True
            ).first()
            if not investigation:
                continue
            # Only apply for investigations with the correct configuration
            logger.debug(
                'Updating cache for project {}..'.format(
                    project.get_log_title()
                )
            )
            # If a name is given, only update that specific CacheItem
            if name:
                study_uuid = name.split('/')[-1]
                studies = Study.objects.filter(sodar_uuid=study_uuid)
            else:
                studies = Study.objects.filter(investigation=investigation)
            for study in studies:
                # Only apply for studies using this plugin
                if (
                    not study.get_plugin()
                    or study.get_plugin().__class__ != self.__class__
                ):
                    continue
                logger.debug(
                    'Updating cache for study "{}" ({})..'.format(
                        study.get_display_name(), study.sodar_uuid
                    )
                )
                self._update_study_cache(
                    study, user, cache_backend, irods_backend
                )
