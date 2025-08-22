"""Tests for plugins in the samplesheets app"""

# NOTE: These are tests for samplesheets ProjectAppPlugin as well as generic
# tests for common plugin methods and helpers. Study/assay plugin specific tests
# should go in their own modules

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint, PluginAPI
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

from samplesheets.models import (
    GenericMaterial,
    ITEM_TYPE_MATERIAL,
    ITEM_TYPE_SAMPLE,
)
from samplesheets.plugins import (
    get_irods_content,
    SHEET_COL_VIEW,
    SHEET_COL_IMPORT,
    SHEET_COL_NO_SHEETS,
    FILE_COL_BROWSE,
    FILE_COL_UNAVAILABLE,
    FILE_COL_TITLE_NO_FILES,
    FILE_COL_TITLE_NO_DAV,
)
from samplesheets.assayapps.dna_sequencing.plugins import (
    SampleSheetAssayPlugin as DnaSequencingPlugin,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


app_settings = AppSettingAPI()
plugin_api = PluginAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']

# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_minimal2.zip'
MATERIAL_NAME = '0815-N1-DNA1'
ASSAY_PLUGIN_NAME = 'samplesheets.assayapps.dna_sequencing'
SHEET_COL_ID = 'sheets'
FILE_COL_ID = 'files'


class SamplesheetsPluginTestBase(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Base class for samplesheets plugin tests"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Init users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.save()
        self.user_owner = self.make_user('user_owner')
        # Init projects and assignments
        self.category = self.make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.owner_as_cat = self.make_assignment(
            self.category, self.user_owner, self.role_owner
        )
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        # Import investigation (DNA sequencing plugin)
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.investigation.irods_status = True
        self.investigation.save()
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.tb = SampleSheetTableBuilder()
        self.ret_data = dict(
            study={'display_name': self.study.get_display_name()}
        )
        self.irods_backend = plugin_api.get_backend_api('omics_irods')


class TestGetProjectListValue(SamplesheetsPluginTestBase):
    """Tests for ProjectAppPlugin.get_project_list_value()"""

    def setUp(self):
        super().setUp()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')
        self.sheets_url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.import_url = reverse(
            'samplesheets:import', kwargs={'project': self.project.sodar_uuid}
        )
        self.webdav_url = (
            settings.IRODS_WEBDAV_URL
            + self.irods_backend.get_sample_path(self.project)
        )

    def test_get_project_list_value_sheets(self):
        """Test get_project_list_value() with sheets column"""
        res = self.plugin.get_project_list_value(
            SHEET_COL_ID, self.project, self.user_owner
        )
        expected = SHEET_COL_VIEW.format(url=self.sheets_url)
        self.assertEqual(res, expected)

    def test_get_project_list_value_sheets_no_inv(self):
        """Test sheets column with no investigation and edit_sheet perm"""
        self.investigation.active = False
        self.investigation.save()
        self.assertTrue(
            self.user_owner.has_perm('samplesheets.edit_sheet', self.project)
        )
        res = self.plugin.get_project_list_value(
            SHEET_COL_ID, self.project, self.user_owner
        )
        expected = SHEET_COL_IMPORT.format(url=self.import_url)
        self.assertEqual(res, expected)

    def test_get_project_list_value_sheets_no_inv_no_perm(self):
        """Test sheets column with no investigation and no perm"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_guest)
        self.investigation.active = False
        self.investigation.save()
        self.assertFalse(
            user_new.has_perm('samplesheets.edit_sheet', self.project)
        )
        res = self.plugin.get_project_list_value(
            SHEET_COL_ID, self.project, user_new
        )
        self.assertEqual(res, SHEET_COL_NO_SHEETS)

    def test_get_project_list_value_sheets_sync(self):
        """Test sheets column with no investigation and sheet sync enabled"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        self.investigation.active = False
        self.investigation.save()
        res = self.plugin.get_project_list_value(
            SHEET_COL_ID, self.project, self.user_owner
        )
        self.assertEqual(res, SHEET_COL_NO_SHEETS)

    def test_get_project_list_value_sheets_guest(self):
        """Test sheets column as guest"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_guest)
        res = self.plugin.get_project_list_value(
            SHEET_COL_ID, self.project, user_new
        )
        expected = SHEET_COL_VIEW.format(url=self.sheets_url)
        self.assertEqual(res, expected)

    def test_get_project_list_value_sheets_viewer(self):
        """Test sheets column as viewer"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_viewer)
        res = self.plugin.get_project_list_value(
            SHEET_COL_ID, self.project, user_new
        )
        expected = SHEET_COL_VIEW.format(url=self.sheets_url)
        self.assertEqual(res, expected)

    def test_get_project_list_value_files(self):
        """Test get_project_list_value() with files column"""
        res = self.plugin.get_project_list_value(
            FILE_COL_ID, self.project, self.user_owner
        )
        expected = FILE_COL_BROWSE.format(url=self.webdav_url)
        self.assertEqual(res, expected)

    def test_get_project_list_value_files_irods_status_false(self):
        """Test files column with irods_status=False"""
        self.investigation.irods_status = False
        self.investigation.save()
        res = self.plugin.get_project_list_value(
            FILE_COL_ID, self.project, self.user_owner
        )
        expected = FILE_COL_UNAVAILABLE.format(title=FILE_COL_TITLE_NO_FILES)
        self.assertEqual(res, expected)

    @override_settings(IRODS_WEBDAV_ENABLED=False)
    def test_get_project_list_value_files_disable_webdav(self):
        """Test files column with disabled WebDAV"""
        res = self.plugin.get_project_list_value(
            FILE_COL_ID, self.project, self.user_owner
        )
        expected = FILE_COL_UNAVAILABLE.format(title=FILE_COL_TITLE_NO_DAV)
        self.assertEqual(res, expected)

    def test_get_project_list_value_files_guest(self):
        """Test files column as guest"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_guest)
        res = self.plugin.get_project_list_value(
            FILE_COL_ID, self.project, user_new
        )
        expected = FILE_COL_BROWSE.format(url=self.webdav_url)
        self.assertEqual(res, expected)

    def test_get_project_list_value_files_viewer(self):
        """Test files column as viewer"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_viewer)
        res = self.plugin.get_project_list_value(
            FILE_COL_ID, self.project, user_new
        )
        self.assertEqual(res, '')

    def test_get_project_list_value_invalid_column_id(self):
        """Test get_project_list_value() with invalid column ID"""
        res = self.plugin.get_project_list_value(
            'INVALID_COLUMN', self.project, self.user_owner
        )
        self.assertEqual(res, '')


class TestGetCategoryStats(SamplesheetsPluginTestBase):
    """Tests for ProjectAppPlugin.get_category_stats()"""

    def setUp(self):
        super().setUp()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')
        self.sample_kw = {'item_type': ITEM_TYPE_SAMPLE, 'study': self.study}

    # NOTE: For iRODS stats tests, see test_plugins_taskflow

    def test_get_category_stats(self):
        """Test get_category_stats()"""
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(len(res), 3)
        self.assertIsInstance(res[0].plugin, self.plugin.__class__)
        self.assertEqual(res[0].title, 'Samples')
        self.assertEqual(res[0].value, 1)  # One sample in i_minimal2

    def test_get_category_stats_multi_sample(self):
        """Test get_category_stats() with multiple samples in same study"""
        GenericMaterial.objects.create(
            name='0816-N1', unique_name='0816-N1-1-1', **self.sample_kw
        )
        GenericMaterial.objects.create(
            name='0817-N1', unique_name='0817-N1-1-1', **self.sample_kw
        )
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(res[0].value, 3)

    def test_get_category_stats_no_inv(self):
        """Test get_category_stats() with no investigation"""
        self.investigation.delete()
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(res[0].value, 0)

    def test_get_category_stats_multi_inv(self):
        """Test get_category_stats() with multiple investigations under category"""
        new_project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.investigation = self.import_isa_from_file(SHEET_PATH, new_project)
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(res[0].value, 2)

    def test_get_category_stats_no_sample(self):
        """Test get_category_stats() with no sample"""
        material = GenericMaterial.objects.filter(
            item_type=ITEM_TYPE_SAMPLE, study=self.study
        ).first()
        material.item_type = ITEM_TYPE_MATERIAL
        material.save()
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(res[0].value, 0)

    def test_get_category_stats_no_projects(self):
        """Test get_category_stats() with no projects under category"""
        new_category = self.make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        res = self.plugin.get_category_stats(new_category)
        self.assertEqual(res[0].value, 0)

    def test_get_category_stats_subcategory(self):
        """Test get_category_stats() with project in subcategory"""
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.project.parent = sub_cat
        self.project.save()
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(res[0].value, 1)


class TestGetIrodsContent(SamplesheetsPluginTestBase):
    """Tests for the get_irods_content() helper"""

    def test_get_irods_content(self):
        """Test get_irods_content()"""
        self.ret_data['tables'] = self.tb.build_study_tables(self.study)
        ret_data = get_irods_content(
            self.investigation, self.study, self.irods_backend, self.ret_data
        )
        assay_data = ret_data['tables']['assays'][str(self.assay.sodar_uuid)]
        self.assertEqual(len(assay_data['irods_paths']), 1)
        self.assertTrue(
            assay_data['irods_paths'][0]['path'].endswith(MATERIAL_NAME)
        )
        self.assertEqual(len(assay_data['shortcuts']), 2)

    def test_get_invalid_path(self):
        """Test get_irods_content() with invalid iRODS path"""
        m = GenericMaterial.objects.filter(
            assay=self.assay, name=MATERIAL_NAME
        ).first()
        m.name = 'invalid/../path'
        m.save()
        self.ret_data['tables'] = self.tb.build_study_tables(self.study)
        with self.assertRaises(ValueError):
            get_irods_content(
                self.investigation,
                self.study,
                self.irods_backend,
                self.ret_data,
            )


class TestUpdateCacheRows(SamplesheetsPluginTestBase):
    """Tests for update_cache_rows()"""

    def setUp(self):
        super().setUp()
        # NOTE: Using dna_sequencing as the example plugin here
        self.plugin = DnaSequencingPlugin()
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        item_name = 'irods/rows/{}'.format(self.assay.sodar_uuid)
        self.item_kwargs = {
            'app_name': ASSAY_PLUGIN_NAME,
            'name': item_name,
            'project': self.project,
        }

    def test_update_cache_rows(self):
        """Test update_cache_rows()"""
        self.assertIsNone(self.cache_backend.get_cache_item(**self.item_kwargs))
        self.plugin.update_cache_rows(ASSAY_PLUGIN_NAME, project=self.project)
        cache_item = self.cache_backend.get_cache_item(**self.item_kwargs)
        self.assertIsNotNone(cache_item)
        self.assertTrue(
            list(cache_item.data['paths'].keys())[0].endswith(MATERIAL_NAME)
        )

    def test_update_invalid_path(self):
        """Test update_cache_rows() with invalid iRODS path"""
        m = GenericMaterial.objects.filter(
            assay=self.assay, name=MATERIAL_NAME
        ).first()
        m.name = 'invalid/../path'
        m.save()
        with self.assertRaises(ValueError):
            self.plugin.update_cache_rows(
                ASSAY_PLUGIN_NAME, project=self.project
            )
