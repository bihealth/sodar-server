"""View tests in the landingzones app with taskflow"""

import os
import time

from irods.exception import GroupDoesNotExist
from irods.test.helpers import make_object

from django.contrib import auth
from django.contrib.messages import get_messages
from django.core import mail
from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Appalerts dependency
from appalerts.models import AppAlert

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views import RESULTS_COLL, MISC_FILES_COLL, TRACK_HUBS_COLL

# Taskflowbackend dependency
from taskflowbackend.tasks.irods_tasks import NO_FILE_CHECKSUM_LABEL
from taskflowbackend.tests.base import TaskflowViewTestBase, IRODS_ACCESS_OWN

# Timeline dependency
from timeline.models import TimelineEvent, TL_STATUS_OK

from landingzones.constants import (
    ZONE_STATUS_CREATING,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_FAILED,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_DELETED,
)
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.views import (
    ZONE_MOVE_INVALID_STATUS,
    ZONE_CREATE_LIMIT_MSG,
    ZONE_VALIDATE_LIMIT_MSG,
)


app_settings = AppSettingAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'landingzones'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20190703_172456'
ZONE_SUFFIX = 'Test Zone'
ZONE_DESC = 'description'
TEST_OBJ_NAME = 'test1.txt'
ASYNC_WAIT_SECONDS = 5
ASYNC_RETRY_COUNT = 3
INVALID_MD5 = '11111111111111111111111111111111'
INVALID_REDIS_URL = 'redis://127.0.0.1:6666/0'
ZONE_BASE_COLLS = [MISC_FILES_COLL, RESULTS_COLL, TRACK_HUBS_COLL]
ZONE_PLUGIN_COLLS = ['0815-N1-DNA1', '0815-T1-DNA1']
ZONE_ALL_COLLS = ZONE_BASE_COLLS + ZONE_PLUGIN_COLLS
RAW_DATA_COLL = 'RawData'
MAX_QUANT_COLL = 'MaxQuantResults'
IRODS_ACCESS_READ = 'read_object'


class LandingZoneTaskflowMixin:
    """Taskflow helpers for landingzones tests"""

    def make_zone_taskflow(
        self, zone, colls=None, restrict_colls=False, request=None
    ):
        """
        Create landing zone in iRODS using taskflowbackend.

        :param zone: LandingZone object
        :param colls: Collections to be created (optional, default=[])
        :param restrict_colls: Restrict access to created collections (optional)
        :param request: HTTP request object (optional, default=None)
        :return: Updated LandingZone object
        :raise taskflow.FlowSubmitException if submit fails
        """
        timeline = get_backend_api('timeline_backend')
        user = request.user if request else zone.user
        self.assertEqual(zone.status, ZONE_STATUS_CREATING)

        # Create timeline event to prevent taskflow failure
        tl_event = timeline.add_event(
            project=zone.project,
            app_name='landingzones',
            user=user,
            event_name='zone_create',
            description='create landing zone',
            status_type=timeline.TL_STATUS_SUBMIT,
        )

        flow_data = {
            'zone_uuid': str(zone.sodar_uuid),
            'colls': colls or [],
            'restrict_colls': restrict_colls,
        }
        values = {
            'project': zone.project,
            'flow_name': 'landing_zone_create',
            'flow_data': flow_data,
            'async_mode': True,
            'tl_event': tl_event,
        }
        self.taskflow.submit(**values)

        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        return zone

    def assert_zone_status(self, zone, status=ZONE_STATUS_ACTIVE):
        """
        Assert status of landing zone(s) after waiting for async taskflow
        operation to finish.

        :param zone: LandingZone object
        :param status: Zone status to wait for (string, default=ACTIVE)
        """
        for i in range(0, ASYNC_RETRY_COUNT):
            zone.refresh_from_db()
            if zone.status == status:
                return True
            time.sleep(ASYNC_WAIT_SECONDS)
        raise AssertionError(
            'Timed out waiting for zone status "{}"'.format(status)
        )

    def assert_zone_count(self, count):
        """
        Assert landing zone count after waiting for async taskflow
        operation to finish.

        :param count: Expected zone count
        """
        for i in range(0, ASYNC_RETRY_COUNT):
            if LandingZone.objects.count() == count:
                return True
            time.sleep(ASYNC_WAIT_SECONDS)
        raise AssertionError(
            'Timed out waiting for zone count of {}'.format(count)
        )


class TestProjectZoneView(
    SampleSheetIOMixin,
    LandingZoneMixin,
    SampleSheetTaskflowMixin,
    LandingZoneTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for ProjectZoneView with Taskflow and iRODS"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        self.url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get_locked(self):
        """Test ProjectZoneView GET with locked project"""
        self.lock_project(self.project)
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project_lock'], True)


class TestZoneCreateView(
    SampleSheetIOMixin,
    LandingZoneMixin,
    SampleSheetTaskflowMixin,
    LandingZoneTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for ZoneCreateView with Taskflow and iRODS"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        self.project_path = self.irods_backend.get_path(self.project)
        self.zone_root_path = self.irods_backend.get_zone_path(self.project)
        self.owner_group = self.irods_backend.get_group_name(self.project, True)
        # Set up URLs and default data
        self.url = reverse(
            'landingzones:create', kwargs={'project': self.project.sodar_uuid}
        )
        self.redirect_url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )
        self.post_data = {
            'assay': str(self.assay.sodar_uuid),
            'title_suffix': ZONE_SUFFIX,
            'description': ZONE_DESC,
            'configuration': '',
            'create_colls': False,
            'restrict_colls': False,
        }

    def test_post(self):
        """Test ZoneCreateView POST"""
        self.assertEqual(LandingZone.objects.count(), 0)
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_create').count(), 0
        )
        self.assertEqual(len(mail.outbox), 1)

        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
            self.assertRedirects(response, self.redirect_url)

        self.assert_zone_count(1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assert_irods_coll(zone)
        for c in ZONE_BASE_COLLS:
            self.assert_irods_coll(zone, c, False)
        tl_event = TimelineEvent.objects.filter(
            event_name='zone_create'
        ).first()
        expected_extra = {
            'title': zone.title,
            'assay': str(zone.assay.sodar_uuid),
            'description': ZONE_DESC,
            'create_colls': False,
            'restrict_colls': False,
            'user_message': '',
            'configuration': None,
            'config_data': {},
        }
        self.assertEqual(tl_event.extra_data, expected_extra)
        self.assertEqual(len(mail.outbox), 1)

        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        root_coll = self.irods.collections.get(self.zone_root_path)
        self.assert_irods_access(self.owner_group, root_coll, IRODS_ACCESS_READ)
        zone_path = self.irods_backend.get_path(zone)
        zone_coll = self.irods.collections.get(zone_path)
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )

    def test_post_no_owner_group(self):
        """Test POST with no project owner group"""
        self.irods.users.remove(self.owner_group)
        with self.assertRaises(GroupDoesNotExist):
            self.irods.user_groups.get(self.owner_group)
        self.assertEqual(LandingZone.objects.count(), 0)
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_create').count(), 0
        )
        self.assertEqual(len(mail.outbox), 1)

        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
            self.assertRedirects(response, self.redirect_url)

        self.assert_zone_count(1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assert_irods_coll(zone)
        for c in ZONE_BASE_COLLS:
            self.assert_irods_coll(zone, c, False)
        root_coll = self.irods.collections.get(self.zone_root_path)
        self.assertIsNotNone(self.irods.user_groups.get(self.owner_group))
        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_irods_access(self.owner_group, root_coll, IRODS_ACCESS_READ)
        zone_path = self.irods_backend.get_path(zone)
        zone_coll = self.irods.collections.get(zone_path)
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )

    def test_post_colls(self):
        """Test POST with default collections"""
        self.assertEqual(LandingZone.objects.count(), 0)
        self.post_data['create_colls'] = True
        with self.login(self.user):
            self.client.post(self.url, self.post_data)

        self.assert_zone_count(1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        tl_event = TimelineEvent.objects.filter(
            event_name='zone_create'
        ).first()
        self.assertEqual(tl_event.extra_data['create_colls'], True)
        self.assertEqual(tl_event.extra_data['restrict_colls'], False)
        self.assert_irods_coll(zone)
        for c in ZONE_BASE_COLLS:
            self.assert_irods_coll(zone, c, True)
        for c in ZONE_PLUGIN_COLLS:
            self.assert_irods_coll(zone, c, False)
        zone_path = self.irods_backend.get_path(zone)
        self.assert_irods_access(
            self.user.username, zone_path, IRODS_ACCESS_OWN
        )
        for c in ZONE_BASE_COLLS:
            self.assert_irods_access(
                self.user.username, os.path.join(zone_path, c), IRODS_ACCESS_OWN
            )
            self.assert_irods_access(
                self.owner_group, os.path.join(zone_path, c), IRODS_ACCESS_OWN
            )

    def test_post_colls_plugin(self):
        """Test POST with plugin collections"""
        self.assertEqual(LandingZone.objects.count(), 0)
        # Mock assay configuration
        self.assay.measurement_type = {'name': 'genome sequencing'}
        self.assay.technology_type = {'name': 'nucleotide sequencing'}
        self.assay.save()
        # Update row cache
        plugin = self.assay.get_plugin()
        self.assertIsNotNone(plugin)
        plugin.update_cache(
            'irods/rows/{}'.format(self.assay.sodar_uuid),
            self.project,
            self.user,
        )

        self.post_data['create_colls'] = True
        with self.login(self.user):
            self.client.post(self.url, self.post_data)

        self.assert_zone_count(1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assert_irods_coll(zone)
        for c in ZONE_ALL_COLLS:
            self.assert_irods_coll(zone, c, True)
        zone_path = self.irods_backend.get_path(zone)
        self.assert_irods_access(
            self.user.username, zone_path, IRODS_ACCESS_OWN
        )
        for c in ZONE_ALL_COLLS:
            self.assert_irods_access(
                self.user.username, os.path.join(zone_path, c), IRODS_ACCESS_OWN
            )
            self.assert_irods_access(
                self.owner_group, os.path.join(zone_path, c), IRODS_ACCESS_OWN
            )
        # These should not be created for this plugin
        for c in [MAX_QUANT_COLL, RAW_DATA_COLL]:
            self.assert_irods_coll(zone, c, False)

    def test_post_plugin_shortcuts(self):
        """Test POST with shortcut collections in plugin"""
        self.assertEqual(LandingZone.objects.count(), 0)
        # Set pep_ms plugin
        self.assay.measurement_type = {'name': 'protein expression profiling'}
        self.assay.technology_type = {'name': 'mass spectrometry'}
        self.assay.save()
        # NOTE: update_cache() not implemented in this plugin

        self.post_data['create_colls'] = True
        with self.login(self.user):
            self.client.post(self.url, self.post_data)

        self.assert_zone_count(1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        zone_colls = ZONE_BASE_COLLS + [RAW_DATA_COLL, MAX_QUANT_COLL]
        for c in zone_colls:
            self.assert_irods_coll(zone, c, True)
        for c in ZONE_PLUGIN_COLLS:
            self.assert_irods_coll(zone, c, False)

    # TODO: Test without sodarcache (see issue #1157)

    def test_post_colls_plugin_restrict(self):
        """Test POST with plugin collections and restriction"""
        self.assertEqual(LandingZone.objects.count(), 0)
        # Mock assay configuration
        self.assay.measurement_type = {'name': 'genome sequencing'}
        self.assay.technology_type = {'name': 'nucleotide sequencing'}
        self.assay.save()
        # Update row cache
        plugin = self.assay.get_plugin()
        self.assertIsNotNone(plugin)
        plugin.update_cache(
            'irods/rows/{}'.format(self.assay.sodar_uuid),
            self.project,
            self.user,
        )

        self.post_data['create_colls'] = True
        self.post_data['restrict_colls'] = True
        with self.login(self.user):
            self.client.post(self.url, self.post_data)

        self.assert_zone_count(1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assert_irods_coll(zone)
        zone_path = self.irods_backend.get_path(zone)
        # Read access to root path
        self.assert_irods_access(
            self.user.username, zone_path, self.irods_access_read
        )
        self.assert_irods_access(
            self.owner_group, zone_path, self.irods_access_read
        )
        for c in ZONE_ALL_COLLS:
            self.assert_irods_access(
                self.user.username, os.path.join(zone_path, c), IRODS_ACCESS_OWN
            )
            self.assert_irods_access(
                self.owner_group, os.path.join(zone_path, c), IRODS_ACCESS_OWN
            )

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_post_limit(self):
        """Test POST with zone creation limit reached (should fail)"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            status=ZONE_STATUS_ACTIVE,
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
            self.assertRedirects(response, self.redirect_url)
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[0].message,
            ZONE_CREATE_LIMIT_MSG.format(limit=1) + '.',
        )

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_post_limit_existing_finished(self):
        """Test POST with zone creation limit and finished zone"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            status=ZONE_STATUS_MOVED,
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LandingZone.objects.count(), 2)


class TestZoneMoveView(
    SampleSheetIOMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for ZoneMoveView view with Taskflow and iRODS"""

    def setUp(self):
        super().setUp()
        self.timeline = get_backend_api('timeline_backend')
        self.user_owner = self.make_user('user_owner')
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner,
            description='description',
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Create zone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        # Create zone in taskflow
        self.make_zone_taskflow(self.zone)
        # Get collections
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.zone_coll = self.irods.collections.get(self.zone_path)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.assay_coll = self.irods.collections.get(self.assay_path)
        self.sample_path = self.irods_backend.get_path(self.assay)
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.owner_group = self.irods_backend.get_group_name(self.project, True)
        # Set up URLs
        self.url_move = reverse(
            'landingzones:move',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )
        self.url_validate = reverse(
            'landingzones:validate',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )
        self.url_redirect = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get(self):
        """Test ZoneMoveView GET"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        zone = LandingZone.objects.first()
        self.assertEqual(zone.status, ZONE_STATUS_ACTIVE)
        with self.login(self.user):
            response = self.client.get(self.url_move)
        self.assertEqual(response.status_code, 200)

    def test_post_move(self):
        """Test POST to move landing zone with objects"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assert_irods_access(
            self.owner_group, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(
            self.user_owner.username, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.user.username, self.zone_path, None)
        self.assert_irods_access(self.project_group, self.zone_path, None)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 2)
        obj_path = os.path.join(self.assay_path, TEST_OBJ_NAME)
        self.assert_irods_access(self.owner_group, obj_path, None)
        self.assert_irods_access(self.user.username, obj_path, None)
        self.assert_irods_access(
            self.project_group, obj_path, IRODS_ACCESS_READ
        )
        # Mails to owner and category owner
        self.assertEqual(len(mail.outbox), mail_count + 2)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 1
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').first().user,
            self.user_owner,
        )

    # TODO: Test with SHA256 checksum

    def test_post_move_inactive_user(self):
        """Test POST to move with inactive zone owner"""
        self.user_owner.is_active = False
        self.user_owner.save()
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        mail_count = len(mail.outbox)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )
        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)
        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        # No mail to owner
        self.assertEqual(len(mail.outbox), mail_count + 1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )  # No alert

    def test_post_move_no_files(self):
        """Test POST to move landing zone without objects"""
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )
        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

    def test_post_move_invalid_checksum_md5(self):
        """Test POST with invalid checksum in file (should fail)"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        make_object(self.irods, irods_obj.path + '.md5', INVALID_MD5)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assert_irods_access(
            self.owner_group, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(
            self.user_owner.username, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.user.username, self.zone_path, None)
        self.assert_irods_access(self.project_group, self.zone_path, None)
        self.assertEqual(len(mail.outbox), mail_count + 1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 1
        )

    # TODO: Test with invalid SHA256 file

    def test_post_no_checksum(self):
        """Test POST without checksum file (should fail)"""
        self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        # No checksum file
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 1)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )
        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)
        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertEqual(len(self.zone_coll.data_objects), 1)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 1
        )

    def test_post_move_invalid_status(self):
        """Test POST to move with invalid zone status (should fail)"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.zone.status = ZONE_STATUS_VALIDATING
        self.zone.save()
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_move').count(), 0
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)

        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            ZONE_MOVE_INVALID_STATUS,
        )
        self.assert_zone_status(self.zone, ZONE_STATUS_VALIDATING)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(len(mail.outbox), mail_count)
        tl_event = TimelineEvent.objects.filter(event_name='zone_move').first()
        self.assertIsNone(tl_event)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

    def test_post_move_locked(self):
        """Test POST to move with locked project (should fail)"""
        self.lock_project(self.project)
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_move').count(), 0
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(len(mail.outbox), mail_count)
        # Timeline event should not exist for locked project
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_move').count(), 0
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_post_move_lock_failure(self):
        """Test POST to move with project lock failure"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_move').count(), 0
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        # TODO: Should this send email?
        self.assertEqual(len(mail.outbox), mail_count)
        tl_event = TimelineEvent.objects.filter(event_name='zone_move').first()
        self.assertIsInstance(tl_event, TimelineEvent)
        self.assertEqual(
            tl_event.get_status().status_type, self.timeline.TL_STATUS_FAILED
        )
        # TODO: Create app alerts for async failures (see #1499)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

    def test_post_move_restrict(self):
        """Test POST to move with restricted collections"""
        # Create new zone with restricted collections
        zone = self.make_landing_zone(
            title=ZONE_TITLE + '_new',
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(
            zone=zone,
            colls=[MISC_FILES_COLL, RESULTS_COLL],
            restrict_colls=True,
        )
        new_zone_path = self.irods_backend.get_path(zone)
        zone_results_coll = self.irods.collections.get(
            os.path.join(new_zone_path, RESULTS_COLL)
        )
        irods_obj = self.make_irods_object(zone_results_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(zone_results_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

        url = reverse(
            'landingzones:move', kwargs={'landingzone': zone.sodar_uuid}
        )
        with self.login(self.user):
            response = self.client.post(url)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_status(zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(zone_results_coll.data_objects), 0)
        assay_results_path = os.path.join(self.sample_path, RESULTS_COLL)
        assay_results_coll = self.irods.collections.get(assay_results_path)
        self.assertEqual(len(assay_results_coll.data_objects), 2)
        # Mails to owner & category owner
        self.assertEqual(len(mail.outbox), mail_count + 2)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 1
        )
        sample_obj_path = os.path.join(assay_results_path, TEST_OBJ_NAME)
        self.assert_irods_access(
            self.project_group,
            sample_obj_path,
            self.irods_access_read,
        )
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + '.md5',
            self.irods_access_read,
        )

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_move_limit(self):
        """Test POST to move with validation limit reached"""
        self.make_landing_zone(
            title='other_zone',
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[0].message,
            ZONE_VALIDATE_LIMIT_MSG + '.',
        )
        self.assert_zone_status(self.zone, ZONE_STATUS_ACTIVE)  # No fail
        # Nothing moved either
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_move_limit_other_project(self):
        """Test POST to move with validation limit and zone in another project"""
        new_project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_landing_zone(
            title='other_zone',
            project=new_project,
            user=self.user_owner,
            assay=self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)
        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 2)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_move_limit_other_zone_moved(self):
        """Test POST to move with validation limit and other zone in moved status"""
        self.make_landing_zone(
            title='other_zone',
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=ZONE_STATUS_MOVED,
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            response = self.client.post(self.url_move)
            self.assertRedirects(response, self.url_redirect)
        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 2)

    def test_post_validate(self):
        """Test POST to validate landing zone with objects without moving"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url_validate)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_status(self.zone, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assert_irods_access(
            self.owner_group, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(
            self.user_owner.username, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.user.username, self.zone_path, None)
        self.assert_irods_access(self.project_group, self.zone_path, None)
        self.assertEqual(len(mail.outbox), mail_count)  # No new mail
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 1
        )

    def test_post_validate_no_files(self):
        """Test POST to validate landing zone without files"""
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 0
        )
        with self.login(self.user):
            response = self.client.post(self.url_validate)
            self.assertRedirects(response, self.url_redirect)
        self.assert_zone_status(self.zone, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 1
        )

    def test_post_validate_invalid_checksum_md5(self):
        """Test POST to validate with invalid MD5 checksum in file (should fail)"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        make_object(self.irods, irods_obj.path + '.md5', INVALID_MD5)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 0
        )
        with self.login(self.user):
            self.client.post(self.url_validate)
        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertTrue('BatchValidateChecksumsTask' in self.zone.status_info)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(len(mail.outbox), mail_count)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 1
        )

    # TODO: Test with invalid SHA256

    def test_post_validate_empty_checksum_md5(self):
        """Test POST to validate with empty MD5 checksum in file (should fail)"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        make_object(self.irods, irods_obj.path + '.md5', '')
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 0
        )
        with self.login(self.user):
            self.client.post(self.url_validate)
        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertTrue('BatchValidateChecksumsTask' in self.zone.status_info)
        self.assertTrue('File: {};'.format(NO_FILE_CHECKSUM_LABEL))
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)

    # TODO: Test with empty SHA256

    def test_post_validate_no_checksum_file_md5(self):
        """Test POST to validate without MD5 checksum file (should fail)"""
        self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        # No md5
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 1)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            self.client.post(self.url_validate)
        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertTrue('BatchCheckFileExistTask' in self.zone.status_info)
        self.assertEqual(len(self.zone_coll.data_objects), 1)
        self.assertEqual(len(self.assay_coll.data_objects), 0)

    # TODO: Test with no SHA256 checksum file

    def test_post_validate_checksum_file_only(self):
        """Test POST to validate with no file for checksum file (should fail)"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.md5_obj = self.make_checksum_object(irods_obj)
        irods_obj.unlink(force=True)
        zone = LandingZone.objects.first()
        self.assertEqual(zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 1)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            self.client.post(self.url_validate)
        self.assert_zone_status(zone, ZONE_STATUS_FAILED)
        self.assertTrue('BatchCheckFileExistTask' in zone.status_info)
        self.assertEqual(len(self.zone_coll.data_objects), 1)
        self.assertEqual(len(self.assay_coll.data_objects), 0)

    def test_post_validate_prohibit(self):
        """Test POST to validate with prohibited file name suffix"""
        app_settings.set(
            APP_NAME, 'file_name_prohibit', 'txt', project=self.project
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        mail_count = len(mail.outbox)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_validate').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url_validate)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_status(self.zone, ZONE_STATUS_FAILED)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        self.assertEqual(len(mail.outbox), mail_count)
        tl_event = TimelineEvent.objects.filter(
            event_name='zone_validate'
        ).first()
        self.assertIsInstance(tl_event, TimelineEvent)
        self.assertEqual(
            tl_event.get_status().status_type, self.timeline.TL_STATUS_FAILED
        )
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_move').count(), 0
        )

    def test_post_validate_invalid_status(self):
        """Test POST to validate with invalid zone status (should fail)"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.zone.status = ZONE_STATUS_VALIDATING
        self.zone.save()
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            response = self.client.post(self.url_validate)
            self.assertRedirects(response, self.url_redirect)
        self.assertEqual(
            str(list(get_messages(response.wsgi_request))[0]),
            ZONE_MOVE_INVALID_STATUS,
        )
        self.assert_zone_status(self.zone, ZONE_STATUS_VALIDATING)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)

    def test_post_validate_locked(self):
        """Test POST to validate with locked project"""
        self.lock_project(self.project)
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            response = self.client.post(self.url_validate)
            self.assertRedirects(response, self.url_redirect)
        self.assert_zone_status(self.zone, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_validate_limit(self):
        """Test POST to validate with validation limit reached"""
        self.make_landing_zone(
            title='other_zone',
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        with self.login(self.user):
            response = self.client.post(self.url_validate)
            self.assertRedirects(response, self.url_redirect)
        self.assertEqual(
            list(get_messages(response.wsgi_request))[0].message,
            ZONE_VALIDATE_LIMIT_MSG + '.',
        )
        self.assert_zone_status(self.zone, ZONE_STATUS_ACTIVE)  # No fail
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)


class TestZoneDeleteView(
    SampleSheetIOMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for ZoneDeleteView with Taskflow and iRODS"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.url = reverse(
            'landingzones:delete', kwargs={'landingzone': self.zone.sodar_uuid}
        )
        self.url_redirect = reverse(
            'landingzones:list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test ZoneDeleteView POST with taskflow"""
        self.make_zone_taskflow(self.zone)
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_delete').count(), 0
        )
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_delete').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_count(1)
        self.zone.refresh_from_db()
        self.assert_zone_status(self.zone, ZONE_STATUS_DELETED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_delete').count(), 1
        )
        tl_events = TimelineEvent.objects.filter(event_name='zone_delete')
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type, TL_STATUS_OK
        )

    def test_post_restrict(self):
        """Test POST with restricted collections"""
        self.make_zone_taskflow(
            zone=self.zone,
            colls=[MISC_FILES_COLL, RESULTS_COLL],
            restrict_colls=True,
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_delete').count(), 0
        )

        with self.login(self.user):
            response = self.client.post(self.url)
            self.assertRedirects(response, self.url_redirect)

        self.assert_zone_count(1)
        self.zone.refresh_from_db()
        self.assert_zone_status(self.zone, ZONE_STATUS_DELETED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_delete').count(), 1
        )

    def test_post_no_coll(self):
        """Test POST with no zone root collection in iRODS"""
        self.make_zone_taskflow(self.zone)
        self.assertEqual(LandingZone.objects.count(), 1)
        zone_path = self.irods_backend.get_path(self.zone)
        self.assertTrue(self.irods.collections.exists(zone_path))
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_delete').count(), 0
        )

        # Remove collection
        self.irods.collections.remove(zone_path)
        self.assertFalse(self.irods.collections.exists(zone_path))
        with self.login(self.user):
            self.client.post(self.url)

        self.assert_zone_count(1)
        self.zone.refresh_from_db()
        self.assert_zone_status(self.zone, ZONE_STATUS_DELETED)
        tl_events = TimelineEvent.objects.filter(event_name='zone_delete')
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type, TL_STATUS_OK
        )
