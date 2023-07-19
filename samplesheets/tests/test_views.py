"""Tests for UI views in the samplesheets app"""

import json
import os

from cubi_isa_templates import _TEMPLATES as ISA_TEMPLATES
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

# Sodarcache dependency
from sodarcache.models import JSONCacheItem

# Landingzones dependency
from landingzones.constants import ZONE_STATUS_ACTIVE
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin

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
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'
IRODS_FILE_PATH = '/sodarZone/path/test1.txt'
with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)
IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)


# TODO: Add testing for study table cache updates


class ViewTestBase(
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


class TestProjectSheetsView(ViewTestBase):
    """Tests for the project sheets view"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_render_no_sheets(self):
        """Test rendering the project sheets view without an investigation"""
        self.investigation.delete()
        self.investigation = None
        self.study = None

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['investigation'])
        self.assertNotIn('study', response.context)
        self.assertNotIn('tables', response.context)


class TestSheetImportView(SheetImportMixin, LandingZoneMixin, ViewTestBase):
    """Tests for the investigation import view"""

    def setUp(self):
        super().setUp()
        self.timeline = get_backend_api('timeline_backend')
        self.cache_backend = get_backend_api('sodar_cache')

    def test_render(self):
        """Test rendering the investigation import view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)

    def test_import(self):
        """Test posting an ISA-Tab zip file in the import form"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)

        with open(SHEET_PATH, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

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

    def test_replace(self):
        """Test replacing an existing investigation by posting"""
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
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

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

    def test_replace_config_keep(self):
        """Test keeping configs when replacing"""
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
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

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

    def test_replace_not_allowed(self):
        """Test replacing an iRODS-enabled investigation with missing data"""
        inv = self.import_isa_from_file(SHEET_PATH, self.project)
        inv.irods_status = True
        inv.save()
        uuid = inv.sodar_uuid
        self.assertEqual(Investigation.objects.count(), 1)

        with open(SHEET_PATH_MINIMAL, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        new_inv = Investigation.objects.first()
        self.assertEqual(uuid, new_inv.sodar_uuid)  # Should not have changed

    def test_replace_zone(self):
        """Test replacing with existing landing zone"""
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
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

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

    def test_replace_study_cache(self):
        """Test replacing with existing study table cache"""
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
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, {})
        self.assertEqual(JSONCacheItem.objects.count(), 1)

    def test_replace_study_cache_new_sheet(self):
        """Test replacing with study table cache and different sheet"""
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
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertIsNone(cache_item)
        self.assertEqual(JSONCacheItem.objects.count(), 0)

    def test_import_critical_warnings(self):
        """Test posting an ISA-Tab which raises critical warnings in altamISA"""
        self.assertEqual(Investigation.objects.count(), 0)
        with open(SHEET_PATH_CRITICAL, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 0)
        # Assert timeline event
        tl_event = self.timeline.get_project_events(self.project).order_by(
            '-pk'
        )[0]
        tl_status = tl_event.get_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    @override_settings(SHEETS_ALLOW_CRITICAL=True)
    def test_import_critical_warnings_allowed(self):
        """Test posting an ISA-Tab with critical warnings allowed"""
        self.assertEqual(Investigation.objects.count(), 0)

        with open(SHEET_PATH_CRITICAL, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        # Assert timeline event
        tl_event = self.timeline.get_project_events(self.project).order_by(
            '-pk'
        )[0]
        tl_status = tl_event.get_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    def test_import_multiple(self):
        """Test posting an ISA-Tab as multiple files"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)

        zf = ZipFile(os.fsdecode(SHEET_PATH))
        with self.login(self.user):
            values = {
                'file_upload': [
                    zf.open(f.filename) for f in zf.filelist if f.file_size > 0
                ]
            }
            response = self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)
        self.assertListEqual(ISATab.objects.first().tags, ['IMPORT'])

    def test_import_multiple_no_study(self):
        """Test posting an ISA-Tab as multiple files without required study"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)

        zf = ZipFile(os.fsdecode(SHEET_PATH))
        with self.login(self.user):
            values = {
                'file_upload': [
                    zf.open(f.filename)
                    for f in zf.filelist
                    if f.file_size > 0
                    and not f.filename.split('/')[-1].startswith('s_')
                ]
            }
            response = self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Investigation.objects.count(), 0)

    def test_import_multiple_no_assay(self):
        """Test posting an ISA-Tab as multiple files without required assay"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)

        zf = ZipFile(os.fsdecode(SHEET_PATH))
        with self.login(self.user):
            values = {
                'file_upload': [
                    zf.open(f.filename)
                    for f in zf.filelist
                    if f.file_size > 0
                    and not f.filename.split('/')[-1].startswith('a_')
                ]
            }
            response = self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 0)

    def test_import_empty_assay(self):
        """Test posting an ISA-Tab with an empty assay table (should fail)"""
        self.assertEqual(Investigation.objects.count(), 0)
        with open(SHEET_PATH_EMPTY_ASSAY, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 0)

    def test_import_no_plugin_assay(self):
        """Test posting an ISA-Tab with an assay without plugin"""
        self.assertEqual(Investigation.objects.count(), 0)
        with open(SHEET_PATH_NO_PLUGIN_ASSAY, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[1].message,
            self.get_assay_plugin_warning(Assay.objects.all().first()),
        )


class TestSheetTemplateSelectView(ViewTestBase):
    """Tests for SheetTemplateSelectView"""

    def test_render(self):
        """Test rendering the template select view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:template_select',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context['sheet_templates']),
            len(settings.SHEETS_ENABLED_TEMPLATES),
        )

    def test_render_with_sheets(self):
        """Test rendering with sheets in project (should fail)"""
        self.import_isa_from_file(SHEET_PATH, self.project)
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:template_select',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )


class TestSheetTemplateCreateFormView(ViewTestBase):
    """Tests for SheetTemplateCreateFormView"""

    def _get_post_data(self, tpl_name):
        """
        Return POST data for creation from template

        :param tpl_name: Template name (string)
        :return: Dict
        """
        templates = {
            t.name: t
            for t in ISA_TEMPLATES
            if t.name in settings.SHEETS_ENABLED_TEMPLATES
        }
        sheet_tpl = templates[tpl_name]
        ret = {TPL_DIR_FIELD: clean_sheet_dir_name(self.project.title)}
        for k, v in sheet_tpl.configuration.items():
            if isinstance(v, str):
                if '{{' in v or '{%' in v:
                    continue
                ret[k] = v
            elif isinstance(v, list):
                ret[k] = v[0]
            elif isinstance(v, dict):
                ret[k] = json.dumps(v)
        return ret

    def test_render_batch(self):
        """Test rendering the view with supported templates"""
        for t in settings.SHEETS_ENABLED_TEMPLATES:
            with self.login(self.user):
                response = self.client.get(
                    reverse(
                        'samplesheets:template_create',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    data={'sheet_tpl': t},
                )
            self.assertEqual(response.status_code, 200, msg=t)

    def test_render_invalid_template(self):
        """Test rendering the view with invalid template (should redirect)"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:template_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
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

    def test_render_no_template(self):
        """Test rendering the view with out template name (should redirect)"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:template_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'sheet_tpl': ''},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                'samplesheets:template_select',
                kwargs={'project': self.project.sodar_uuid},
            ),
        )

    def test_post_batch(self):
        """Test POST request with supported templates and default values"""

        for t in settings.SHEETS_ENABLED_TEMPLATES:
            self.assertIsNone(self.project.investigations.first())
            post_data = self._get_post_data(t)
            with self.login(self.user):
                response = self.client.post(
                    reverse(
                        'samplesheets:template_create',
                        kwargs={'project': self.project.sodar_uuid},
                    )
                    + '?sheet_tpl='
                    + t,
                    data=post_data,
                )
            self.assertEqual(response.status_code, 302, msg=t)
            self.assertIsNotNone(self.project.investigations.first(), msg=t)
            self.project.investigations.first().delete()

    def test_post_multiple(self):
        """Test multiple requests to add multiple sample sheets (should fail)"""
        tpl_name = settings.SHEETS_ENABLED_TEMPLATES[0]
        url = reverse(
            'samplesheets:template_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        url += '?sheet_tpl=' + tpl_name
        post_data = self._get_post_data(tpl_name)
        with self.login(self.user):
            response = self.client.post(url, data=post_data)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.project.investigations.count(), 1)
            response = self.client.post(url, data=post_data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.project.investigations.count(), 1)


class TestSheetExcelExportView(ViewTestBase):
    """Tests for the sample sheet Excel export view"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.timeline = get_backend_api('timeline_backend')

    def test_render_study(self):
        """Test rendering the Excel file for a study table"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_excel',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        # Assert data in timeline event
        tl_event = self.timeline.get_project_events(
            self.project, classified=True
        ).order_by('-pk')[0]
        self.assertEqual(tl_event.event_name, 'sheet_export_excel')

    def test_render_assay(self):
        """Test rendering the Excel file for a assay table"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_excel',
                    kwargs={'assay': self.assay.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        # Assert data in timeline event
        tl_event = self.timeline.get_project_events(
            self.project, classified=True
        ).order_by('-pk')[0]
        self.assertEqual(tl_event.event_name, 'sheet_export_excel')


class TestSheetISAExportView(ViewTestBase):
    """Tests for the investigation ISA-Tab export view"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.timeline = get_backend_api('timeline_backend')

    def test_get(self):
        """Test requesting a file from the ISA-Tab export view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_isa',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename="{}"'.format(self.investigation.archive_name),
        )
        # Assert data in timeline event
        tl_event = self.timeline.get_project_events(
            self.project, classified=True
        ).order_by('-pk')[0]
        tl_status = tl_event.get_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    def test_get_no_investigation(self):
        """Test requesting an ISA-Tab export with no investigation provided"""
        self.investigation.delete()
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_isa',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 302)

    def test_get_version(self):
        """Test requesting export of an ISA-Tab version"""
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


class TestSheetDeleteView(ViewTestBase):
    """Tests for the investigation delete view"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        # Set up helpers
        self.cache_backend = get_backend_api('sodar_cache')

    def test_render(self):
        """Test rendering the project sheets view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['irods_file_count'], 0)
        self.assertEqual(response.context['can_delete_sheets'], True)

    def test_delete(self):
        """Test deleting the project sample sheets"""
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
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'delete_host_confirm': 'testserver'},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.url,
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

    def test_delete_invalid_host(self):
        """Test deleting with an invalid host name supplied in form"""
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'delete_host_confirm': ''},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.url,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 1)

    def test_delete_study_cache(self):
        """Test deleting with cached study tables"""
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
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'delete_host_confirm': 'testserver'},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.url,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertIsNone(cache_item)
        self.assertEqual(JSONCacheItem.objects.count(), 0)


class TestSheetVersionListView(ViewTestBase):
    """Tests for the sample sheet version list view"""

    def test_render(self):
        """Test rendering the sheet version list view"""
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:versions',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

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

    def test_render_no_sheets(self):
        """Test rendering version list view with no versions available"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:versions',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 0)
        self.assertIsNone(response.context['current_version'])


class TestSheetVersionRestoreView(ViewTestBase):
    """Tests for the sample sheet version restore view"""

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

    def test_render(self):
        """Test rendering the sheet version restore view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:version_restore',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['sheet_version'])

    def test_restore(self):
        """Test restoring sheet version"""
        sheet_io = SampleSheetIO()
        isatab_new = sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.investigation.sodar_uuid,
            isa_data=sheet_io.export_isa(self.investigation),
        )
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)

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

    def test_restore_study_cache(self):
        """Test restoring sheet version with cached study table"""
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


class TestSheetVersionUpdateView(ViewTestBase):
    """Tests for the sample sheet version update view"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )

    def test_render(self):
        """Test rendering the update view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:version_update',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.context['object'], self.isatab)

    def test_update(self):
        """Test updating the sheet version"""
        self.assertEqual(ISATab.objects.count(), 1)
        self.assertIsNone(self.isatab.description)
        date_created = self.isatab.date_created
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:version_update',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                ),
                data={'description': SHEET_VERSION_DESC},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ISATab.objects.count(), 1)
        self.isatab.refresh_from_db()
        self.assertEqual(self.isatab.description, SHEET_VERSION_DESC)
        # The date should not change
        self.assertEqual(self.isatab.date_created, date_created)


class TestSheetVersionDeleteView(ViewTestBase):
    """Tests for the sample sheet version delete view"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )

    def test_render(self):
        """Test rendering the sheet version delete view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:version_delete',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['sheet_version'])

    def test_post(self):
        """Test issuing a POST request for the sheet version delete view"""
        self.assertEqual(ISATab.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:version_delete',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ISATab.objects.count(), 0)


class TestSheetVersionDeleteBatchView(SampleSheetModelMixin, ViewTestBase):
    """Tests for the sample sheet version batch delete view"""

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

    def test_render_confirm(self):
        """Test rendering the confirm view"""
        self.assertEqual(ISATab.objects.count(), 2)
        values = {
            'confirm': '1',
            'version_check': [
                str(self.isatab.sodar_uuid),
                str(self.isatab2.sodar_uuid),
            ],
        }
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:version_delete_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ISATab.objects.count(), 2)

    def test_delete(self):
        """Test version deletion"""
        self.assertEqual(ISATab.objects.count(), 2)
        values = {
            'version_check': [
                str(self.isatab.sodar_uuid),
                str(self.isatab2.sodar_uuid),
            ]
        }
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:version_delete_batch',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )
            self.assertRedirects(
                response,
                reverse(
                    'samplesheets:versions',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(ISATab.objects.count(), 0)


class TestProjectSearchResultsView(ViewTestBase):
    """Tests for ProjectSearchResultsView view with sample sheet input"""

    def _get_items(self, response):
        return response.context['app_results'][0]['results']['materials'][
            'items'
        ]

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


class TestSheetVersionCompareView(ViewTestBase):
    """Tests for the SheetVersionCompareView"""

    def setUp(self):
        super().setUp()
        self.import_isa_from_file(SHEET_PATH_SMALL2, self.project)
        with open(SHEET_PATH_SMALL2_ALT, 'rb') as file, self.login(self.user):
            values = {'file_upload': file}
            self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
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

    def test_render(self):
        """Test rendering the sheet version compare view"""
        with self.login(self.user):
            response = self.client.get(
                '{}?source={}&target={}'.format(
                    reverse(
                        'samplesheets:version_compare',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    str(self.isa1.sodar_uuid),
                    str(self.isa2.sodar_uuid),
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['source'], str(self.isa1.sodar_uuid))
        self.assertEqual(response.context['target'], str(self.isa2.sodar_uuid))

    def test_render_no_permission(self):
        """Test rendering the sheet version compare view without permission"""
        with self.login(self.user_no_roles):
            response = self.client.get(
                '{}?source={}&target={}'.format(
                    reverse(
                        'samplesheets:version_compare',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    str(self.isa1.sodar_uuid),
                    str(self.isa2.sodar_uuid),
                ),
                follow=True,
            )
        self.assertRedirects(response, reverse('home'))


class TestSheetVersionCompareFileView(ViewTestBase):
    """Tests for the SheetVersionCompareFileView"""

    def setUp(self):
        super().setUp()
        self.import_isa_from_file(SHEET_PATH_SMALL2, self.project)
        with open(SHEET_PATH_SMALL2_ALT, 'rb') as file, self.login(self.user):
            values = {'file_upload': file}
            self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
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

    def test_render(self):
        """Test rendering the sheet version compare view"""
        with self.login(self.user):
            response = self.client.get(
                '{}?source={}&target={}&filename={}&category={}'.format(
                    reverse(
                        'samplesheets:version_compare_file',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
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

    def test_render_no_permission(self):
        """Test rendering the sheet version compare view without permission"""
        with self.login(self.user_no_roles):
            response = self.client.get(
                '{}?source={}&target={}&filename={}&category={}'.format(
                    reverse(
                        'samplesheets:version_compare_file',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    str(self.isa1.sodar_uuid),
                    str(self.isa2.sodar_uuid),
                    'a_small2.txt',
                    'assays',
                ),
                follow=True,
            )
        self.assertRedirects(response, reverse('home'))


class TestIrodsDataRequestListView(IrodsDataRequestMixin, ViewTestBase):
    """Tests for IrodsDataRequestListView"""

    def test_list(self):
        """Test GET request for listing delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user,
        )
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)
        self.assertEqual(response.context['object_list'][0], request)

    def test_list_as_contributor_by_superuser(self):
        """Test GET as contibutor with request created by superuser"""
        self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user,
        )
        with self.login(self.user_contributor):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_list_as_contributor2_by_contributor(self):
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
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_list_empty(self):
        """Test GET request for empty list of delete requests"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:irods_requests',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)


class TestSheetRemoteSyncBase(
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


class TestSheetRemoteSyncView(TestSheetRemoteSyncBase):
    """Tests for SheetRemoteSyncView"""

    def test_sync(self):
        """Test sync sheets successfully"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
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

    def test_sync_disabled(self):
        """Test sync sheets with sync disabled"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_enable',
            False,
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
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

    def test_sync_invalid_token(self):
        """Test sync sheets with invalid token"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_token',
            'WRONGTOKEN',
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            '{}: {}: 401'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_STATUS_CODE),
        )
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_no_token(self):
        """Test sync sheets with no token"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_token',
            '',
            project=self.project_target,
        )
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            '{}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_UNSET_TOKEN),
        )
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_no_url(self):
        """Test sync sheets with no URL"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            '',
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            '{}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_UNSET_URL),
        )

    def test_sync_invalid_url(self):
        """Test sync sheets with invalid URL"""
        url = 'https://alsdjfasdkjfasdgfli.com'
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            url,
            project=self.project_target,
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            '{}: {}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_INVALID_URL, url),
        )
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_no_connection(self):
        """Test sync sheets with no connection via URL"""
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
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            '{}: {}: {}'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_CONNECT, url),
        )

    def test_sync_no_sheet(self):
        """Test sync with non-existing sheets"""
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
            response = self.client.get(
                reverse(
                    'samplesheets:sync',
                    kwargs={'project': self.project_target.sodar_uuid},
                ),
                follow=True,
            )
        self.assertRedirects(
            response,
            reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project_target.sodar_uuid},
            ),
        )
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            '{}: {}: 404'.format(SYNC_FAIL_PREFIX, SYNC_FAIL_STATUS_CODE),
        )
