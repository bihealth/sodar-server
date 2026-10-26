"""Tests for UI views in the samplesheets app"""

import json
import os
import uuid

from cubi_isa_templates import IsaTabTemplate, _TEMPLATES as ISA_TEMPLATES
from zipfile import ZipFile

from django.conf import settings
from django.contrib.messages import get_messages
from django.test import LiveServerTestCase, override_settings
from django.urls import reverse
from django.utils.timezone import localtime

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import AppSetting, SODAR_CONSTANTS
from projectroles.plugins import PluginAPI
from projectroles.tests.base import SODARAPIViewTestMixin
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)
from projectroles.utils import build_secret

# Timeline dependency
from timeline.models import TimelineEvent

# Isatemplates dependency
from isatemplates.tests.test_models import (
    CookiecutterISATemplateMixin,
    CookiecutterISAFileMixin,
    TEMPLATE_JSON_PATH,
    TEMPLATE_NAME,
    TEMPLATE_DESC,
)
from isatemplates.tests.test_views import ISA_FILE_NAMES, ISA_FILE_PATH

# Landingzones dependency
from landingzones.constants import ZONE_STATUS_ACTIVE
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin

# Sodarcache dependency
from sodarcache.models import JSONCacheItem

import samplesheets.constants as sc
from samplesheets.forms import TPL_DIR_FIELD
from samplesheets.io import SampleSheetIO
from samplesheets.models import (
    Investigation,
    Assay,
    ISATab,
    IrodsDataRequest,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
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
from samplesheets.tests.test_models import (
    SampleSheetModelMixin,
    IrodsDataRequestMixin,
    IrodsAccessTicketMixin,
)
from samplesheets.tests.test_sheet_config import CONFIG_PATH_DEFAULT

# TODO: This should not be required (see issue #1578)
from samplesheets.tests.transaction_testcase import (
    TestCase as TransactionTestCase,
)
from samplesheets.utils import clean_sheet_dir_name
from samplesheets.views import (
    SheetImportMixin,
    SYNC_SUCCESS_MSG,
    SYNC_FAIL_DISABLED,
    SYNC_FAIL_PREFIX,
    SYNC_FAIL_CONNECT,
    SYNC_FAIL_UNSET_TOKEN,
    SYNC_FAIL_UNSET_URL,
    SYNC_FAIL_INVALID_URL,
    SYNC_FAIL_STATUS_CODE,
    MISC_FILES_COLL,
)


app_settings = AppSettingAPI()
conf_api = SheetConfigAPI()
plugin_api = PluginAPI()
table_builder = SampleSheetTableBuilder()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets'
# TODO: Cleanup name/path constants where applicable
SHEET_NAME = 'i_small.zip'
SHEET_PATH = SHEET_DIR + SHEET_NAME
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'
SHEET_NAME_SMALL2 = 'i_small2.zip'
SHEET_PATH_SMALL2 = SHEET_DIR + SHEET_NAME_SMALL2
SHEET_NAME_SMALL2_ALT = 'i_small2_alt.zip'
SHEET_PATH_SMALL2_ALT = SHEET_DIR + SHEET_NAME_SMALL2_ALT
SHEET_NAME_MINIMAL = 'i_minimal.zip'
SHEET_PATH_MINIMAL = SHEET_DIR + SHEET_NAME_MINIMAL
SHEET_NAME_MULTI = 'BII-I-1_edited.zip'
SHEET_PATH_MULTI = SHEET_DIR + SHEET_NAME_MULTI
SHEET_NAME_CRITICAL = 'BII-I-1_critical.zip'
SHEET_PATH_CRITICAL = SHEET_DIR_SPECIAL + SHEET_NAME_CRITICAL
SHEET_NAME_EMPTY_ASSAY = 'i_small_assay_empty.zip'
SHEET_PATH_EMPTY_ASSAY = SHEET_DIR_SPECIAL + SHEET_NAME_EMPTY_ASSAY
SHEET_NAME_NO_PLUGIN_ASSAY = 'i_small_assay_no_plugin.zip'
SHEET_PATH_NO_PLUGIN_ASSAY = SHEET_DIR_SPECIAL + SHEET_NAME_NO_PLUGIN_ASSAY
SHEET_PATH_RENAME = SHEET_DIR_SPECIAL + 'i_small2_renamed_meta.zip'
SHEET_PATH_META = SHEET_DIR_SPECIAL + 'i_small2_export_metadata.zip'
SHEET_PATH_RENAME_META = SHEET_DIR_SPECIAL + 'i_small2_renamed_meta.zip'
SHEET_VERSION_DESC = 'description'
SOURCE_NAME = '0815'
SOURCE_NAME_FAIL = 'oop5Choo'
USER_PASSWORD = 'password'
API_INVALID_VERSION = '9.9.9'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_DESC = 'description'
REMOTE_SITE_SECRET = build_secret()
EDIT_NEW_VALUE_STR = 'edited value'
DUMMY_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
IRODS_FILE_PATH = '/sodarZone/path/test1.txt'
TPL_FILE_NAME_FIELDS = [
    'investigation_title',
    'investigation_id',
    'study_title',
]
with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)
BACKEND_PLUGINS_NO_TPL = settings.ENABLED_BACKEND_PLUGINS.copy()
BACKEND_PLUGINS_NO_TPL.remove('isatemplates_backend')
# Dummy metadata UUIDs as saved in i_small2_export_metadata.zip
META_PROJECT_UUID = '00000000-0000-0000-0000-000000000000'
META_INV_UUID = '11111111-1111-1111-1111-111111111111'
META_STUDY_UUID = '22222222-2222-2222-2222-222222222222'
META_ASSAY_UUID = '33333333-3333-3333-3333-333333333333'


# TODO: Add testing for study table cache updates


# Base Classes and Mixins ------------------------------------------------------


class SheetTemplateCreateMixin:
    """Sheet template creation helpers"""

    def get_tpl_post_data(self, sheet_tpl: IsaTabTemplate) -> dict:
        """
        Return POST data for creating sheet from template.

        :param sheet_tpl: IsaTabTemplate object
        :return: Dict
        """
        ret = {TPL_DIR_FIELD: clean_sheet_dir_name(self.project.title)}
        if not isinstance(sheet_tpl, IsaTabTemplate):  # Custom template
            tpl_config = json.loads(sheet_tpl.configuration)
        else:  # CUBI template
            tpl_config = sheet_tpl.configuration
        for k, v in tpl_config.items():
            if isinstance(v, str):
                if '{{' in v or '{%' in v:
                    continue
                ret[k] = v
            elif isinstance(v, list):
                ret[k] = v[0]
            elif isinstance(v, dict):
                ret[k] = json.dumps(v)
        return ret

    def make_sheets_from_cubi_tpl(
        self, sheet_tpl: IsaTabTemplate
    ) -> Investigation:
        """
        Create investigation from CUBI templates by posting to the template
        create view.

        :param sheet_tpl: IsaTabTemplate object
        :return: Investigation object
        """
        url = reverse(
            'samplesheets:template_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        with self.login(self.user):
            response = self.client.post(
                url + '?sheet_tpl=' + sheet_tpl.name,
                data=self.get_tpl_post_data(sheet_tpl),
            )
        self.assertEqual(response.status_code, 302, msg=sheet_tpl.name)
        return Investigation.objects.get(project=self.project, active=True)


class SamplesheetsViewTestBase(
    ProjectMixin, RoleMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Base view for samplesheets views tests"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Init users
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.user_owner = self.make_user('user_owner')
        self.user_delegate = self.make_user('user_delegate')
        self.user_contributor = self.make_user('user_contributor')
        self.user_guest = self.make_user('user_guest')
        self.user_viewer = self.make_user('user_viewer')
        self.user_no_roles = self.make_user('user_no_roles')
        # Init projects
        self.category = self.make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        self.delegate_as = self.make_assignment(
            self.project, self.user_delegate, self.role_delegate
        )
        self.contributor_as = self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )
        self.guest_as = self.make_assignment(
            self.project, self.user_guest, self.role_guest
        )
        self.viewer_as = self.make_assignment(
            self.project, self.user_viewer, self.role_viewer
        )


# Test Cases -------------------------------------------------------------------


class TestProjectSheetsView(SamplesheetsViewTestBase):
    """Tests for ProjectSheetsView"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get_no_investigation(self):
        """Test ProjectSheetsView GET with no investigation"""
        self.investigation.delete()
        self.investigation = None
        self.study = None

        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['investigation'])
        self.assertNotIn('study', response.context)
        self.assertNotIn('tables', response.context)


class TestSheetImportMixin(SampleSheetModelMixin, SamplesheetsViewTestBase):
    """Tests for SheetImportMixin"""

    def _setup_metadata(self, inv1: Investigation, inv2: Investigation):
        """Set up inv2 SODAR metadata to match inv1 UUIDs"""
        inv2.comments[sc.ISA_META_PROJECT_UUID] = str(self.project.sodar_uuid)
        inv2.save()
        for s1 in inv1.studies.all():
            s2 = inv2.studies.get(identifier=s1.identifier)
            s2.comments[sc.ISA_META_STUDY_UUID] = str(s1.sodar_uuid)
            s2.save()
            for a1 in s1.assays.all():
                a2 = s2.assays.get(file_name=a1.file_name)
                a2.comments[sc.ISA_META_ASSAY_UUID] = str(a1.sodar_uuid)
                a2.save()

    def test_compare(self):
        """Test _compare_invs()"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self.assertEqual(inv2.comments.get(sc.ISA_META_PROJECT_UUID), None)
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_multi(self):
        """Test compare with multi-study and multi-assay investigation"""
        inv1 = self.import_isa_from_file(SHEET_PATH_MULTI, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH_MULTI, project=self.project)
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_inserted_rows(self):
        """Test compare with inserted rows"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(
            SHEET_PATH_INSERTED, project=self.project
        )
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_modified_sheet(self):
        """Test compare with modified studies/assays"""
        inv1 = self.import_isa_from_file(
            SHEET_PATH_SMALL2, project=self.project
        )
        inv2 = self.import_isa_from_file(
            SHEET_PATH_SMALL2_ALT, project=self.project
        )
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), False)

    def test_compare_different_sheet(self):
        """Test compare with different sheet"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(
            SHEET_PATH_SMALL2, project=self.project
        )
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), False)

    def test_compare_missing_assay(self):
        """Test compare with missing assay"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2.studies.first().assays.first().delete()
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), False)

    def test_compare_missing_study(self):
        """Test compare with missing study"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2.studies.first().delete()
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), False)

    def test_compare_study_id(self):
        """Test compare with different study identifier"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        study2 = inv2.studies.first()
        study2.identifier = 'UPDATED-IDENTIFIER'
        study2.save()
        # Should fail
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), False)

    def test_compare_study_file_name(self):
        """Test compare with different study file name"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        study2 = inv2.studies.first()
        study2.file_name = 's_updated_study_name.txt'
        study2.save()
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), False)

    def test_compare_assay_file_name(self):
        """Test compare with and different assay file name"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        study2 = inv2.studies.first()
        assay2 = study2.assays.first()
        assay2.file_name = 'a_updated_assay_name.txt'
        assay2.save()
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), False)

    def test_compare_metadata(self):
        """Test compare with metadata"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self._setup_metadata(inv1, inv2)
        self.assertEqual(
            inv2.comments.get(sc.ISA_META_PROJECT_UUID),
            str(self.project.sodar_uuid),
        )
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_metadata_multi(self):
        """Test compare with metadata and multi-study/assay investigation"""
        inv1 = self.import_isa_from_file(SHEET_PATH_MULTI, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH_MULTI, project=self.project)
        self._setup_metadata(inv1, inv2)
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_metadata_study_id(self):
        """Test compare with metadata and different study identifier"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self._setup_metadata(inv1, inv2)
        study2 = inv2.studies.first()
        study2.identifier = 'UPDATED-IDENTIFIER'
        study2.save()
        # Should still succeed
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_metadata_study_file_name(self):
        """Test compare with metadata and different study file name"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self._setup_metadata(inv1, inv2)
        study2 = inv2.studies.first()
        study2.file_name = 's_updated_study_name.txt'
        study2.save()
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_metadata_assay_file_name(self):
        """Test compare with metadata and different assay file name"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self._setup_metadata(inv1, inv2)
        study2 = inv2.studies.first()
        assay2 = study2.assays.first()
        assay2.file_name = 'a_updated_assay_name.txt'
        assay2.save()
        self.assertEqual(SheetImportMixin._compare_invs(inv1, inv2), True)

    def test_compare_metadata_dupe_study_uuid(self):
        """Test compare with metadata and duplicate study UUID"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self._setup_metadata(inv1, inv2)
        study_uuid = str(inv1.studies.first().sodar_uuid)
        self.make_study(
            identifier='study-id-here',
            file_name='s_another_study.txt',
            investigation=inv2,
            title='Study Title',
            description='',
            comments={sc.ISA_META_STUDY_UUID: study_uuid},
        )
        with self.assertRaises(ValueError):
            SheetImportMixin._compare_invs(inv1, inv2)

    def test_compare_metadata_dupe_assay_uuid(self):
        """Test compare with metadata and duplicate assay UUID"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self._setup_metadata(inv1, inv2)
        assay_uuid = str(inv1.studies.first().assays.first().sodar_uuid)
        self.make_assay(
            file_name='a_another_assay.txt',
            study=inv2.studies.first(),
            tech_platform='',
            tech_type={},
            measurement_type={},
            arcs=[],
            comments={sc.ISA_META_ASSAY_UUID: assay_uuid},
        )
        with self.assertRaises(ValueError):
            SheetImportMixin._compare_invs(inv1, inv2)

    def test_compare_metadata_dupe_assay_uuid_other_study(self):
        """Test compare with metadata and dupe assay UUID in another study"""
        inv1 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        inv2 = self.import_isa_from_file(SHEET_PATH, project=self.project)
        self._setup_metadata(inv1, inv2)
        assay_uuid = str(inv1.studies.first().assays.first().sodar_uuid)
        study2b = self.make_study(
            identifier='study-id-here',
            file_name='s_another_study.txt',
            investigation=inv2,
            title='Study Title',
            description='',
            comments={sc.ISA_META_STUDY_UUID: str(uuid.uuid4())},
        )  # Imaginary UUID, but we don't know it at this point in time
        self.make_assay(
            file_name='a_another_assay.txt',
            study=study2b,
            tech_platform='',
            tech_type={},
            measurement_type={},
            arcs=[],
            comments={sc.ISA_META_ASSAY_UUID: assay_uuid},
        )
        with self.assertRaises(ValueError):
            SheetImportMixin._compare_invs(inv1, inv2)


class TestSheetImportView(
    SheetImportMixin,
    LandingZoneMixin,
    IrodsAccessTicketMixin,
    SamplesheetsViewTestBase,
):
    """Tests for SheetImportView"""

    def _clear_display_config(self):
        """Clear display config for self.user in self.project"""
        app_settings.set(
            'samplesheets',
            'display_config',
            {},
            project=self.project,
            user=self.user,
        )

    def _update_replace_uuids(self, inv: Investigation):
        """Update UUIDs for sheet replace"""
        self.project.sodar_uuid = META_PROJECT_UUID
        self.project.save()
        inv.sodar_uuid = META_INV_UUID
        inv.save()
        study = inv.studies.first()
        study.sodar_uuid = META_STUDY_UUID
        study.save()
        assay = study.assays.first()
        assay.sodar_uuid = META_ASSAY_UUID
        assay.save()
        self.url = reverse(
            'samplesheets:import',
            kwargs={'project': self.project.sodar_uuid},
        )  # Update URL to point to the correct UUID

    def setUp(self):
        super().setUp()
        self.timeline = plugin_api.get_backend_api('timeline_backend')
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self.url = reverse(
            'samplesheets:import',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.irods_backend = PluginAPI.get_backend_api('omics_irods')

    def test_get(self):
        """Test SheetImportView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        """Test POST to import ISA-Tab zip file"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)

        with open(SHEET_PATH, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        isa_version = ISATab.objects.first()
        self.assertListEqual(isa_version.tags, ['IMPORT'])
        self.assertIsNotNone(isa_version.data['sheet_config'])
        self.assertIsNotNone(isa_version.data['display_config'])

        inv = Investigation.objects.first()
        study = inv.studies.first()
        assay = study.assays.first()
        inv_data = isa_version.data['investigation']['tsv']

        # Assert SODAR metadata not in db objects
        self.assertNotIn(sc.ISA_META_PROJECT_UUID, inv.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_PROJECT_UUID}]', inv.headers)
        self.assertNotIn(sc.ISA_META_STUDY_UUID, study.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_STUDY_UUID}]', study.headers)
        self.assertNotIn(sc.ISA_META_ASSAY_UUID, assay.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_ASSAY_UUID}]', assay.headers)
        # Assert SODAR metadata not in version (they were not in original)
        self.assertNotIn(f'Comment[{sc.ISA_META_PROJECT_UUID}]', inv_data)
        self.assertNotIn(f'Comment[{sc.ISA_META_STUDY_UUID}]', inv_data)
        self.assertNotIn(f'Comment[{sc.ISA_META_ASSAY_UUID}]', inv_data)
        # Assert study render table cache
        # NOTE: Cache item not created in this case
        cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=inv.studies.first().sodar_uuid
        )
        self.assertIsNone(
            self.cache_backend.get_cache_item(
                APP_NAME, cache_name, self.project
            )
        )

    def test_post_metadata(self):
        """Test POST with SODAR metadata"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)

        with open(SHEET_PATH_META, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        isa_version = ISATab.objects.first()
        self.assertListEqual(isa_version.tags, ['IMPORT'])
        self.assertIsNotNone(isa_version.data['sheet_config'])
        self.assertIsNotNone(isa_version.data['display_config'])

        inv = Investigation.objects.first()
        study = inv.studies.first()
        assay = study.assays.first()
        inv_data = isa_version.data['investigation']['tsv']

        # Assert SODAR metadata not in db objects (should be stripped)
        self.assertNotIn(sc.ISA_META_PROJECT_UUID, inv.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_PROJECT_UUID}]', inv.headers)
        self.assertNotIn(sc.ISA_META_STUDY_UUID, study.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_STUDY_UUID}]', study.headers)
        self.assertNotIn(sc.ISA_META_ASSAY_UUID, assay.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_ASSAY_UUID}]', assay.headers)
        # Assert SODAR metadata in version
        self.assertIn(
            f'Comment[{sc.ISA_META_PROJECT_UUID}]\t{META_PROJECT_UUID}',
            inv_data,
        )
        self.assertIn(
            f'Comment[{sc.ISA_META_STUDY_UUID}]\t{META_STUDY_UUID}', inv_data
        )
        self.assertIn(
            f'Comment[{sc.ISA_META_ASSAY_UUID}]\t{META_ASSAY_UUID}', inv_data
        )

    def test_post_replace(self):
        """Test POST to replace existing investigation"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        uuid = inv.sodar_uuid
        old_inv_pk = inv.pk
        self._clear_display_config()

        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        self.assertEqual(
            AppSetting.objects.filter(name='display_config').count(), 1
        )

        with open(SHEET_PATH_SMALL2, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        inv = Investigation.objects.get(project=self.project, active=True)
        self.assertEqual(inv.sodar_uuid, uuid)
        self.assertNotEqual(inv.pk, old_inv_pk)  # Db id should have changed
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertListEqual(
            ISATab.objects.all().order_by('-pk').first().tags,
            ['IMPORT', 'REPLACE'],
        )
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['sheet_config']
        )
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['display_config']
        )
        self.assertEqual(
            AppSetting.objects.filter(name='display_config').count(), 0
        )
        # Assert study render table cache
        inv = Investigation.objects.first()
        cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=inv.studies.first().sodar_uuid
        )
        self.assertIsNone(
            self.cache_backend.get_cache_item(
                APP_NAME, cache_name, self.project
            )
        )

    def test_post_replace_config_keep(self):
        """Test POST to replace and keep configs"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        s_uuid = str(inv.studies.first().sodar_uuid)
        # Get and update config
        edited_field = {
            'name': 'age',
            'type': 'characteristics',
            'unit': ['day'],
            'regex': '',
            'format': 'integer',
            'default': '',
            'editable': True,
        }
        sheet_config = conf_api.get_sheet_config(inv)
        sheet_config['studies'][s_uuid]['nodes'][0]['fields'][2] = edited_field
        app_settings.set(
            'samplesheets', 'sheet_config', sheet_config, project=self.project
        )

        with open(SHEET_PATH_INSERTED, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        sheet_config = app_settings.get(
            'samplesheets', 'sheet_config', project=self.project
        )
        version_config = (
            ISATab.objects.all().order_by('-pk').first().data['sheet_config']
        )
        self.assertEqual(
            sheet_config['studies'][s_uuid]['nodes'][0]['fields'][2],
            edited_field,
        )
        self.assertEqual(
            version_config['studies'][s_uuid]['nodes'][0]['fields'][2],
            edited_field,
        )

    def test_post_replace_not_allowed(self):
        """Test post to replace iRODS-enabled investigation with missing data"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        inv.irods_status = True
        inv.save()
        uuid = inv.sodar_uuid
        self.assertEqual(Investigation.objects.count(), 1)
        with open(SHEET_PATH_MINIMAL, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        new_inv = Investigation.objects.first()
        self.assertEqual(uuid, new_inv.sodar_uuid)  # Should not have changed

    def test_post_replace_zone(self):
        """Test POST to replace with existing landing zone"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        inv.irods_status = True
        inv.save()
        uuid = inv.sodar_uuid
        self._clear_display_config()
        conf_api.get_sheet_config(inv)
        zone = self.make_landing_zone(
            'new_zone',
            self.project,
            self.user,
            inv.get_assays().first(),
            status=ZONE_STATUS_ACTIVE,
        )

        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        self.assertEqual(
            AppSetting.objects.filter(name='display_config').count(), 1
        )

        with open(SHEET_PATH_INSERTED, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(uuid, Investigation.objects.first().sodar_uuid)
        self.assertEqual(ISATab.objects.count(), 2)
        inv = Investigation.objects.get(project=self.project, active=True)
        zone.refresh_from_db()
        self.assertEqual(
            LandingZone.objects.get(assay__study__investigation=inv),
            zone,
        )
        self.assertEqual(
            zone.assay,
            Assay.objects.filter(study__investigation=inv).first(),
        )

    def test_post_replace_ticket(self):
        """Test POST to replace with existing iRODS access ticket"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        inv.irods_status = True
        inv.save()
        old_inv_pk = inv.pk
        uuid = inv.sodar_uuid
        self._clear_display_config()
        conf_api.get_sheet_config(inv)

        study = inv.studies.first()
        assay = study.assays.first()
        ticket = self.make_irods_ticket(
            study=study,
            assay=assay,
            path=os.path.join(
                self.irods_backend.get_path(assay), MISC_FILES_COLL
            ),
            user=self.user,
        )
        self.assertEqual(Investigation.objects.count(), 1)

        with open(SHEET_PATH_INSERTED, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(uuid, Investigation.objects.first().sodar_uuid)
        inv = Investigation.objects.get(project=self.project, active=True)
        self.assertNotEqual(inv.pk, old_inv_pk)

        # Assert ticket still exists and refers current study/assay
        study = inv.studies.first()
        ticket.refresh_from_db()
        self.assertEqual(ticket.study, study)
        self.assertEqual(ticket.assay, study.assays.first())

    def test_post_replace_study_cache(self):
        """Test POST to replace with existing study table cache"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        conf_api.get_sheet_config(inv)
        study = inv.studies.first()
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

        with open(SHEET_PATH_INSERTED, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, {})
        self.assertEqual(JSONCacheItem.objects.count(), 1)

    def test_post_replace_study_cache_new_sheet(self):
        """Test POST to replace with study table cache and different sheet"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        conf_api.get_sheet_config(inv)
        study = inv.studies.first()
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

        with open(SHEET_PATH_SMALL2, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertIsNone(cache_item)
        self.assertEqual(JSONCacheItem.objects.count(), 0)

    def test_post_replace_metadata(self):
        """Test POST to replace with metadata"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        self._update_replace_uuids(inv)  # Update UUIDS to match metadata

        old_inv_pk = inv.pk
        self._clear_display_config()

        with open(SHEET_PATH_META, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)

        inv = Investigation.objects.get(project=self.project, active=True)
        study = inv.studies.first()
        assay = study.assays.first()

        self.assertEqual(str(inv.sodar_uuid), META_INV_UUID)
        self.assertNotEqual(inv.pk, old_inv_pk)
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertListEqual(
            ISATab.objects.all().order_by('-pk').first().tags,
            ['IMPORT', 'REPLACE'],
        )
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['sheet_config']
        )
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['display_config']
        )
        self.assertEqual(
            AppSetting.objects.filter(name='display_config').count(), 0
        )
        # Assert study render table cache
        cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=inv.studies.first().sodar_uuid
        )
        self.assertIsNone(
            self.cache_backend.get_cache_item(
                APP_NAME, cache_name, self.project
            )
        )
        # Assert SODAR metadata has been stripped
        self.assertNotIn(sc.ISA_META_PROJECT_UUID, inv.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_PROJECT_UUID}]', inv.headers)
        self.assertNotIn(sc.ISA_META_STUDY_UUID, study.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_STUDY_UUID}]', study.headers)
        self.assertNotIn(sc.ISA_META_ASSAY_UUID, assay.comments)
        self.assertNotIn(f'Comment[{sc.ISA_META_ASSAY_UUID}]', assay.headers)

    def test_post_replace_metadata_zone(self):
        """Test POST to replace with metadata and existing landing zone"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        self._update_replace_uuids(inv)
        inv.irods_status = True
        inv.save()

        uuid = inv.sodar_uuid
        self._clear_display_config()
        conf_api.get_sheet_config(inv)
        zone = self.make_landing_zone(
            'new_zone',
            self.project,
            self.user,
            inv.get_assays().first(),
            status=ZONE_STATUS_ACTIVE,
        )

        with open(SHEET_PATH_META, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(uuid, str(Investigation.objects.first().sodar_uuid))
        self.assertEqual(ISATab.objects.count(), 2)
        inv = Investigation.objects.get(project=self.project, active=True)
        zone.refresh_from_db()
        self.assertEqual(
            LandingZone.objects.get(assay__study__investigation=inv),
            zone,
        )
        self.assertEqual(
            zone.assay,
            Assay.objects.filter(study__investigation=inv).first(),
        )

    def test_post_replace_metadata_ticket(self):
        """Test POST to replace with metadata and iRODS access ticket"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        self._update_replace_uuids(inv)
        inv.irods_status = True
        inv.save()

        old_inv_pk = inv.pk
        uuid = inv.sodar_uuid
        self._clear_display_config()
        conf_api.get_sheet_config(inv)

        study = inv.studies.first()
        assay = study.assays.first()
        ticket = self.make_irods_ticket(
            study=study,
            assay=assay,
            path=os.path.join(
                self.irods_backend.get_path(assay), MISC_FILES_COLL
            ),
            user=self.user,
        )

        with open(SHEET_PATH_INSERTED, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(uuid, str(Investigation.objects.first().sodar_uuid))
        inv = Investigation.objects.get(project=self.project, active=True)
        self.assertNotEqual(inv.pk, old_inv_pk)

        # Assert ticket still exists and refers current study/assay
        study = inv.studies.first()
        ticket.refresh_from_db()
        self.assertEqual(ticket.study, study)
        self.assertEqual(ticket.assay, study.assays.first())

    def test_post_replace_metadata_rename(self):
        """Test POST to replace with metadata and renamed study/assay files"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        self._update_replace_uuids(inv)  # Update UUIDS to match metadata

        old_inv_pk = inv.pk
        self._clear_display_config()

        with open(SHEET_PATH_RENAME_META, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)

        inv = Investigation.objects.get(project=self.project, active=True)
        study = inv.studies.first()
        assay = study.assays.first()

        self.assertEqual(str(inv.sodar_uuid), META_INV_UUID)
        self.assertNotEqual(inv.pk, old_inv_pk)
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['sheet_config']
        )
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['display_config']
        )
        self.assertEqual(
            AppSetting.objects.filter(name='display_config').count(), 0
        )
        cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=inv.studies.first().sodar_uuid
        )
        self.assertIsNone(
            self.cache_backend.get_cache_item(
                APP_NAME, cache_name, self.project
            )
        )
        # Study and assay filenames should be updated
        self.assertEqual(study.file_name, 's_small2_renamed.txt')
        self.assertEqual(assay.file_name, 'a_small2_renamed.txt')

    def test_post_replace_irods_rename_meta(self):
        """Test POST to replace with iRODS, renamed tables and metadata"""
        inv = self.import_isa_from_file(SHEET_PATH_META, self.project)
        self._update_replace_uuids(inv)  # Update UUIDS to match metadata
        inv.irods_status = True  # Enable iRODS colls
        inv.save()
        sheet_config = conf_api.get_sheet_config(inv)
        app_settings.set(
            'samplesheets', 'sheet_config', sheet_config, project=self.project
        )
        old_inv_pk = inv.pk
        self._clear_display_config()

        with open(SHEET_PATH_RENAME_META, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        inv = Investigation.objects.get(project=self.project, active=True)
        self.assertEqual(str(inv.sodar_uuid), META_INV_UUID)
        self.assertNotEqual(inv.pk, old_inv_pk)
        self.assertEqual(inv.irods_status, True)
        self.assertEqual(ISATab.objects.count(), 2)

    def test_post_replace_irods_rename_meta_invalid(self):
        """Test POST to replace with iRODS, renamed tables and invalid metadata"""
        inv = self.import_isa_from_file(SHEET_PATH_META, self.project)
        # NOTE: No UUID update so metadata will not match
        inv.irods_status = True  # Enable iRODS colls
        inv.save()
        sheet_config = conf_api.get_sheet_config(inv)
        app_settings.set(
            'samplesheets', 'sheet_config', sheet_config, project=self.project
        )
        old_inv_pk = inv.pk
        self._clear_display_config()

        with open(SHEET_PATH_RENAME_META, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        inv = Investigation.objects.get(project=self.project, active=True)
        # Replace should have failed
        self.assertNotEqual(str(inv.sodar_uuid), META_INV_UUID)
        self.assertEqual(inv.pk, old_inv_pk)
        self.assertEqual(inv.irods_status, True)
        self.assertEqual(ISATab.objects.count(), 1)

    def test_post_import_critical_warnings(self):
        """Test POST with critical warnings raised in altamISA"""
        self.assertEqual(Investigation.objects.count(), 0)
        with open(SHEET_PATH_CRITICAL, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 0)
        # Assert timeline event
        tl_event = self.timeline.get_project_events(self.project).order_by(
            '-pk'
        )[0]
        tl_status = tl_event.get_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    @override_settings(SHEETS_ALLOW_CRITICAL=True)
    def test_post_import_critical_warnings_allowed(self):
        """Test POST with critical warnings allowed"""
        self.assertEqual(Investigation.objects.count(), 0)
        with open(SHEET_PATH_CRITICAL, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        # Assert timeline event
        tl_event = self.timeline.get_project_events(self.project).order_by(
            '-pk'
        )[0]
        tl_status = tl_event.get_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    def test_post_import_multiple(self):
        """Test POST with ISA-Tab as multiple files"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)
        zf = ZipFile(os.fsdecode(SHEET_PATH))
        post_data = {
            'file_upload': [
                zf.open(f.filename) for f in zf.filelist if f.file_size > 0
            ]
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        self.assertListEqual(ISATab.objects.first().tags, ['IMPORT'])

    def test_post_import_multiple_no_study(self):
        """Test POST as multiple files without required study"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)
        zf = ZipFile(os.fsdecode(SHEET_PATH))
        post_data = {
            'file_upload': [
                zf.open(f.filename)
                for f in zf.filelist
                if f.file_size > 0
                and not f.filename.split('/')[-1].startswith('s_')
            ]
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Investigation.objects.count(), 0)

    def test_post_import_multiple_no_assay(self):
        """Test POST as multiple files without required assay"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)
        zf = ZipFile(os.fsdecode(SHEET_PATH))
        post_data = {
            'file_upload': [
                zf.open(f.filename)
                for f in zf.filelist
                if f.file_size > 0
                and not f.filename.split('/')[-1].startswith('a_')
            ]
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 0)

    def test_post_import_empty_assay(self):
        """Test POST with empty assay table (should fail)"""
        self.assertEqual(Investigation.objects.count(), 0)
        with open(SHEET_PATH_EMPTY_ASSAY, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 0)

    def test_import_no_plugin_assay(self):
        """Test posting an ISA-Tab with an assay without plugin"""
        self.assertEqual(Investigation.objects.count(), 0)
        with open(SHEET_PATH_NO_PLUGIN_ASSAY, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[1].message,
            self.get_assay_plugin_warning(Assay.objects.all().first()),
        )


class TestSheetTemplateSelectView(
    CookiecutterISATemplateMixin, SamplesheetsViewTestBase
):
    """Tests for SheetTemplateSelectView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:template_select',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetTemplateSelectView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': t.name,
                'description': t.description[0].upper() + t.description[1:],
            }
            for t in ISA_TEMPLATES
        ]
        self.assertEqual(
            response.context['sheet_templates'],
            sorted(expected, key=lambda x: x['description'].lower()),
        )

    def test_get_with_sheets(self):
        """Test GET with sheets in project (should fail)"""
        self.import_isa_from_file(SHEET_PATH, self.project)
        with self.login(self.user):
            response = self.client.get(self.url)
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

    def test_get_custom(self):
        """Test GET with custom template"""
        tpl = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': t.name,
                'description': t.description[0].upper() + t.description[1:],
            }
            for t in ISA_TEMPLATES
        ]
        expected.append({'name': tpl.name, 'description': tpl.description})
        self.assertEqual(
            response.context['sheet_templates'],
            sorted(expected, key=lambda x: x['description'].lower()),
        )

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_get_custom_only(self):
        """Test GET with custom template only"""
        tpl = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        expected = [{'name': tpl.name, 'description': tpl.description}]
        self.assertEqual(response.context['sheet_templates'], expected)

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_get_custom_only_inactive(self):
        """Test GET with inactive custom template only"""
        self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=False,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sheet_templates'], [])

    @override_settings(ENABLED_BACKEND_PLUGINS=BACKEND_PLUGINS_NO_TPL)
    def test_get_custom_backend_disabled(self):
        """Test GET with custom template and disabled backend"""
        self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': t.name,
                'description': t.description[0].upper() + t.description[1:],
            }
            for t in ISA_TEMPLATES
        ]
        self.assertEqual(
            response.context['sheet_templates'],
            sorted(expected, key=lambda x: x['description'].lower()),
        )


class TestSheetTemplateCreateView(
    SheetTemplateCreateMixin,
    CookiecutterISATemplateMixin,
    CookiecutterISAFileMixin,
    SamplesheetsViewTestBase,
):
    """Tests for SheetTemplateCreateView"""

    def _make_custom_template(self):
        """Make custom template with data"""
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            configuration = f.read().decode('utf-8')
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration=configuration,
            user=self.user,
        )
        self.file_data = {}
        for fn in ISA_FILE_NAMES:
            fp = os.path.join(str(ISA_FILE_PATH), fn)
            with open(fp, 'rb') as f:
                fd = f.read().decode('utf-8')
                self.file_data[fn] = fd
                self.make_isa_file(
                    template=self.template, file_name=fn, content=fd
                )

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:template_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get_batch_cubi(self):
        """Test SheetTemplateCreateView GET with CUBI templates"""
        for t in ISA_TEMPLATES:
            with self.login(self.user):
                response = self.client.get(self.url, data={'sheet_tpl': t.name})
            self.assertEqual(response.status_code, 200, msg=t.name)

    def test_get_invalid_template(self):
        """Test GET with invalid template (should redirect)"""
        with self.login(self.user):
            response = self.client.get(
                self.url,
                data={'sheet_tpl': 'NOT_A_REAL_TEMPLATE'},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                'samplesheets:template_select',
                kwargs={'project': self.project.sodar_uuid},
            ),
        )

    def test_get_no_template(self):
        """Test GET view with out template name (should redirect)"""
        with self.login(self.user):
            response = self.client.get(self.url, data={'sheet_tpl': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                'samplesheets:template_select',
                kwargs={'project': self.project.sodar_uuid},
            ),
        )

    def test_get_custom(self):
        """Test GET with custom template"""
        self._make_custom_template()
        with self.login(self.user):
            response = self.client.get(
                self.url, data={'sheet_tpl': self.template.name}
            )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsNotNone(form)
        expected = [
            k
            for k, v in json.loads(self.template.configuration).items()
            if not (isinstance(v, str) and ('{{' in v or '{%' in v))
        ]
        self.assertEqual(list(form.fields.keys()), expected)

    def test_get_custom_inactive(self):
        """Test GET with inactive custom template (should fail)"""
        self._make_custom_template()
        self.template.active = False
        self.template.save()
        with self.login(self.user):
            response = self.client.get(
                self.url, data={'sheet_tpl': self.template.name}
            )
        self.assertEqual(response.status_code, 302)

    def test_post_batch_cubi(self):
        """Test POST with supported templates and default values"""
        for t in ISA_TEMPLATES:
            self.assertIsNone(self.project.investigations.first())
            self.make_sheets_from_cubi_tpl(t)
            isa_tab = ISATab.objects.first()
            self.assertEqual(isa_tab.tags, ['CREATE'])
            self.assertIsNotNone(
                self.project.investigations.first(), msg=t.name
            )
            self.project.investigations.first().delete()

    def test_post_batch_file_name_slash(self):
        """Test POST with slashes in values used for file names"""
        for t in ISA_TEMPLATES:
            self.assertIsNone(self.project.investigations.first())
            post_data = self.get_tpl_post_data(t)
            for k in TPL_FILE_NAME_FIELDS:
                if k in post_data:
                    post_data[k] += '/test'
            with self.login(self.user):
                response = self.client.post(
                    self.url + '?sheet_tpl=' + t.name,
                    data=post_data,
                )
            self.assertEqual(response.status_code, 302, msg=t.name)
            self.assertIsNotNone(
                self.project.investigations.first(), msg=t.name
            )
            self.project.investigations.first().delete()

    def test_post_multiple(self):
        """Test POST with multiple requests (should fail)"""
        tpl = ISA_TEMPLATES[0]
        url = self.url + '?sheet_tpl=' + tpl.name
        post_data = self.get_tpl_post_data(tpl)
        with self.login(self.user):
            response = self.client.post(url, data=post_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.project.investigations.count(), 1)
            response = self.client.post(url, data=post_data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.project.investigations.count(), 1)

    def test_post_custom(self):
        """Test POST with custom template"""
        self._make_custom_template()
        self.assertIsNone(self.project.investigations.first())
        post_data = self.get_tpl_post_data(self.template)
        with self.login(self.user):
            response = self.client.post(
                self.url + '?sheet_tpl=' + self.template.name,
                data=post_data,
            )
        isa_tab = ISATab.objects.first()
        self.assertEqual(isa_tab.tags, ['CREATE'])
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(self.project.investigations.first())


class TestSheetExcelExportView(SamplesheetsViewTestBase):
    """Tests for SheetExcelExportView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.timeline = plugin_api.get_backend_api('timeline_backend')

    def test_getr_study(self):
        """Test SheetExcelExportView GET with study table"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_excel',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)

    def test_getr_assay(self):
        """Test GET with assay table"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_excel',
                    kwargs={'assay': self.assay.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)


class TestSheetISAExportView(SamplesheetsViewTestBase):
    """Tests for SheetISAExportView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.timeline = plugin_api.get_backend_api('timeline_backend')
        self.url = reverse(
            'samplesheets:export_isa',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.url_meta_suffix = '?meta=1'

    def test_get(self):
        """Test SheetISAExportView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            f'attachment; filename="{self.investigation.archive_name}"',
        )
        # TODO: Assert no metadata

    def test_get_metadata(self):
        """Test GET with metadata enabled"""
        with self.login(self.user):
            response = self.client.get(self.url + self.url_meta_suffix)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            f'attachment; filename="{self.investigation.archive_name}"',
        )
        # TODO: Assert metadata

    def test_get_no_investigation(self):
        """Test GET with no investigation"""
        self.investigation.delete()
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_version(self):
        """Test GET with ISA-Tab version"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        filename = (
            self.investigation.archive_name.split('.zip')[0]
            + '_'
            + localtime(isa_version.date_created).strftime('%Y-%m-%d_%H%M%S')
            + '.zip'
        )
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_isa',
                    kwargs={'isatab': isa_version.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            f'attachment; filename="{filename}"',
        )

    # TODO: Test with version and metadata?


class TestSheetDeleteView(SamplesheetsViewTestBase):
    """Tests for SheetDeleteView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        # Set up helpers
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self.url = reverse(
            'samplesheets:delete',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetDeleteView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['irods_file_count'], 0)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_post(self):
        """Test POST"""
        app_settings.set(
            'samplesheets',
            'display_config',
            {},
            project=self.project,
            user=self.user,
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        self.assertEqual(
            AppSetting.objects.filter(name='display_config').count(), 1
        )

        with self.login(self.user):
            response = self.client.post(
                self.url, data={'delete_host_confirm': 'testserver'}
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)
        self.assertEqual(
            AppSetting.objects.filter(name='display_config').count(), 0
        )

    def test_post_invalid_host(self):
        """Test POST with invalid host name given in form"""
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(
                self.url, data={'delete_host_confirm': ''}
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)

    def test_post_study_cache(self):
        """Test POST with cached study tables"""
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)

        study_tables = table_builder.build_study_tables(self.study)
        cache_name = STUDY_TABLE_CACHE_ITEM.format(study=self.study.sodar_uuid)
        self.cache_backend.set_cache_item(
            APP_NAME, cache_name, study_tables, 'json', self.project
        )
        cache_args = [APP_NAME, cache_name, self.project]
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, study_tables)
        self.assertEqual(JSONCacheItem.objects.count(), 1)

        with self.login(self.user):
            response = self.client.post(
                self.url, data={'delete_host_confirm': 'testserver'}
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertIsNone(cache_item)
        self.assertEqual(JSONCacheItem.objects.count(), 0)


class TestSheetVersionListView(SamplesheetsViewTestBase):
    """Tests for SheetVersionListView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:versions',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionListView GET"""
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 1)
        self.assertEqual(
            response.context['current_version'],
            ISATab.objects.filter(
                project=self.project,
                investigation_uuid=self.investigation.sodar_uuid,
            )
            .order_by('-date_created')
            .first(),
        )

    def test_get_empty(self):
        """Test GET with no versions"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 0)
        self.assertIsNone(response.context['current_version'])


class TestSheetVersionRestoreView(SamplesheetsViewTestBase):
    """Tests for SheetVersionRestoreView"""

    @classmethod
    def _get_table_uuids(cls, inv: Investigation) -> (str, str):
        """Return study and assay UUIDs for a single study/assay inv"""
        study = inv.studies.first()
        ret_study = str(study.sodar_uuid)
        ret_assay = str(study.assays.first().sodar_uuid)
        return (ret_study, ret_assay)

    @classmethod
    def _get_tl_events(cls):
        """Return timeline events for sheet restore"""
        return TimelineEvent.objects.filter(event_name='sheet_restore')

    @classmethod
    def _get_url(cls, isa: ISATab) -> str:
        """Return SheetVersionRestoreView URL for given ISATab object"""
        return reverse(
            'samplesheets:version_restore', kwargs={'isatab': isa.sodar_uuid}
        )

    def _import_isa(self, path: str):
        """Import ISA-Tab and retrieve ISATab version"""
        self.inv = self.import_isa_from_file(path, self.project)
        self.isatab = ISATab.objects.get(investigation_uuid=self.inv.sodar_uuid)

    def _update_replace_uuids(self, inv: Investigation):
        """Update UUIDs for sheet replace"""
        # TODO: Combine with helper in TestSheetImportView to reduce repetition
        self.project.sodar_uuid = META_PROJECT_UUID
        self.project.save()
        inv.sodar_uuid = META_INV_UUID
        inv.save()
        study = inv.studies.first()
        study.sodar_uuid = META_STUDY_UUID
        study.save()
        assay = study.assays.first()
        assay.sodar_uuid = META_ASSAY_UUID
        assay.save()

    def setUp(self):
        super().setUp()
        self.inv = None  # Set in _import_isa()
        self.isatab = None  # Set in _import_isa()
        self.dc_kwargs = {
            'name': 'display_config',
            'project': self.project,
            'user': self.user,
        }
        # Set up helpers
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self.timeline = plugin_api.get_backend_api('timeline_backend')
        self.sheet_io = SampleSheetIO()

    def test_get(self):
        """Test SheetVersionRestoreView GET"""
        self._import_isa(SHEET_PATH_SMALL2)
        with self.login(self.user):
            response = self.client.get(self._get_url(self.isatab))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['sheet_version'])

    def test_post(self):
        """Test POST"""
        self._import_isa(SHEET_PATH_SMALL2)
        isatab_new = self.sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.inv.sodar_uuid,
            isa_data=self.sheet_io.export_isa(self.inv),
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertEqual(self._get_tl_events().count(), 0)

        with self.login(self.user):
            response = self.client.post(self._get_url(isatab_new))

        self.assertEqual(response.status_code, 302)
        isatab_latest = ISATab.objects.all().order_by('-date_created').first()
        self.assertNotEqual(
            isatab_latest.date_created, self.isatab.date_created
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        tl_events = self._get_tl_events()
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type,
            self.timeline.TL_STATUS_OK,
        )

    def test_post_study_cache(self):
        """Test POST with cached study table"""
        self._import_isa(SHEET_PATH_SMALL2)
        isatab_new = self.sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.inv.sodar_uuid,
            isa_data=self.sheet_io.export_isa(self.inv),
        )

        study = self.inv.studies.first()
        study_tables = table_builder.build_study_tables(study)
        cache_name = STUDY_TABLE_CACHE_ITEM.format(study=study.sodar_uuid)
        self.cache_backend.set_cache_item(
            APP_NAME, cache_name, study_tables, 'json', self.project
        )
        cache_args = [APP_NAME, cache_name, self.project]
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, study_tables)
        self.assertEqual(JSONCacheItem.objects.count(), 1)

        with self.login(self.user):
            response = self.client.post(self._get_url(isatab_new))

        self.assertEqual(response.status_code, 302)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, {})
        self.assertEqual(JSONCacheItem.objects.count(), 1)

    def test_post_metadata(self):
        """Test POST with SODAR export metadata"""
        self._import_isa(SHEET_PATH_SMALL2)
        isatab_new = self.sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.inv.sodar_uuid,
            isa_data=self.sheet_io.export_isa(self.inv, True),
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)

        with self.login(self.user):
            response = self.client.post(self._get_url(isatab_new))

        self.assertEqual(response.status_code, 302)
        isatab_latest = ISATab.objects.all().order_by('-date_created').first()
        self.assertNotEqual(
            isatab_latest.date_created, self.isatab.date_created
        )

        # Assert export-only metadata has been stripped
        inv = Investigation.objects.get(project=self.project, active=True)
        study = inv.studies.first()
        assay = study.assays.first()
        self.assertNotIn(sc.ISA_META_PROJECT_UUID, inv.comments)
        self.assertNotIn(sc.ISA_META_STUDY_UUID, study.comments)
        self.assertNotIn(sc.ISA_META_ASSAY_UUID, assay.comments)

    def test_post_rename(self):
        """Test POST with renamed study and assay files without metadata"""
        self._import_isa(SHEET_PATH_SMALL2)
        og_study_uuid, og_assay_uuid = self._get_table_uuids(self.inv)

        isatab_new = self.sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.inv.sodar_uuid,
            isa_data=self.sheet_io.export_isa(self.inv),
        )
        # Save sheet config for version to be restored
        isatab_new.data['sheet_config'] = conf_api.get_sheet_config(self.inv)
        isatab_new.save()

        # Delete investigation and import new one with renamed files
        self.inv.delete()
        self.inv = self.import_isa_from_file(SHEET_PATH_RENAME, self.project)

        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 3)
        self.assertEqual(self._get_tl_events().count(), 0)
        self.assertIsNone(AppSetting.objects.filter(**self.dc_kwargs).first())

        with self.login(self.user):
            response = self.client.post(self._get_url(isatab_new))

        self.assertEqual(response.status_code, 302)
        isatab_latest = ISATab.objects.all().order_by('-date_created').first()
        self.assertNotEqual(
            isatab_latest.date_created, self.isatab.date_created
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 3)

        self.inv = Investigation.objects.get(project=self.project, active=True)
        study_uuid, assay_uuid = self._get_table_uuids(self.inv)
        # Study/assay UUIDs are changed, since we can't know they are the same
        self.assertNotEqual(study_uuid, og_study_uuid)
        self.assertNotEqual(assay_uuid, og_assay_uuid)

        # Assert sheet config and display configs
        s_conf = app_settings.get(
            APP_NAME, 'sheet_config', project=self.project
        )
        self.assertIn(assay_uuid, s_conf['studies'][study_uuid]['assays'])
        d_conf = app_settings.get(
            APP_NAME, 'display_config_default', project=self.project
        )
        self.assertIn(assay_uuid, d_conf['studies'][study_uuid]['assays'])
        # User display config should be None (created when navigating to view)
        self.assertIsNone(AppSetting.objects.filter(**self.dc_kwargs).first())

        tl_events = self._get_tl_events()
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type,
            self.timeline.TL_STATUS_OK,
        )

    def test_post_rename_metadata(self):
        """Test POST with renamed files and metadata"""
        self._import_isa(SHEET_PATH_META)  # Import with metadata and OG naming
        self._update_replace_uuids(self.inv)  # Replace UUIDs for metadata

        self.assertEqual(self.project.sodar_uuid, META_PROJECT_UUID)
        inv_data = self.isatab.data['investigation']['tsv']
        self.assertIn(
            f'Comment[{sc.ISA_META_PROJECT_UUID}]\t{META_PROJECT_UUID}',
            inv_data,
        )
        s_conf = conf_api.get_sheet_config(self.inv)
        self.assertNotIn(
            'editable',
            s_conf['studies'][META_STUDY_UUID]['nodes'][0]['fields'][0],
        )
        s_conf['studies'][META_STUDY_UUID]['nodes'][0]['fields'][0][
            'editable'
        ] = True  # Update sheet config to verify restore later
        self.isatab.data['sheet_config'] = s_conf
        self.isatab.save()  # Save sheet config for version to be restored

        self.inv.delete()  # Replace current investigation
        self.inv = self.import_isa_from_file(
            SHEET_PATH_RENAME_META, self.project
        )
        self.assertEqual(
            self.inv.studies.first().file_name, 's_small2_renamed.txt'
        )

        with self.login(self.user):  # Restore original version
            response = self.client.post(self._get_url(self.isatab))

        self.assertEqual(response.status_code, 302)
        self.inv = Investigation.objects.get(project=self.project, active=True)
        self.assertEqual(self.inv.studies.first().file_name, 's_small2.txt')
        # Assert sheet config and display configs
        self.inv = Investigation.objects.get(project=self.project, active=True)
        s_conf = app_settings.get(
            APP_NAME, 'sheet_config', project=self.project
        )
        self.assertIn(
            META_ASSAY_UUID, s_conf['studies'][META_STUDY_UUID]['assays']
        )
        self.assertTrue(
            s_conf['studies'][META_STUDY_UUID]['nodes'][0]['fields'][0][
                'editable'
            ]
        )  # Edited value should be restored
        d_conf = app_settings.get(
            APP_NAME, 'display_config_default', project=self.project
        )
        self.assertIn(
            META_ASSAY_UUID, d_conf['studies'][META_STUDY_UUID]['assays']
        )
        self.assertEqual(
            self._get_tl_events().first().get_status().status_type,
            self.timeline.TL_STATUS_OK,
        )

    def test_post_rename_metadata_other_project(self):
        """Test POST with renamed files and metadata from other project"""
        self._import_isa(SHEET_PATH_META)
        og_study_uuid, og_assay_uuid = self._get_table_uuids(self.inv)
        # NOTE: No UUID update, so the ones in the version won't match

        self.assertNotEqual(self.project.sodar_uuid, META_PROJECT_UUID)
        inv_data = self.isatab.data['investigation']['tsv']
        self.assertIn(
            f'Comment[{sc.ISA_META_PROJECT_UUID}]\t{META_PROJECT_UUID}',
            inv_data,
        )
        s_conf = conf_api.get_sheet_config(self.inv)
        s_conf['studies'][og_study_uuid]['nodes'][0]['fields'][0][
            'editable'
        ] = True
        self.isatab.data['sheet_config'] = s_conf
        self.isatab.save()  # Save sheet config for version to be restored

        self.inv.delete()  # Replace current investigation
        self.inv = self.import_isa_from_file(
            SHEET_PATH_RENAME_META, self.project
        )
        self.assertEqual(
            self.inv.studies.first().file_name, 's_small2_renamed.txt'
        )

        with self.login(self.user):  # Restore original version
            response = self.client.post(self._get_url(self.isatab))

        self.assertEqual(response.status_code, 302)
        self.inv = Investigation.objects.get(project=self.project, active=True)
        self.assertEqual(self.inv.studies.first().file_name, 's_small2.txt')
        self.inv = Investigation.objects.get(project=self.project, active=True)
        study_uuid, assay_uuid = self._get_table_uuids(self.inv)
        self.assertNotEqual(study_uuid, og_study_uuid)
        self.assertNotEqual(assay_uuid, og_assay_uuid)

        # Assert sheet config and display configs
        s_conf = app_settings.get(
            APP_NAME, 'sheet_config', project=self.project
        )
        self.assertNotIn(
            'editable', s_conf['studies'][study_uuid]['nodes'][0]['fields'][0]
        )  # Config should be recreated = no edited value present
        d_conf = app_settings.get(
            APP_NAME, 'display_config_default', project=self.project
        )
        self.assertIn(assay_uuid, d_conf['studies'][study_uuid]['assays'])
        self.assertEqual(
            self._get_tl_events().first().get_status().status_type,
            self.timeline.TL_STATUS_OK,
        )

    def test_post_irods_different_sheet(self):
        """Test POST with iRODS and different sample sheet"""
        self._import_isa(SHEET_PATH_SMALL2)
        isatab_new = self.sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.inv.sodar_uuid,
            isa_data=self.sheet_io.export_isa(self.inv),
        )
        # Replace project investigation with another one from different sheets
        self.inv.delete()
        self.inv = self.import_isa_from_file(SHEET_PATH_MINIMAL, self.project)
        # Set irods_status to True to force extra checks
        self.inv.irods_status = True
        self.inv.save()

        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(self._get_tl_events().count(), 0)
        version_count = ISATab.objects.count()

        with self.login(self.user):
            response = self.client.post(self._get_url(isatab_new))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        # No ISATab versions should be added or removed
        self.assertEqual(ISATab.objects.count(), version_count)
        tl_events = self._get_tl_events()
        self.assertEqual(tl_events.count(), 1)
        # Timeline event should denote failure
        self.assertEqual(
            tl_events.first().get_status().status_type,
            self.timeline.TL_STATUS_FAILED,
        )

    def test_post_irods_rename(self):
        """Test POST with iRODS and renamed tables"""
        self._import_isa(SHEET_PATH_SMALL2)
        # og_study_uuid, og_assay_uuid = self._get_table_uuids(self.inv)
        isatab_new = self.sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.inv.sodar_uuid,
            isa_data=self.sheet_io.export_isa(self.inv),
        )

        self.inv.delete()
        self.inv = self.import_isa_from_file(SHEET_PATH_RENAME, self.project)
        self.inv.irods_status = True  # Enable iRODS colls
        self.inv.save()
        s_conf_old = conf_api.get_sheet_config(self.inv)
        app_settings.set(
            APP_NAME, 'sheet_config', value=s_conf_old, project=self.project
        )

        with self.login(self.user):
            response = self.client.post(self._get_url(isatab_new))

        self.assertEqual(response.status_code, 302)
        s_conf = app_settings.get(
            APP_NAME, 'sheet_config', project=self.project
        )
        self.assertEqual(s_conf, s_conf_old)  # Sheet config should be unchanged
        self.assertEqual(
            self._get_tl_events().first().get_status().status_type,
            self.timeline.TL_STATUS_FAILED,
        )

    def test_post_irods_rename_metadata(self):
        """Test POST with iRODS, renamed files and metadata"""
        self._import_isa(SHEET_PATH_META)
        self._update_replace_uuids(self.inv)

        self.assertEqual(self.project.sodar_uuid, META_PROJECT_UUID)
        inv_data = self.isatab.data['investigation']['tsv']
        self.assertIn(
            f'Comment[{sc.ISA_META_PROJECT_UUID}]\t{META_PROJECT_UUID}',
            inv_data,
        )
        s_conf = conf_api.get_sheet_config(self.inv)
        self.assertNotIn(
            'editable',
            s_conf['studies'][META_STUDY_UUID]['nodes'][0]['fields'][0],
        )
        s_conf['studies'][META_STUDY_UUID]['nodes'][0]['fields'][0][
            'editable'
        ] = True
        self.isatab.data['sheet_config'] = s_conf
        self.isatab.save()

        self.inv.delete()  # Replace current investigation
        self.inv = self.import_isa_from_file(
            SHEET_PATH_RENAME_META, self.project
        )
        self.assertEqual(
            self.inv.studies.first().file_name, 's_small2_renamed.txt'
        )
        self.inv.irods_status = True  # Enable iRODS colls
        self.inv.save()
        self._update_replace_uuids(self.inv)  # Make sure UUIDs still match

        with self.login(self.user):  # Restore original version
            response = self.client.post(self._get_url(self.isatab))

        self.assertEqual(response.status_code, 302)
        self.inv = Investigation.objects.get(project=self.project, active=True)
        self.assertEqual(self.inv.studies.first().file_name, 's_small2.txt')
        # Assert sheet config and display configs
        self.inv = Investigation.objects.get(project=self.project, active=True)
        s_conf = app_settings.get(
            APP_NAME, 'sheet_config', project=self.project
        )
        self.assertIn(
            META_ASSAY_UUID, s_conf['studies'][META_STUDY_UUID]['assays']
        )
        self.assertTrue(
            s_conf['studies'][META_STUDY_UUID]['nodes'][0]['fields'][0][
                'editable'
            ]
        )  # Edited value should be restored
        d_conf = app_settings.get(
            APP_NAME, 'display_config_default', project=self.project
        )
        self.assertIn(
            META_ASSAY_UUID, d_conf['studies'][META_STUDY_UUID]['assays']
        )
        self.assertEqual(
            self._get_tl_events().first().get_status().status_type,
            self.timeline.TL_STATUS_OK,
        )

    def test_post_irods_rename_metadata_other_project(self):
        """Test POST with iRODS, renamed files and metadata from other project"""
        self._import_isa(SHEET_PATH_META)
        # NOTE: No UUID update
        s_conf_old = conf_api.get_sheet_config(self.inv)
        self.isatab.data['sheet_config'] = s_conf_old
        self.isatab.save()

        self.inv.delete()  # Replace current investigation
        self.inv = self.import_isa_from_file(
            SHEET_PATH_RENAME_META, self.project
        )
        self.assertEqual(
            self.inv.studies.first().file_name, 's_small2_renamed.txt'
        )
        self.inv.irods_status = True  # Enable iRODS colls
        self.inv.save()
        # NOTE: No UUID update here either, metadata UUIDs will not match

        with self.login(self.user):  # Restore original version
            response = self.client.post(self._get_url(self.isatab))

        self.assertEqual(response.status_code, 302)
        self.inv = Investigation.objects.get(project=self.project, active=True)
        self.assertEqual(
            self.inv.studies.first().file_name, 's_small2_renamed.txt'
        )  # Should still be the second sheet
        s_conf = app_settings.get(
            APP_NAME, 'sheet_config', project=self.project
        )
        self.assertEqual(s_conf, s_conf_old)  # Sheet config should be unchanged
        self.assertEqual(
            self._get_tl_events().first().get_status().status_type,
            self.timeline.TL_STATUS_FAILED,
        )


class TestSheetVersionUpdateView(SamplesheetsViewTestBase):
    """Tests for SheetVersionUpdateView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        self.url = reverse(
            'samplesheets:version_update',
            kwargs={'isatab': self.isatab.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionUpdateView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], self.isatab)

    def test_post(self):
        """Test POST"""
        self.assertEqual(ISATab.objects.count(), 1)
        self.assertIsNone(self.isatab.description)
        date_created = self.isatab.date_created
        with self.login(self.user):
            response = self.client.post(
                self.url, data={'description': SHEET_VERSION_DESC}
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ISATab.objects.count(), 1)
        self.isatab.refresh_from_db()
        self.assertEqual(self.isatab.description, SHEET_VERSION_DESC)
        # The date should not change
        self.assertEqual(self.isatab.date_created, date_created)


class TestSheetVersionDeleteView(SamplesheetsViewTestBase):
    """Tests for SheetVersionDeleteView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        self.url = reverse(
            'samplesheets:version_delete',
            kwargs={'isatab': self.isatab.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionDeleteView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['sheet_version'])

    def test_post(self):
        """Test POST"""
        self.assertEqual(ISATab.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ISATab.objects.count(), 0)


class TestSheetVersionDeleteBatchView(
    SampleSheetModelMixin, SamplesheetsViewTestBase
):
    """Tests for SheetVersionDeleteBatchView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        # Mock a second version
        self.isatab2 = self.make_isatab(
            project=self.project,
            data=self.isatab.data,
            investigation_uuid=self.investigation.sodar_uuid,
            user=self.user,
        )
        self.url = reverse(
            'samplesheets:version_delete_batch',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get_confirm(self):
        """Test SheetVersionDeleteBatchView GET with confirm view"""
        self.assertEqual(ISATab.objects.count(), 2)
        post_data = {
            'confirm': '1',
            'version_check': [
                str(self.isatab.sodar_uuid),
                str(self.isatab2.sodar_uuid),
            ],
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ISATab.objects.count(), 2)

    def test_post_delete(self):
        """Test POST to delete versions"""
        self.assertEqual(ISATab.objects.count(), 2)
        post_data = {
            'version_check': [
                str(self.isatab.sodar_uuid),
                str(self.isatab2.sodar_uuid),
            ]
        }
        with self.login(self.user):
            response = self.client.post(self.url, post_data)
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:versions',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(ISATab.objects.count(), 0)


class TestSheetVersionCompareView(SamplesheetsViewTestBase):
    """Tests for SheetVersionCompareView"""

    def setUp(self):
        super().setUp()
        self.import_isa_from_file(SHEET_PATH_SMALL2, self.project)
        with open(SHEET_PATH_SMALL2_ALT, 'rb') as file, self.login(self.user):
            post_data = {'file_upload': file}
            self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )
        self.isa1 = ISATab.objects.first()
        self.isa2 = ISATab.objects.last()
        self.isa2.data['studies']['s_small2.txt'] = self.isa2.data[
            'studies'
        ].pop('s_small2_alt.txt')
        self.isa2.data['assays']['a_small2.txt'] = self.isa2.data['assays'].pop(
            'a_small2_alt.txt'
        )
        self.isa2.save()
        self.url = reverse(
            'samplesheets:version_compare',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionCompareView GET"""
        with self.login(self.user):
            response = self.client.get(
                self.url + f'?source={self.isa1.sodar_uuid}'
                f'&target={self.isa2.sodar_uuid}'
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['source'], str(self.isa1.sodar_uuid))
        self.assertEqual(response.context['target'], str(self.isa2.sodar_uuid))


class TestSheetVersionCompareFileView(SamplesheetsViewTestBase):
    """Tests for SheetVersionCompareFileView"""

    def setUp(self):
        super().setUp()
        self.import_isa_from_file(SHEET_PATH_SMALL2, self.project)
        with open(SHEET_PATH_SMALL2_ALT, 'rb') as file, self.login(self.user):
            post_data = {'file_upload': file}
            self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                post_data,
            )
        self.isa1 = ISATab.objects.first()
        self.isa2 = ISATab.objects.last()
        self.isa2.data['studies']['s_small2.txt'] = self.isa2.data[
            'studies'
        ].pop('s_small2_alt.txt')
        self.isa2.data['assays']['a_small2.txt'] = self.isa2.data['assays'].pop(
            'a_small2_alt.txt'
        )
        self.isa2.save()
        self.url = reverse(
            'samplesheets:version_compare_file',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetVersionCompareFileView GET"""
        with self.login(self.user):
            response = self.client.get(
                self.url
                + '?source={}&target={}&filename={}&category={}'.format(
                    str(self.isa1.sodar_uuid),
                    str(self.isa2.sodar_uuid),
                    'a_small2.txt',
                    'assays',
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['source'], str(self.isa1.sodar_uuid))
        self.assertEqual(response.context['target'], str(self.isa2.sodar_uuid))
        self.assertEqual(response.context['filename'], 'a_small2.txt')
        self.assertEqual(response.context['category'], 'assays')


class TestIrodsDataRequestListView(
    IrodsDataRequestMixin, SamplesheetsViewTestBase
):
    """Tests for IrodsDataRequestListView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:irods_requests',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestListView GET"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        irods_req = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)
        context_obj = response.context['object_list'][0]
        self.assertEqual(context_obj, irods_req)
        self.assertEqual(
            context_obj.webdav_url, 'https://127.0.0.1' + IRODS_FILE_PATH
        )  # Ensure no extra slash is between host and iRODS path
        self.assertEqual(context_obj.is_collection, False)

    def test_get_as_contributor_by_superuser(self):
        """Test GET as contibutor with request created by superuser"""
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user,
        )
        with self.login(self.user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_get_as_contributor2_by_contributor(self):
        """Test GET as contributor2 with request created by contributor"""
        user_contributor2 = self.make_user('user_contributor2')
        self.make_assignment(
            self.project, user_contributor2, self.role_contributor
        )
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        with self.login(user_contributor2):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_list_empty(self):
        """Test GET for empty list of delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)


class SheetRemoteSyncTestBase(
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    SODARAPIViewTestMixin,
    SampleSheetIOMixin,
    LiveServerTestCase,
    TransactionTestCase,
):
    """Base class for sample sheet sync tests"""

    def setUp(self):
        super().setUp()
        self.init_roles()
        self.user = self.make_user('user')
        self.user.save()
        self.category = self.make_project(
            title='TestCategory',
            type=PROJECT_TYPE_CATEGORY,
            parent=None,
        )
        self.make_assignment(self.category, self.user, self.role_owner)
        self.project_source = self.make_project(
            title='TestProjectSource',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
        )
        self.owner_as_source = self.make_assignment(
            self.project_source, self.user, self.role_owner
        )
        self.project_target = self.make_project(
            title='TestProjectTarget',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
        )
        self.owner_as_target = self.make_assignment(
            self.project_target, self.user, self.role_owner
        )

        # Import investigation
        self.inv_source = self.import_isa_from_file(
            SHEET_PATH, self.project_source
        )
        # Allow sheet sync in project
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project_target
        )
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            self.live_server_url
            + reverse(
                'samplesheets:api_export_json',
                kwargs={'project': self.project_source.sodar_uuid},
            ),
            project=self.project_target,
        )
        app_settings.set(
            APP_NAME,
            'sheet_sync_token',
            self.get_token(self.user),
            project=self.project_target,
        )


class TestSheetRemoteSyncView(SheetRemoteSyncTestBase):
    """Tests for SheetRemoteSyncView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:sync',
            kwargs={'project': self.project_target.sodar_uuid},
        )

    def test_get(self):
        """Test SheetRemoteSyncView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
            )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            SYNC_SUCCESS_MSG,
        )
        # Check if investigation was created
        self.assertEqual(self.project_target.investigations.count(), 1)

    def test_get_disabled(self):
        """Test GET with sync disabled"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_enable',
            False,
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
            )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            SYNC_FAIL_DISABLED,
        )
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_invalid_token(self):
        """Test GET with invalid token"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_token',
            'WRONGTOKEN',
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            f'{SYNC_FAIL_PREFIX}: {SYNC_FAIL_STATUS_CODE}: 401',
        )
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_no_token(self):
        """Test GET with no token"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_token',
            '',
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            f'{SYNC_FAIL_PREFIX}: {SYNC_FAIL_UNSET_TOKEN}',
        )
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_no_url(self):
        """Test GET with no URL"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            '',
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            f'{SYNC_FAIL_PREFIX}: {SYNC_FAIL_UNSET_URL}',
        )

    def test_get_invalid_url(self):
        """Test GET with invalid URL"""
        url = 'https://alsdjfasdkjfasdgfli.com'
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            url,
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            f'{SYNC_FAIL_PREFIX}: {SYNC_FAIL_INVALID_URL}: {url}',
        )
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_get_no_connection(self):
        """Test GET with no connection via URL"""
        url = 'https://alsdjfasdkjfasdgfli.com' + reverse(
            'samplesheets:api_export_json',
            kwargs={'project': self.project_target.sodar_uuid},
        )
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            url,
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            f'{SYNC_FAIL_PREFIX}: {SYNC_FAIL_CONNECT}: {url}',
        )

    def test_get_no_sheet(self):
        """Test GET with non-existing sheets"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            self.live_server_url
            + reverse(
                'samplesheets:api_export_json',
                kwargs={'project': DUMMY_UUID},
            ),
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            f'{SYNC_FAIL_PREFIX}: {SYNC_FAIL_STATUS_CODE}: 404',
        )
