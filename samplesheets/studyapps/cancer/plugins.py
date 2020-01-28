from django.conf import settings
from django.contrib import auth
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from samplesheets.models import Investigation, Study, GenericMaterial
from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import (
    get_sample_libraries,
    get_study_libraries,
    get_isa_field_name,
)

from samplesheets.studyapps.utils import get_igv_session_url, get_igv_irods_url

from .utils import get_library_file_path


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.studyapps.cancer'

User = auth.get_user_model()


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for cancer studies in sample sheets"""

    # Properties required by django-plugins ------------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_cancer'

    #: Title (used in templates)
    title = 'Sample Sheets Cancer Study Plugin'

    # Properties defined in SampleSheetStudyPluginPoint ------------------------

    #: Configuration name
    config_name = 'bih_cancer'

    #: Description string
    description = 'Sample sheets cancer study app'

    #: Required permission for accessing the plugin
    permission = None

    def _ms_assays(self, study):
        """Return True if study only contains mass spectrometry assays"""
        # HACK: temporary workaround for issue #482
        for assay in study.assays.all():
            if get_isa_field_name(assay.technology_type) != 'mass spectrometry':
                return False

        return True

    def get_shortcut_column(self, study, study_tables):
        """
        Return structure containing links for an extra study table links column.

        :param study: Study object
        :param study_tables: Rendered study tables (dict)
        :return: Dict or None if not found
        """
        # Omit for mass spectrometry studies (workaround for issue #482)
        if self._ms_assays(study):
            return None

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
                    'icon': 'fa-share-square-o',
                    'title': 'Open IGV session file for case in IGV',
                },
                'files': {
                    'type': 'modal',
                    'icon': 'fa-folder-open-o',
                    'title': 'View links to BAM, VCF and IGV session files '
                    'for the case',
                },
            },
            'data': [],
        }

        igv_urls = {}

        for source in study.get_sources():
            igv_urls[source.name] = get_igv_session_url(source, APP_NAME)

        if not igv_urls:
            return ret

        # NOTE: Not fool proof but better than assay search for lib id:s
        # TODO: Better way to do this? Tired now so this may be silly
        def _source_files_exist(cache, prefix, item_type):
            vals = list(
                set(
                    [
                        v
                        for k, v in cache.data[item_type].items()
                        if prefix in k and k.index(prefix) == 0
                    ]
                )
            )

            if len(vals) == 0 or (len(vals) == 1 and not vals[0]):
                return False

            return True

        for row in study_tables['study']['table_data']:
            source_id = row[0]['value']
            source_prefix = source_id + '-'
            enabled = True

            # Set initial state based on cache
            if (
                cache_item
                and not _source_files_exist(cache_item, source_prefix, 'bam')
                and not _source_files_exist(cache_item, source_prefix, 'vcf')
            ):
                enabled = False

            ret['data'].append(
                {
                    'igv': {'url': igv_urls[source_id], 'enabled': enabled},
                    'files': {
                        'query': {'key': 'case', 'value': source_id},
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
        case_id = kwargs['case'][0]
        source = GenericMaterial.objects.filter(
            study=study, name=case_id
        ).first()

        if not case_id or not source:  # This should not happen..
            return None

        webdav_url = settings.IRODS_WEBDAV_URL

        ret = {
            'title': 'Case-Wise Links for {}'.format(case_id),
            'data': {
                'session': {'title': 'IGV Session File', 'files': []},
                'bam': {'title': 'BAM Files', 'files': []},
                'vcf': {'title': 'VCF Files', 'files': []},
            },
        }

        if cache_backend:
            cache_item = cache_backend.get_cache_item(
                app_name=APP_NAME,
                name='irods/{}'.format(study.sodar_uuid),
                project=study.get_project(),
            )

        def _add_lib_path(library, file_type):
            # Get iRODS URLs from cache if it's available
            if cache_item and library.name in cache_item.data[file_type]:
                path = cache_item.data[file_type][library.name]

            # Else query iRODS
            else:
                path = get_library_file_path(
                    file_type=file_type, library=library
                )

            if path:
                ret['data'][file_type]['files'].append(
                    {
                        'label': library.name,
                        'url': webdav_url + path,
                        'title': 'Download {} file'.format(file_type.upper()),
                        'extra_links': [
                            {
                                'label': 'Add {} file to IGV'.format(
                                    file_type.upper()
                                ),
                                'icon': 'plus',
                                'url': get_igv_irods_url(path, merge=True),
                            }
                        ],
                    }
                )

        samples = source.get_samples()

        if not samples:
            return ret

        libraries = []

        for sample in source.get_samples():
            libraries += get_sample_libraries(sample, study_tables)

        for library in libraries:
            _add_lib_path(library, 'bam')
            _add_lib_path(library, 'vcf')

        # Session file link (only make available if other files exist)
        if (
            len(ret['data']['bam']['files']) > 0
            or len(ret['data']['vcf']['files']) > 0
        ):
            ret['data']['session']['files'].append(
                {
                    'label': 'Download session file',
                    'url': reverse(
                        'samplesheets.studyapps.cancer:igv',
                        kwargs={'genericmaterial': source.sodar_uuid},
                    ),
                    'title': None,
                    'extra_links': [
                        {
                            'label': 'Open session file in IGV '
                            '(replace current)',
                            'icon': 'share-square-o',
                            'url': get_igv_session_url(
                                source, APP_NAME, merge=False
                            ),
                        },
                        {
                            'label': 'Merge into current IGV session',
                            'icon': 'plus',
                            'url': get_igv_session_url(
                                source, APP_NAME, merge=True
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
        # Omit for mass spectrometry studies (workaround for issue #482)
        if name and name.split('/')[0] != 'irods':
            return

        cache_backend = get_backend_api('sodar_cache')

        if not cache_backend:
            return

        tb = SampleSheetTableBuilder()

        projects = (
            [project]
            if project
            else Project.objects.filter(type=PROJECT_TYPE_PROJECT)
        )

        for project in projects:
            try:
                investigation = Investigation.objects.get(
                    project=project, active=True
                )

            except Investigation.DoesNotExist:
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
                if self._ms_assays(study):
                    continue

                item_name = 'irods/{}'.format(study.sodar_uuid)
                bam_paths = {}
                vcf_paths = {}

                # Build render table
                study_tables = tb.build_study_tables(study)

                for library in get_study_libraries(study, study_tables):
                    if not library.assay:
                        continue

                    bam_path = get_library_file_path(
                        file_type='bam', library=library
                    )
                    bam_paths[library.name] = bam_path

                    bam_path = get_library_file_path(
                        file_type='vcf', library=library
                    )
                    vcf_paths[library.name] = bam_path

                updated_data = {'bam': bam_paths, 'vcf': vcf_paths}
                cache_backend.set_cache_item(
                    name=item_name,
                    app_name=APP_NAME,
                    user=user,
                    data=updated_data,
                    project=project,
                )
