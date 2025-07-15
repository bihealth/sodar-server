"""Tests for Taskflow flows in the taskflowbackend app"""

import os

from irods.access import iRODSAccess
from irods.exception import (
    UserDoesNotExist,
    GroupDoesNotExist,
)
from irods.test.helpers import make_object
from irods.ticket import Ticket
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings
from django.test import override_settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS, ROLE_RANKING

# Timeline dependency
from timeline.tests.test_models import TimelineEventMixin

# Landingzones dependency
from landingzones.constants import (
    ZONE_STATUS_MOVED,
    ZONE_STATUS_CREATING,
    ZONE_STATUS_NOT_CREATED,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_FAILED,
    ZONE_STATUS_DELETED,
)
from landingzones.tests.test_models import ZONE_TITLE, ZONE_DESC
from landingzones.tests.test_views import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin

# Samplesheets dependency
from samplesheets.models import Investigation
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views import RESULTS_COLL, MISC_FILES_COLL

from taskflowbackend.flows.data_delete import Flow as DataDeleteFlow
from taskflowbackend.flows.landing_zone_create import (
    Flow as LandingZoneCreateFlow,
)
from taskflowbackend.flows.landing_zone_delete import (
    Flow as LandingZoneDeleteFlow,
)
from taskflowbackend.flows.landing_zone_move import (
    Flow as LandingZoneMoveFlow,
)
from taskflowbackend.flows.project_create import Flow as ProjectCreateFlow
from taskflowbackend.flows.project_update import Flow as ProjectUpdateFlow
from taskflowbackend.flows.public_access_update import (
    Flow as PublicAccessUpdateFlow,
)
from taskflowbackend.flows.role_update_irods_batch import (
    Flow as RoleUpdateIrodsBatchFlow,
)
from taskflowbackend.flows.sheet_colls_create import (
    Flow as SheetCollsCreateFlow,
    PUBLIC_GROUP,
)
from taskflowbackend.flows.sheet_delete import Flow as SheetDeleteFlow
from taskflowbackend.tasks.irods_tasks import META_EMPTY_VALUE
from taskflowbackend.tests.base import (
    TaskflowViewTestBase,
    IRODS_ACCESS_OWN,
    TICKET_STR,
)
from taskflowbackend.irods_utils import get_flow_role


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']

# Local constants
COLL_NAME = 'test_coll'
SUB_COLL_NAME = 'sub'
OBJ_COLL_NAME = 'obj'
OBJ_NAME = 'test_file.txt'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
UPDATED_TITLE = 'NewTitle'
UPDATED_DESC = 'updated description'
SCRIPT_USER_NAME = 'script_user'
IRODS_ROOT_PATH = 'sodar/root'
INVALID_REDIS_URL = 'redis://127.0.0.1:6666/0'
IRODS_ACCESS_READ = 'read_object'
MD5_SUFFIX = '.md5'


class TaskflowbackendFlowTestBase(TaskflowViewTestBase):
    """Base class for flow tests"""

    def build_and_run(self, flow, force_fail=False):
        """Build and run flow"""
        flow.build(force_fail)
        flow.run()


class TestDataDelete(TaskflowbackendFlowTestBase):
    """Tests for the data_delete flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_path = self.irods_backend.get_path(self.project)
        # Set up iRODS data
        self.coll_path = os.path.join(self.project_path, COLL_NAME)
        self.coll = self.irods.collections.create(self.coll_path)
        self.obj_path = os.path.join(self.project_path, OBJ_NAME)
        self.obj = self.irods.data_objects.create(self.obj_path)

    def test_delete(self):
        """Test data_delete for deleting a collection and a data object"""
        self.assertEqual(self.irods.collections.exists(self.coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)

        flow_data = {'paths': [self.coll_path, self.obj_path]}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='data_delete',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), DataDeleteFlow)
        self.build_and_run(flow)

        self.assertEqual(self.irods.collections.exists(self.coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), False)

    def test_delete_locked(self):
        """Test data_delete with locked project (should fail)"""
        flow_data = {'paths': [self.coll_path, self.obj_path]}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='data_delete',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        with self.assertRaises(self.taskflow.FlowSubmitException):
            self.taskflow.run_flow(flow, self.project)
        self.assertEqual(self.irods.collections.exists(self.coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)

    def test_delete_nested(self):
        """Test data_delete for deleting a nested object"""
        sub_coll_path = os.path.join(self.coll_path, SUB_COLL_NAME)
        self.irods.collections.create(sub_coll_path)
        new_obj_path = os.path.join(sub_coll_path, OBJ_NAME)
        self.irods.data_objects.create(new_obj_path)
        self.assertEqual(self.irods.collections.exists(self.coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(new_obj_path), True)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)

        flow_data = {'paths': [self.coll_path]}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='data_delete',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assertEqual(self.irods.collections.exists(self.coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(new_obj_path), False)
        # NOTE: Not deleted in this case
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)


class TestLandingZoneCreate(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendFlowTestBase,
):
    """Tests for the landing_zone_create flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Create zone without taskflow
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.zone_root_path = self.irods_backend.get_zone_path(self.project)
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.owner_group = self.irods_backend.get_group_name(self.project, True)

    def test_create(self):
        """Test landing_zone_create for creating a zone"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.zone.status, ZONE_STATUS_CREATING)

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [],
            'restrict_colls': False,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)

        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        root_coll = self.irods.collections.get(self.zone_root_path)
        self.assert_irods_access(self.owner_group, root_coll, IRODS_ACCESS_READ)
        zone_coll = self.irods.collections.get(self.zone_path)
        self.assertEqual(
            zone_coll.metadata.get_one('description').value,
            self.zone.description,
        )
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.owner_group, zone_coll, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.project_group, zone_coll, None)

    def test_create_locked(self):
        """Test landing_zone_create with locked project"""
        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [],
            'restrict_colls': False,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        self.taskflow.run_flow(flow, self.project)  # Lock not required
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)

    def test_create_revert(self):
        """Test landing_zone_create for reverting creation"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.zone.status, ZONE_STATUS_CREATING)

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [],
            'restrict_colls': False,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        self.build_and_run(flow, force_fail=True)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_NOT_CREATED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)

    def test_create_colls(self):
        """Test landing_zone_create with collections"""
        results_path = os.path.join(self.zone_path, RESULTS_COLL)
        misc_path = os.path.join(self.zone_path, MISC_FILES_COLL)
        self.assertEqual(self.irods.collections.exists(results_path), False)
        self.assertEqual(self.irods.collections.exists(misc_path), False)

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [RESULTS_COLL, MISC_FILES_COLL],
            'restrict_colls': False,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        self.assertEqual(self.irods.collections.exists(results_path), True)
        self.assertEqual(self.irods.collections.exists(misc_path), True)
        self.assert_irods_access(
            self.user.username, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(
            self.user.username, results_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.project_group, results_path, None)

    def test_create_colls_restrict(self):
        """Test landing_zone_create with restricted collections"""
        results_path = os.path.join(self.zone_path, RESULTS_COLL)
        misc_path = os.path.join(self.zone_path, MISC_FILES_COLL)
        self.assertEqual(self.irods.collections.exists(results_path), False)
        self.assertEqual(self.irods.collections.exists(misc_path), False)

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [RESULTS_COLL, MISC_FILES_COLL],
            'restrict_colls': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        self.assertEqual(self.irods.collections.exists(results_path), True)
        self.assertEqual(self.irods.collections.exists(misc_path), True)
        self.assert_irods_access(
            self.user.username, self.zone_path, self.irods_access_read
        )
        self.assert_irods_access(
            self.user.username, results_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.project_group, results_path, None)
        new_root_path = os.path.join(self.zone_path, 'new_root_path')
        self.irods.collections.create(new_root_path)
        self.assert_irods_access(
            self.user.username, new_root_path, self.irods_access_read
        )
        new_sub_path = os.path.join(results_path, 'new_sub_path')
        self.irods.collections.create(new_sub_path)
        self.assert_irods_access(
            self.user.username, new_sub_path, IRODS_ACCESS_OWN
        )

    def test_create_colls_restrict_revert(self):
        """Test reverting creation with created and restricted collections"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.zone.status, ZONE_STATUS_CREATING)

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [RESULTS_COLL, MISC_FILES_COLL],
            'restrict_colls': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        self.build_and_run(flow, force_fail=True)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_NOT_CREATED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)

    def test_create_script_user(self):
        """Test landing_zone_create with script user"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(SCRIPT_USER_NAME)
        self.irods.users.create(
            SCRIPT_USER_NAME, 'rodsuser', settings.IRODS_ZONE
        )

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [],
            'restrict_colls': False,
            'script_user': SCRIPT_USER_NAME,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        zone_coll = self.irods.collections.get(self.zone_path)
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(
            SCRIPT_USER_NAME, zone_coll, self.irods_access_write
        )
        self.assert_irods_access(self.project_group, zone_coll, None)

    def test_create_script_user_not_created(self):
        """Test landing_zone_create with invalid script user (should fail)"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(SCRIPT_USER_NAME)

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [],
            'restrict_colls': False,
            'script_user': SCRIPT_USER_NAME,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        flow.build()
        with self.assertRaises(Exception):
            flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_NOT_CREATED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(SCRIPT_USER_NAME)

    def test_revert_script_user(self):
        """Test reverting landing_zone_create with script user"""
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(SCRIPT_USER_NAME)
        self.irods.users.create(
            SCRIPT_USER_NAME, 'rodsuser', settings.IRODS_ZONE
        )

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'colls': [],
            'restrict_colls': False,
            'script_user': SCRIPT_USER_NAME,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneCreateFlow)
        self.build_and_run(flow, force_fail=True)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_NOT_CREATED)
        self.assertIsNotNone(self.irods.users.get(SCRIPT_USER_NAME))


class TestLandingZoneDelete(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendFlowTestBase,
):
    """Tests for the landing_zone_delete flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)

    def test_delete(self):
        """Test landing_zone_delete with empty landing zone"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(zone)
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(zone_path), True)

        flow_data = {'zone_uuid': str(zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_delete',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneDeleteFlow)
        self.build_and_run(flow)

        zone.refresh_from_db()
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    def test_delete_locked(self):
        """Test landing_zone_delete with locked project"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(zone)
        flow_data = {'zone_uuid': str(zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_delete',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        self.taskflow.run_flow(flow, self.project)  # Lock not required
        zone.refresh_from_db()
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)

    def test_delete_files(self):
        """Test landing_zone_delete with files"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(zone)
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(zone_path), True)
        coll_path = os.path.join(zone_path, COLL_NAME)
        self.irods.collections.create(coll_path)
        obj_path = os.path.join(zone_path, OBJ_NAME)
        self.irods.data_objects.create(obj_path)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)

        flow_data = {'zone_uuid': str(zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_delete',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        zone.refresh_from_db()
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)
        self.assertEqual(self.irods.collections.exists(coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(obj_path), False)
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    def test_delete_files_restrict(self):
        """Test landing_zone_delete with files and restricted collections"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
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
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(zone_path), True)
        results_path = os.path.join(zone_path, RESULTS_COLL)
        self.assertEqual(self.irods.collections.exists(results_path), True)

        coll_path = os.path.join(results_path, COLL_NAME)
        self.irods.collections.create(coll_path)
        obj_path = os.path.join(results_path, OBJ_NAME)
        self.irods.data_objects.create(obj_path)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)

        flow_data = {'zone_uuid': str(zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_delete',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        zone.refresh_from_db()
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)
        self.assertEqual(self.irods.collections.exists(coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(obj_path), False)
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    def test_delete_finished(self):
        """Test landing_zone_delete with finished zone"""
        # NOTE: This may happen with concurrent requests. See #1909, #1910
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_DELETED,
        )
        # Do not create in taskflow
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)
        flow_data = {'zone_uuid': str(zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_delete',
            flow_data=flow_data,
        )
        self.build_and_run(flow)
        zone.refresh_from_db()
        # This should still be deleted, not failed
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)

    @override_settings(REDIS_URL=INVALID_REDIS_URL)
    def test_delete_finished_lock_failure(self):
        """Test landing_zone_delete with finished zone and lock failure"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_DELETED,
        )
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)
        flow_data = {'zone_uuid': str(zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_delete',
            flow_data=flow_data,
        )
        self.build_and_run(flow)
        zone.refresh_from_db()
        self.assertEqual(zone.status, ZONE_STATUS_DELETED)


class TestLandingZoneMove(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TimelineEventMixin,
    TaskflowbackendFlowTestBase,
):
    """Tests for the landing_zone_move flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
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
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(self.zone)
        self.sample_path = self.irods_backend.get_path(self.assay)
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.owner_group = self.irods_backend.get_group_name(
            self.project, owner=True
        )

    def test_move(self):
        """Test landing_zone_move"""
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        empty_coll_path = os.path.join(self.zone_path, COLL_NAME)
        self.irods.collections.create(empty_coll_path)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.make_checksum_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        self.assert_irods_access(self.owner_group, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.user.username, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.project_group, obj_path, None)

        sample_obj_path = os.path.join(
            self.sample_path, OBJ_COLL_NAME, OBJ_NAME
        )
        tl_event = self.make_event(
            project=self.project,
            app='taskflowbackend',
            user=self.user,
            event_name='landing_zone_move',
            extra_data={},
        )

        self.assertEqual(self.irods.collections.exists(empty_coll_path), True)
        self.assertEqual(self.irods.collections.exists(obj_coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
            tl_event=tl_event,
        )
        self.assertEqual(type(flow), LandingZoneMoveFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        sample_empty_path = os.path.join(self.sample_path, COLL_NAME)
        # An empty collection should not be created by moving
        self.assertEqual(
            self.irods.collections.exists(sample_empty_path), False
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )
        self.assert_irods_access(
            self.project_group, sample_obj_path, self.irods_access_read
        )
        self.assert_irods_access(self.owner_group, sample_obj_path, None)
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + MD5_SUFFIX,
            self.irods_access_read,
        )
        self.assert_irods_access(
            self.owner_group, sample_obj_path + MD5_SUFFIX, None
        )
        tl_event.refresh_from_db()
        expected = {
            'files': [os.path.join(OBJ_COLL_NAME, OBJ_NAME)],
            'total_size': 1024,
        }
        self.assertEqual(tl_event.extra_data, expected)

    def test_move_extra_user_obj(self):
        """Test landing_zone_move with extra user access to data object"""
        # Create new user
        user_new = self.make_user('user_new')
        self.irods.users.create('user_new', 'rodsuser')
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.make_checksum_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        self.assert_irods_access(self.owner_group, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.user.username, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.project_group, obj_path, None)

        # Manually set access to new user
        acl = iRODSAccess(
            access_name='own',
            path=obj_path,
            user_name=user_new.username,
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=False)
        self.assert_irods_access(user_new.username, obj_path, IRODS_ACCESS_OWN)

        sample_obj_path = os.path.join(
            self.sample_path, OBJ_COLL_NAME, OBJ_NAME
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
            tl_event=None,
        )
        self.assertEqual(type(flow), LandingZoneMoveFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )
        self.assert_irods_access(
            self.project_group, sample_obj_path, self.irods_access_read
        )
        self.assert_irods_access(self.owner_group, sample_obj_path, None)
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + MD5_SUFFIX,
            self.irods_access_read,
        )
        self.assert_irods_access(
            self.owner_group, sample_obj_path + MD5_SUFFIX, None
        )
        # New user should have no access
        self.assert_irods_access(user_new.username, sample_obj_path, None)

    def test_move_extra_user_coll(self):
        """Test landing_zone_move with extra user access to collection"""
        # Create new user
        user_new = self.make_user('user_new')
        self.irods.users.create('user_new', 'rodsuser')
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.assertEqual(self.irods.data_objects.exists(obj.path), True)
        self.make_checksum_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        self.assert_irods_access(self.owner_group, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.user.username, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.project_group, obj_path, None)

        acl = iRODSAccess(
            access_name='own',
            path=obj_coll_path,
            user_name=user_new.username,
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=True)
        self.assert_irods_access(
            user_new.username, obj_coll_path, IRODS_ACCESS_OWN
        )

        sample_obj_path = os.path.join(
            self.sample_path, OBJ_COLL_NAME, OBJ_NAME
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
            tl_event=None,
        )
        self.assertEqual(type(flow), LandingZoneMoveFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )
        self.assert_irods_access(
            self.project_group, sample_obj_path, self.irods_access_read
        )
        self.assert_irods_access(self.owner_group, sample_obj_path, None)
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + MD5_SUFFIX,
            self.irods_access_read,
        )
        self.assert_irods_access(
            self.owner_group, sample_obj_path + MD5_SUFFIX, None
        )
        # New user should have no access
        self.assert_irods_access(user_new.username, sample_obj_path, None)

    def test_move_locked(self):
        """Test landing_zone_move with locked project (should fail)"""
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.make_checksum_object(obj)
        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        with self.assertRaises(self.taskflow.FlowSubmitException):
            self.taskflow.run_flow(flow, self.project)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_FAILED)

    def test_move_no_checksum_irods(self):
        """Test landing_zone_move with no checksum in iRODS"""
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME, checksum=False)
        self.make_checksum_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        sample_obj_path = os.path.join(
            self.sample_path, OBJ_COLL_NAME, OBJ_NAME
        )

        self.assertEqual(self.irods.collections.exists(obj_coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )
        self.assertIsNone(obj.replicas[0].checksum)

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneMoveFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )
        obj = self.irods.data_objects.get(sample_obj_path)  # Reload object
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))

    def test_move_no_checksum_file(self):
        """Test landing_zone_move without an checksum file (should fail)"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        # No checksum file

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), False
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        flow.build()
        with self.assertRaises(Exception):
            flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_FAILED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        sample_obj_path = os.path.join(self.sample_path, COLL_NAME, OBJ_NAME)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        # Assert access after revert
        self.assert_irods_access(self.owner_group, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.user.username, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.project_group, obj_path, None)

    # TODO: Test with invalid MD5 file
    # TODO: Test with invalid SHA256 file

    def test_move_coll_exists(self):
        """Test landing_zone_move with existing collection"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_checksum_object(obj)
        sample_coll_path = os.path.join(self.sample_path, COLL_NAME)
        self.irods.collections.create(sample_coll_path)

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        # The sample collection path should already be there
        self.assertEqual(self.irods.collections.exists(sample_coll_path), True)

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        sample_obj_path = os.path.join(self.sample_path, COLL_NAME, OBJ_NAME)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )

    def test_move_obj_exists(self):
        """Test landing_zone_move with existing object (should fail)"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_checksum_object(obj)
        sample_coll_path = os.path.join(self.sample_path, COLL_NAME)
        sample_coll = self.irods.collections.create(sample_coll_path)
        sample_obj = self.make_irods_object(sample_coll, OBJ_NAME)

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.collections.exists(sample_coll_path), True)
        # Object should exist in sample repository
        self.assertEqual(self.irods.data_objects.exists(sample_obj.path), True)

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        flow.build()
        with self.assertRaises(Exception):
            flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_FAILED)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj.path), True)

    def test_move_obj_with_coll_name_exists(self):
        """Test landing_zone_move with existing object sharing name with zone collection"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_checksum_object(obj)
        sample_coll_path = os.path.join(self.sample_path)
        sample_coll = self.irods.collections.create(sample_coll_path)
        # NOTE: Using collection name for the data object
        sample_obj = self.make_irods_object(sample_coll, COLL_NAME)
        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        flow.build()
        with self.assertRaisesRegex(Exception, 'CAT_NAME_EXISTS_AS_DATAOBJ'):
            flow.run()
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_FAILED)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj.path), True)

    def test_move_no_owner_group(self):
        """Test landing_zone_move with no owner group"""
        # Remove owner group
        self.irods.users.remove(self.owner_group)
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        empty_coll_path = os.path.join(self.zone_path, COLL_NAME)
        self.irods.collections.create(empty_coll_path)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.make_checksum_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        self.assert_irods_access(self.user.username, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.project_group, obj_path, None)

        sample_obj_path = os.path.join(
            self.sample_path, OBJ_COLL_NAME, OBJ_NAME
        )
        self.assertEqual(self.irods.collections.exists(empty_coll_path), True)
        self.assertEqual(self.irods.collections.exists(obj_coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
            tl_event=None,
        )
        self.assertEqual(type(flow), LandingZoneMoveFlow)
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )
        self.assert_irods_access(
            self.project_group, sample_obj_path, self.irods_access_read
        )
        self.assert_irods_access(self.owner_group, sample_obj_path, None)
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + MD5_SUFFIX,
            self.irods_access_read,
        )
        self.assert_irods_access(
            self.owner_group, sample_obj_path + MD5_SUFFIX, None
        )

    def test_validate(self):
        """Test landing_zone_move with validate_only=True"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_checksum_object(obj)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'validate_only': True,
        }
        tl_event = self.make_event(
            project=self.project,
            app='taskflowbackend',
            user=self.user,
            event_name='landing_zone_move',
            extra_data={},
        )
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
            tl_event=tl_event,
        )
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        sample_coll_path = os.path.join(self.sample_path, COLL_NAME)
        self.assertEqual(self.irods.collections.exists(sample_coll_path), False)
        self.assert_irods_access(self.owner_group, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.user.username, obj_path, IRODS_ACCESS_OWN)
        self.assert_irods_access(self.project_group, obj_path, None)
        tl_event.refresh_from_db()
        expected = {
            'files': [os.path.join(COLL_NAME, OBJ_NAME)],
            'total_size': 1024,
        }
        self.assertEqual(tl_event.extra_data, expected)

    # TODO: Test validation with SHA256 checksum (see #2170)

    def test_validate_upper_case(self):
        """Test landing_zone_move validation with upper case checksum in file"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        chk_path = obj.path + MD5_SUFFIX
        chk_content = self.get_checksum(obj).upper()
        make_object(self.irods, chk_path, chk_content)
        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'validate_only': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.build_and_run(flow)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)

    def test_validate_bom_header(self):
        """Test landing_zone_move validation with BOM header in MD5 file"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        # Make MD5 object with BOM header
        chk_path = obj.path + MD5_SUFFIX
        chk_content = bytes(self.get_checksum(obj), encoding='utf-8-sig')
        make_object(self.irods, chk_path, chk_content)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'validate_only': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        sample_coll_path = os.path.join(self.sample_path, COLL_NAME)
        self.assertEqual(self.irods.collections.exists(sample_coll_path), False)

    # TODO: Test validation with BOM header and SHA256 checksum (see #2170)

    def test_validate_no_checksum_file_md5(self):
        """Test landing_zone_move validation with missing MD5 checksum file"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME, checksum=False)
        self.assertIsNone(obj.replicas[0].checksum)
        obj_path = obj.path
        self.make_checksum_object(obj)

        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'validate_only': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        obj = self.irods.data_objects.get(obj_path)  # Reload object
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))

    # TODO: Test with SHA256 checksum (see #2170)

    def test_validate_prohibit(self):
        """Test landing_zone_move validation with prohibited file name"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_checksum_object(obj)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'validate_only': True,
            'file_name_prohibit': 'txt',
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        with self.assertRaisesRegex(Exception, OBJ_NAME):
            self.build_and_run(flow)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_FAILED)

    def test_validate_locked(self):
        """Test landing_zone_move validation with locked project"""
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.make_checksum_object(obj)
        flow_data = {
            'zone_uuid': str(self.zone.sodar_uuid),
            'validate_only': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        self.taskflow.run_flow(flow, self.project)
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)

    def test_revert(self):
        """Test reverting landing_zone_move"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_irods_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_checksum_object(obj)

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.build_and_run(flow, force_fail=True)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_FAILED)
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        sample_obj_path = os.path.join(self.sample_path, COLL_NAME, OBJ_NAME)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )
        self.assert_irods_access(self.owner_group, zone_coll, IRODS_ACCESS_OWN)
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.project_group, zone_coll, None)

    def test_move_restrict(self):
        """Test landing_zone_move with created and restricted collections"""
        # Create new zone with restricted collections
        new_zone = self.make_landing_zone(
            title=ZONE_TITLE + '_new',
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(
            zone=new_zone,
            colls=[MISC_FILES_COLL, RESULTS_COLL],
            restrict_colls=True,
        )
        new_zone_path = self.irods_backend.get_path(new_zone)
        self.assertEqual(new_zone.status, ZONE_STATUS_ACTIVE)
        self.assertEqual(self.irods.collections.exists(new_zone_path), True)
        results_path = os.path.join(new_zone_path, RESULTS_COLL)
        self.assertEqual(self.irods.collections.exists(results_path), True)

        empty_coll_path = os.path.join(results_path, COLL_NAME)
        self.irods.collections.create(empty_coll_path)
        obj_coll_path = os.path.join(results_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.make_checksum_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        sample_obj_path = os.path.join(
            self.sample_path, RESULTS_COLL, OBJ_COLL_NAME, OBJ_NAME
        )

        self.assertEqual(self.irods.collections.exists(empty_coll_path), True)
        self.assertEqual(self.irods.collections.exists(obj_coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )

        flow_data = {'zone_uuid': str(new_zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        new_zone.refresh_from_db()
        self.assertEqual(new_zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(new_zone_path), False)
        sample_empty_path = os.path.join(
            self.sample_path, RESULTS_COLL, COLL_NAME
        )
        # An empty collection should not be created by moving
        self.assertEqual(
            self.irods.collections.exists(sample_empty_path), False
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )
        self.assert_irods_access(
            self.project_group, sample_obj_path, self.irods_access_read
        )
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + MD5_SUFFIX,
            self.irods_access_read,
        )


@override_settings(IRODS_ROOT_PATH=IRODS_ROOT_PATH)
class TestLandingZoneMoveAltRootPath(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendFlowTestBase,
):
    """Tests for the landing_zone_move flow with IRODS_ROOT_PATH set"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
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
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(self.zone)
        self.sample_path = self.irods_backend.get_path(self.assay)
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.project_group = self.irods_backend.get_group_name(self.project)

    def test_move_alt_root_path(self):
        """Test landing_zone_move with IRODS_ROOT_PATH set"""
        # Assert alt path have been set correctly and returned for all paths
        root_path = self.irods_backend.get_root_path()
        self.assertEqual(
            root_path, '/{}/{}'.format(settings.IRODS_ZONE, IRODS_ROOT_PATH)
        )
        self.assertTrue(self.project_path.startswith(root_path))
        self.assertTrue(self.sample_path.startswith(root_path))
        self.assertTrue(self.zone_path.startswith(root_path))
        self.assertEqual(self.irods.collections.exists(self.project_path), True)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)

        self.assertEqual(self.zone.status, ZONE_STATUS_ACTIVE)
        empty_coll_path = os.path.join(self.zone_path, COLL_NAME)
        self.irods.collections.create(empty_coll_path)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_irods_object(obj_coll, OBJ_NAME)
        self.make_checksum_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        sample_obj_path = os.path.join(
            self.sample_path, OBJ_COLL_NAME, OBJ_NAME
        )

        self.assertEqual(self.irods.collections.exists(empty_coll_path), True)
        self.assertEqual(self.irods.collections.exists(obj_coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + MD5_SUFFIX), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), False
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, ZONE_STATUS_MOVED)
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        sample_empty_path = os.path.join(self.sample_path, COLL_NAME)
        # An empty collection should not be created by moving
        self.assertEqual(
            self.irods.collections.exists(sample_empty_path), False
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + MD5_SUFFIX), True
        )
        self.assert_irods_access(
            self.project_group, sample_obj_path, self.irods_access_read
        )
        self.assert_irods_access(
            self.project_group,
            sample_obj_path + MD5_SUFFIX,
            self.irods_access_read,
        )


class TestProjectCreate(TaskflowbackendFlowTestBase):
    """Tests for the project_create flow"""

    def setUp(self):
        super().setUp()
        # Create project without taskflow
        self.project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(self.project, self.user, self.role_owner)
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.owner_group = self.irods_backend.get_group_name(self.project, True)
        self.user_assign = self.make_user('user_assign')

    def test_create(self):
        """Test project_create for creating a project"""
        self.assert_irods_coll(self.project, expected=False)
        with self.assertRaises(GroupDoesNotExist):
            self.irods.user_groups.get(self.project_group)
        with self.assertRaises(GroupDoesNotExist):
            self.irods.user_groups.get(self.owner_group)

        flow_data = {
            'owner': self.user.username,
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_owner_cat,
                    ROLE_RANKING[PROJECT_ROLE_OWNER],
                )
            ],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='project_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), ProjectCreateFlow)
        self.build_and_run(flow)

        self.assert_irods_coll(self.project, expected=True)
        group = self.irods.user_groups.get(self.project_group)
        self.assertIsInstance(group, iRODSUserGroup)
        group = self.irods.user_groups.get(self.owner_group)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            self.project_group,
            self.irods_backend.get_path(self.project),
            self.irods_access_read,
        )
        # NOTE: Owner group does not need special access here, as owners and
        #       delegates are also in the user group and everything is read-only
        self.assertIsInstance(
            self.irods.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(self.project, self.user, True, True)
        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('title').value, self.project.title
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value, META_EMPTY_VALUE
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        # Assert inherited category owner status
        self.assertIsInstance(
            self.irods.users.get(self.user_owner_cat.username), iRODSUser
        )
        self.assert_group_member(self.project, self.user_owner_cat, True, True)

    def test_create_inherited_delegate(self):
        """Test project_create with inherited delegate"""
        flow_data = {
            'owner': self.user.username,
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_assign,
                    ROLE_RANKING[PROJECT_ROLE_DELEGATE],
                )
            ],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='project_create',
            flow_data=flow_data,
        )
        self.build_and_run(flow)
        self.assert_group_member(self.project, self.user_assign, True, True)

    def test_create_inherited_contributor(self):
        """Test project_create with inherited contributor"""
        flow_data = {
            'owner': self.user.username,
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_assign,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                )
            ],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='project_create',
            flow_data=flow_data,
        )
        self.build_and_run(flow)
        self.assert_group_member(self.project, self.user_assign, True, False)


class TestProjectUpdate(TaskflowbackendFlowTestBase):
    """Tests for the project_update flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_path = self.irods_backend.get_path(self.project)

    def test_update_metadata(self):
        """Test project_update with updated metadata"""
        self.assertNotEqual(self.project.title, UPDATED_TITLE)
        self.assertNotEqual(self.project.description, UPDATED_DESC)
        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('title').value, self.project.title
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value, META_EMPTY_VALUE
        )

        self.project.title = UPDATED_TITLE
        self.project.description = UPDATED_DESC
        self.project.save()
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='project_update',
            flow_data={},
        )
        self.assertEqual(type(flow), ProjectUpdateFlow)
        self.build_and_run(flow)

        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('title').value, UPDATED_TITLE
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value, UPDATED_DESC
        )

    def test_update_metadata_locked(self):
        """Test project_update with locked project"""
        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('title').value, self.project.title
        )
        self.project.title = UPDATED_TITLE
        self.project.save()
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='project_update',
            flow_data={},
        )
        self.lock_project(self.project)
        self.taskflow.run_flow(flow, self.project)  # Lock not required
        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('title').value, UPDATED_TITLE
        )

    def test_update_parent(self):
        """Test project_update with updated parent"""
        user_contributor = self.make_user('user_contributor')
        user_cat_new = self.make_user('user_cat_new')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, user_contributor, True, False)
        self.assert_group_member(self.project, user_cat_new, False, False)
        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )

        new_category = self.make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.make_assignment(new_category, user_cat_new, self.role_owner)
        self.project.parent = new_category
        self.project.save()

        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    user_cat_new,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                )
            ],
            'roles_delete': [
                get_flow_role(
                    self.project,
                    self.user_owner_cat,
                    ROLE_RANKING[PROJECT_ROLE_OWNER],
                )
            ],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='project_update',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(
            self.project, self.user_owner_cat, False, False
        )
        self.assert_group_member(self.project, user_contributor, True, False)
        self.assert_group_member(self.project, user_cat_new, True, False)
        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(new_category.sodar_uuid),
        )


class TestPublicAccessUpdate(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendFlowTestBase,
):
    """Tests for the public_access_update flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.sample_path = self.irods_backend.get_sample_path(self.project)

    def test_enable_access(self):
        """Test public_access_update to enable public access"""
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

        flow_data = {
            'path': self.sample_path,
            'access': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), PublicAccessUpdateFlow)
        self.build_and_run(flow)

        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, self.irods_access_read
        )

    def test_enable_access_locked(self):
        """Test public_access_update with locked project"""
        self.make_irods_colls(self.investigation)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)
        flow_data = {
            'path': self.sample_path,
            'access': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        self.taskflow.run_flow(flow, self.project)  # Lock not required
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, self.irods_access_read
        )

    def test_disable_access(self):
        """Test public_access_update to disable public access"""
        self.project.public_guest_access = True
        self.project.save()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, self.irods_access_read
        )

        flow_data = {
            'path': self.sample_path,
            'access': False,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

    def test_revert(self):
        """Test reverting public_access_update"""
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

        flow_data = {
            'path': self.sample_path,
            'access': True,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), PublicAccessUpdateFlow)
        self.build_and_run(flow, force_fail=True)

        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

    def test_enable_access_anon(self):
        """Test enabling public access with anonymous access enabled"""
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

        flow_data = {
            'path': self.sample_path,
            'access': True,
            'ticket_str': TICKET_STR,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), PublicAccessUpdateFlow)
        with override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True):
            self.build_and_run(flow)

        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, self.irods_access_read
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_disable_access_anon(self):
        """Test disabling public access with anonymous access enabled"""
        self.project.public_guest_access = True
        self.project.save()
        # Create iRODS collections
        self.make_irods_colls(self.investigation, ticket_str=TICKET_STR)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, self.irods_access_read
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

        flow_data = {
            'path': self.sample_path,
            'access': False,
            'ticket_str': TICKET_STR,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))


class TestRoleUpdateIrodsBatch(TaskflowbackendFlowTestBase):
    """Tests for the role_update_irods_batch flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        # self.project_path = self.irods_backend.get_path(self.project)
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.owner_group = self.irods_backend.get_group_name(self.project, True)
        self.project_group = self.irods.user_groups.get(self.project_group)
        self.owner_group = self.irods.user_groups.get(self.owner_group)
        self.user_new = self.make_user('user_new')
        self.user_new2 = self.make_user('user_new2')

    def test_add(self):
        """Test role_update_irods_batch for adding users"""
        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(self.project, self.user_new2, False, False)

        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
                get_flow_role(
                    self.project,
                    self.user_new2,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), RoleUpdateIrodsBatchFlow)
        self.build_and_run(flow)

        self.assert_group_member(self.project, self.user_new, True, False)
        self.assert_group_member(self.project, self.user_new2, True, False)

    def test_add_owner(self):
        """Test role_update_irods_batch for adding users with owner"""
        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(self.project, self.user_new2, False, False)
        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
                get_flow_role(
                    self.project,
                    self.user_new2,
                    ROLE_RANKING[PROJECT_ROLE_OWNER],
                ),
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.build_and_run(flow)
        self.assert_group_member(self.project, self.user_new, True, False)
        self.assert_group_member(self.project, self.user_new2, True, True)

    def test_add_delegate(self):
        """Test role_update_irods_batch for adding users with delegate"""
        self.assert_group_member(self.project, self.user_new, False, False)
        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_DELEGATE],
                ),
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.build_and_run(flow)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_add_locked(self):
        """Test role_update_irods_batch with locked project"""
        self.assert_group_member(self.project, self.user_new, False, False)
        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                )
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        self.taskflow.run_flow(flow, self.project)  # Lock not required
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_add_multi_project(self):
        """Test role_update_irods_batch for adding users to multiple projects"""
        new_project, _ = self.make_project_taskflow(
            'NewProject2', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(new_project, self.user_new, False, False)

        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
                get_flow_role(
                    new_project,
                    self.user_new2,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assert_group_member(self.project, self.user_new, True, False)
        self.assert_group_member(self.project, self.user_new2, False, False)
        self.assert_group_member(new_project, self.user_new, False, False)
        self.assert_group_member(new_project, self.user_new2, True, False)

    def test_add_multi_project_owner(self):
        """Test role_update_irods_batch for adding users to multiple projects with owner"""
        new_project, _ = self.make_project_taskflow(
            'NewProject2', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(self.project, self.user_new2, False, False)
        self.assert_group_member(new_project, self.user_new, False, False)
        self.assert_group_member(new_project, self.user_new2, False, False)

        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_OWNER],
                ),
                get_flow_role(
                    new_project,
                    self.user_new2,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assert_group_member(self.project, self.user_new, True, True)
        self.assert_group_member(self.project, self.user_new2, False, False)
        self.assert_group_member(new_project, self.user_new, False, False)
        self.assert_group_member(new_project, self.user_new2, True, False)

    def test_delete(self):
        """Test role_update_irods_batch for deleting users"""
        self.irods.users.create(
            self.user_new.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.irods.users.create(
            self.user_new2.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.project_group.addmember(self.user_new.username)
        self.project_group.addmember(self.user_new2.username)

        self.assert_group_member(self.project, self.user_new)
        self.assert_group_member(self.project, self.user_new2)

        flow_data = {
            'roles_add': [],
            'roles_delete': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
                get_flow_role(
                    self.project,
                    self.user_new2,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                ),
            ],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assert_group_member(self.project, self.user_new, False)
        self.assert_group_member(self.project, self.user_new2, False)

    def test_delete_owner(self):
        """Test role_update_irods_batch for deleting users with owner roles"""
        self.irods.users.create(
            self.user_new.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.irods.users.create(
            self.user_new2.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.project_group.addmember(self.user_new.username)
        self.owner_group.addmember(self.user_new.username)
        self.project_group.addmember(self.user_new2.username)
        self.owner_group.addmember(self.user_new2.username)

        self.assert_group_member(self.project, self.user_new, True, True)
        self.assert_group_member(self.project, self.user_new2, True, True)

        flow_data = {
            'roles_add': [],
            'roles_delete': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_OWNER],
                ),
                get_flow_role(
                    self.project,
                    self.user_new2,
                    ROLE_RANKING[PROJECT_ROLE_DELEGATE],
                ),
            ],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(self.project, self.user_new2, False, False)

    def test_update_to_owner(self):
        """Test role_update_irods_batch with updating user to owner"""
        self.irods.users.create(
            self.user_new.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.project_group.addmember(self.user_new.username)
        self.assert_group_member(self.project, self.user_new, True, False)
        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_DELEGATE],
                )
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.taskflow.run_flow(flow, self.project)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_update_from_owner(self):
        """Test role_update_irods_batch with updating user from owner"""
        self.irods.users.create(
            self.user_new.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.project_group.addmember(self.user_new.username)
        self.owner_group.addmember(self.user_new.username)
        self.assert_group_member(self.project, self.user_new, True, True)
        flow_data = {
            'roles_add': [
                get_flow_role(
                    self.project,
                    self.user_new,
                    ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR],
                )
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        self.taskflow.run_flow(flow, self.project)
        self.assert_group_member(self.project, self.user_new, True, False)


class TestSheetCollsCreate(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendFlowTestBase,
):
    """Tests for the sheet_colls_create flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.sample_path = self.irods_backend.get_sample_path(self.project)

    def test_create(self):
        """Test sheet_colls_create for creating sample repository collections"""
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)

        flow_data = {'colls': [RESULTS_COLL, MISC_FILES_COLL]}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_colls_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), SheetCollsCreateFlow)
        self.build_and_run(flow)

        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)
        results_path = os.path.join(self.sample_path, RESULTS_COLL)
        self.assertEqual(self.irods.collections.exists(results_path), True)
        self.assert_irods_access(
            self.project_group, results_path, self.irods_access_read
        )
        misc_path = os.path.join(self.sample_path, MISC_FILES_COLL)
        self.assertEqual(self.irods.collections.exists(misc_path), True)
        self.assert_irods_access(
            self.project_group, misc_path, self.irods_access_read
        )

    def test_create_locked(self):
        """Test sheet_colls_create with locked project (should fail)"""
        flow_data = {'colls': [RESULTS_COLL, MISC_FILES_COLL]}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_colls_create',
            flow_data=flow_data,
        )
        self.lock_project(self.project)
        with self.assertRaises(self.taskflow.FlowSubmitException):
            self.taskflow.run_flow(flow, self.project)
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, False)

    def test_create_public_access(self):
        """Test sheet_colls_create with public guest access"""
        self.project.public_guest_access = True
        self.project.save()
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)

        flow_data = {'colls': [RESULTS_COLL, MISC_FILES_COLL]}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_colls_create',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, self.irods_access_read
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_create_anon(self):
        """Test creating colls with public guest access and anonymous access"""
        self.project.public_guest_access = True
        self.project.save()
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

        flow_data = {
            'colls': [RESULTS_COLL, MISC_FILES_COLL],
            'ticket_str': TICKET_STR,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_colls_create',
            flow_data=flow_data,
        )
        self.build_and_run(flow)

        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.project_group, self.sample_path, self.irods_access_read
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, self.irods_access_read
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_revert(self):
        """Test reverting sheet_colls_create"""
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)

        flow_data = {'colls': [RESULTS_COLL, MISC_FILES_COLL]}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_colls_create',
            flow_data=flow_data,
        )
        self.build_and_run(flow, force_fail=True)

        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_revert_anon(self):
        """Test reverting with anonymous access"""
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

        flow_data = {
            'colls': [RESULTS_COLL, MISC_FILES_COLL],
            'ticket_str': TICKET_STR,
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_colls_create',
            flow_data=flow_data,
        )
        self.build_and_run(flow, force_fail=True)

        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))


class TestSheetDelete(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendFlowTestBase,
):
    """Tests for the sheet_delete flow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_group = self.irods_backend.get_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.sample_path = self.irods_backend.get_sample_path(self.project)

    def test_delete(self):
        """Test sheet_delete for deleting project sample sheets"""
        self.assertIsNotNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_delete',
            flow_data={},
        )
        self.assertEqual(type(flow), SheetDeleteFlow)
        self.build_and_run(flow)
        self.assertIsNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )

    def test_delete_locked(self):
        """Test sheet_delete with locked project (should fail)"""
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_delete',
            flow_data={},
        )
        self.lock_project(self.project)
        with self.assertRaises(self.taskflow.FlowSubmitException):
            self.taskflow.run_flow(flow, self.project)
        self.assertIsNotNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )

    def test_delete_colls(self):
        """Test sheet_delete with collections"""
        self.assertIsNotNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)

        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_delete',
            flow_data={},
        )
        self.assertEqual(type(flow), SheetDeleteFlow)
        self.build_and_run(flow)

        self.assertIsNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)

    def test_delete_zone(self):
        """Test sheet_delete with a landing zone"""
        self.assertIsNotNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        # Create landing zone
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_CREATING,
        )
        self.make_zone_taskflow(zone)
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(self.irods.collections.exists(zone_path), True)

        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_delete',
            flow_data={},
        )
        self.assertEqual(type(flow), SheetDeleteFlow)
        self.build_and_run(flow)

        self.assertIsNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    # NOTE: Can't be reverted
