"""Tests for REST API views in the samplesheets app"""

import json
import os

from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import RemoteSiteMixin, RemoteProjectMixin
from projectroles.tests.test_views_api import APIViewTestBase

# Sodarcache dependency
from sodarcache.models import JSONCacheItem

# Timeline dependency
from timeline.models import TimelineEvent

# Landingzones dependency
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin

from samplesheets.io import SampleSheetIO
from samplesheets.models import (
    Investigation,
    Assay,
    GenericMaterial,
    ISATab,
    IrodsDataRequest,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACCEPTED,
    IRODS_REQUEST_STATUS_ACTIVE,
    IRODS_REQUEST_STATUS_FAILED,
    IrodsAccessTicket,
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
    IrodsDataRequestMixin,
    IrodsAccessTicketMixin,
)
from samplesheets.tests.test_sheet_config import SheetConfigMixin
from samplesheets.tests.test_views import (
    SamplesheetsViewTestBase,
    REMOTE_SITE_NAME,
    REMOTE_SITE_URL,
    REMOTE_SITE_DESC,
    REMOTE_SITE_SECRET,
)
from samplesheets.tests.test_views_taskflow import (
    TICKET_LABEL,
    TICKET_STR,
    IrodsAccessTicketViewTestMixin,
)
from samplesheets.views import SheetImportMixin
from samplesheets.views_api import (
    SAMPLESHEETS_API_MEDIA_TYPE,
    SAMPLESHEETS_API_DEFAULT_VERSION,
)


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
IRODS_FILE_NAME = 'test1.txt'
IRODS_FILE_MD5 = '0b26e313ed4a7ca6904b0e9369e5b957'
TICKET_PATH = '/test/path'


# TODO: Add testing for study table cache updates


class SampleSheetAPIViewTestBase(SampleSheetIOMixin, APIViewTestBase):
    """Base view for samplesheets API views tests"""

    media_type = SAMPLESHEETS_API_MEDIA_TYPE
    api_version = SAMPLESHEETS_API_DEFAULT_VERSION


class IrodsAccessTicketAPITestBase(
    IrodsAccessTicketMixin,
    IrodsAccessTicketViewTestMixin,
    SampleSheetAPIViewTestBase,
):
    """Base view for iRODS access ticket requests API tests"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Init contributor user
        self.user_contributor = self.make_user('user_contributor')
        self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )
        self.token_contrib = self.get_token(self.user_contributor)
        # Get appalerts API and model
        self.app_alerts = get_backend_api('appalerts_backend')
        self.app_alert_model = self.app_alerts.get_model()


class TestInvestigationRetrieveAPIView(SampleSheetAPIViewTestBase):
    """Tests for InvestigationRetrieveAPIView"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test InvestigationRetrieveAPIView GET"""
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
    SheetImportMixin,
    SheetConfigMixin,
    LandingZoneMixin,
    SampleSheetAPIViewTestBase,
):
    """Tests for SheetImportAPIView"""

    def setUp(self):
        super().setUp()
        self.cache_backend = get_backend_api('sodar_cache')
        self.url = reverse(
            'samplesheets:api_import',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post_zip(self):
        """Test SheetImportAPIView with zip archive"""
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)
        with open(SHEET_PATH, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

    def test_post_tsv(self):
        """Test POST with ISA-Tab tsv files"""
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)

        tsv_file_i = open(SHEET_TSV_DIR + 'i_small2.txt', 'r')
        tsv_file_s = open(SHEET_TSV_DIR + 's_small2.txt', 'r')
        tsv_file_a = open(SHEET_TSV_DIR + 'a_small2.txt', 'r')
        post_data = {
            'file_investigation': tsv_file_i,
            'file_study': tsv_file_s,
            'file_assay': tsv_file_a,
        }
        response = self.request_knox(
            self.url, method='POST', format='multipart', data=post_data
        )
        tsv_file_i.close()
        tsv_file_s.close()
        tsv_file_a.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

    def test_post_replace(self):
        """Test POST to replace sheets"""
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

        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
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

    def test_post_replace_display_config_keep(self):
        """Test POST to replace and ensure user display configs are kept"""
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

        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
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

    def test_post_replace_display_config_delete(self):
        """Test POST to replace and ensure user display configs are deleted"""
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

        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
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

    def test_post_replace_alt_sheet(self):
        """Test POST to replace with alternative sheet and irods_status=False"""
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
        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)

    def test_post_replace_alt_sheet_irods(self):
        """Test POST to replace with alternative sheet and iRODS (should fail)"""
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        investigation.irods_status = True  # fake irods status
        investigation.save()
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)
        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 1)

    def test_post_replace_zone(self):
        """Test POST to replace with exising landing zone"""
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

        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
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

    def test_post_replace_study_cache(self):
        """Test POST to replace with existing study table cache"""
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

        with open(SHEET_PATH_EDITED, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertEqual(cache_item.data, {})
        self.assertEqual(JSONCacheItem.objects.count(), 1)

    def test_post_replace_study_cache_new_sheet(self):
        """Test POST to replace with study table cache and different sheet"""
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

        with open(SHEET_PATH_ALT, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 2)
        cache_item = self.cache_backend.get_cache_item(*cache_args)
        self.assertIsNone(cache_item)
        self.assertEqual(JSONCacheItem.objects.count(), 0)

    def test_post_import_no_plugin_assay(self):
        """Test POST with assay without plugin"""
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        with open(SHEET_PATH_NO_PLUGIN_ASSAY, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
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
        """Test POST with sheet sync enabled (should fail)"""
        app_settings.set(
            APP_NAME, 'sheet_sync_enable', True, project=self.project
        )
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)
        with open(SHEET_PATH, 'rb') as file:
            post_data = {'file': file}
            response = self.request_knox(
                self.url, method='POST', format='multipart', data=post_data
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Investigation.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(ISATab.objects.filter(project=self.project).count(), 0)


class TestSheetISAExportAPIView(SampleSheetAPIViewTestBase):
    """Tests for SheetISAExportAPIView"""

    def test_get_zip(self):
        """Test SheetISAExportAPIView GET with Zip export"""
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
        """Test GET with no imported investigation"""
        url = reverse(
            'samplesheets:api_export_zip',
            kwargs={'project': self.project.sodar_uuid},
        )
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 404)

    def test_get_json(self):
        """Test GET with JSON epxort"""
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


class TestIrodsAccessTicketRetrieveAPIView(IrodsAccessTicketAPITestBase):
    """Tests for IrodsAccessTicketRetrieveAPIView"""

    def setUp(self):
        super().setUp()
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path=TICKET_PATH,
            label=TICKET_LABEL,
            user=self.user,
            date_expires=None,
        )
        self.url = reverse(
            'samplesheets:api_irods_ticket_retrieve',
            kwargs={'irodsaccessticket': self.ticket.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsAccessTicketRetrieveAPIView GET"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user_contributor):
            response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.ticket.label,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,
            'date_created': local_date_created.isoformat(),
            'date_expires': self.ticket.date_expires,
            'allowed_hosts': [],
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(json.loads(response.content), expected)

    def test_get_hosts(self):
        """Test GET with allowed hosts"""
        self.ticket.allowed_hosts = '127.0.0.1,192.168.0.1'
        self.ticket.save()
        with self.login(self.user_contributor):
            response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.ticket.label,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,
            'date_created': local_date_created.isoformat(),
            'date_expires': self.ticket.date_expires,
            'allowed_hosts': ['127.0.0.1', '192.168.0.1'],
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(json.loads(response.content), expected)

    def test_get_v1_0(self):
        """Test GET with API version 1.0"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user_contributor):
            response = self.request_knox(self.url, version='1.0')
        self.assertEqual(response.status_code, 200)
        local_date_created = self.ticket.date_created.astimezone(
            timezone.get_current_timezone()
        )
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.ticket.label,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,
            'date_created': local_date_created.isoformat(),
            'date_expires': self.ticket.date_expires,
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }  # No allowed_hosts field
        self.assertEqual(json.loads(response.content), expected)


class TestIrodsAccessTicketListAPIView(IrodsAccessTicketAPITestBase):
    """Tests for IrodsAccessListAPIView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:api_irods_ticket_list',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path='/test/path',
            label=TICKET_LABEL,
            user=self.user,
            date_expires=None,
        )

    def test_get(self):
        """Test IrodsAccessTicketListAPIView GET"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user_contributor):
            response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.ticket.label,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,
            'date_created': self.get_drf_datetime(self.ticket.date_created),
            'date_expires': self.ticket.date_expires,
            'allowed_hosts': [],
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(json.loads(response.content), [expected])

    def test_get_active(self):
        """Test GET with active = True"""
        self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=TICKET_STR,
            path='/test/path2',
            label=TICKET_LABEL,
            user=self.user,
            date_expires=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(IrodsAccessTicket.objects.count(), 2)
        with self.login(self.user_contributor):
            response = self.request_knox(self.url + '?active=1')
        self.assertEqual(response.status_code, 200)
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.ticket.label,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,
            'date_created': self.get_drf_datetime(self.ticket.date_created),
            'date_expires': self.ticket.date_expires,
            'allowed_hosts': [],
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }
        self.assertEqual(json.loads(response.content), [expected])

    def test_get_pagination(self):
        """Test GET with pagination"""
        url = self.url + '?page=1'
        with self.login(self.user_contributor):
            response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        expected = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'sodar_uuid': str(self.ticket.sodar_uuid),
                    'label': self.ticket.label,
                    'ticket': self.ticket.ticket,
                    'study': str(self.study.sodar_uuid),
                    'assay': str(self.assay.sodar_uuid),
                    'path': self.ticket.path,
                    'date_created': self.get_drf_datetime(
                        self.ticket.date_created
                    ),
                    'date_expires': self.ticket.date_expires,
                    'allowed_hosts': [],
                    'user': str(self.user.sodar_uuid),
                    'is_active': self.ticket.is_active(),
                }
            ],
        }
        self.assertEqual(json.loads(response.content), expected)

    def test_get_v1_0(self):
        """Test GET with API version 1.0"""
        self.assertEqual(IrodsAccessTicket.objects.count(), 1)
        with self.login(self.user_contributor):
            response = self.request_knox(self.url, version='1.0')
        self.assertEqual(response.status_code, 200)
        expected = {
            'sodar_uuid': str(self.ticket.sodar_uuid),
            'label': self.ticket.label,
            'ticket': self.ticket.ticket,
            'study': str(self.study.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'path': self.ticket.path,
            'date_created': self.get_drf_datetime(self.ticket.date_created),
            'date_expires': self.ticket.date_expires,
            'user': str(self.user.sodar_uuid),
            'is_active': self.ticket.is_active(),
        }  # No allowed_hosts
        self.assertEqual(json.loads(response.content), [expected])


class TestIrodsDataRequestRetrieveAPIView(
    IrodsDataRequestMixin, SampleSheetAPIViewTestBase
):
    """Tests for IrodsDataRequestRetrieveAPIView"""

    def setUp(self):
        super().setUp()
        self.user_contributor = self.make_user('user_contributor')
        self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up iRODS backend and paths
        self.irods_backend = get_backend_api('omics_irods')
        self.assay_path = self.irods_backend.get_path(self.assay)
        # Make request
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=os.path.join(self.assay_path, IRODS_FILE_NAME),
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_retrieve',
            kwargs={'irodsdatarequest': self.request.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestRetrieveAPIView GET"""
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        expected = {
            'project': str(self.project.sodar_uuid),
            'action': IRODS_REQUEST_ACTION_DELETE,
            'path': self.request.path,
            'target_path': '',
            'user': str(self.user_contributor.sodar_uuid),
            'status': IRODS_REQUEST_STATUS_ACTIVE,
            'status_info': '',
            'description': self.request.description,
            'date_created': self.get_drf_datetime(self.request.date_created),
            'sodar_uuid': str(self.request.sodar_uuid),
        }
        self.assertEqual(response_data, expected)


class TestIrodsDataRequestListAPIView(
    IrodsDataRequestMixin, SampleSheetAPIViewTestBase
):
    """Tests for IrodsDataRequestListAPIView"""

    def setUp(self):
        super().setUp()
        self.user_contributor = self.make_user('user_contributor')
        self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.irods_backend = get_backend_api('omics_irods')
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=os.path.join(self.assay_path, IRODS_FILE_NAME),
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )
        self.url = reverse(
            'samplesheets:api_irods_request_list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test IrodsDataRequestListAPIView GET"""
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response_data = json.loads(response.content)
        expected = {
            'project': str(self.project.sodar_uuid),
            'action': IRODS_REQUEST_ACTION_DELETE,
            'path': self.request.path,
            'target_path': '',
            'user': str(self.user_contributor.sodar_uuid),
            'status': IRODS_REQUEST_STATUS_ACTIVE,
            'status_info': '',
            'description': self.request.description,
            'date_created': self.get_drf_datetime(self.request.date_created),
            'sodar_uuid': str(self.request.sodar_uuid),
        }
        self.assertEqual(response_data[0], expected)

    def test_get_pagination(self):
        """Test GET with pagination"""
        url = self.url + '?page=1'
        response = self.request_knox(url)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        expected = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'project': str(self.project.sodar_uuid),
                    'action': IRODS_REQUEST_ACTION_DELETE,
                    'path': self.request.path,
                    'target_path': '',
                    'user': str(self.user_contributor.sodar_uuid),
                    'status': IRODS_REQUEST_STATUS_ACTIVE,
                    'status_info': '',
                    'description': self.request.description,
                    'date_created': self.get_drf_datetime(
                        self.request.date_created
                    ),
                    'sodar_uuid': str(self.request.sodar_uuid),
                }
            ],
        }
        self.assertEqual(response_data, expected)

    def test_get_failed_as_superuser(self):
        """Test GET as superuser with failed request"""
        self.request.status = IRODS_REQUEST_STATUS_FAILED
        self.request.save()
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_accepted_as_superuser(self):
        """Test GET as superuser with accepted request"""
        self.request.status = IRODS_REQUEST_STATUS_ACCEPTED
        self.request.save()
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_accepted_as_owner(self):
        """Test GET as owner with accepted request"""
        self.request.status = IRODS_REQUEST_STATUS_ACCEPTED
        self.request.save()
        response = self.request_knox(
            self.url, token=self.get_token(self.user_owner)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_accepted_as_request_creator(self):
        """Test GET as request creator with accepted request"""
        self.request.status = IRODS_REQUEST_STATUS_ACCEPTED
        self.request.save()
        response = self.request_knox(
            self.url, token=self.get_token(self.user_contributor)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class TestIrodsDataRequestDestroyAPIView(
    IrodsDataRequestMixin, SampleSheetAPIViewTestBase
):
    """Tests for IrodsDataRequestDestroyAPIView"""

    def _assert_tl_count(self, count):
        """Assert timeline TimelineEvent count"""
        self.assertEqual(
            TimelineEvent.objects.filter(
                event_name='irods_request_delete'
            ).count(),
            count,
        )

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up iRODS backend and paths
        self.irods_backend = get_backend_api('omics_irods')
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.obj_path = os.path.join(self.assay_path, IRODS_FILE_NAME)

    def test_delete(self):
        """Test IrodsDataRequestDestroyAPIView DELETE"""
        self._assert_tl_count(0)
        obj = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user,
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        with self.login(self.user):
            response = self.client.delete(
                reverse(
                    'samplesheets:api_irods_request_delete',
                    kwargs={'irodsdatarequest': obj.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_tl_count(1)


class TestSampleDataFileExistsAPIView(SampleSheetAPIViewTestBase):
    """Tests for SampleDataFileExistsAPIView"""

    @override_settings(ENABLE_IRODS=False)
    def test_get_no_irods(self):
        """Test SampleDataFileExistsAPIView GET without iRODS (should fail)"""
        url = reverse('samplesheets:api_file_exists')
        response = self.request_knox(url, data={'checksum': IRODS_FILE_MD5})
        self.assertEqual(response.status_code, 500)


# NOTE: Not yet standardized API, use old base class to test
class TestRemoteSheetGetAPIView(
    RemoteSiteMixin, RemoteProjectMixin, SamplesheetsViewTestBase
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
        self.url = reverse(
            'samplesheets:api_remote_get',
            kwargs={
                'project': self.project.sodar_uuid,
                'secret': REMOTE_SITE_SECRET,
            },
        )

    def test_get_tables(self):
        """Test RemoteSheetGetAPIView GET as rendered tables"""
        response = self.client.get(self.url)
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
        """Test GET as ISA-Tab"""
        response = self.client.get(self.url, {'isa': '1'})
        sheet_io = SampleSheetIO()
        expected = sheet_io.export_isa(self.investigation)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)
