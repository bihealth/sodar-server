"""Tests for REST API views in the samplesheets app"""

import json

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import RemoteSiteMixin, RemoteProjectMixin
from projectroles.tests.test_views_api import TestAPIViewsBase

# Sodarcache dependency
from sodarcache.models import JSONCacheItem

# Landingzones dependency
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin

from samplesheets.io import SampleSheetIO
from samplesheets.models import Investigation, Assay, GenericMaterial, ISATab
from samplesheets.rendering import (
    SampleSheetTableBuilder,
    STUDY_TABLE_CACHE_ITEM,
)
from samplesheets.sheet_config import SheetConfigAPI
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)
from samplesheets.tests.test_sheet_config import SheetConfigMixin
from samplesheets.tests.test_views import (
    TestViewsBase,
    REMOTE_SITE_NAME,
    REMOTE_SITE_URL,
    REMOTE_SITE_DESC,
    REMOTE_SITE_SECRET,
)
from samplesheets.views import SheetImportMixin


app_settings = AppSettingAPI()
conf_api = SheetConfigAPI()
table_builder = SampleSheetTableBuilder()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets'
SHEET_TSV_DIR = SHEET_DIR + 'i_small2/'
SHEET_PATH = SHEET_DIR + 'i_small2.zip'
SHEET_PATH_EDITED = SHEET_DIR + 'i_small2_edited.zip'
SHEET_NAME_ALT = 'i_small.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2_alt.zip'
SHEET_PATH_NO_PLUGIN_ASSAY = SHEET_DIR_SPECIAL + 'i_small_assay_no_plugin.zip'
IRODS_FILE_MD5 = '0b26e313ed4a7ca6904b0e9369e5b957'


# TODO: Add testing for study table cache updates


class TestSampleSheetAPIBase(SampleSheetIOMixin, TestAPIViewsBase):
    """Base view for samplesheets API views tests"""


class TestInvestigationRetrieveAPIView(TestSampleSheetAPIBase):
    """Tests for InvestigationRetrieveAPIView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test get() in InvestigationRetrieveAPIView"""
        url = reverse(
            'samplesheets:api_investigation_retrieve',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)

        expected = {
            'sodar_uuid': str(self.investigation.sodar_uuid),
            'identifier': self.investigation.identifier,
            'file_name': self.investigation.file_name,
            'project': str(self.project.sodar_uuid),
            'title': self.investigation.title,
            'description': self.investigation.description,
            'irods_status': False,
            'parser_version': self.investigation.parser_version,
            'archive_name': self.investigation.archive_name,
            'comments': self.investigation.comments,
            'studies': {
                str(self.study.sodar_uuid): {
                    'identifier': self.study.identifier,
                    'file_name': self.study.file_name,
                    'title': self.study.title,
                    'description': self.study.description,
                    'comments': self.study.comments,
                    'irods_path': None,
                    'sodar_uuid': str(self.study.sodar_uuid),
                    'assays': {
                        str(self.assay.sodar_uuid): {
                            'file_name': self.assay.file_name,
                            'technology_platform': self.assay.technology_platform,
                            'technology_type': self.assay.technology_type,
                            'measurement_type': self.assay.measurement_type,
                            'comments': self.assay.comments,
                            'irods_path': None,
                            'sodar_uuid': str(self.assay.sodar_uuid),
                        }
                    },
                }
            },
        }
        self.assertEqual(json.loads(response.content), expected)


class TestSheetImportAPIView(
    SheetImportMixin, SheetConfigMixin, LandingZoneMixin, TestSampleSheetAPIBase
):
    """Tests for SampleSheetImportAPIView"""

    def setUp(self):
        super().setUp()
        self.cache_backend = get_backend_api('sodar_cache')

    def test_import_zip(self):
        """Test importing sheets as zip archive"""
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

    def test_import_tsv(self):
        """Test Test importing sheets as ISA-Tab tsv files"""
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        tsv_file_i = open(SHEET_TSV_DIR + 'i_small2.txt', 'r')
        tsv_file_s = open(SHEET_TSV_DIR + 's_small2.txt', 'r')
        tsv_file_a = open(SHEET_TSV_DIR + 'a_small2.txt', 'r')
        post_data = {
            'file_investigation': tsv_file_i,
            'file_study': tsv_file_s,
            'file_assay': tsv_file_a,
        }
        response = self.request_knox(
            url, method='POST', format='multipart', data=post_data
        )
        tsv_file_i.close()
        tsv_file_s.close()
        tsv_file_a.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

    def test_replace(self):
        """Test replacing sheets"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        app_settings.set(
            APP_NAME,
            'sheet_config',
            conf_api.get_sheet_config(investigation),
            project=self.project,
        )

        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)
        self.assertIsNone(GenericMaterial.objects.filter(name='0816').first())

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)
        # Added material
        self.assertIsNotNone(
            GenericMaterial.objects.filter(name='0816').first()
        )

    def test_replace_display_config_keep(self):
        """Test replacing sheets and ensure user display configs are kept"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        inv_tables = table_builder.build_inv_tables(investigation)
        sheet_config = self.build_sheet_config(investigation, inv_tables)
        app_settings.set(
            APP_NAME, 'sheet_config', sheet_config, project=self.project
        )
        display_config = conf_api.build_display_config(inv_tables, sheet_config)
        app_settings.set(
            APP_NAME,
            'display_config_default',
            display_config,
            project=self.project,
        )
        app_settings.set(
            APP_NAME,
            'display_config',
            display_config,
            project=self.project,
            user=self.user,
        )
        self.assertEqual(
            app_settings.get(
                APP_NAME,
                'display_config',
                project=self.project,
                user=self.user,
            ),
            display_config,
        )

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            app_settings.get(
                APP_NAME,
                'display_config',
                project=self.project,
                user=self.user,
            ),
            display_config,
        )

    def test_replace_display_config_delete(self):
        """Test replacing sheets and ensure user display configs are deleted"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        inv_tables = table_builder.build_inv_tables(investigation)
        sheet_config = self.build_sheet_config(investigation, inv_tables)
        app_settings.set(
            APP_NAME, 'sheet_config', sheet_config, project=self.project
        )
        display_config = conf_api.build_display_config(inv_tables, sheet_config)
        app_settings.set(
            APP_NAME,
            'display_config_default',
            display_config,
            project=self.project,
        )
        app_settings.set(
            APP_NAME,
            'display_config',
            display_config,
            project=self.project,
            user=self.user,
        )
        self.assertEqual(
            app_settings.get(
                APP_NAME,
                'display_config',
                project=self.project,
                user=self.user,
            ),
            display_config,
        )

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            app_settings.get(
                APP_NAME,
                'display_config',
                project=self.project,
                user=self.user,
            ),
            {},
        )

    def test_replace_alt_sheet(self):
        """Test replacing with an alternative sheet and irods_status=False"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        app_settings.set(
            APP_NAME,
            'sheet_config',
            conf_api.get_sheet_config(investigation),
            project=self.project,
        )

        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)

    def test_replace_alt_sheet_irods(self):
        """Test replacing with alternative sheet and irods (should fail)"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        investigation.irods_status = True  # fake irods status
        investigation.save()

        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

    def test_replace_zone(self):
        """Test replacing sheets with exising landing zone"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        investigation.irods_status = True
        investigation.save()
        assay = Assay.objects.filter(study__investigation=investigation).first()
        zone = self.make_landing_zone(
            'new_zone',
            self.project,
            self.user,
            assay,
            status='FAILED',
        )
        app_settings.set(
            APP_NAME,
            'sheet_config',
            conf_api.get_sheet_config(investigation),
            project=self.project,
        )
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)
        self.assertIsNone(GenericMaterial.objects.filter(name='0816').first())
        self.assertEqual(LandingZone.objects.filter(assay=assay).count(), 1)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)
        self.assertIsNotNone(
            GenericMaterial.objects.filter(name='0816').first()
        )
        self.investigation = Investigation.objects.get(
            project=self.project, active=True
        )
        zone.refresh_from_db()
        self.assertEqual(
            LandingZone.objects.get(
                assay__study__investigation=self.investigation
            ),
            zone,
        )
        self.assertEqual(
            zone.assay,
            Assay.objects.filter(
                study__investigation=self.investigation
            ).first(),
        )

    def test_replace_study_cache(self):
        """Test replacing sheets with existing study table cache"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        conf_api.get_sheet_config(investigation)
        study = investigation.studies.first()
        study_uuid = str(study.sodar_uuid)

        # Build study tables and cache item
        study_tables = table_builder.build_study_tables(study)
        cache_name = STUDY_TABLE_CACHE_ITEM.format(study=study_uuid)
        self.cache_backend.set_cache_item(
            APP_NAME, cache_name, study_tables, 'json', self.project
        )
        cache_args = [APP_NAME, cache_name, self.project]
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, study_tables)
        self.assertEqual(JSONCacheItem.objects.count(), 1)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, {})
        self.assertEqual(JSONCacheItem.objects.count(), 1)

    def test_replace_study_cache_new_sheet(self):
        """Test replacing with study table cache and different sheet"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        conf_api.get_sheet_config(investigation)
        study = investigation.studies.first()
        study_uuid = str(study.sodar_uuid)

        study_tables = table_builder.build_study_tables(study)
        cache_name = STUDY_TABLE_CACHE_ITEM.format(study=study_uuid)
        self.cache_backend.set_cache_item(
            APP_NAME, cache_name, study_tables, 'json', self.project
        )
        cache_args = [APP_NAME, cache_name, self.project]
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, study_tables)
        self.assertEqual(JSONCacheItem.objects.count(), 1)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertIsNone(cache_item)
        self.assertEqual(JSONCacheItem.objects.count(), 0)

    def test_import_no_plugin_assay(self):
        """Test post() with an assay without plugin"""
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH_NO_PLUGIN_ASSAY, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(
            response.data['sodar_warnings'],
            [self.get_assay_plugin_warning(Assay.objects.all().first())],
        )

    def test_post_sync(self):
        """Test post() with sheet sync enabled (should fail)"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)

        url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )
        with open(SHEET_PATH, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)


class TestSheetISAExportAPIView(TestSampleSheetAPIBase):
    """Tests for SheetISAExportAPIView"""

    def test_get_zip(self):
        """Test zip export in SampleSheetISAExportAPIView"""
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/zip')

    def test_get_no_investigation(self):
        """Test get() with no imported investigation"""
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 404)

    def test_get_json(self):
        """Test json export  in SampleSheetISAExportAPIView"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        url = reverse(
            'samplesheets:api_export_json',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url)
        sheet_io = SampleSheetIO()
        expected = sheet_io.export_isa(investigation)
        expected['date_modified'] = str(investigation.date_modified)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)


class TestSampleDataFileExistsAPIView(TestSampleSheetAPIBase):
    """Tests for SampleDataFileExistsAPIView"""

    @override_settings(ENABLE_IRODS=False)
    def test_get_no_irods(self):
        """Test getting file existence info without iRODS (should fail)"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': IRODS_FILE_MD5})
        self.assertEqual(response.status_code, 500)


# NOTE: Not yet standardized api, use old base class to test
class TestRemoteSheetGetAPIView(
    RemoteSiteMixin, RemoteProjectMixin, TestViewsBase
):
    """Tests for RemoteSheetGetAPIView"""

    def setUp(self):
        super().setUp()
        # Create target site
        self.target_site = self.make_site(
            name=REMOTE_SITE_NAME,
            url=REMOTE_SITE_URL,
            mode=SODAR_CONSTANTS['SITE_MODE_TARGET'],
            description=REMOTE_SITE_DESC,
            secret=REMOTE_SITE_SECRET,
        )
        # Create target project
        self.target_project = self.make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES'],
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_get_tables(self):
        """Test getting the investigation as rendered tables"""
        response = self.client.get(
            reverse(
                'samplesheets:api_remote_get',
                kwargs={
                    'project': self.project.sodar_uuid,
                    'secret': REMOTE_SITE_SECRET,
                },
            )
        )
        expected = {
            'studies': {
                str(self.study.sodar_uuid): table_builder.build_study_tables(
                    self.study
                )
            }
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)

    def test_get_isatab(self):
        """Test getting the investigation as ISA-Tab"""
        response = self.client.get(
            reverse(
                'samplesheets:api_remote_get',
                kwargs={
                    'project': self.project.sodar_uuid,
                    'secret': REMOTE_SITE_SECRET,
                },
            ),
            {'isa': '1'},
        )
        sheet_io = SampleSheetIO()
        expected = sheet_io.export_isa(self.investigation)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)
