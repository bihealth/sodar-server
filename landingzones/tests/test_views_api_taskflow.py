"""
Tests for REST API views in the landingzones app with SODAR Taskflow enabled
"""

import json
import os

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from landingzones.tests.test_views_api import INVALID_UUID
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views import RESULTS_COLL, MISC_FILES_COLL

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowAPIViewTestBase, IRODS_ACCESS_OWN

from landingzones.constants import (
    DEFAULT_STATUS_INFO,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_CREATING,
    ZONE_STATUS_DELETED,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_FAILED,
)
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import (
    LandingZoneTaskflowMixin,
    ZONE_TITLE,
    ZONE_DESC,
    INVALID_REDIS_URL,
    ZONE_BASE_COLLS,
    ZONE_PLUGIN_COLLS,
    ZONE_ALL_COLLS,
    TEST_OBJ_NAME,
)


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


class ZoneAPIViewTaskflowTestBase(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    TaskflowAPIViewTestBase,
):
    """Base landing zone API view test class with Taskflow enabled"""

    def setUp(self):
        super().setUp()
        # Get iRODS backend for session access
        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)
        self.irods = self.irods_backend.get_session_obj()
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
        # Create collections in iRODS
        self.make_irods_colls(self.investigation)
        # Set up helpers
        self.group_name = self.irods_backend.get_user_group_name(self.project)


class TestZoneCreateAPIView(ZoneAPIViewTaskflowTestBase):
    """Tests for ZoneCreateAPIView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:api_create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test ZoneCreateAPIView POST"""
        self.assertEqual(LandingZone.objects.count(), 0)
        # NOTE: No optional create_colls and restrict_colls args, default=False
        request_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'user_message': 'user message',
            'configuration': None,
            'config_data': {},
        }
        response = self.request_knox(self.url, method='POST', data=request_data)

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
            'user': self.get_serialized_user(self.user),
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

        # Assert collection status
        self.assert_irods_coll(zone)
        for c in ZONE_BASE_COLLS:
            self.assert_irods_coll(zone, c, False)
        zone_coll = self.irods.collections.get(
            self.irods_backend.get_path(zone)
        )
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.group_name, zone_coll, None)

    def test_post_colls(self):
        """Test POST with default collections"""
        self.assertEqual(LandingZone.objects.count(), 0)
        request_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'create_colls': True,
            'config_data': {},
        }
        response = self.request_knox(self.url, method='POST', data=request_data)

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
            self.user.username, zone_path, IRODS_ACCESS_OWN
        )
        for c in ZONE_BASE_COLLS:
            self.assert_irods_access(
                self.user.username, os.path.join(zone_path, c), IRODS_ACCESS_OWN
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

        request_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'create_colls': True,
            'config_data': {},
        }
        response = self.request_knox(self.url, method='POST', data=request_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(LandingZone.objects.count(), 1)
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
            'irods/rows/{}'.format(self.assay.sodar_uuid),
            self.project,
            self.user,
        )

        request_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'create_colls': True,
            'restrict_colls': True,
            'config_data': {},
        }
        response = self.request_knox(self.url, method='POST', data=request_data)

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
            self.user.username, zone_path, self.irods_access_read
        )
        for c in ZONE_ALL_COLLS:
            self.assert_irods_access(
                self.user.username, os.path.join(zone_path, c), IRODS_ACCESS_OWN
            )

    # TODO: Test without sodarcache (see issue #1157)

    def test_post_no_investigation(self):
        """Test POST with no investigation"""
        self.investigation.delete()
        self.assertEqual(LandingZone.objects.count(), 0)
        request_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'config_data': {},
        }
        response = self.request_knox(self.url, method='POST', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 0)

    def test_post_no_irods_collections(self):
        """Test POST with no iRODS collections"""
        self.investigation.irods_status = False
        self.investigation.save()
        self.assertEqual(LandingZone.objects.count(), 0)
        request_data = {
            'title': 'new zone',
            'assay': str(self.assay.sodar_uuid),
            'description': 'description',
            'configuration': None,
            'config_data': {},
        }
        response = self.request_knox(self.url, method='POST', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 0)


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
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_DELETED)

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


class TestZoneSubmitMoveAPIView(ZoneAPIViewTaskflowTestBase):
    """Tests for ZoneSubmitMoveAPIView"""

    def setUp(self):
        super().setUp()
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.make_zone_taskflow(self.landing_zone)
        self.sample_path = self.irods_backend.get_path(self.assay)
        self.group_name = self.irods_backend.get_user_group_name(self.project)
        self.zone_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.landing_zone)
        )
        self.assay_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.assay)
        )
        self.url = reverse(
            'landingzones:api_submit_validate',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )
        self.url_move = reverse(
            'landingzones:api_submit_move',
            kwargs={'landingzone': self.landing_zone.sodar_uuid},
        )

    def test_post_validate(self):
        """Test POST for validation"""
        # Update to check status change
        self.landing_zone.status = ZONE_STATUS_FAILED
        self.landing_zone.save()
        response = self.request_knox(self.url, method='POST')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        zone = LandingZone.objects.first()
        self.assert_zone_status(zone, ZONE_STATUS_ACTIVE)
        self.assertEqual(
            LandingZone.objects.first().status_info,
            'Successfully validated 0 files',
        )

    def test_post_validate_invalid_status(self):
        """Test POST for validation with invalid zone status (should fail)"""
        self.landing_zone.status = ZONE_STATUS_MOVED
        self.landing_zone.save()
        response = self.request_knox(self.url, method='POST')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(LandingZone.objects.first().status, ZONE_STATUS_MOVED)

    def test_post_move(self):
        """Test POST for moving"""
        irods_obj = self.make_irods_object(self.zone_coll, TEST_OBJ_NAME)
        self.make_irods_md5_object(irods_obj)
        self.assertEqual(self.landing_zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(len(self.zone_coll.data_objects), 2)
        self.assertEqual(len(self.assay_coll.data_objects), 0)
        response = self.request_knox(self.url_move, method='POST')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['sodar_uuid'], str(self.landing_zone.sodar_uuid)
        )
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assert_zone_status(self.landing_zone, ZONE_STATUS_MOVED)
        self.assertEqual(len(self.zone_coll.data_objects), 0)
        self.assertEqual(len(self.assay_coll.data_objects), 2)

    def test_post_move_invalid_status(self):
        """Test POST for moving with invalid zone status (should fail)"""
        self.landing_zone.status = ZONE_STATUS_DELETED
        self.landing_zone.save()
        response = self.request_knox(self.url_move, method='POST')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LandingZone.objects.count(), 1)
        self.assertEqual(
            LandingZone.objects.first().status, ZONE_STATUS_DELETED
        )

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
            os.path.join(new_zone_path, RESULTS_COLL)
        )
        irods_obj = self.make_irods_object(zone_results_coll, TEST_OBJ_NAME)
        self.make_irods_md5_object(irods_obj)
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
        assay_results_path = os.path.join(self.sample_path, RESULTS_COLL)
        assay_results_coll = self.irods.collections.get(assay_results_path)
        self.assertEqual(len(assay_results_coll.data_objects), 2)
        sample_obj_path = os.path.join(assay_results_path, TEST_OBJ_NAME)
        self.assert_irods_access(
            self.group_name,
            sample_obj_path,
            self.irods_access_read,
        )
        self.assert_irods_access(
            self.group_name,
            sample_obj_path + '.md5',
            self.irods_access_read,
        )
