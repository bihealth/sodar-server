"""Tests for plugins in the samplesheets app"""

# NOTE: These are tests for samplesheets ProjectAppPlugin as well as generic
# tests for common plugin methods and helpers. Study/assay plugin specific tests
# should go in their own modules

from irods.path import iRODSPath

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS, Project
from projectroles.plugins import (
    ProjectAppPluginPoint,
    PluginAPI,
    PluginSearchResult,
)
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

from samplesheets.models import (
    Assay,
    GenericMaterial,
    ITEM_TYPE_MATERIAL,
    ITEM_TYPE_SAMPLE,
    ITEM_TYPE_SOURCE,
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
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
)


app_settings = AppSettingAPI()
plugin_api = PluginAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']

# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_minimal2.zip'
MATERIAL_NAME = '0815-N1-DNA1'
SOURCE_NAME = '0815-N1'
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
        self.ret_data = dict(study={'display_name': self.study.get_name()})
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

    def setUp(self):
        super().setUp()
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.row_path = iRODSPath(self.assay_path, MATERIAL_NAME)

    def test_get_irods_content(self):
        """Test get_irods_content()"""
        self.ret_data['tables'] = self.tb.build_study_tables(self.study)
        ret_data = get_irods_content(
            self.investigation, self.study, self.irods_backend, self.ret_data
        )
        assay_data = ret_data['tables']['assays'][str(self.assay.sodar_uuid)]
        self.assertEqual(len(assay_data['irods_paths']), 1)
        print(assay_data['irods_paths'][0]['path'])
        self.assertTrue(
            assay_data['irods_paths'][0]['path'].endswith(MATERIAL_NAME)
        )
        # No cache item = enabled is true
        self.assertEqual(assay_data['irods_paths'][0]['enabled'], True)
        self.assertEqual(len(assay_data['shortcuts']), 2)

    def test_get_row_cache_item_no_files(self):
        """Test get_irods_content() with row cache item and no files"""
        cache_data = {'paths': {self.row_path: {'file_count': 0}}}
        self.cache_backend.set_cache_item(
            app_name=ASSAY_PLUGIN_NAME,
            name=f'irods/rows/{self.assay.sodar_uuid}',
            data=cache_data,
            project=self.project,
        )
        self.ret_data['tables'] = self.tb.build_study_tables(self.study)
        ret_data = get_irods_content(
            self.investigation, self.study, self.irods_backend, self.ret_data
        )
        assay_data = ret_data['tables']['assays'][str(self.assay.sodar_uuid)]
        # Cache item with file_count==0: should not be enabled
        self.assertEqual(assay_data['irods_paths'][0]['enabled'], False)

    def test_get_row_cache_item_files(self):
        """Test get_irods_content() with row cache item and files"""
        cache_data = {'paths': {self.row_path: {'file_count': 1}}}
        self.cache_backend.set_cache_item(
            app_name=ASSAY_PLUGIN_NAME,
            name=f'irods/rows/{self.assay.sodar_uuid}',
            data=cache_data,
            project=self.project,
        )
        self.ret_data['tables'] = self.tb.build_study_tables(self.study)
        ret_data = get_irods_content(
            self.investigation, self.study, self.irods_backend, self.ret_data
        )
        assay_data = ret_data['tables']['assays'][str(self.assay.sodar_uuid)]
        # Cache item with file_count>0: should be enabled
        self.assertEqual(assay_data['irods_paths'][0]['enabled'], True)

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
        item_name = f'irods/rows/{self.assay.sodar_uuid}'
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


class TestSearch(SamplesheetsPluginTestBase):
    """Tests for plugin search()"""

    def setUp(self):
        super().setUp()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')
        GenericMaterial.objects.create(
            name='0816-N1',
            unique_name='0816-N1-1-1',
            item_type=ITEM_TYPE_SAMPLE,
            study=self.study,
        )
        self.project2 = self.make_project(
            'TestProject2', PROJECT_TYPE_PROJECT, self.category
        )
        self.investigation2 = self.import_isa_from_file(
            SHEET_DIR + 'bih_cancer.zip', self.project2
        )
        self.investigation2.irods_status = True
        self.investigation2.save()
        self.study2 = self.investigation2.studies.first()
        self.assay2 = self.study2.assays.first()
        # Create the same sample in the project2
        GenericMaterial.objects.create(
            name='0816-N1',
            unique_name='0816-N1-1-1',
            item_type=ITEM_TYPE_SAMPLE,
            study=self.study2,
        )

    def _test_material_row_contents(self, row, name, type, study, assay=None):
        self.assertEqual(row[0].value, name)
        self.assertTrue(row[0].value_url.startswith(study.get_url()))
        self.assertEqual(row[1].value, type)
        self.assertIn(study.investigation.project.title, row[2].value)
        self.assertEqual(row[3].value, study.get_name())
        self.assertEqual(row[3].value_url, study.get_url())
        if assay:
            self.assertIn(str(assay.sodar_uuid), row[4].value)
        else:
            self.assertEqual(row[4].value, '')

    def test_search_simple(self):
        """Test search() with simple term"""
        ret = self.plugin.search(
            [SOURCE_NAME],
            self.user_owner,
            Project.objects.all(),
        )
        self.assertEqual(len(ret), 2)
        self.assertIsInstance(ret[0], PluginSearchResult)
        self.assertIsInstance(ret[1], PluginSearchResult)
        self.assertEqual(ret[0].category, 'materials')
        self.assertEqual(
            [col.title for col in ret[0].columns],
            ['Name', 'Type', 'Project', 'Study', 'Assay(s)'],
        )
        self.assertEqual(len(ret[0].rows), 1)
        self._test_material_row_contents(
            ret[0].rows[0],
            SOURCE_NAME,
            'Sample',
            self.study,
            assay=self.assay,
        )
        self.assertEqual(len(ret[1].rows), 0)

    def test_search_empty(self):
        """Test search() with no data"""
        for material in GenericMaterial.objects.all():
            material.delete()
        ret = self.plugin.search(
            [SOURCE_NAME],
            self.user_owner,
            Project.objects.all(),
        )
        self.assertEqual(len(ret), 2)
        self.assertIsInstance(ret[0], PluginSearchResult)
        self.assertIsInstance(ret[1], PluginSearchResult)
        self.assertEqual(ret[0].rows, [])
        self.assertEqual(ret[1].rows, [])

    def test_search_multiple_terms(self):
        """Test search() with multiple terms"""
        ret = self.plugin.search(
            ['0815', '0816-N1', 'fictitious-sample-0x123'],
            self.user_owner,
            Project.objects.all(),
        )
        self.assertEqual(len(ret[0].rows), 3)
        rows = sorted(ret[0].rows, key=lambda x: (x[0].value, x[3].value))
        self._test_material_row_contents(
            rows[0],
            '0815',
            'Source',
            self.study,
        )
        self._test_material_row_contents(
            rows[1],
            '0816-N1',
            'Sample',
            self.study2,
        )
        self._test_material_row_contents(
            rows[2],
            '0816-N1',
            'Sample',
            self.study,
        )

    def test_search_within_project(self):
        """Test search() with project keyword"""
        ret = self.plugin.search(
            ['0816-N1', 'test1.txt'],
            self.user_owner,
            Project.objects.filter(title=self.project2.title),
        )
        self.assertEqual(len(ret[0].rows), 1)
        self._test_material_row_contents(
            ret[0].rows[0],
            '0816-N1',
            'Sample',
            self.study2,
        )

    def test_search_type_source(self):
        """Test search() with type source"""
        ret = self.plugin.search(
            ['0815', '0815-N1'],
            self.user_owner,
            Project.objects.all(),
            type=ITEM_TYPE_SOURCE.lower(),
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].category, 'materials')
        self.assertEqual(len(ret[0].rows), 1)
        # 0815-N1 (the sample) is not found
        self.assertEqual(ret[0].rows[0][0].value, '0815')

    def test_search_type_sample(self):
        """Test search() with type sample"""
        ret = self.plugin.search(
            ['0815', '0815-N1'],
            self.user_owner,
            Project.objects.all(),
            type=ITEM_TYPE_SAMPLE.lower(),
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].category, 'materials')
        self.assertEqual(len(ret[0].rows), 1)
        # 0815 (the source) is not found
        self.assertEqual(ret[0].rows[0][0].value, '0815-N1')

    def test_search_no_assays(self):
        """Test search() with type sample and no assays"""
        for a in Assay.objects.all():
            a.delete()
        ret = self.plugin.search(
            [SOURCE_NAME],
            self.user_owner,
            Project.objects.all(),
            type=ITEM_TYPE_SAMPLE.lower(),
        )
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].category, 'materials')
        self.assertEqual(len(ret[0].rows), 1)
        self._test_material_row_contents(
            ret[0].rows[0],
            SOURCE_NAME,
            'Sample',
            self.study,
        )

    def test_search_type_invalid(self):
        """Test search() with invalid type"""
        ret = self.plugin.search(
            [SOURCE_NAME],
            self.user_owner,
            Project.objects.all(),
            type='NOT_A_MATERIAL_TYPE',
        )
        self.assertEqual(len(ret), 0)

    def test_search_no_permission(self):
        """Test search() when user has no permission"""
        ret = self.plugin.search(
            [SOURCE_NAME],
            self.user_owner,
            Project.objects.filter(title=self.project2.title),
        )
        self.assertEqual(len(ret), 2)
        self.assertEqual(len(ret[0].rows), 0)
        self.assertEqual(len(ret[1].rows), 0)
