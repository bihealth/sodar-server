"""Plugin tests for the cancer study app with taskflow"""

import os

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowbackendTestBase

from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import SampleSheetModelMixin
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.studyapps.germline.utils import get_pedigree_file_path
from samplesheets.studyapps.utils import get_igv_session_url


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.studyapps.cancer'
PLUGIN_NAME_CANCER = 'samplesheets_study_cancer'
PLUGIN_TITLE_CANCER = 'Sample Sheets Cancer Study Plugin'
SHEET_PATH = SHEET_DIR + 'bih_cancer.zip'
SOURCE_ID_NORMAL = 'normal1'
SOURCE_ID_TUMOR = 'tumor1'
SAMPLE_ID_NORMAL = 'normal1-N1'
SAMPLE_ID_TUMOR = 'tumor1-T1'
LIBRARY_ID_NORMAL = 'normal1-N1-DNA1-WES1'
LIBRARY_ID_TUMOR = 'tumor1-T1-DNA1-WES1'
CASE_IDS = [
    'normal1-N1-DNA1-WES1',
    'tumor1-T1-DNA1-WES1',
    'normal2-N1-DNA1-WES1',
    'tumor2-T1-DNA1-WES1',
]


class TestCancerPlugin(
    SampleSheetModelMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Class for testing the cancer studyapp plugin"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)

        # Set up plugin and helpers
        self.plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_CANCER)
        self.tb = SampleSheetTableBuilder()
        self.cache_name = 'irods/{}'.format(self.study.sodar_uuid)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.source_path = os.path.join(self.assay_path, LIBRARY_ID_NORMAL)
        self.source = self.study.get_sources().first()
        self.cache_backend = get_backend_api('sodar_cache')
        self.cache_name = 'irods/{}'.format(self.study.sodar_uuid)

    def test_plugin_retrieval(self):
        """Test retrieving SampleSheetStudyPlugin from the database"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_CANCER)
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.get_model().name, PLUGIN_NAME_CANCER)
        self.assertEqual(plugin.name, PLUGIN_NAME_CANCER)
        self.assertEqual(plugin.get_model().title, PLUGIN_TITLE_CANCER)
        self.assertEqual(plugin.title, PLUGIN_TITLE_CANCER)

    def test_get_shortcut_column(self):
        """Test get_shortcut_column() with no cache item or files"""
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)
        self.assertIsInstance(sc, dict)
        self.assertEqual(len(sc['data']), 4)
        row = sc['data'][0]
        self.assertEqual(
            row['igv']['url'],
            get_igv_session_url(self.source, APP_NAME),
        )
        self.assertEqual(row['igv']['enabled'], True)  # Enabled by default
        self.assertEqual(row['files']['query']['key'], 'case')
        self.assertEqual(row['files']['query']['value'], SOURCE_ID_NORMAL)
        self.assertEqual(row['files']['enabled'], True)

    def test_get_shortcut_column_cache(self):
        """Test get_shortcut_column() with cache and no files"""
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)
        for i in range(0, 4):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_column_files(self):
        """Test get_shortcut_column() with files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)

        self.assertEqual(sc['data'][0]['igv']['enabled'], True)
        self.assertEqual(sc['data'][0]['files']['enabled'], True)
        for i in range(1, 4):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_links(self):
        """Test get_shortcut_links() with no cache item or files"""
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )
        self.assertIsInstance(sl, dict)
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_cache(self):
        """Test get_shortcut_links() with cache item and no files"""
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )
        self.assertIsInstance(sl, dict)
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_files(self):
        """Test get_shortcut_links() with files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )

        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)
        self.assertEqual(
            sl['data']['session']['files'][0]['url'],
            reverse(
                'samplesheets.studyapps.cancer:igv',
                kwargs={'genericmaterial': self.source.sodar_uuid},
            ),
        )
        self.assertEqual(
            sl['data']['bam']['files'][0]['url'],
            settings.IRODS_WEBDAV_URL
            + get_pedigree_file_path('bam', self.source, study_tables),
        )
        self.assertEqual(
            sl['data']['vcf']['files'][0]['url'],
            settings.IRODS_WEBDAV_URL
            + get_pedigree_file_path('vcf', self.source, study_tables),
        )

    def test_get_shortcut_links_multiple(self):
        """Test get_shortcut_links() with multiple BAM/VCF files"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test_2022-11-06.bam'.format(SAMPLE_ID_NORMAL)
        )
        bam_path2 = os.path.join(
            self.source_path, '{}_test_2022-11-07.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path,
            '{}_test.vcf_2022-11-06.vcf.gz'.format(SAMPLE_ID_NORMAL),
        )
        vcf_path2 = os.path.join(
            self.source_path,
            '{}_test.vcf_2022-11-07.vcf.gz'.format(SAMPLE_ID_NORMAL),
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(bam_path2)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path2)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )

        self.assertEqual(len(sl['data']['session']['files']), 1)
        # Only the most recent bam and vcf should be returned
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)
        self.assertTrue(
            sl['data']['bam']['files'][0]['url'].endswith(bam_path2)
        )
        self.assertTrue(
            sl['data']['vcf']['files'][0]['url'].endswith(vcf_path2)
        )

    def test_get_shortcut_links_bam(self):
        """Test get_shortcut_links() with BAM file only"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )
        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_vcf(self):
        """Test get_shortcut_links() with VCF file only"""
        self.irods.collections.create(self.source_path)
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(vcf_path)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )
        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)

    def test_get_shortcut_links_invalid(self):
        """Test get_shortcut_links() with a non-BAM/VCF file"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.txt'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SAMPLE_ID_NORMAL]
        )
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_files_omit(self):
        """Test get_shortcut_links() with omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        # Create omittable files which come before real ones alphabetically
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path_omit)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )

        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)
        self.assertEqual(
            sl['data']['session']['files'][0]['url'],
            reverse(
                'samplesheets.studyapps.cancer:igv',
                kwargs={'genericmaterial': self.source.sodar_uuid},
            ),
        )
        self.assertEqual(
            sl['data']['bam']['files'][0]['url'],
            settings.IRODS_WEBDAV_URL
            + get_pedigree_file_path('bam', self.source, study_tables),
        )
        self.assertEqual(
            sl['data']['vcf']['files'][0]['url'],
            settings.IRODS_WEBDAV_URL
            + get_pedigree_file_path('vcf', self.source, study_tables),
        )

    def test_get_shortcut_links_files_omit_only(self):
        """Test get_shortcut_links() with only omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_files_omit_override(self):
        """Test get_shortcut_links() with project-specific omit override"""
        app_settings.set(
            'samplesheets',
            'igv_omit_bam',
            'test.bam, xxx.bam',
            project=self.project,
        )
        app_settings.set(
            'samplesheets',
            'igv_omit_vcf',
            'test.vcf.gz, yyy.vcf.gz',
            project=self.project,
        )
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, case=[SOURCE_ID_NORMAL]
        )
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_update_cache(self):
        """Test update_cache()"""
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertIsInstance(ci, dict)
        for c in CASE_IDS:
            self.assertIsNone(ci['bam'][c])
            self.assertIsNone(ci['vcf'][c])

    def test_update_cache_files(self):
        """Test update_cache() with files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertEqual(ci['bam'][CASE_IDS[0]], bam_path)
        self.assertEqual(ci['vcf'][CASE_IDS[0]], vcf_path)
        for i in range(1, len(CASE_IDS) - 1):
            self.assertEqual(ci['bam'][CASE_IDS[i]], None)
            self.assertEqual(ci['vcf'][CASE_IDS[i]], None)

    def test_update_cache_files_omit(self):
        """Test update_cache() with omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        # Create omittable files which come before real ones alphabetically
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertEqual(ci['bam'][CASE_IDS[0]], bam_path)
        self.assertEqual(ci['vcf'][CASE_IDS[0]], vcf_path)
        for i in range(1, len(CASE_IDS) - 1):
            self.assertEqual(ci['bam'][CASE_IDS[i]], None)
            self.assertEqual(ci['vcf'][CASE_IDS[i]], None)

    def test_update_cache_files_omit_only(self):
        """Test update_cache() with only omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        # Create omittable files which come before real ones alphabetically
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        for i in range(0, len(CASE_IDS) - 1):
            self.assertEqual(ci['bam'][CASE_IDS[i]], None)
            self.assertEqual(ci['vcf'][CASE_IDS[i]], None)

    def test_update_cache_files_omit_override(self):
        """Test update_cache() with project-specific omit override"""
        app_settings.set(
            'samplesheets',
            'igv_omit_bam',
            'test.bam, xxx.bam',
            project=self.project,
        )
        app_settings.set(
            'samplesheets',
            'igv_omit_vcf',
            'test.vcf.gz, yyy.vcf.gz',
            project=self.project,
        )
        self.irods.collections.create(self.source_path)
        # Create omittable files which come before real ones alphabetically
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID_NORMAL)
        )
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(SAMPLE_ID_NORMAL)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertEqual(ci['bam'][CASE_IDS[0]], bam_path_omit)
        self.assertEqual(ci['vcf'][CASE_IDS[0]], vcf_path_omit)
        for i in range(1, len(CASE_IDS) - 1):
            self.assertEqual(ci['bam'][CASE_IDS[i]], None)
            self.assertEqual(ci['vcf'][CASE_IDS[i]], None)
