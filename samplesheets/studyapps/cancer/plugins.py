"""BIH cancer config study app plugin for samplesheets"""

import logging

from django.conf import settings
from django.contrib import auth
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from samplesheets.models import Investigation, Study, Assay, GenericMaterial
from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.studyapps.cancer.utils import (
    get_library_file_path,
    get_latest_file_path,
)
from samplesheets.studyapps.utils import get_igv_session_url, get_igv_irods_url
from samplesheets.utils import get_isa_field_name, get_last_material_index


logger = logging.getLogger(__name__)
table_builder = SampleSheetTableBuilder()
User = auth.get_user_model()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
# Local constants
APP_NAME = 'samplesheets.studyapps.cancer'


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for cancer studies in sample sheets"""

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_cancer'

    #: Title (used in templates)
    title = 'Sample Sheets Cancer Study Plugin'

    #: Configuration name
    config_name = 'bih_cancer'

    #: Description string
    description = 'Sample sheets cancer study app'

    #: Required permission for accessing the plugin
    permission = None

    @classmethod
    def _has_only_ms_assays(cls, study):
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
        if self._has_only_ms_assays(study):
            logger.debug('Skipping for MS-only study')
            return None

        ret = {
            'schema': {
                'igv': {
                    'type': 'link',
                    'icon': 'mdi:open-in-new',
                    'title': 'Open IGV session file for case in IGV',
                },
                'files': {
                    'type': 'modal',
                    'icon': 'mdi:folder-open-outline',
                    'title': 'View links to BAM/CRAM, VCF and IGV session '
                    'files for the case',
                },
            },
            'data': [],
        }
        igv_urls = {}
        for source in study.get_sources():
            igv_urls[source.name] = get_igv_session_url(source, APP_NAME)
        if not igv_urls:
            logger.debug('No IGV urls generated')
            return ret

        logger.debug('Set shortcut column data..')
        # Get iRODS URLs from cache
        cache_backend = get_backend_api('sodar_cache')
        cache_item = None
        if cache_backend:
            cache_item = cache_backend.get_cache_item(
                app_name=APP_NAME,
                name='irods/{}'.format(study.sodar_uuid),
                project=study.get_project(),
            )
        # Get source libraries
        source_libs = {}
        for k, assay_table in study_tables['assays'].items():
            lib_idx = get_last_material_index(assay_table)
            for row in assay_table['table_data']:
                source_name = row[0]['value'].strip()
                lib_name = row[lib_idx]['value'].strip()
                if source_name not in source_libs:
                    source_libs[source_name] = [lib_name]
                elif lib_name not in source_libs[source_name]:
                    source_libs[source_name].append(lib_name)

        # Set links
        for row in study_tables['study']['table_data']:
            source_name = row[0]['value'].strip()
            enabled = False
            if cache_item and source_name in source_libs:
                for lib in source_libs[source_name]:
                    if cache_item.data['bam'].get(lib) or cache_item.data[
                        'vcf'
                    ].get(lib):
                        enabled = True
                        break
            elif not cache_item:
                enabled = True
            ret['data'].append(
                {
                    'igv': {'url': igv_urls[source_name], 'enabled': enabled},
                    'files': {
                        'query': {'key': 'case', 'value': source_name},
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
        case_id = kwargs['case'][0]
        source = GenericMaterial.objects.filter(
            study=study, name=case_id
        ).first()
        if not case_id or not source:  # This should not happen..
            return None

        cache_item = None
        if cache_backend:
            cache_item = cache_backend.get_cache_item(
                app_name=APP_NAME,
                name='irods/{}'.format(study.sodar_uuid),
                project=study.get_project(),
            )
        webdav_url = settings.IRODS_WEBDAV_URL
        ret = {
            'title': 'Case-Wise Links for {}'.format(case_id),
            'data': {
                'session': {'title': 'IGV Session File', 'files': []},
                'bam': {'title': 'BAM/CRAM Files', 'files': []},
                'vcf': {'title': 'VCF Files', 'files': []},
            },
        }

        def _add_lib_path(library_name, file_type):
            path = None
            if cache_item and library_name in cache_item.data[file_type]:
                path = cache_item.data[file_type][library_name]
            if path:
                ret['data'][file_type]['files'].append(
                    {
                        'label': library_name,
                        'url': webdav_url + path,
                        'title': 'Download {} file'.format(file_type.upper()),
                        'extra_links': [
                            {
                                'label': 'Add {} file to IGV'.format(
                                    'BAM/CRAM' if file_type == 'bam' else 'VCF'
                                ),
                                'icon': 'mdi:plus-thick',
                                'url': get_igv_irods_url(path, merge=True),
                            }
                        ],
                    }
                )

        # Add paths of libraries related to source
        libs = []
        for k, assay_table in study_tables['assays'].items():
            lib_idx = get_last_material_index(assay_table)
            for row in assay_table['table_data']:
                lib_name = row[lib_idx]['value'].strip()
                if row[0]['value'].strip() == case_id and lib_name not in libs:
                    _add_lib_path(lib_name, 'bam')
                    _add_lib_path(lib_name, 'vcf')
                    libs.append(lib_name)

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
                            'icon': 'mdi:open-in-new',
                            'url': get_igv_session_url(
                                source, APP_NAME, merge=False
                            ),
                        },
                        {
                            'label': 'Merge into current IGV session',
                            'icon': 'mdi:plus-thick',
                            'url': get_igv_session_url(
                                source, APP_NAME, merge=True
                            ),
                        },
                    ],
                }
            )
        return ret

    @classmethod
    def _update_study_cache(cls, study, user, cache_backend):
        """
        Update cancer study app cache for a single study.

        :param study: Study object
        :param user: User object or None
        :param cache_backend: Sodarcache backend object
        """
        irods_backend = get_backend_api('omics_irods')
        item_name = 'irods/{}'.format(study.sodar_uuid)
        bam_paths = {}
        vcf_paths = {}
        # Get/build render tables
        study_tables = table_builder.get_study_tables(study)

        # Get libraries and library file paths
        for k, assay_table in study_tables['assays'].items():
            libs = []
            lib_idx = get_last_material_index(assay_table)
            for row in assay_table['table_data']:
                lib_name = row[lib_idx]['value'].strip()
                if lib_name not in libs:
                    libs.append(lib_name)
            assay = Assay.objects.get(sodar_uuid=k)
            with irods_backend.get_session() as irods:
                # NOTE: If multiple libraries with the same name are found, they
                #       are treated as one with only the latest file returned
                for lib in libs:
                    bam_path = get_library_file_path(
                        assay, lib, 'bam', irods_backend, irods
                    )
                    if bam_path and bam_paths.get(lib):
                        bam_paths[lib] = get_latest_file_path(
                            [bam_paths[lib], bam_path]
                        )
                    elif not bam_paths.get(lib):
                        bam_paths[lib] = bam_path
                    vcf_path = get_library_file_path(
                        assay, lib, 'vcf', irods_backend, irods
                    )
                    if vcf_path and vcf_paths.get(lib):
                        vcf_paths[lib] = get_latest_file_path(
                            [vcf_paths[lib], vcf_path]
                        )
                    elif not vcf_paths.get(lib):
                        vcf_paths[lib] = vcf_path

        updated_data = {'bam': bam_paths, 'vcf': vcf_paths}
        logger.debug('Set cache item "{}": {}'.format(item_name, updated_data))
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
        # Omit for mass spectrometry studies (workaround for issue #482)
        if name and name.split('/')[0] != 'irods':
            return
        cache_backend = get_backend_api('sodar_cache')
        if not cache_backend:
            return
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
                if self._has_only_ms_assays(study):
                    continue
                self._update_study_cache(study, user, cache_backend)
