"""Tests for Celery tasks for the samplesheets app with taskflow enabled"""

from django.contrib import auth
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI

# Appalerts dependency
from appalerts.models import AppAlert

# Sodarcache dependency
from sodarcache.models import JSONCacheItem

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

# Timeline dependency
from timeline.models import TimelineEvent

from samplesheets.models import ISATab
from samplesheets.tasks_celery import (
    update_project_cache_task,
    sheet_sync_task,
    CACHE_UPDATE_EVENT,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views import SheetRemoteSyncTestBase
from samplesheets.tests.test_views_taskflow import (
    SampleSheetTaskflowMixin,
)


app_settings = AppSettingAPI()
plugin_api = PluginAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
CACHE_ALERT_MESSAGE = 'Testing'


class TestUpdateProjectCacheTask(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowViewTestBase
):
    """Tests for project cache update task"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.app_alerts = plugin_api.get_backend_api('appalerts_backend')
        self.make_irods_colls(self.investigation)

    def test_update_cache(self):
        """Test cache update"""
        self.assertEqual(
            JSONCacheItem.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name=CACHE_UPDATE_EVENT).count(), 0
        )
        self.assertEqual(TimelineEvent.objects.count(), 2)

        update_project_cache_task(
            self.project.sodar_uuid,
            self.user.sodar_uuid,
            add_alert=True,
            alert_msg=CACHE_ALERT_MESSAGE,
        )

        self.assertEqual(
            JSONCacheItem.objects.filter(project=self.project).count(), 1
        )
        cache_item = JSONCacheItem.objects.first()
        self.assertEqual(
            cache_item.name,
            'irods/shortcuts/assay/{}'.format(self.assay.sodar_uuid),
        )
        expected_data = {
            'shortcuts': {
                'misc_files': False,
                'track_hubs': [],
                'results_reports': False,
            }
        }
        self.assertEqual(cache_item.data, expected_data)
        self.assertEqual(
            AppAlert.objects.filter(alert_name=CACHE_UPDATE_EVENT).count(), 1
        )
        alert = AppAlert.objects.order_by('-pk').first()
        self.assertTrue(alert.message.endswith(CACHE_ALERT_MESSAGE))
        self.assertEqual(TimelineEvent.objects.count(), 3)

    def test_update_cache_no_alert(self):
        """Test cache update with app alert disabled"""
        self.assertEqual(
            JSONCacheItem.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name=CACHE_UPDATE_EVENT).count(), 0
        )
        self.assertEqual(TimelineEvent.objects.count(), 2)

        update_project_cache_task(
            self.project.sodar_uuid, self.user.sodar_uuid, add_alert=False
        )

        self.assertEqual(
            JSONCacheItem.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name=CACHE_UPDATE_EVENT).count(), 0
        )
        self.assertEqual(TimelineEvent.objects.count(), 3)

    def test_update_cache_no_user(self):
        """Test cache update with no user"""
        self.assertEqual(
            JSONCacheItem.objects.filter(project=self.project).count(), 0
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name=CACHE_UPDATE_EVENT).count(), 0
        )
        self.assertEqual(TimelineEvent.objects.count(), 2)

        update_project_cache_task(self.project.sodar_uuid, None, add_alert=True)

        self.assertEqual(
            JSONCacheItem.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name=CACHE_UPDATE_EVENT).count(), 0
        )
        self.assertEqual(TimelineEvent.objects.count(), 3)


class TestSheetRemoteSyncTask(SheetRemoteSyncTestBase):
    """Tests for periodic sample sheet sync task"""

    def setUp(self):
        super().setUp()
        self.p_id_source = 'p{}'.format(self.project_source.pk)
        self.p_id_target = 'p{}'.format(self.project_target.pk)

    def test_sync_task(self):
        """Test sync"""
        sheet_sync_task()

        self.assertEqual(self.project_source.investigations.count(), 1)
        self.assertEqual(
            self.project_source.investigations.first().studies.count(), 1
        )
        self.assertEqual(
            self.project_source.investigations.first()
            .studies.first()
            .assays.count(),
            1,
        )
        self.assertEqual(self.project_target.investigations.count(), 1)
        self.assertEqual(
            self.project_target.investigations.first().studies.count(), 1
        )
        self.assertEqual(
            self.project_target.investigations.first()
            .studies.first()
            .assays.count(),
            1,
        )
        self.assertEqual(ISATab.objects.count(), 2)

        data_target = ISATab.objects.get(
            investigation_uuid=self.project_target.investigations.first().sodar_uuid
        ).data
        data_source = ISATab.objects.get(
            investigation_uuid=self.inv_source.sodar_uuid
        ).data
        self.assertEqual(data_target, data_source)

    def test_sync_existing_source_newer(self):
        """Test sync with existing sheet and changes in source sheet"""
        # Create investigation for target project
        self.import_isa_from_file(SHEET_PATH, self.project_target)
        # Update source investigation
        material = self.inv_source.studies.first().materials.get(
            unique_name=f'{self.p_id_source}-s0-source-0817'
        )
        material.characteristics['age']['value'] = '200'
        material.save()
        self.inv_source.save()

        # Check if both projects have an investigation
        self.assertEqual(self.project_source.investigations.count(), 1)
        self.assertEqual(self.project_target.investigations.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertEqual(
            self.project_source.investigations.first()
            .studies.first()
            .materials.get(unique_name=f'{self.p_id_source}-s0-source-0817')
            .characteristics['age']['value'],
            '200',
        )
        self.assertEqual(
            self.project_target.investigations.first()
            .studies.first()
            .materials.get(unique_name=f'{self.p_id_target}-s0-source-0817')
            .characteristics['age']['value'],
            '150',
        )

        sheet_sync_task()

        self.assertEqual(self.project_source.investigations.count(), 1)
        self.assertEqual(self.project_target.investigations.count(), 1)
        self.assertEqual(ISATab.objects.count(), 3)
        self.assertEqual(
            self.project_source.investigations.first()
            .studies.first()
            .materials.get(unique_name=f'{self.p_id_source}-s0-source-0817')
            .characteristics['age']['value'],
            '200',
        )
        self.assertEqual(
            self.project_target.investigations.first()
            .studies.first()
            .materials.get(unique_name=f'{self.p_id_target}-s0-source-0817')
            .characteristics['age']['value'],
            '200',
        )

    def test_sync_existing_target_newer(self):
        """Test sync with existing sheet and changes in target sheet"""
        inv_target = self.import_isa_from_file(SHEET_PATH, self.project_target)
        material = inv_target.studies.first().materials.get(
            unique_name=f'{self.p_id_target}-s0-source-0817'
        )
        material.characteristics['age']['value'] = '300'
        material.save()
        inv_target.save()
        target_date_modified = inv_target.date_modified
        self.assertEqual(self.project_source.investigations.count(), 1)
        self.assertEqual(self.project_target.investigations.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)

        sheet_sync_task()

        self.assertEqual(self.project_source.investigations.count(), 1)
        self.assertEqual(self.project_target.investigations.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)
        self.assertEqual(
            self.project_target.investigations.first().date_modified,
            target_date_modified,
        )
        self.assertEqual(
            self.project_source.investigations.first()
            .studies.first()
            .materials.get(unique_name=f'{self.p_id_source}-s0-source-0817')
            .characteristics['age']['value'],
            '150',
        )
        self.assertEqual(
            self.project_target.investigations.first()
            .studies.first()
            .materials.get(unique_name=f'{self.p_id_target}-s0-source-0817')
            .characteristics['age']['value'],
            '300',
        )

    def test_sync_wrong_token(self):
        """Test sync with wrong token"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_token',
            'WRONGTOKEN',
            project=self.project_target,
        )
        sheet_sync_task()
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_missing_token(self):
        """Test sync with missing token"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_token',
            '',
            project=self.project_target,
        )
        sheet_sync_task()
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_wrong_url(self):
        """Test sync with wrong url"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            'https://qazxdfjajsrd.com',
            project=self.project_target,
        )
        sheet_sync_task()
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_url_to_nonexisting_sheet(self):
        """Test sync with url to nonexisting sheet"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            self.live_server_url
            + reverse(
                'samplesheets:api_export_json',
                kwargs={'project': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'},
            ),
            project=self.project_target,
        )
        sheet_sync_task()
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_missing_url(self):
        """Test sync with missing url"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_url',
            '',
            project=self.project_target,
        )
        sheet_sync_task()
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_disabled(self):
        """Test sync with sync disabled"""
        app_settings.set(
            APP_NAME,
            'sheet_sync_enable',
            False,
            project=self.project_target,
        )
        sheet_sync_task()
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_read_only(self):
        """Test sync with site read-only mode"""
        app_settings.set('projectroles', 'site_read_only', True)
        sheet_sync_task()
        self.assertEqual(self.project_target.investigations.count(), 0)
