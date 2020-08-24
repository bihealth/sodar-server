"""Tests for utility functions in the samplesheets app"""
import json
import os

from test_plus.test import TestCase
from unittest import skipIf

from django.conf import settings

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.models import Study, Assay, GenericMaterial, Process, Protocol
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import (
    get_alt_names,
    get_sample_colls,
    get_index_by_header,
    get_last_material_name,
    build_sheet_config,
    build_display_config,
)
from .test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
SHEET_PATH_SMALL2 = SHEET_DIR + 'i_small2.zip'
OBJ_NAME = 'AA_BB_01'
OBJ_ALT_NAMES = ['aa-bb-01', 'aabb01', 'aa_bb_01']

CONFIG_STUDY_UUID = '11111111-1111-1111-1111-111111111111'
CONFIG_ASSAY_UUID = '22222222-2222-2222-2222-222222222222'
CONFIG_PROTOCOL_UUIDS = [
    '11111111-1111-1111-bbbb-000000000000',
    '22222222-2222-2222-bbbb-111111111111',
    '22222222-2222-2222-bbbb-000000000000',
]
CONFIG_DIR = os.path.dirname(__file__) + '/config/'
CONFIG_PATH_DEFAULT = CONFIG_DIR + 'i_small_default.json'
CONFIG_PATH_UPDATED = CONFIG_DIR + 'i_small_updated.json'

with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)

IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


# TODO: TBD: Best location for this?
class SheetConfigMixin:
    """Mixin for sheet config testing helpers"""

    @classmethod
    def _update_uuids(cls, investigation, sheet_config):
        """
        Update study, assay and protocol UUIDs in the database to match a test
        sheet config file.

        :param investigation: Investigation object
        :param sheet_config: Dict
        """
        study_names = {}
        assay_names = {}

        for study in investigation.studies.all():
            study_names[study.get_display_name()] = str(study.sodar_uuid)

            for assay in study.assays.all():
                assay_names[assay.get_display_name()] = str(assay.sodar_uuid)

        for s_uuid, sc in sheet_config['studies'].items():
            study = Study.objects.get(
                sodar_uuid=study_names[sc['display_name']]
            )
            study.sodar_uuid = s_uuid
            study.save()

            for a_uuid, ac in sc['assays'].items():
                assay = Assay.objects.get(
                    sodar_uuid=assay_names[ac['display_name']]
                )
                assay.sodar_uuid = a_uuid
                assay.save()

            protocols = list(
                Protocol.objects.filter(study=study).order_by('pk')
            )

            for i in range(len(protocols)):
                protocols[i].sodar_uuid = CONFIG_PROTOCOL_UUIDS[i]
                protocols[i].save()


class TestUtilsBase(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Class for samplesheets utils tests"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner
        )

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH_SMALL2, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        self.tb = SampleSheetTableBuilder()


class TestGetAltNames(TestUtilsBase):
    """Tests for get_alt_names()"""

    def test_get_alt_names(self):
        """Test get_alt_names() with a typical object name"""
        self.assertEqual(get_alt_names(OBJ_NAME), OBJ_ALT_NAMES)

    # TODO: See issue #494
    def test_get_alt_names_dupe(self):
        """Test get_alt_names() resulting in dupes"""
        self.assertEqual(
            get_alt_names(OBJ_ALT_NAMES[1]), [OBJ_ALT_NAMES[1]] * 3
        )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestGetSampleColls(TestUtilsBase):
    """Tests for get_sample_colls()"""

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods', conn=False)

    def test_get_sample_colls(self):
        """Test get_sample_colls() with a minimal ISAtab example"""
        expected = [
            self.irods_backend.get_sub_path(self.study),
            self.irods_backend.get_sub_path(self.assay),
        ]

        self.assertEqual(get_sample_colls(self.investigation), expected)


# TODO: Test compare_inv_replace() (requires special ISAtabs, see #434)


class TestGetIndexByHeader(TestUtilsBase):
    """Tests for get_index_by_header()"""

    def setUp(self):
        super().setUp()
        tb = SampleSheetTableBuilder()
        self.study_tables = tb.build_study_tables(self.study)

    def test_get_sample_name(self):
        """Test getting sample name from study table"""
        self.assertEqual(
            get_index_by_header(
                render_table=self.study_tables['study'],
                header_value='name',
                obj_cls=GenericMaterial,
                item_type='SAMPLE',
            ),
            2,
        )

    def test_get_process_protocol(self):
        """Test getting process protocol from assay"""
        self.assertEqual(
            get_index_by_header(
                render_table=self.study_tables['assays'][
                    str(self.assay.sodar_uuid)
                ],
                header_value='protocol',
                obj_cls=Process,
            ),
            1,
        )

    def test_get_no_cls(self):
        """Test getting index without an object class"""
        self.assertEqual(
            get_index_by_header(
                render_table=self.study_tables['assays'][
                    str(self.assay.sodar_uuid)
                ],
                header_value='replicate',
            ),
            8,
        )

    def test_get_not_found(self):
        """Test getting a non-existent column"""
        self.assertIsNone(
            get_index_by_header(
                render_table=self.study_tables['study'],
                header_value='Oequ5aiL Xe8Ahnuv',
            )
        )


class TestGetLastMaterialName(TestUtilsBase):
    """Tests for get_last_material_name()"""

    def setUp(self):
        super().setUp()
        tb = SampleSheetTableBuilder()
        self.study_tables = tb.build_study_tables(self.study)

    def test_get_study(self):
        """Test getting the last non-DATA material name with a study"""
        study_table = self.study_tables['study']
        # TODO: Assert ordering or use a specific row instead of index
        self.assertIn(
            get_last_material_name(study_table['table_data'][0], study_table),
            ['0815-N1', '0815-T1'],
        )


# TODO: Decent way to test get_sample_libraries()?


class TestBuildSheetConfig(
    ProjectMixin,
    RoleAssignmentMixin,
    SampleSheetIOMixin,
    SheetConfigMixin,
    TestCase,
):
    """Tests for build_sheet_config()"""

    # NOTE: Not using TestUtilsBase

    def setUp(self):
        self.tb = SampleSheetTableBuilder()

        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner
        )

    def test_build_sheet_config(self):
        """Test sheet building against the default i_small JSON config file"""
        investigation = self._import_isa_from_file(SHEET_PATH, self.project)
        # Update UUIDs to match JSON file
        self._update_uuids(investigation, CONFIG_DATA_DEFAULT)
        sheet_config = build_sheet_config(investigation)
        self.assertEqual(sheet_config, CONFIG_DATA_DEFAULT)

    # TODO: Test fields once we are finished with the notation
    def test_build_sheet_config_batch(self):
        """Test build_sheet_config() in batch"""
        for zip_name, zip_file in self._get_isatab_files().items():
            msg = 'file={}'.format(zip_name)

            try:
                investigation = self._import_isa_from_file(
                    zip_file.path, self.project
                )

            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            sc = build_sheet_config(investigation)
            self.assertEqual(
                len(sc['studies']), investigation.studies.all().count(), msg=msg
            )

            for sk, sv in sc['studies'].items():
                study = investigation.studies.get(sodar_uuid=sk)
                study_tables = self.tb.build_study_tables(study)
                self.assertEqual(
                    len(sv['nodes']),
                    len(study_tables['study']['top_header']),
                    msg=msg,
                )
                self.assertEqual(
                    len(sv['assays']), study.assays.all().count(), msg=msg
                )

                for ak, av in sv['assays'].items():
                    # Get sample node index
                    s_idx = 0

                    for h in study_tables['study']['top_header']:
                        if h['value'] == 'Sample':
                            break
                        s_idx += 1

                    self.assertEqual(
                        len(av['nodes']),
                        len(study_tables['assays'][ak]['top_header'])
                        - s_idx
                        - 1,
                        msg=msg,
                    )

            investigation.delete()


class TestBuildDisplayConfig(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase,
):
    """Tests for build_display_config()"""

    # NOTE: Not using TestUtilsBase

    def setUp(self):
        self.tb = SampleSheetTableBuilder()

        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner
        )

    def test_build_config_batch(self):
        """Test building default display configs for example ISAtabs"""
        for zip_name, zip_file in self._get_isatab_files().items():
            msg = 'file={}'.format(zip_name)

            try:
                investigation = self._import_isa_from_file(
                    zip_file.path, self.project
                )

            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            sc = build_sheet_config(investigation)
            s_uuid = str(investigation.studies.first().sodar_uuid)
            a_uuid = str(
                investigation.studies.first().assays.first().sodar_uuid
            )
            dc = build_display_config(investigation, sc)
            study_node_count = len(sc['studies'][s_uuid]['nodes'])

            self.assertEqual(
                len(dc['studies'][s_uuid]['nodes']), study_node_count, msg=msg,
            )
            self.assertEqual(
                len(dc['studies'][s_uuid]['assays'][a_uuid]['nodes']),
                len(sc['studies'][s_uuid]['assays'][a_uuid]['nodes'])
                + study_node_count,
                msg=msg,
            )
