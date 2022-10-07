"""Tests for utility functions in the samplesheets app"""

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.constants import DEFAULT_EXTERNAL_LINK_LABELS
from samplesheets.models import GenericMaterial, Process
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.utils import (
    get_alt_names,
    get_sample_colls,
    get_index_by_header,
    get_last_material_name,
    compare_inv_replace,
    get_webdav_url,
    get_ext_link_labels,
)
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)


app_settings = AppSettingAPI()


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'
SHEET_PATH_SMALL2 = SHEET_DIR + 'i_small2.zip'
SHEET_PATH_SMALL2_ALT = SHEET_DIR + 'i_small2_alt.zip'
OBJ_NAME = 'AA_BB_01'
OBJ_ALT_NAMES = ['aa-bb-01', 'aabb01', 'aa_bb_01']
CONFIG_PROTOCOL_UUIDS = [
    '11111111-1111-1111-bbbb-000000000000',
    '22222222-2222-2222-bbbb-111111111111',
    '22222222-2222-2222-bbbb-000000000000',
]
IRODS_TICKET_STR = 'ooChaa1t'
EXT_LINK_PATH_INVALID = '/tmp/NON_EXISTING_EXT_LINK_FILE.json'


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
        self.investigation = self.import_isa_from_file(
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


class TestGetSampleColls(TestUtilsBase):
    """Tests for get_sample_colls()"""

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods', conn=False)

    def test_get_sample_colls(self):
        """Test get_sample_colls() with a minimal ISA-Tab example"""
        expected = [
            self.irods_backend.get_sub_path(self.study),
            self.irods_backend.get_sub_path(self.assay),
        ]
        self.assertEqual(get_sample_colls(self.investigation), expected)


class TestCompareInvReplace(TestUtilsBase):
    """Tests for compare_inv_replace()"""

    def test_inserted_rows(self):
        """Test comparison with inserted rows"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(
            SHEET_PATH_INSERTED, project=self.project
        )
        self.assertTrue(compare_inv_replace(inv1, inv2))

    def test_modified_sheet(self):
        """Test comparison with modified studies/assays (should fail)"""
        inv1 = self.import_isa_from_file(
            SHEET_PATH_SMALL2, project=self.project
        )
        inv2 = self.import_isa_from_file(
            SHEET_PATH_SMALL2_ALT, project=self.project
        )
        self.assertFalse(compare_inv_replace(inv1, inv2))

    def test_different_sheet(self):
        """Test comparison with a different sheet (should fail)"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(
            SHEET_PATH_SMALL2, project=self.project
        )
        self.assertFalse(compare_inv_replace(inv1, inv2))


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


class TestGetWebdavUrl(TestUtilsBase):
    """Tests for get_webdav_url()"""

    def setUp(self):
        super().setUp()
        self.user_anon = AnonymousUser()

    def test_project_user(self):
        """Test get_webdav_url() with a project user"""
        expected = settings.IRODS_WEBDAV_URL
        self.assertEqual(
            get_webdav_url(self.project, self.user_owner), expected
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_anon_user(self):
        """Test get_webdav_url() with anonymous user for a public project"""
        # Mock public project update
        self.project.public_guest_access = True
        self.project.save()
        app_settings.set_app_setting(
            'samplesheets',
            'public_access_ticket',
            IRODS_TICKET_STR,
            project=self.project,
        )
        expected = settings.IRODS_WEBDAV_URL_ANON_TMPL.format(
            user=settings.IRODS_WEBDAV_USER_ANON,
            ticket=IRODS_TICKET_STR,
            path='',
        )
        self.assertEqual(get_webdav_url(self.project, self.user_anon), expected)

    def test_anon_user_not_allowed(self):
        """Test get_webdav_url() with anonymous user without anon access"""
        # Mock public project update
        self.project.set_public()
        app_settings.set_app_setting(
            'samplesheets',
            'public_access_ticket',
            IRODS_TICKET_STR,
            project=self.project,
        )
        self.assertIsNone(get_webdav_url(self.project, self.user_anon))

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_anon_user_private_project(self):
        """Test get_webdav_url() with anonymous user and non-public project"""
        self.assertIsNone(get_webdav_url(self.project, self.user_anon))

    @override_settings(IRODS_WEBDAV_ENABLED=False)
    def test_webdav_disabled(self):
        """Test get_webdav_url() with disabled WebDAV"""
        self.assertIsNone(get_webdav_url(self.project, self.user_owner))


class TestGetExtLinkLabels(TestUtilsBase):
    """Tests for get_ext_link_labels()"""

    def test_get(self):
        """Test retrieving labels from default test JSON file"""
        labels = get_ext_link_labels()
        expected = {
            'x-generic-remote': {'label': 'External ID'},
            'x-sodar-example': {'label': 'Example ID', 'url': None},
            'x-sodar-example-link': {
                'label': 'Example ID with hyperlink',
                'url': 'https://example.com/{id}',
            },
        }
        self.assertEqual(labels, expected)
        self.assertNotEqual(labels, DEFAULT_EXTERNAL_LINK_LABELS)

    @override_settings(SHEETS_EXTERNAL_LINK_PATH=EXT_LINK_PATH_INVALID)
    def test_get_default(self):
        """Test retrievint default labels"""
        labels = get_ext_link_labels()
        self.assertEqual(labels, DEFAULT_EXTERNAL_LINK_LABELS)
