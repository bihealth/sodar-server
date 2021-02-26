"""Celery tasks for the samplesheets app"""

from unittest import skipIf

from django.conf import settings
from django.contrib import auth

# Projectroles dependency
from django.urls import reverse
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_views_api import SODARAPIViewTestMixin
from projectroles.tests.test_views_taskflow import TestTaskflowBase

# Samplesheets dependency
from samplesheets.models import ISATab
from samplesheets.tasks import sheet_sync_task
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = SODAR_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = SODAR_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = SODAR_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW'
]


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TASKFLOW_ENABLED = (
    True if 'taskflow' in settings.ENABLED_BACKEND_PLUGINS else False
)
TASKFLOW_SKIP_MSG = 'Taskflow not enabled in settings'
APP_NAME = 'samplesheets'

ZONE_TITLE = '20190703_172456'
ZONE_SUFFIX = 'Test Zone'
ZONE_DESC = 'description'
TEST_OBJ_NAME = 'test1.txt'

ASYNC_WAIT_SECONDS = 5
ASYNC_RETRY_COUNT = 3


app_settings = AppSettingAPI()


class TestSheetSyncBase(
    SODARAPIViewTestMixin,
    SampleSheetIOMixin,
    TestTaskflowBase,
):
    def setUp(self):
        super().setUp()

        # Make owner user
        self.user_owner_source = self.make_user('owner_source')
        self.user_owner_target = self.make_user('owner_target')

        # Create Projects
        self.project_source, self.owner_as_source = self._make_project_taskflow(
            title='TestProjectSource',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner_source,
            description='description',
        )
        self.project_target, self.owner_as_target = self._make_project_taskflow(
            title='TestProjectTarget',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner_target,
            description='description',
        )

        # Import investigation
        self.inv_source = self._import_isa_from_file(
            SHEET_PATH, self.project_source
        )

        self.p_id_source = 'p{}'.format(self.project_source.pk)
        self.p_id_target = 'p{}'.format(self.project_target.pk)

        # Allow sample sheet editing in project
        app_settings.set_app_setting(
            APP_NAME, 'sheet_sync_enable', True, project=self.project_target
        )
        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_url',
            self.live_server_url
            + reverse(
                'samplesheets:api_export_json',
                kwargs={'project': str(self.project_source.sodar_uuid)},
            ),
            project=self.project_target,
        )
        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_token',
            self.get_token(self.user_owner_source),
            project=self.project_target,
        )

        # Check if source is set up correctly
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
        self.assertEqual(self.project_target.investigations.count(), 0)
        self.assertEqual(ISATab.objects.count(), 1)


@skipIf(not TASKFLOW_ENABLED, TASKFLOW_SKIP_MSG)
class TestSheetSyncTask(TestSheetSyncBase):
    """Tests for periodic sample sheet sync task"""

    def test_sync_task(self):
        """Test sync sheet"""

        # Perform sync
        sheet_sync_task(self.user.username)

        # Check if target synced correctly
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
        """Test sync sheet with existing sheet and changes in source sheet"""

        # Create investigation for target project
        self._import_isa_from_file(SHEET_PATH, self.project_target)

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

        # Do the sync
        sheet_sync_task(self.user.username)

        # Check if sync was performed correctly
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
        """Test sync sheet with existing sheet and changes in target sheet"""

        # Create investigation for target project
        inv_target = self._import_isa_from_file(SHEET_PATH, self.project_target)
        material = inv_target.studies.first().materials.get(
            unique_name=f'{self.p_id_target}-s0-source-0817'
        )
        material.characteristics['age']['value'] = '300'
        material.save()
        inv_target.save()

        # Check if both projects have an investigation
        self.assertEqual(self.project_source.investigations.count(), 1)
        self.assertEqual(self.project_target.investigations.count(), 1)
        self.assertEqual(ISATab.objects.count(), 2)

        target_date_modified = inv_target.date_modified

        # Do the sync
        sheet_sync_task(self.user.username)

        # Check if sync was not performed
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
        """Test sync sheet with wrong token"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_token',
            'WRONGTOKEN',
            project=self.project_target,
        )

        # Perform sync
        sheet_sync_task(self.user.username)

        # Check if target synced correctly
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_missing_token(self):
        """Test sync sheet with missing token"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_token',
            '',
            project=self.project_target,
        )

        # Perform sync
        sheet_sync_task(self.user.username)

        # Check if target synced correctly
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_wrong_url(self):
        """Test sync sheet with wrong url"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_url',
            'https://qazxdfjajsrd.com',
            project=self.project_target,
        )

        # Perform sync
        sheet_sync_task(self.user.username)

        # Check if target synced correctly
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_url_to_nonexisting_sheet(self):
        """Test sync sheet with url to nonexisting sheet"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_url',
            self.live_server_url
            + reverse(
                'samplesheets:api_export_json',
                kwargs={'project': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'},
            ),
            project=self.project_target,
        )

        # Perform sync
        sheet_sync_task(self.user.username)

        # Check if target synced correctly
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_enabled_missing_url(self):
        """Test sync sheet with missing url"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_url',
            '',
            project=self.project_target,
        )

        # Perform sync
        sheet_sync_task(self.user.username)

        # Check if target synced correctly
        self.assertEqual(self.project_target.investigations.count(), 0)

    def test_sync_disabled(self):
        """Test sync sheet disabled"""

        app_settings.set_app_setting(
            APP_NAME,
            'sheet_sync_enable',
            False,
            project=self.project_target,
        )

        # Perform sync
        sheet_sync_task(self.user.username)

        # Check if target synced correctly
        self.assertEqual(self.project_target.investigations.count(), 0)
