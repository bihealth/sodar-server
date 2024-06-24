"""Tests for plugins in the samplesheets app"""

# NOTE: These are generic tests for common plugin methods and helpers,
# study/assay plugin specific tests should go in their own modules

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

from samplesheets.models import GenericMaterial
from samplesheets.plugins import get_irods_content
from samplesheets.assayapps.dna_sequencing.plugins import (
    SampleSheetAssayPlugin as DnaSequencingPlugin,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
)


# Local constants
SHEET_PATH = SHEET_DIR + 'i_minimal2.zip'
MATERIAL_NAME = '0815-N1-DNA1'
ASSAY_PLUGIN_NAME = 'samplesheets.assayapps.dna_sequencing'


class SamplesheetsPluginTestBase(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Base class for samplesheets plugin tests"""

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
        # Import investigation (DNA sequencing plugin)
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.investigation.irods_status = True
        self.investigation.save()
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # HACK: Force correct measurement type for assay (see #1954)
        self.assay.measurement_type = 'exome sequencing'
        self.assay.save()
        self.tb = SampleSheetTableBuilder()
        self.ret_data = dict(
            study={'display_name': self.study.get_display_name()}
        )
        self.irods_backend = get_backend_api('omics_irods')


class TestGetIrodsContent(SamplesheetsPluginTestBase):
    """Tests for get_irods_content()"""

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
        self.cache_backend = get_backend_api('sodar_cache')
        item_name = 'irods/rows/{}'.format(self.assay.sodar_uuid)
        self.item_kwargs = {
            'app_name': ASSAY_PLUGIN_NAME,
            'name': item_name,
            'project': self.project,
        }

    def test_update_cache_rows(self):
        """Test update_cache_rows()"""
        self.assertIsNone(self.cache_backend.get_cache_item(**self.item_kwargs))
        self.plugin._update_cache_rows(ASSAY_PLUGIN_NAME, project=self.project)
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
            self.plugin._update_cache_rows(
                ASSAY_PLUGIN_NAME, project=self.project
            )
