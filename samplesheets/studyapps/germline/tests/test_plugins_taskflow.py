"""Plugin tests for the the germline study app with taskflow"""

import os

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from samplesheets.models import GenericMaterial, ISA_META_STUDY_PLUGIN
from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.studyapps.germline.utils import get_pedigree_file_path
from samplesheets.studyapps.utils import get_igv_session_url
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import SampleSheetModelMixin
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin


app_settings = AppSettingAPI()
plugin_api = PluginAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets.studyapps.germline'
PLUGIN_NAME_GERMLINE = 'samplesheets_study_germline'
PLUGIN_TITLE_GERMLINE = 'Sample Sheets Germline Study Plugin'
SHEET_PATH = os.path.join(SHEET_DIR, 'bih_germline.zip')
FAMILY_ID = 'FAM_p1'
FAMILY_ID2 = 'FAM_p2'
SAMPLE_ID = 'p1-N1'
SAMPLE_ID_PARENT = 'p1_mother-N1'
LIBRARY_ID = 'p1-N1-DNA1-WES1'
LIBRARY_ID_PARENT = 'p1_mother-N1-DNA1-WES1'


class TestGermlinePlugin(
    SampleSheetModelMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Class for testing the germline studyapp plugin"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )

        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)

        # Set up plugin and helpers
        self.plugin = SampleSheetStudyPluginPoint.get_plugin(
            PLUGIN_NAME_GERMLINE
        )
        self.tb = SampleSheetTableBuilder()
        self.cache_name = 'irods/{}'.format(self.study.sodar_uuid)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.source_path = os.path.join(self.assay_path, LIBRARY_ID)
        self.parent_path = os.path.join(self.assay_path, LIBRARY_ID_PARENT)
        self.source = self.study.get_sources().first()
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self.cache_name = 'irods/{}'.format(self.study.sodar_uuid)

    def test_plugin_retrieval(self):
        """Test retrieving SampleSheetStudyPlugin from the database"""
        self.assertIsNotNone(self.plugin)
        self.assertEqual(self.plugin.get_model().name, PLUGIN_NAME_GERMLINE)
        self.assertEqual(self.plugin.name, PLUGIN_NAME_GERMLINE)
        self.assertEqual(self.plugin.get_model().title, PLUGIN_TITLE_GERMLINE)
        self.assertEqual(self.plugin.title, PLUGIN_TITLE_GERMLINE)

    def test_get_shortcut_column(self):
        """Test get_shortcut_column() with no cache item or files"""
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)
        self.assertIsInstance(sc, dict)
        self.assertEqual(len(sc['data']), 6)
        row = sc['data'][0]
        self.assertEqual(
            row['igv']['url'],
            get_igv_session_url(self.source, APP_NAME),
        )
        self.assertEqual(row['igv']['enabled'], True)  # Enabled by default
        self.assertEqual(row['files']['query']['key'], 'family')
        self.assertEqual(row['files']['query']['value'], 'FAM_p1')
        self.assertEqual(row['files']['enabled'], True)

    def test_get_shortcut_column_cache(self):
        """Test get_shortcut_column() with cache item and no files"""
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)
        for i in range(0, 5):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_column_files(self):
        """Test get_shortcut_column() with cache item and files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)

        for i in range(0, 2):
            self.assertEqual(sc['data'][i]['igv']['enabled'], True)
            self.assertEqual(sc['data'][i]['files']['enabled'], True)
        for i in range(3, 5):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_column_cram_file(self):
        """Test get_shortcut_column() with cache item and CRAM file in iRODS"""
        self.irods.collections.create(self.source_path)
        cram_path = os.path.join(
            self.source_path, '{}_test.cram'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(cram_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)

        for i in range(0, 2):
            self.assertEqual(sc['data'][i]['igv']['enabled'], True)
            self.assertEqual(sc['data'][i]['files']['enabled'], True)
        for i in range(3, 5):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_column_parent_vcf(self):
        """Test get_shortcut_column() with VCF file in a parent's collection"""
        self.irods.collections.create(self.parent_path)
        vcf_path = os.path.join(
            self.parent_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)

        for i in range(0, 2):
            self.assertEqual(sc['data'][i]['igv']['enabled'], True)
            self.assertEqual(sc['data'][i]['files']['enabled'], True)
        for i in range(3, 5):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_column_no_family_id(self):
        """Test get_shortcut_column() with pedigree vcf file and no family ID"""
        for s in self.study.get_sources():
            s.characteristics['Family']['value'] = ''
            s.save()
        self.irods.collections.create(self.source_path)
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID)
        )
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)

        self.assertEqual(sc['data'][0]['igv']['enabled'], True)
        self.assertEqual(sc['data'][0]['files']['enabled'], True)
        for i in range(1, 5):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_column_no_family_id_parent(self):
        """Test get_shortcut_column() with vcf file on parent and no family ID"""
        for s in self.study.get_sources():
            s.characteristics['Family']['value'] = ''
            s.save()

        self.irods.collections.create(self.parent_path)
        vcf_path = os.path.join(
            self.parent_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sc = self.plugin.get_shortcut_column(self.study, study_tables)

        self.assertEqual(sc['data'][0]['igv']['enabled'], False)
        self.assertEqual(sc['data'][0]['files']['enabled'], False)
        self.assertEqual(sc['data'][1]['igv']['enabled'], True)
        self.assertEqual(sc['data'][1]['files']['enabled'], True)
        for i in range(2, 5):
            self.assertEqual(sc['data'][i]['igv']['enabled'], False)
            self.assertEqual(sc['data'][i]['files']['enabled'], False)

    def test_get_shortcut_links(self):
        """Test get_shortcut_links() with no cache item or files"""
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
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
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertIsInstance(sl, dict)
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_files(self):
        """Test get_shortcut_links() with files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )

        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)
        self.assertEqual(
            sl['data']['session']['files'][0]['url'],
            reverse(
                'samplesheets.studyapps.germline:igv',
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

    def test_get_shortcut_links_cram(self):
        """Test get_shortcut_links() with CRAM file in iRODS"""
        self.irods.collections.create(self.source_path)
        cram_path = os.path.join(
            self.source_path, '{}_test.cram'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(cram_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )

        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)
        self.assertEqual(
            sl['data']['session']['files'][0]['url'],
            reverse(
                'samplesheets.studyapps.germline:igv',
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
            self.source_path, '{}_test_2022-11-06.bam'.format(SAMPLE_ID)
        )
        cram_path = os.path.join(
            self.source_path, '{}_test_2022-11-07.cram'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf_2022-11-06.vcf.gz'.format(FAMILY_ID)
        )
        vcf_path2 = os.path.join(
            self.source_path, '{}_test.vcf_2022-11-07.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(cram_path)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path2)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )

        self.assertEqual(len(sl['data']['session']['files']), 1)
        # Only the most recent bam/cram and vcf should be returned
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)
        self.assertTrue(
            sl['data']['bam']['files'][0]['url'].endswith(cram_path)
        )
        self.assertTrue(
            sl['data']['vcf']['files'][0]['url'].endswith(vcf_path2)
        )

    def test_get_shortcut_links_bam_only(self):
        """Test get_shortcut_links() with BAM file only"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_cram_only(self):
        """Test get_shortcut_links() with CRAM file only"""
        self.irods.collections.create(self.source_path)
        cram_path = os.path.join(
            self.source_path, '{}_test.cram'.format(SAMPLE_ID)
        )
        self.irods.data_objects.create(cram_path)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_vcf_only(self):
        """Test get_shortcut_links() with VCF file only"""
        self.irods.collections.create(self.source_path)
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(vcf_path)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)

    def test_get_shortcut_links_invalid(self):
        """Test get_shortcut_links() with a non-BAM/VCF file"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.txt'.format(SAMPLE_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_omit(self):
        """Test get_shortcut_links() with omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path_omit)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )

        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)
        self.assertEqual(
            sl['data']['session']['files'][0]['url'],
            reverse(
                'samplesheets.studyapps.germline:igv',
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

    def test_get_shortcut_links_omit_only(self):
        """Test get_shortcut_links() with only omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path_omit)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_omit_only_empty_overrides(self):
        """Test get_shortcut_links() with empty project overrides"""
        app_settings.set(
            'samplesheets', 'igv_omit_bam', '', project=self.project
        )
        app_settings.set(
            'samplesheets', 'igv_omit_vcf', '', project=self.project
        )
        self.irods.collections.create(self.source_path)
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path_omit)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertEqual(len(sl['data']['session']['files']), 1)
        self.assertEqual(len(sl['data']['bam']['files']), 1)
        self.assertEqual(len(sl['data']['vcf']['files']), 1)

    def test_get_shortcut_links_omit_cram(self):
        """Test get_shortcut_links() with omittable CRAM file in iRODS"""
        app_settings.set(
            'samplesheets', 'igv_omit_bam', '*omit.cram', project=self.project
        )
        self.irods.collections.create(self.source_path)
        cram_path_omit = os.path.join(
            self.source_path, '{}_omit.cram'.format(SAMPLE_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(cram_path_omit)
        self.irods.data_objects.create(vcf_path_omit)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
        )
        self.assertEqual(len(sl['data']['session']['files']), 0)
        self.assertEqual(len(sl['data']['bam']['files']), 0)
        self.assertEqual(len(sl['data']['vcf']['files']), 0)

    def test_get_shortcut_links_omit_override(self):
        """Test get_shortcut_links() with project-specific omit override"""
        app_settings.set(
            'samplesheets',
            'igv_omit_bam',
            '*test.bam,*xxx.bam',
            project=self.project,
        )
        app_settings.set(
            'samplesheets',
            'igv_omit_vcf',
            '*test.vcf.gz,*yyy.vcf.gz',
            project=self.project,
        )
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)

        self.plugin.update_cache(self.cache_name, self.project)
        study_tables = self.tb.build_study_tables(self.study)
        sl = self.plugin.get_shortcut_links(
            self.study, study_tables, family=[FAMILY_ID]
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
        for s in self.study.get_sources():
            self.assertIsNone(ci['bam'][s.name])
        self.assertIsNone(ci['vcf'][FAMILY_ID])
        self.assertIsNone(ci['vcf'][FAMILY_ID2])

    def test_update_cache_no_config(self):
        """Test update_cache() without config"""
        # Clear investigation configuration comments
        self.investigation.comments = {}
        self.investigation.save()
        self.plugin.update_cache(self.cache_name, self.project)
        self.assertIsNone(
            self.cache_backend.get_cache_item(
                APP_NAME, self.cache_name, self.project
            )
        )

    def test_update_cache_files(self):
        """Test update_cache() with files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertEqual(ci['bam'][self.source.name], bam_path)
        self.assertEqual(ci['vcf'][FAMILY_ID], vcf_path)
        self.assertIsNone(ci['vcf'][FAMILY_ID2])

    def test_update_cache_files_override(self):
        """Test update_cache() with files in iRODS and study override"""
        # Clear investigation configuration comments and set study override
        self.investigation.comments = {}
        self.investigation.save()
        self.study.comments = {
            ISA_META_STUDY_PLUGIN: 'samplesheets_study_germline'
        }
        self.study.save()
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertEqual(ci['bam'][self.source.name], bam_path)
        self.assertEqual(ci['vcf'][FAMILY_ID], vcf_path)
        self.assertIsNone(ci['vcf'][FAMILY_ID2])

    def test_update_cache_cram(self):
        """Test update_cache() with CRAM file in iRODS"""
        self.irods.collections.create(self.source_path)
        cram_path = os.path.join(
            self.source_path, '{}_test.cram'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(cram_path)
        self.irods.data_objects.create(vcf_path)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertEqual(ci['bam'][self.source.name], cram_path)
        self.assertEqual(ci['vcf'][FAMILY_ID], vcf_path)
        self.assertIsNone(ci['vcf'][FAMILY_ID2])

    def test_update_cache_omit(self):
        """Test update_cache() with omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        # Create omittable files which come before real ones alphabetically
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        # Omitted files should not be returned
        self.assertEqual(ci['bam'][self.source.name], bam_path)
        self.assertEqual(ci['vcf'][FAMILY_ID], vcf_path)

    def test_update_cache_omit_only(self):
        """Test update_cache() with only omittable files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        # Omitted files should not be returned
        self.assertIsNone(ci['bam'][self.source.name])
        self.assertIsNone(ci['vcf'][FAMILY_ID])

    def test_update_cache_omit_only_empty_overrides(self):
        """Test update_cache() with empty project overrides"""
        app_settings.set(
            'samplesheets', 'igv_omit_bam', '', project=self.project
        )
        app_settings.set(
            'samplesheets', 'igv_omit_vcf', '', project=self.project
        )
        self.irods.collections.create(self.source_path)
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        # Omitted files should not be returned
        self.assertEqual(ci['bam'][self.source.name], bam_path_omit)
        self.assertEqual(ci['vcf'][FAMILY_ID], vcf_path_omit)

    def test_update_cache_omit_only_cram(self):
        """Test update_cache() with omittable CRAM file in iRODS"""
        app_settings.set(
            'samplesheets', 'igv_omit_bam', '*omit.cram', project=self.project
        )
        self.irods.collections.create(self.source_path)
        cram_path_omit = os.path.join(
            self.source_path, '{}_omit.cram'.format(SAMPLE_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(cram_path_omit)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertIsNone(ci['bam'][self.source.name])
        self.assertIsNone(ci['vcf'][FAMILY_ID])

    def test_update_cache_omit_override(self):
        """Test update_cache() with project-specific omit override"""
        app_settings.set(
            'samplesheets',
            'igv_omit_bam',
            '*test.bam,*xxx.bam',
            project=self.project,
        )
        app_settings.set(
            'samplesheets',
            'igv_omit_vcf',
            '*test.vcf.gz,*yyy.vcf.gz',
            project=self.project,
        )
        self.irods.collections.create(self.source_path)
        # Create omittable files which come before real ones alphabetically
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        bam_path_omit = os.path.join(
            self.source_path, '{}_dragen_evidence.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        vcf_path_omit = os.path.join(
            self.source_path, '{}_cnv.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(bam_path_omit)
        self.irods.data_objects.create(vcf_path)
        self.irods.data_objects.create(vcf_path_omit)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        # Omitted files should not be returned
        self.assertEqual(ci['bam'][self.source.name], bam_path_omit)
        self.assertEqual(ci['vcf'][FAMILY_ID], vcf_path_omit)

    def test_update_cache_no_family(self):
        """Test update_cache() with no family characteristic in source"""
        # Clear the family characteristics and header
        for m in GenericMaterial.objects.filter(
            study=self.study, item_type='SOURCE'
        ):
            m.characteristics.pop('Family')
            m.headers.remove('Characteristics[Family]')
            m.save()
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(SAMPLE_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)
        self.plugin.update_cache(self.cache_name, self.project)
        ci = self.cache_backend.get_cache_item(
            APP_NAME, self.cache_name, self.project
        ).data
        self.assertEqual(ci['bam'][self.source.name], bam_path)
        self.assertEqual(ci['vcf'][self.source.name], vcf_path)
