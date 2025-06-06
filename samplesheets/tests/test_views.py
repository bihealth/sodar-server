"""Tests for UI views in the samplesheets app"""

import json
import os

from cubi_isa_templates import IsaTabTemplate, _TEMPLATES as ISA_TEMPLATES
from urllib.parse import urlencode
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
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)
from projectroles.tests.test_views_api import SODARAPIViewTestMixin
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
)


app_settings = AppSettingAPI()
conf_api = SheetConfigAPI()
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
SHEET_NAME = 'i_small.zip'
SHEET_PATH = SHEET_DIR + SHEET_NAME
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'
SHEET_NAME_SMALL2 = 'i_small2.zip'
SHEET_PATH_SMALL2 = SHEET_DIR + SHEET_NAME_SMALL2
SHEET_NAME_SMALL2_ALT = 'i_small2_alt.zip'
SHEET_PATH_SMALL2_ALT = SHEET_DIR + SHEET_NAME_SMALL2_ALT
SHEET_NAME_MINIMAL = 'i_minimal.zip'
SHEET_PATH_MINIMAL = SHEET_DIR + SHEET_NAME_MINIMAL
SHEET_NAME_CRITICAL = 'BII-I-1_critical.zip'
SHEET_PATH_CRITICAL = SHEET_DIR_SPECIAL + SHEET_NAME_CRITICAL
SHEET_NAME_EMPTY_ASSAY = 'i_small_assay_empty.zip'
SHEET_PATH_EMPTY_ASSAY = SHEET_DIR_SPECIAL + SHEET_NAME_EMPTY_ASSAY
SHEET_NAME_NO_PLUGIN_ASSAY = 'i_small_assay_no_plugin.zip'
SHEET_PATH_NO_PLUGIN_ASSAY = SHEET_DIR_SPECIAL + SHEET_NAME_NO_PLUGIN_ASSAY
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


# TODO: Add testing for study table cache updates


# Base Classes and Mixins ------------------------------------------------------


class SheetTemplateCreateMixin:
    """Sheet template creation helpers"""

    def get_tpl_post_data(self, sheet_tpl):
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

    def make_sheets_from_cubi_tpl(self, sheet_tpl):
        """
        Create investigation from CUBI templates by posting to the template
        create view.

        :param sheet_tpl: IsaTabTemplate object
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
        self.user_owner = self.make_user('owner')
        self.user_delegate = self.make_user('delegate')
        self.user_contributor = self.make_user('contributor')
        self.user_guest = self.make_user('guest')
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


class TestSheetImportView(
    SheetImportMixin, LandingZoneMixin, SamplesheetsViewTestBase
):
    """Tests for SheetImportView"""

    def setUp(self):
        super().setUp()
        self.timeline = get_backend_api('timeline_backend')
        self.cache_backend = get_backend_api('sodar_cache')
        self.url = reverse(
            'samplesheets:import',
            kwargs={'project': self.project.sodar_uuid},
        )

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
        # Assert study render table cache
        # NOTE: Cache item not created in this case
        inv = Investigation.objects.first()
        cache_name = STUDY_TABLE_CACHE_ITEM.format(
            study=inv.studies.first().sodar_uuid
        )
        self.assertIsNone(
            self.cache_backend.get_cache_item(
                APP_NAME, cache_name, self.project
            )
        )

    def test_post_replace(self):
        """Test POST to replace replacing existing investigation"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        uuid = inv.sodar_uuid
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

        with open(SHEET_PATH_SMALL2, 'rb') as file:
            post_data = {'file_upload': file}
            with self.login(self.user):
                response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(uuid, Investigation.objects.first().sodar_uuid)
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
        app_settings.set(
            'samplesheets',
            'display_config',
            {},
            project=self.project,
            user=self.user,
        )
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
        self.timeline = get_backend_api('timeline_backend')

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
        self.timeline = get_backend_api('timeline_backend')
        self.url = reverse(
            'samplesheets:export_isa',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetISAExportView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename="{}"'.format(self.investigation.archive_name),
        )

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
            'attachment; filename="{}"'.format(filename),
        )


class TestSheetDeleteView(SamplesheetsViewTestBase):
    """Tests for SheetDeleteView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        # Set up helpers
        self.cache_backend = get_backend_api('sodar_cache')
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

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        # Set up helpers
        self.cache_backend = get_backend_api('sodar_cache')
        self.timeline = get_backend_api('timeline_backend')

    def test_get(self):
        """Test SheetVersionRestoreView GET"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:version_restore',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['sheet_version'])

    def test_post(self):
        """Test POST"""
        sheet_io = SampleSheetIO()
        isatab_new = sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.investigation.sodar_uuid,
            isa_data=sheet_io.export_isa(self.investigation),
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='sheet_restore').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:version_restore',
                    kwargs={'isatab': isatab_new.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 302)
        isatab_latest = ISATab.objects.all().order_by('-date_created').first()
        self.assertNotEqual(
            isatab_latest.date_created, self.isatab.date_created
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='sheet_restore').count(), 1
        )
        e = TimelineEvent.objects.filter(event_name='sheet_restore').first()
        self.assertEqual(e.get_status().status_type, self.timeline.TL_STATUS_OK)

    def test_post_study_cache(self):
        """Test POST with cached study table"""
        sheet_io = SampleSheetIO()
        isatab_new = sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.investigation.sodar_uuid,
            isa_data=sheet_io.export_isa(self.investigation),
        )

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
                reverse(
                    'samplesheets:version_restore',
                    kwargs={'isatab': isatab_new.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 302)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, {})
        self.assertEqual(JSONCacheItem.objects.count(), 1)


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
        self.assertEquals(response.context['object'], self.isatab)

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


class TestProjectSearchResultsView(SamplesheetsViewTestBase):
    """Tests for ProjectSearchResultsView view with sample sheet input"""

    def _get_items(self, response):
        return response.context['app_results'][0]['results']['materials'].items

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.source = self.study.materials.filter(item_type='SOURCE').first()
        self.sample = (
            self.study.materials.filter(item_type='SAMPLE')
            .exclude(name='')
            .first()
        )

    def test_search_source(self):
        """Test simple search with source"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': self.source.name})
            )
        self.assertEqual(response.status_code, 200)
        items = self._get_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], self.source.name)

    def test_search_source_type_source(self):
        """Test simple search with source and source type"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': self.source.name + ' type:source'})
            )
        self.assertEqual(response.status_code, 200)
        items = self._get_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], self.source.name)

    def test_search_source_type_sample(self):
        """Test simple search with source and sample type (should fail)"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': self.source.name + ' type:sample'})
            )
        self.assertEqual(response.status_code, 200)
        items = self._get_items(response)
        self.assertEqual(len(items), 0)

    def test_search_sample(self):
        """Test simple search with sample"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': self.sample.name})
            )
        self.assertEqual(response.status_code, 200)
        items = self._get_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], self.sample.name)

    def test_search_sample_type_sample(self):
        """Test simple search with sample and sample type"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': self.sample.name + ' type:sample'})
            )
        self.assertEqual(response.status_code, 200)
        items = self._get_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], self.sample.name)

    def test_search_sample_type_source(self):
        """Test simple search with sample and source type (should fail)"""
        with self.login(self.user):
            response = self.client.get(
                reverse('projectroles:search')
                + '?'
                + urlencode({'s': self.sample.name + ' type:source'})
            )
        self.assertEqual(response.status_code, 200)
        items = self._get_items(response)
        self.assertEqual(len(items), 0)

    def test_search_multi(self):
        """Test simple search with multiple terms"""
        post_data = {'m': self.source.name + '\r\n' + self.sample.name}
        with self.login(self.user):
            response = self.client.post(
                reverse('projectroles:search'), data=post_data
            )
        self.assertEqual(response.status_code, 200)
        items = self._get_items(response)
        self.assertEqual(len(items), 2)


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
                self.url
                + '?source={}&target={}'.format(
                    str(self.isa1.sodar_uuid),
                    str(self.isa2.sodar_uuid),
                )
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
                self.url + '?source={}&target={}&filename={}'
                '&category={}'.format(
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
        irods_request = self.make_irods_request(
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
        self.assertEqual(context_obj, irods_request)
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
        """Test GET request for empty list of delete requests"""
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
            '{}: {}: 401'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_STATUS_CODE),
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
            '{}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_UNSET_TOKEN),
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
            '{}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_UNSET_URL),
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
            '{}: {}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_INVALID_URL, url),
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
            '{}: {}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_CONNECT, url),
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
            '{}: {}: 404'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_STATUS_CODE),
        )
