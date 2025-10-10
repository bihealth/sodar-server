"""
Tests for REST API views in the landingzones app with SODAR Taskflow enabled
"""

import json
import time

from irods.exception import GroupDoesNotExist
from irods.path import iRODSPath

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI

# Appalerts dependency
from appalerts.models import AppAlert

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from landingzones.tests.test_views_api import INVALID_UUID
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views import RESULTS_COLL, MISC_FILES_COLL

# Taskflowbackend dependency
from taskflowbackend.constants import (
    IRODS_ACCESS_DELETE_OBJ,
    IRODS_ACCESS_READ_OBJ,
)
from taskflowbackend.tests.base import TaskflowAPIViewTestBase

# Timeline dependency
from timeline.models import TimelineEvent, TL_STATUS_OK

from landingzones.constants import (
    DEFAULT_STATUS_INFO,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_CREATING,
    ZONE_STATUS_DELETED,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_FAILED,
    ZONE_STATUS_VALIDATING,
)
from landingzones.models import LandingZone
from landingzones.serializers import ZONE_NO_INV_MSG
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import (
    LandingZoneTaskflowMixin,
    ZONE_TITLE,
    ZONE_DESC,
    INVALID_REDIS_URL,
    ZONE_BASE_COLLS,
    ZONE_PLUGIN_COLLS,
    ZONE_ALL_COLLS,
)
from landingzones.views import ZONE_CREATE_LIMIT_MSG, ZONE_VALIDATE_LIMIT_MSG
from landingzones.views_api import (
    LANDINGZONES_API_MEDIA_TYPE,
    LANDINGZONES_API_DEFAULT_VERSION,
    ZONE_NO_COLLS_MSG,
)


plugin_api = PluginAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_STATUS_INFO = 'Testing'
TEST_OBJ_NAME = 'test1.txt'
TEST_OBJ_NAME2 = 'test2.txt'


class ZoneAPIViewTaskflowTestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    TaskflowAPIViewTestBase,
):
    """Base landing zone API view test class with Taskflow enabled"""

    media_type = LANDINGZONES_API_MEDIA_TYPE
    api_version = LANDINGZONES_API_DEFAULT_VERSION

    def setUp(self):
        super().setUp()
        # Get iRODS backend for session access
        self.irods_backend = plugin_api.get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        self.irods = self.irods_backend.get_session_obj()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create collections in iRODS
        self.make_irods_colls(self.investigation)
        # Set up helpers
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.owner_group = self.irods_backend.get_group_name(self.project, True)


class TestZoneCreateAPIView(ZoneAPIViewTaskflowTestBase):
    """Tests for ZoneCreateAPIView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:api_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        # NOTE: No optional create_colls and restrict_colls args, default=False
        self.post_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'user_message': 'user message',
            'configuration': None,
            'config_data': {},
        }

    def test_post(self):
        """Test ZoneCreateAPIView POST"""
        self.assertEqual(LandingZone.objects.count(), 0)
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )

        # Assert status after creation
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 1)
        # Assert status after taskflow has finished
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)

        # NOTE: date_modified will be changend async, can't test
        response_data = json.loads(response.content)
        expected = {
            'title': zone.title,
            'project': str(self.project.sodar_uuid),
            'user': str(self.user.sodar_uuid),
            'assay': str(self.assay.sodar_uuid),
            'status': ZONE_STATUS_CREATING,
            'status_info': DEFAULT_STATUS_INFO[ZONE_STATUS_CREATING],
            'status_locked': False,
            'date_modified': response_data['date_modified'],
            'description': zone.description,
            'user_message': zone.user_message,
            'configuration': zone.configuration,
            'config_data': zone.config_data,
            'irods_path': self.irods_backend.get_path(zone),
            'sodar_uuid': str(zone.sodar_uuid),
        }
        self.assertEqual(response_data, expected)

        # Assert collection and access status
        self.assert_irods_coll(zone)
        for c in ZONE_BASE_COLLS:
            self.assert_irods_coll(zone, c, False)
        zone_coll = self.irods.collections.get(
            self.irods_backend.get_path(zone)
        )
        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_DELETE_OBJ
        )
        self.assert_irods_access(
            self.owner_group, zone_coll, IRODS_ACCESS_DELETE_OBJ
        )
        self.assert_irods_access(self.project_group, zone_coll, None)

    def test_post_no_owner_group(self):
        """Test POST with no project owner group"""
        owner_group = self.irods_backend.get_group_name(self.project, True)
        self.irods.users.remove(owner_group)
        with self.assertRaises(GroupDoesNotExist):
            self.irods.user_groups.get(owner_group)
        self.assertEqual(LandingZone.objects.count(), 0)
        # NOTE: No optional create_colls and restrict_colls args, default=False
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)

        self.assert_irods_coll(zone)
        for c in ZONE_BASE_COLLS:
            self.assert_irods_coll(zone, c, False)
        zone_coll = self.irods.collections.get(
            self.irods_backend.get_path(zone)
        )
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_DELETE_OBJ
        )
        self.assert_irods_access(
            self.owner_group, zone_coll, IRODS_ACCESS_DELETE_OBJ
        )
        self.assert_irods_access(self.project_group, zone_coll, None)
        self.assertIsNotNone(self.irods.user_groups.get(owner_group))
        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)

    def test_post_colls(self):
        """Test POST with default collections"""
        self.assertEqual(LandingZone.objects.count(), 0)
        self.post_data['create_colls'] = True
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assert_irods_coll(zone)
        for c in ZONE_BASE_COLLS:
            self.assert_irods_coll(zone, c, True)
        for c in ZONE_PLUGIN_COLLS:
            self.assert_irods_coll(zone, c, False)
        zone_path = self.irods_backend.get_path(zone)
        self.assert_irods_access(
            self.user.username, zone_path, IRODS_ACCESS_DELETE_OBJ
        )
        for c in ZONE_BASE_COLLS:
            self.assert_irods_access(
                self.user.username,
                iRODSPath(zone_path, c),
                IRODS_ACCESS_DELETE_OBJ,
            )
            self.assert_irods_access(
                self.owner_group,
                iRODSPath(zone_path, c),
                IRODS_ACCESS_DELETE_OBJ,
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
            f'irods/rows/{self.assay.sodar_uuid}', self.project, self.user
        )

        self.post_data['create_colls'] = True
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assert_irods_coll(zone)
        for c in ZONE_ALL_COLLS:
            self.assert_irods_coll(zone, c, True)
        zone_path = self.irods_backend.get_path(zone)
        self.assert_irods_access(
            self.user.username, zone_path, IRODS_ACCESS_DELETE_OBJ
        )
        for c in ZONE_ALL_COLLS:
            self.assert_irods_access(
                self.user.username,
                iRODSPath(zone_path, c),
                IRODS_ACCESS_DELETE_OBJ,
            )
            self.assert_irods_access(
                self.owner_group,
                iRODSPath(zone_path, c),
                IRODS_ACCESS_DELETE_OBJ,
            )

    def test_post_colls_plugin_restrict(self):
        """Test POST with restricted collections"""
        self.assertEqual(LandingZone.objects.count(), 0)
        # Mock assay configuration
        self.assay.measurement_type = {'name': 'genome sequencing'}
        self.assay.technology_type = {'name': 'nucleotide sequencing'}
        self.assay.save()
        # Update row cache
        plugin = self.assay.get_plugin()
        self.assertIsNotNone(plugin)
        plugin.update_cache(
            f'irods/rows/{self.assay.sodar_uuid}', self.project, self.user
        )

        self.post_data['create_colls'] = True
        self.post_data['restrict_colls'] = True
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assert_irods_coll(zone)
        for c in ZONE_ALL_COLLS:
            self.assert_irods_coll(zone, c, True)
        zone_path = self.irods_backend.get_path(zone)
        # Read access to root path
        self.assert_irods_access(
            self.user.username, zone_path, IRODS_ACCESS_READ_OBJ
        )
        for c in ZONE_ALL_COLLS:
            self.assert_irods_access(
                self.user.username,
                iRODSPath(zone_path, c),
                IRODS_ACCESS_DELETE_OBJ,
            )
            self.assert_irods_access(
                self.owner_group,
                iRODSPath(zone_path, c),
                IRODS_ACCESS_DELETE_OBJ,
            )

    # TODO: Test without sodarcache (see issue #1157)

    def test_post_no_investigation(self):
        """Test POST with no investigation"""
        self.investigation.delete()
        self.assertEqual(LandingZone.objects.count(), 0)
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(ZONE_NO_INV_MSG, response.data['detail'])
        self.assertEqual(LandingZone.objects.count(), 0)

    def test_post_no_irods_collections(self):
        """Test POST with no iRODS collections"""
        self.investigation.irods_status = False
        self.investigation.save()
        self.assertEqual(LandingZone.objects.count(), 0)
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn(ZONE_NO_COLLS_MSG, response.data['detail'])
        self.assertEqual(LandingZone.objects.count(), 0)

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
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data['detail'], ZONE_CREATE_LIMIT_MSG.format(limit=1)
        )
        self.assertEqual(LandingZone.objects.count(), 1)

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
        response = self.request_knox(
            self.url, method='POST', data=self.post_data
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 2)


class TestZoneSubmitDeleteAPIView(ZoneAPIViewTaskflowTestBase):
    """Tests for ZoneSubmitDeleteAPIView"""

    def setUp(self):
        super().setUp()
        # Create zone
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.url = reverse(
            'landingzones:api_submit_delete',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )

    def test_post(self):
        """Test ZoneSubmitDeleteAPIView POST"""
        self.make_zone_taskflow(self.landing_zone)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_delete').count(), 0
        )
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_delete').count(), 0
        )
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_DELETED)
        self.assertEqual(
            AppAlert.objects.filter(alert_name='zone_delete').count(), 1
        )
        tl_events = TimelineEvent.objects.filter(event_name='zone_delete')
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type, TL_STATUS_OK
        )

    def test_post_invalid_status(self):
        """Test POST with invalid zone status (should fail)"""
        self.make_zone_taskflow(self.landing_zone)
        self.landing_zone.status = ZONE_STATUS_MOVED
        self.landing_zone.save()
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(LandingZone.objects.first().status, ZONE_STATUS_MOVED)

    def test_post_invalid_uuid(self):
        """Test POST with invalid zone UUID (should fail)"""
        self.make_zone_taskflow(self.landing_zone)
        url = reverse(
            'landingzones:api_submit_delete',
            kwargs={'landingzone': INVALID_UUID},
        )
        response = self.request_knox(url, method='POST')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(LandingZone.objects.count(), 1)

    def test_post_restrict(self):
        """Test POST on restricted collections"""
        self.make_zone_taskflow(
            zone=self.landing_zone,
            colls=[MISC_FILES_COLL, RESULTS_COLL],
            restrict_colls=True,
        )
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_DELETED)

    def test_post_no_coll(self):
        """Test POST with no zone root collection in iRODS"""
        self.make_zone_taskflow(self.landing_zone)
        zone_path = self.irods_backend.get_path(self.landing_zone)
        self.assertTrue(self.irods.collections.exists(zone_path))
        self.assertEqual(
            TimelineEvent.objects.filter(event_name='zone_delete').count(), 0
        )
        # Remove collection
        self.irods.collections.remove(zone_path)
        self.assertFalse(self.irods.collections.exists(zone_path))
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_DELETED)
        tl_events = TimelineEvent.objects.filter(event_name='zone_delete')
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(
            tl_events.first().get_status().status_type, TL_STATUS_OK
        )


class TestZoneSubmitMoveAPIView(ZoneAPIViewTaskflowTestBase):
    """Tests for ZoneSubmitMoveAPIView"""

    def setUp(self):
        super().setUp()
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.make_zone_taskflow(self.zone)
        self.sample_path = self.irods_backend.get_path(self.assay)
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.owner_group = self.irods_backend.get_group_name(self.project, True)
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.zone_coll = self.irods.collections.get(self.zone_path)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.assay_coll = self.irods.collections.get(self.assay_path)
        self.url_validate = reverse(
            'landingzones:api_submit_validate',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )
        self.url_move = reverse(
            'landingzones:api_submit_move',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_post_move(self):
        """Test POST for moving"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        response = self.request_knox(self.url_move, method='POST')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sodar_uuid'], str(self.zone.sodar_uuid))
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 2)
        obj_path = iRODSPath(self.assay_path, TEST_OBJ_NAME)
        self.assert_irods_access(self.owner_group, obj_path, None)
        self.assert_irods_access(self.user.username, obj_path, None)
        self.assert_irods_access(
            self.project_group, obj_path, IRODS_ACCESS_READ_OBJ
        )

    def test_post_move_invalid_status(self):
        """Test POST for moving with invalid zone status (should fail)"""
        self.zone.status = ZONE_STATUS_DELETED
        self.zone.save()
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(
            LandingZone.objects.first().status, ZONE_STATUS_DELETED
        )

    def test_post_move_locked(self):
        """Test POST for moving with locked project (should fail)"""
        self.lock_project(self.project)
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_FAILED)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_post_move_lock_failure(self):
        """Test POST for moving with project lock failure"""
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_FAILED)

    def test_post_move_restricted(self):
        """Test POST for moving with restricted collections"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE + '_new',
            project=self.project,
            user=self.user,
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
            iRODSPath(new_zone_path, RESULTS_COLL)
        )
        irods_obj = self.make_irods_object(zone_results_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(zone_results_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)

        url = reverse(
            'landingzones:api_submit_move',
            kwargs={'landingzone': zone.sodar_uuid},
        )
        response = self.request_knox(url, method='POST')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sodar_uuid'], str(zone.sodar_uuid))
        self.assert_zone_status(zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(zone_results_coll.data_objects), 0)
        assay_results_path = iRODSPath(self.sample_path, RESULTS_COLL)
        assay_results_coll = self.irods.collections.get(assay_results_path)
        self.assertEqual(len(assay_results_coll.data_objects), 2)
        sample_obj_path = iRODSPath(assay_results_path, TEST_OBJ_NAME)
        self.assert_irods_access(
            self.project_group,
            sample_obj_path,
            IRODS_ACCESS_READ_OBJ,
        )
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + '.md5',
            IRODS_ACCESS_READ_OBJ,
        )

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_move_limit(self):
        """Test POST to move with validation limit reached"""
        self.make_landing_zone(
            title='other_zone',
            project=self.project,
            user=self.user,
            assay=self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 503)
        self.assert_zone_status(self.zone, ZONE_STATUS_ACTIVE)
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
            user=self.user,
            assay=self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 2)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_move_limit_other_zone_moved(self):
        """Test POST to move with validation limit and other zone in moved status"""
        self.make_landing_zone(
            title='other_zone',
            project=self.project,
            user=self.user,
            assay=self.assay,
            status=ZONE_STATUS_MOVED,
        )
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 2)

    @override_settings(LANDINGZONES_ZONE_MOVE_VERIFY=True)
    def test_post_move_verify(self):
        """Test POST for moving with verification enabled"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertIsNone(
            TimelineEvent.objects.filter(event_name='zone_verify').first()
        )
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assert_zone_status(self.zone, ZONE_STATUS_MOVED)
        # Verify second async flow has run by checking timeline event
        tl_event = None
        for i in range(0, 10):
            tl_event = TimelineEvent.objects.filter(
                event_name='zone_verify'
            ).first()
            if tl_event:
                break
            elif i == 9:
                self.fail('Timeline event not found')
            time.sleep(3)
        self.assertEqual(tl_event.get_status().status_type, 'OK')

    def test_post_validate(self):
        """Test POST for validation"""
        # Update to check status change
        self.zone.status = ZONE_STATUS_FAILED
        self.zone.save()
        response = self.request_knox(self.url_validate, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sodar_uuid'], str(self.zone.sodar_uuid))
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assertEqual(
            LandingZone.objects.first().status_info,
            'Successfully validated 0 files',
        )
        self.assert_irods_access(
            self.owner_group, self.zone_path, IRODS_ACCESS_DELETE_OBJ
        )
        self.assert_irods_access(
            self.user.username, self.zone_path, IRODS_ACCESS_DELETE_OBJ
        )
        self.assert_irods_access(self.project_group, self.zone_path, None)

    def test_post_validate_locked(self):
        """Test POST for validation with locked project"""
        self.lock_project(self.project)
        self.zone.status = ZONE_STATUS_FAILED
        self.zone.save()
        response = self.request_knox(self.url_validate, method='POST')
        self.assertEqual(response.status_code, 200)

    def test_post_validate_invalid_status(self):
        """Test POST for validation with invalid zone status (should fail)"""
        self.zone.status = ZONE_STATUS_VALIDATING
        self.zone.save()
        response = self.request_knox(self.url_validate, method='POST')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(
            LandingZone.objects.first().status, ZONE_STATUS_VALIDATING
        )

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_post_validate_limit(self):
        """Test POST to validate with validation limit reached"""
        self.make_landing_zone(
            title='other_zone',
            project=self.project,
            user=self.user,
            assay=self.assay,
            status=ZONE_STATUS_VALIDATING,
        )
        response = self.request_knox(self.url_validate, method='POST')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['detail'], ZONE_VALIDATE_LIMIT_MSG)
        self.assert_zone_status(self.zone, ZONE_STATUS_ACTIVE)


class TestZoneIrodsFileListAPIView(ZoneAPIViewTaskflowTestBase):
    """Tests for ZoneIrodsFileListAPIView"""

    def setUp(self):
        super().setUp()
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        # Create zone with one default collection
        self.make_zone_taskflow(self.zone, colls=[MISC_FILES_COLL])
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.url = reverse(
            'landingzones:api_file_list',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneIrodsFileListAPIView GET"""
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_get_include_colls(self):
        """Test GET with include_colls=True"""
        response = self.request_knox(self.url + '?include_colls=1')
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': MISC_FILES_COLL,
                'path': iRODSPath(self.zone_path, MISC_FILES_COLL),
                'type': 'coll',
            }
        ]
        self.assertEqual(response.data, expected)

    def test_get_file(self):
        """Test GET with file in zone"""
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        data_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(data_obj)
        response = self.request_knox(self.url)
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': TEST_OBJ_NAME,
                'path': iRODSPath(
                    self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME
                ),
                'type': 'obj',
                'size': 1024,
                'modify_time': self.get_drf_datetime(data_obj.modify_time),
                'checksum': data_obj.checksum,
            }
        ]
        self.assertEqual(response.data, expected)

    def test_get_file_include_checksum(self):
        """Test GET with file and include_checksum"""
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        data_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        chk_obj = self.make_checksum_object(data_obj)
        response = self.request_knox(self.url + '?include_checksum=1')
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': TEST_OBJ_NAME,
                'path': iRODSPath(
                    self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME
                ),
                'type': 'obj',
                'size': 1024,
                'modify_time': self.get_drf_datetime(data_obj.modify_time),
                'checksum': data_obj.checksum,
            },
            {
                'name': TEST_OBJ_NAME + '.md5',
                'path': iRODSPath(
                    self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME + '.md5'
                ),
                'type': 'obj',
                'size': 32,
                'modify_time': self.get_drf_datetime(chk_obj.modify_time),
                'checksum': chk_obj.checksum,
            },
        ]
        self.assertEqual(response.data, expected)

    def test_get_file_include_colls(self):
        """Test GET with file in zone and include_colls"""
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        data_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(data_obj)  # Should not be included in results
        response = self.request_knox(self.url + '?include_colls=1')
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': MISC_FILES_COLL,
                'path': iRODSPath(self.zone_path, MISC_FILES_COLL),
                'type': 'coll',
            },
            {
                'name': TEST_OBJ_NAME,
                'path': iRODSPath(
                    self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME
                ),
                'type': 'obj',
                'size': 1024,
                'modify_time': self.get_drf_datetime(data_obj.modify_time),
                'checksum': data_obj.checksum,
            },
        ]
        self.assertEqual(response.data, expected)

    def test_get_include_checksum_include_colls(self):
        """Test GET with include_checksum and include_colls"""
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        data_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        chk_obj = self.make_checksum_object(data_obj)
        response = self.request_knox(
            self.url + '?include_checksum=1&include_colls=1'
        )
        self.assertEqual(response.status_code, 200)
        expected = [
            {
                'name': MISC_FILES_COLL,
                'path': iRODSPath(self.zone_path, MISC_FILES_COLL),
                'type': 'coll',
            },
            {
                'name': TEST_OBJ_NAME,
                'path': iRODSPath(
                    self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME
                ),
                'type': 'obj',
                'size': 1024,
                'modify_time': self.get_drf_datetime(data_obj.modify_time),
                'checksum': data_obj.checksum,
            },
            {
                'name': TEST_OBJ_NAME + '.md5',
                'path': iRODSPath(
                    self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME + '.md5'
                ),
                'type': 'obj',
                'size': 32,
                'modify_time': self.get_drf_datetime(chk_obj.modify_time),
                'checksum': chk_obj.checksum,
            },
        ]
        self.assertEqual(response.data, expected)

    @override_settings(SODAR_API_PAGE_SIZE=1)
    def test_get_pagination(self):
        """Test GET with pagination"""
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        data_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_irods_object(misc_coll, TEST_OBJ_NAME2)
        response = self.request_knox(self.url + '?page=1')
        self.assertEqual(response.status_code, 200)
        obj_res = {
            'name': TEST_OBJ_NAME,
            'path': data_obj.path,
            'type': 'obj',
            'size': 1024,
            'modify_time': self.get_drf_datetime(data_obj.modify_time),
            'checksum': data_obj.checksum,
        }
        expected = {
            'count': 2,
            'next': self.url + '?page=2&include_checksum=0&include_colls=0',
            'previous': None,
            'results': [obj_res],
        }
        self.assertEqual(response.data, expected)

    @override_settings(SODAR_API_PAGE_SIZE=1)
    def test_get_pagination_include_checksum(self):
        """Test GET with pagination and include_checksum"""
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        data_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        chk_obj = self.make_checksum_object(data_obj)
        response = self.request_knox(self.url + '?page=2&include_checksum=1')
        self.assertEqual(response.status_code, 200)
        obj_res = {
            'name': TEST_OBJ_NAME + '.md5',
            'path': iRODSPath(
                self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME + '.md5'
            ),
            'type': 'obj',
            'size': 32,
            'modify_time': self.get_drf_datetime(chk_obj.modify_time),
            'checksum': chk_obj.checksum,
        }
        expected = {
            'count': 2,
            'next': None,
            'previous': self.url + '?page=1&include_checksum=1&include_colls=0',
            'results': [obj_res],
        }
        self.assertEqual(response.data, expected)

    @override_settings(SODAR_API_PAGE_SIZE=1)
    def test_get_pagination_include_colls(self):
        """Test GET with pagination and include_colls"""
        self.irods.collections.create(iRODSPath(self.zone_path, RESULTS_COLL))
        response = self.request_knox(self.url + '?page=1&include_colls=1')
        self.assertEqual(response.status_code, 200)
        coll_res = {
            'name': MISC_FILES_COLL,
            'path': iRODSPath(self.zone_path, MISC_FILES_COLL),
            'type': 'coll',
        }
        expected = {
            'count': 2,
            'next': self.url + '?page=2&include_checksum=0&include_colls=1',
            'previous': None,
            'results': [coll_res],
        }
        self.assertEqual(response.data, expected)

    @override_settings(SODAR_API_PAGE_SIZE=1)
    def test_get_pagination_include_colls_second_page(self):
        """Test GET with pagination and include_colls on second page"""
        self.irods.collections.create(iRODSPath(self.zone_path, RESULTS_COLL))
        response = self.request_knox(self.url + '?page=2&include_colls=1')
        self.assertEqual(response.status_code, 200)
        coll_res = {
            'name': RESULTS_COLL,
            'path': iRODSPath(self.zone_path, RESULTS_COLL),
            'type': 'coll',
        }
        expected = {
            'count': 2,
            'next': None,
            'previous': self.url + '?page=1&include_checksum=0&include_colls=1',
            'results': [coll_res],
        }
        self.assertEqual(response.data, expected)

    @override_settings(SODAR_API_PAGE_SIZE=2)
    def test_get_pagination_include_checksum_include_colls(self):
        """Test GET with pagination, include_checksum and include_colls"""
        misc_coll = self.irods.collections.get(
            iRODSPath(self.zone_path, MISC_FILES_COLL)
        )
        data_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(data_obj)
        response = self.request_knox(
            self.url + '?page=1&include_checksum=1&include_colls=1'
        )
        self.assertEqual(response.status_code, 200)
        coll_res = {
            'name': MISC_FILES_COLL,
            'path': iRODSPath(self.zone_path, MISC_FILES_COLL),
            'type': 'coll',
        }
        obj_res = {
            'name': TEST_OBJ_NAME,
            'path': iRODSPath(self.zone_path, MISC_FILES_COLL, TEST_OBJ_NAME),
            'type': 'obj',
            'size': 1024,
            'modify_time': self.get_drf_datetime(data_obj.modify_time),
            'checksum': data_obj.checksum,
        }
        expected = {
            'count': 3,
            'next': self.url + '?page=2&include_checksum=1&include_colls=1',
            'previous': None,
            'results': [coll_res, obj_res],
        }
        self.assertEqual(response.data, expected)

    def test_get_v1_0(self):
        """Test with API version 1.0 (should fail)"""
        response = self.request_knox(self.url, version='1.0')
        self.assertEqual(response.status_code, 406)
