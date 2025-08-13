"""Tests for management commands in the samplesheets app"""

import uuid

from django.core.management import call_command

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

# Sodarcache dependency
from sodarcache.models import JSONCacheItem

# Timeline dependency
from timeline.models import TimelineEvent

from samplesheets.management.commands.normalizesheets import (
    LIB_NAME,
    LIB_NAME_REPLACE,
)
from samplesheets.models import GenericMaterial, ISATab
from samplesheets.rendering import (
    SampleSheetTableBuilder,
    STUDY_TABLE_CACHE_ITEM,
)
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)
from samplesheets.utils import get_alt_names


plugin_api = PluginAPI()


# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2.zip'
ALT_NAMES_INVALID = ['XXX', 'YYY', 'ZZZ']


class TestNormalizesheets(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Tests for the normalizesheets command"""

    def _assert_material_header(self, materials, header, expected):
        """Assert count of materials which contain a specific header name"""
        self.assertEqual(
            materials.filter(headers__icontains=header).count(),
            expected,
        )

    def _assert_study_table_header(self, study_tables, assay, header, expected):
        """
        Assert count of assay table headers which contain a specific header
        name.
        """
        a = str(assay.sodar_uuid)
        h_name = header.lower()
        top_header = study_tables['assays'][a]['top_header']
        self.assertEqual(
            len(
                [
                    h
                    for h in top_header
                    if h['value'].lower() == h_name
                    and h['headers'][0].lower() == h_name
                ]
            ),
            expected,
        )

    def _assert_tl_event(self, expected):
        self.assertEqual(
            TimelineEvent.objects.filter(
                event_name='sheet_normalize', project=self.project
            ).count(),
            expected,
        )

    def setUp(self):
        # Init roles
        self.init_roles()
        # Make owner user
        self.user_owner = self.make_user('owner')
        # Init project and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up study tables in cache
        self.tb = SampleSheetTableBuilder()
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self.cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=self.study.sodar_uuid
        )
        self.cache_args = [APP_NAME, self.cache_name, self.project]
        self.tb.get_study_tables(self.study)

    def test_command(self):
        """Test normalizesheets"""
        # Materials
        materials = GenericMaterial.objects.filter(assay=self.assay)
        self._assert_material_header(materials, LIB_NAME, 2)
        self._assert_material_header(materials, LIB_NAME_REPLACE, 0)
        # Cached study tables
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME, 1
        )
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME_REPLACE, 0
        )
        # Sheet version
        self.assertEqual(ISATab.objects.count(), 1)
        # Timeline event
        self._assert_tl_event(0)
        call_command('normalizesheets')
        materials = GenericMaterial.objects.filter(assay=self.assay)
        self._assert_material_header(materials, LIB_NAME, 0)
        self._assert_material_header(materials, LIB_NAME_REPLACE, 2)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME, 0
        )
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME_REPLACE, 1
        )
        # Sheet version
        self.assertEqual(ISATab.objects.count(), 2)
        # Timeline event
        self._assert_tl_event(1)

    def test_command_check(self):
        """Test normalizesheets with check mode"""
        materials = GenericMaterial.objects.filter(assay=self.assay)
        self._assert_material_header(materials, LIB_NAME, 2)
        self._assert_material_header(materials, LIB_NAME_REPLACE, 0)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME, 1
        )
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME_REPLACE, 0
        )
        self.assertEqual(ISATab.objects.count(), 1)
        self._assert_tl_event(0)
        call_command('normalizesheets', check=True)
        materials = GenericMaterial.objects.filter(assay=self.assay)
        self._assert_material_header(materials, LIB_NAME, 2)
        self._assert_material_header(materials, LIB_NAME_REPLACE, 0)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME, 1
        )
        self._assert_study_table_header(
            cache_item.data, self.assay, LIB_NAME_REPLACE, 0
        )
        self.assertEqual(ISATab.objects.count(), 1)
        self._assert_tl_event(0)


class TestSyncnames(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Tests for the syncnames command"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Make owner user
        self.user_owner = self.make_user('owner')
        # Init project and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        # Clear alt names from imported materials
        for m in GenericMaterial.objects.all():
            m.alt_names = ALT_NAMES_INVALID
            m.save()

    def test_command(self):
        """Test syncnames"""
        for m in GenericMaterial.objects.all():
            self.assertEqual(m.alt_names, ALT_NAMES_INVALID)
        call_command('syncnames')
        for m in GenericMaterial.objects.all():
            self.assertEqual(m.alt_names, get_alt_names(m.name))


class TestSyncstudytables(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Tests for the syncstudytables command"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Init user
        self.user_owner = self.make_user('owner')
        # Init project and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

        # Init second project
        self.project2 = self.make_project(
            'TestProject2', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.owner_as2 = self.make_assignment(
            self.project2, self.user_owner, self.role_owner
        )
        self.investigation2 = self.import_isa_from_file(
            SHEET_PATH_ALT, self.project2
        )
        self.study2 = self.investigation2.studies.first()

        # Init helpers
        self.cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=self.study.sodar_uuid
        )
        self.cache_name2 = STUDY_TABLE_CACHE_ITEM.format(
            study=self.study2.sodar_uuid
        )
        self.cache_args = [APP_NAME, self.cache_name, self.project]
        self.cache_args2 = [APP_NAME, self.cache_name2, self.project2]
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')

    def test_sync_all(self):
        """Test syncstudytables for all projects"""
        self.assertEqual(JSONCacheItem.objects.count(), 0)
        call_command('syncstudytables')
        self.assertEqual(JSONCacheItem.objects.count(), 2)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self.assertIsInstance(cache_item, JSONCacheItem)
        self.assertNotEqual(cache_item.data, {})
        cache_item2 = self.cache_backend.get_cache_item(*self.cache_args2)
        self.assertIsInstance(cache_item2, JSONCacheItem)
        self.assertNotEqual(cache_item2.data, {})

    def test_sync_all_existing(self):
        """Test syncstudytables for all projects with existing items"""
        self.cache_backend.set_cache_item(
            APP_NAME, self.cache_name, {}, project=self.project
        )
        self.cache_backend.set_cache_item(
            APP_NAME, self.cache_name2, {}, project=self.project2
        )
        self.assertEqual(JSONCacheItem.objects.count(), 2)
        call_command('syncstudytables')
        self.assertEqual(JSONCacheItem.objects.count(), 2)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self.assertIsInstance(cache_item, JSONCacheItem)
        self.assertNotEqual(cache_item.data, {})
        cache_item2 = self.cache_backend.get_cache_item(*self.cache_args2)
        self.assertIsInstance(cache_item2, JSONCacheItem)
        self.assertNotEqual(cache_item2.data, {})

    def test_sync_limit(self):
        """Test syncstudytables limiting for single project"""
        self.assertEqual(JSONCacheItem.objects.count(), 0)
        call_command('syncstudytables', project=str(self.project.sodar_uuid))
        self.assertEqual(JSONCacheItem.objects.count(), 1)
        cache_item = self.cache_backend.get_cache_item(*self.cache_args)
        self.assertIsInstance(cache_item, JSONCacheItem)
        self.assertNotEqual(cache_item.data, {})
        cache_item2 = self.cache_backend.get_cache_item(*self.cache_args2)
        self.assertIsNone(cache_item2)

    def test_sync_limit_invalid_project(self):
        """Test syncstudytables limiting for non-existent project"""
        self.assertEqual(JSONCacheItem.objects.count(), 0)
        invalid_uuid = uuid.uuid4()
        call_command('syncstudytables', project=str(invalid_uuid))
        self.assertEqual(JSONCacheItem.objects.count(), 0)
