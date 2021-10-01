"""BIH germline config study app plugin for samplesheets"""

from django.conf import settings
from django.contrib import auth
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from samplesheets.models import Investigation, Study, GenericMaterial
from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import get_index_by_header

from samplesheets.studyapps.utils import get_igv_session_url, get_igv_irods_url

from .utils import get_pedigree_file_path, get_families, get_family_sources


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.studyapps.germline'

User = auth.get_user_model()


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for germline studies in sample sheets"""

    # Properties required by django-plugins ------------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_germline'

    #: Title (used in templates)
    title = 'Sample Sheets Germline Study Plugin'

    # Properties defined in SampleSheetStudyPluginPoint ------------------------

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
                    'title': 'View links to pedigree BAM, VCF and IGV session '
                    'files',
                },
            },
            'data': [],
        }

        # NOTE: This expects that the first field named "family" is the one..
        family_idx = get_index_by_header(study_tables['study'], 'family')
        igv_urls = {}
        id_idx = 0  # Default is the source name
        query_key = 'source'  # Default is source

        # Group by family
        if family_idx and study_tables['study']['col_values'][family_idx] == 1:
            id_idx = family_idx
            query_key = 'family'

            for family in get_families(study):
                sources = get_family_sources(study, family)
                igv_urls[family] = get_igv_session_url(
                    sources.first(), APP_NAME
                )

        # Else group by source
        else:
            for source in study.get_sources():
                igv_urls[source.name] = get_igv_session_url(source, APP_NAME)

        if not igv_urls:
            return ret  # Nothing else to do

        for row in study_tables['study']['table_data']:
            ped_id = row[id_idx]['value']
            source_id = row[0]['value']
            enabled = True

            # Fix potential crash due to pedigree mapping failure (issue #589)
            igv_url = igv_urls[ped_id] if ped_id in igv_urls else None

            # Set initial state based on URL and cache
            if not igv_url or (
                cache_item
                and source_id in cache_item.data['bam']
                and not cache_item.data['bam'][source_id]
                and ped_id in cache_item.data['vcf']
                and not cache_item.data['vcf'][ped_id]
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
                'bam': {'title': 'BAM Files', 'files': []},
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

        # BAM links
        for source in sources:
            # Use cached value if present
            if cache_item and source.name in cache_item.data['bam']:
                bam_path = cache_item.data['bam'][source.name]

            # Else query iRODS
            else:
                bam_path = get_pedigree_file_path(
                    file_type='bam', source=source, study_tables=study_tables
                )

            if bam_path:
                ret['data']['bam']['files'].append(
                    {
                        'label': source.name,
                        'url': webdav_url + bam_path,
                        'title': 'Download BAM file',
                        'extra_links': [
                            {
                                'label': 'Add BAM file to IGV',
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

    def update_cache(self, name=None, project=None, user=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        :param user: User object to denote user triggering the update (optional)
        """
        if name and name.split('/')[0] != 'irods':
            return

        cache_backend = get_backend_api('sodar_cache')

        tb = SampleSheetTableBuilder()
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
            if investigation.get_configuration() != self.config_name:
                continue

            # If a name is given, only update that specific CacheItem
            if name:
                study_uuid = name.split('/')[-1]
                studies = Study.objects.filter(sodar_uuid=study_uuid)
            else:
                studies = Study.objects.filter(investigation=investigation)

            for study in studies:
                # Get paths for all latest bam files for all sources in family
                item_name = 'irods/{}'.format(study.sodar_uuid)
                bam_paths = {}
                vcf_paths = {}
                prev_query_id = None
                # Build render table
                study_tables = tb.build_study_tables(study, ui=False)
                sources = GenericMaterial.objects.filter(
                    study=study, item_type='SOURCE'
                )

                for source in sources:
                    # BAM path for each source
                    bam_path = get_pedigree_file_path(
                        file_type='bam',
                        source=source,
                        study_tables=study_tables,
                    )
                    bam_paths[source.name.strip()] = bam_path

                    # Get family ID
                    if (
                        'Family' in source.characteristics
                        and source.characteristics['Family']['value']
                    ):
                        query_id = source.characteristics['Family']['value']
                    else:
                        query_id = source.name.strip()

                    # One VCF path for each family (or source if no family)
                    if (
                        query_id != prev_query_id
                        or query_id == source.name.strip()
                    ):
                        vcf_path = get_pedigree_file_path(
                            file_type='vcf',
                            source=source,
                            study_tables=study_tables,
                        )
                        vcf_paths[query_id] = vcf_path

                    prev_query_id = query_id

                # Update data
                updated_data = {'bam': bam_paths, 'vcf': vcf_paths}
                cache_backend.set_cache_item(
                    name=item_name,
                    app_name=APP_NAME,
                    user=user,
                    data=updated_data,
                    project=project,
                )
