"""Tests for Taskflow flows in the taskflowbackend app"""

import os

from irods.exception import (
    UserDoesNotExist,
    UserGroupDoesNotExist,
)
from irods.ticket import Ticket
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings
from django.test import override_settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Landingzones dependency
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
from taskflowbackend.flows.role_delete import Flow as RoleDeleteFlow
from taskflowbackend.flows.role_update import Flow as RoleUpdateFlow
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
    TaskflowbackendTestBase,
    IRODS_ACCESS_READ,
    IRODS_ACCESS_OWN,
    IRODS_ACCESS_WRITE,
    TICKET_STR,
)


# SODAR constants
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
COLL_NAME = 'test_coll'
SUB_COLL_NAME = 'sub'
OBJ_COLL_NAME = 'obj'
OBJ_NAME = 'test_file'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
UPDATED_TITLE = 'NewTitle'
UPDATED_DESC = 'updated description'
SCRIPT_USER_NAME = 'script_user'


class TestDataDelete(TaskflowbackendTestBase):
    """Tests for the data_delete flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
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
        flow.build()
        flow.run()

        self.assertEqual(self.irods.collections.exists(self.coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), False)

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
        flow.build()
        flow.run()

        self.assertEqual(self.irods.collections.exists(self.coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(new_obj_path), False)
        # NOTE: Not deleted in this case
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)


class TestLandingZoneCreate(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Tests for the landing_zone_create flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)
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
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='CREATING',
        )
        self.zone_path = self.irods_backend.get_path(self.zone)

    def test_create(self):
        """Test landing_zone_create for creating a zone"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.zone.status, 'CREATING')

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
        flow.build()
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'ACTIVE')
        zone_coll = self.irods.collections.get(self.zone_path)
        self.assertEqual(
            zone_coll.metadata.get_one('description').value,
            self.zone.description,
        )
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.group_name, zone_coll, None)

    def test_create_revert(self):
        """Test landing_zone_create for reverting creation"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.zone.status, 'CREATING')

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
        flow.build(force_fail=True)
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'NOT CREATED')
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
        flow.build()
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'ACTIVE')
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        self.assertEqual(self.irods.collections.exists(results_path), True)
        self.assertEqual(self.irods.collections.exists(misc_path), True)
        self.assert_irods_access(
            self.user.username, self.zone_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(
            self.user.username, results_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.group_name, results_path, None)

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
        flow.build()
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'ACTIVE')
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        self.assertEqual(self.irods.collections.exists(results_path), True)
        self.assertEqual(self.irods.collections.exists(misc_path), True)
        self.assert_irods_access(
            self.user.username, self.zone_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(
            self.user.username, results_path, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(self.group_name, results_path, None)
        new_root_path = os.path.join(self.zone_path, 'new_root_path')
        self.irods.collections.create(new_root_path)
        self.assert_irods_access(
            self.user.username, new_root_path, IRODS_ACCESS_READ
        )
        new_sub_path = os.path.join(results_path, 'new_sub_path')
        self.irods.collections.create(new_sub_path)
        self.assert_irods_access(
            self.user.username, new_sub_path, IRODS_ACCESS_OWN
        )

    def test_create_colls_restrict_revert(self):
        """Test reverting creation with created and restricted collections"""
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        self.assertEqual(self.zone.status, 'CREATING')

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
        flow.build(force_fail=True)
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'NOT CREATED')
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
        flow.build()
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'ACTIVE')
        zone_coll = self.irods.collections.get(self.zone_path)
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )
        self.assert_irods_access(
            SCRIPT_USER_NAME, zone_coll, IRODS_ACCESS_WRITE
        )
        self.assert_irods_access(self.group_name, zone_coll, None)

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
        self.assertEqual(self.zone.status, 'NOT CREATED')
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
        flow.build(force_fail=True)
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'NOT CREATED')
        self.assertIsNotNone(self.irods.users.get(SCRIPT_USER_NAME))


class TestLandingZoneDelete(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Tests for the landing_zone_delete flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)
        self.project_path = self.irods_backend.get_path(self.project)
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)

    def test_delete(self):
        """Test landing_zone_delete with an empty landing zone"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='CREATING',
        )
        self.make_zone_taskflow(zone)
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(zone.status, 'ACTIVE')
        self.assertEqual(self.irods.collections.exists(zone_path), True)

        flow_data = {'zone_uuid': str(zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_delete',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneDeleteFlow)
        flow.build()
        flow.run()

        zone.refresh_from_db()
        self.assertEqual(zone.status, 'DELETED')
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    def test_delete_files(self):
        """Test landing_zone_delete with files"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='CREATING',
        )
        self.make_zone_taskflow(zone)
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(zone.status, 'ACTIVE')
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
        flow.build()
        flow.run()

        zone.refresh_from_db()
        self.assertEqual(zone.status, 'DELETED')
        self.assertEqual(self.irods.collections.exists(coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(obj_path), False)
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    def test_delete_files_restrict(self):
        """Test landing_zone_delete with files and restricted collections"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='CREATING',
        )
        self.make_zone_taskflow(
            zone=zone,
            colls=[MISC_FILES_COLL, RESULTS_COLL],
            restrict_colls=True,
        )
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(zone.status, 'ACTIVE')
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
        flow.build()
        flow.run()

        zone.refresh_from_db()
        self.assertEqual(zone.status, 'DELETED')
        self.assertEqual(self.irods.collections.exists(coll_path), False)
        self.assertEqual(self.irods.data_objects.exists(obj_path), False)
        self.assertEqual(self.irods.collections.exists(zone_path), False)


class TestLandingZoneMove(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Tests for the landing_zone_move flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)
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
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='CREATING',
        )
        self.make_zone_taskflow(self.zone)
        self.sample_path = self.irods_backend.get_path(self.assay)
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.group_name = self.irods_backend.get_user_group_name(self.project)

    def test_move(self):
        """Test landing_zone_move"""
        self.assertEqual(self.zone.status, 'ACTIVE')
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        empty_coll_path = os.path.join(self.zone_path, COLL_NAME)
        self.irods.collections.create(empty_coll_path)
        obj_coll_path = os.path.join(self.zone_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_object(obj_coll, OBJ_NAME)
        self.make_md5_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        sample_obj_path = os.path.join(
            self.sample_path, OBJ_COLL_NAME, OBJ_NAME
        )

        self.assertEqual(self.irods.collections.exists(empty_coll_path), True)
        self.assertEqual(self.irods.collections.exists(obj_coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + '.md5'),
            False,
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), LandingZoneMoveFlow)
        flow.build()
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'MOVED')
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        sample_empty_path = os.path.join(self.sample_path, COLL_NAME)
        # An empty collection should not be created by moving
        self.assertEqual(
            self.irods.collections.exists(sample_empty_path), False
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + '.md5'),
            True,
        )
        self.assert_irods_access(
            self.group_name,
            sample_obj_path,
            IRODS_ACCESS_READ,
        )
        self.assert_irods_access(
            self.group_name,
            sample_obj_path + '.md5',
            IRODS_ACCESS_READ,
        )

    def test_move_no_md5(self):
        """Test landing_zone_move without an MD5 checksum file (should fail)"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        # No MD5 file

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), False
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
        self.assertEqual(self.zone.status, 'FAILED')
        self.assertEqual(self.irods.collections.exists(self.zone_path), True)
        sample_obj_path = os.path.join(self.sample_path, COLL_NAME, OBJ_NAME)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)

    # TODO: Test with invalid .md5 file

    def test_move_coll_exists(self):
        """Test landing_zone_move with existing collection"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_md5_object(obj)
        sample_coll_path = os.path.join(self.sample_path, COLL_NAME)
        self.irods.collections.create(sample_coll_path)

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
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
        flow.build()
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'MOVED')
        self.assertEqual(self.irods.collections.exists(self.zone_path), False)
        sample_obj_path = os.path.join(self.sample_path, COLL_NAME, OBJ_NAME)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + '.md5'),
            True,
        )

    def test_move_obj_exists(self):
        """Test landing_zone_move with existing object (should fail)"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_md5_object(obj)
        sample_coll_path = os.path.join(self.sample_path, COLL_NAME)
        sample_coll = self.irods.collections.create(sample_coll_path)
        sample_obj = self.make_object(sample_coll, OBJ_NAME)

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
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
        self.assertEqual(self.zone.status, 'FAILED')
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj.path), True)

    def test_validate(self):
        """Test landing_zone_move with validate_only=True"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_md5_object(obj)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
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
        flow.build()
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'ACTIVE')
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
        )
        sample_coll_path = os.path.join(self.sample_path, COLL_NAME)
        self.assertEqual(self.irods.collections.exists(sample_coll_path), False)

    def test_revert(self):
        """Test reverting landing_zone_move"""
        coll_path = os.path.join(self.zone_path, COLL_NAME)
        zone_coll = self.irods.collections.create(coll_path)
        obj = self.make_object(zone_coll, OBJ_NAME)
        obj_path = obj.path
        self.make_md5_object(obj)

        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
        )

        flow_data = {'zone_uuid': str(self.zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        flow.build(force_fail=True)
        flow.run()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.status, 'FAILED')
        self.assertEqual(self.irods.collections.exists(coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
        )
        sample_obj_path = os.path.join(self.sample_path, COLL_NAME, OBJ_NAME)
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + '.md5'),
            False,
        )
        self.assert_irods_access(
            self.user.username, zone_coll, IRODS_ACCESS_OWN
        )

    def test_move_restrict(self):
        """Test landing_zone_move with created and restricted collections"""
        # Create new zone with restricted collections
        new_zone = self.make_landing_zone(
            title=ZONE_TITLE + '_new',
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='CREATING',
        )
        self.make_zone_taskflow(
            zone=new_zone,
            colls=[MISC_FILES_COLL, RESULTS_COLL],
            restrict_colls=True,
        )
        new_zone_path = self.irods_backend.get_path(new_zone)
        self.assertEqual(new_zone.status, 'ACTIVE')
        self.assertEqual(self.irods.collections.exists(new_zone_path), True)
        results_path = os.path.join(new_zone_path, RESULTS_COLL)
        self.assertEqual(self.irods.collections.exists(results_path), True)

        empty_coll_path = os.path.join(results_path, COLL_NAME)
        self.irods.collections.create(empty_coll_path)
        obj_coll_path = os.path.join(results_path, OBJ_COLL_NAME)
        obj_coll = self.irods.collections.create(obj_coll_path)
        obj = self.make_object(obj_coll, OBJ_NAME)
        self.make_md5_object(obj)
        obj_path = os.path.join(obj_coll_path, OBJ_NAME)
        sample_obj_path = os.path.join(
            self.sample_path, RESULTS_COLL, OBJ_COLL_NAME, OBJ_NAME
        )

        self.assertEqual(self.irods.collections.exists(empty_coll_path), True)
        self.assertEqual(self.irods.collections.exists(obj_coll_path), True)
        self.assertEqual(self.irods.data_objects.exists(obj_path), True)
        self.assertEqual(
            self.irods.data_objects.exists(obj_path + '.md5'), True
        )
        self.assertEqual(self.irods.data_objects.exists(sample_obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(sample_obj_path + '.md5'),
            False,
        )

        flow_data = {'zone_uuid': str(new_zone.sodar_uuid)}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='landing_zone_move',
            flow_data=flow_data,
        )
        flow.build()
        flow.run()

        new_zone.refresh_from_db()
        self.assertEqual(new_zone.status, 'MOVED')
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
            self.irods.data_objects.exists(sample_obj_path + '.md5'),
            True,
        )
        self.assert_irods_access(
            self.group_name,
            sample_obj_path,
            IRODS_ACCESS_READ,
        )
        self.assert_irods_access(
            self.group_name,
            sample_obj_path + '.md5',
            IRODS_ACCESS_READ,
        )


class TestProjectCreate(TaskflowbackendTestBase):
    """Tests for the project_create flow"""

    def test_create(self):
        """Test project_create for creating a project"""
        # Create project without taskflow
        project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(project, self.user, self.role_owner)
        group_name = self.irods_backend.get_user_group_name(project)

        self.assert_irods_coll(project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)

        flow_data = {
            'owner': self.user.username,
            'users_add': [self.user_owner_cat.username],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=project,
            flow_name='project_create',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), ProjectCreateFlow)
        flow.build()
        flow.run()

        self.assert_irods_coll(project, expected=True)
        group = self.irods.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name, self.irods_backend.get_path(project), IRODS_ACCESS_READ
        )
        self.assertIsInstance(
            self.irods.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(project, self.user, True)
        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('title').value,
            project.title,
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value,
            META_EMPTY_VALUE,
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        # Assert inherited category owner status
        self.assertIsInstance(
            self.irods.users.get(self.user_owner_cat.username), iRODSUser
        )
        self.assert_group_member(project, self.user_owner_cat, True)


class TestProjectUpdate(TaskflowbackendTestBase):
    """Tests for the project_update flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_path = self.irods_backend.get_path(self.project)

    def test_update_metadata(self):
        """Test project_update with updated metadata"""
        self.assertNotEqual(self.project.title, UPDATED_TITLE)
        self.assertNotEqual(self.project.description, UPDATED_DESC)
        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('title').value,
            self.project.title,
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value,
            META_EMPTY_VALUE,
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
        flow.build()
        flow.run()

        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('title').value,
            UPDATED_TITLE,
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value,
            UPDATED_DESC,
        )

    def test_update_parent(self):
        """Test project_update with updated parent"""
        user_contrib = self.make_user('contrib_user')
        user_cat_new = self.make_user('user_cat_new')
        self.make_assignment_taskflow(
            self.project, user_contrib, self.role_contributor
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        self.assert_group_member(self.project, user_contrib, True)
        self.assert_group_member(self.project, user_cat_new, False)
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
            'users_add': [user_cat_new.username],
            'users_delete': [self.user_owner_cat.username],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='project_update',
            flow_data=flow_data,
        )
        flow.build()
        flow.run()

        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_owner_cat, False)
        self.assert_group_member(self.project, user_contrib, True)
        self.assert_group_member(self.project, user_cat_new, True)
        project_coll = self.irods.collections.get(self.project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(new_category.sodar_uuid),
        )


class TestPublicAccessUpdate(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Tests for the public_access_update flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)
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
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

        flow_data = {'path': self.sample_path, 'access': True}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), PublicAccessUpdateFlow)
        flow.build()
        flow.run()

        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, IRODS_ACCESS_READ
        )

    def test_disable_access(self):
        """Test public_access_update to disable public access"""
        self.project.public_guest_access = True
        self.project.save()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, IRODS_ACCESS_READ
        )

        flow_data = {'path': self.sample_path, 'access': False}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        flow.build()
        flow.run()

        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

    def test_revert(self):
        """Test reverting public_access_update"""
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

        flow_data = {'path': self.sample_path, 'access': True}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='public_access_update',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), PublicAccessUpdateFlow)
        flow.build(force_fail=True)
        flow.run()

        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)

    def test_enable_access_anon(self):
        """Test enabling public access with anonymous access enabled"""
        self.make_irods_colls(self.investigation)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
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
            flow.build()
            flow.run()

        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, IRODS_ACCESS_READ
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
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, IRODS_ACCESS_READ
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
        flow.build()
        flow.run()

        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))


class TestRoleDelete(TaskflowbackendTestBase):
    """Tests for the role_delete flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.user_new = self.make_user('user_new')
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.project_path = self.irods_backend.get_path(self.project)

    def test_delete(self):
        """Test role_delete for deleting a role assignment"""
        self.assert_group_member(self.project, self.user_new, True)
        flow_data = {'username': self.user_new.username}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_delete',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), RoleDeleteFlow)
        flow.build()
        flow.run()
        self.assert_group_member(self.project, self.user_new, False)


class TestRoleUpdate(TaskflowbackendTestBase):
    """Tests for the role_update flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.project_path = self.irods_backend.get_path(self.project)

    def test_update(self):
        """Test role_update for creating a role assignment"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_contributor)
        self.assert_group_member(self.project, user_new, False)

        flow_data = {'username': user_new.username}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), RoleUpdateFlow)
        flow.build()
        flow.run()

        self.assert_group_member(self.project, user_new, True)


class TestRoleUpdateIrodsBatch(TaskflowbackendTestBase):
    """Tests for the role_update_irods_batch flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        # self.project_path = self.irods_backend.get_path(self.project)
        self.group_name = self.irods_backend.get_user_group_name(self.project)
        self.project_group = self.irods.user_groups.get(self.group_name)
        self.user_new1 = self.make_user('user_new1')
        self.user_new2 = self.make_user('user_new2')

    def test_add(self):
        """Test role_update_irods_batch for adding users"""
        self.assert_group_member(self.project, self.user_new1, False)
        self.assert_group_member(self.project, self.user_new2, False)

        flow_data = {
            'roles_add': [
                {
                    'user_name': self.user_new1.username,
                    'project_uuid': str(self.project.sodar_uuid),
                },
                {
                    'user_name': self.user_new2.username,
                    'project_uuid': str(self.project.sodar_uuid),
                },
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
        flow.build()
        flow.run()

        self.assert_group_member(self.project, self.user_new1, True)
        self.assert_group_member(self.project, self.user_new2, True)

    def test_add_multi_project(self):
        """Test role_update_irods_batch for adding users to multiple projects"""
        new_project, _ = self.make_project_taskflow(
            'NewProject2', PROJECT_TYPE_PROJECT, self.category, self.user
        )

        self.assert_group_member(self.project, self.user_new1, False)
        self.assert_group_member(self.project, self.user_new2, False)
        self.assert_group_member(new_project, self.user_new1, False)
        self.assert_group_member(new_project, self.user_new2, False)

        flow_data = {
            'roles_add': [
                {
                    'user_name': self.user_new1.username,
                    'project_uuid': str(self.project.sodar_uuid),
                },
                {
                    'user_name': self.user_new2.username,
                    'project_uuid': str(new_project.sodar_uuid),
                },
            ],
            'roles_delete': [],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        flow.build()
        flow.run()

        self.assert_group_member(self.project, self.user_new1, True)
        self.assert_group_member(self.project, self.user_new2, False)
        self.assert_group_member(new_project, self.user_new1, False)
        self.assert_group_member(new_project, self.user_new2, True)

    def test_delete(self):
        """Test role_update_irods_batch for deleting users"""
        self.irods.users.create(
            self.user_new1.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.irods.users.create(
            self.user_new2.username, 'rodsuser', settings.IRODS_ZONE
        )
        self.project_group.addmember(self.user_new1.username)
        self.project_group.addmember(self.user_new2.username)

        self.assert_group_member(self.project, self.user_new1, True)
        self.assert_group_member(self.project, self.user_new2, True)

        flow_data = {
            'roles_add': [],
            'roles_delete': [
                {
                    'user_name': self.user_new1.username,
                    'project_uuid': str(self.project.sodar_uuid),
                },
                {
                    'user_name': self.user_new2.username,
                    'project_uuid': str(self.project.sodar_uuid),
                },
            ],
        }
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='role_update_irods_batch',
            flow_data=flow_data,
        )
        flow.build()
        flow.run()

        self.assert_group_member(self.project, self.user_new1, False)
        self.assert_group_member(self.project, self.user_new2, False)


class TestSheetCollsCreate(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Tests for the sheet_colls_create flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)
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
        flow.build()
        flow.run()

        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, True)
        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(PUBLIC_GROUP, self.sample_path, None)
        results_path = os.path.join(self.sample_path, RESULTS_COLL)
        self.assertEqual(self.irods.collections.exists(results_path), True)
        self.assert_irods_access(
            self.group_name, results_path, IRODS_ACCESS_READ
        )
        misc_path = os.path.join(self.sample_path, MISC_FILES_COLL)
        self.assertEqual(self.irods.collections.exists(misc_path), True)
        self.assert_irods_access(self.group_name, misc_path, IRODS_ACCESS_READ)

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
        flow.build()
        flow.run()

        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, IRODS_ACCESS_READ
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
        flow.build()
        flow.run()

        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            self.group_name, self.sample_path, IRODS_ACCESS_READ
        )
        self.assert_irods_access(
            PUBLIC_GROUP, self.sample_path, IRODS_ACCESS_READ
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
        flow.build(force_fail=True)
        flow.run()

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
        flow.build(force_fail=True)
        flow.run()

        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.irods_status, False)
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))


class TestSheetDelete(
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    TaskflowbackendTestBase,
):
    """Tests for the sheet_delete flow"""

    def setUp(self):
        super().setUp()
        self.project, self.as_owner = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)
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

        flow_data = {}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_delete',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), SheetDeleteFlow)
        flow.build()
        flow.run()

        self.assertIsNone(
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

        flow_data = {}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_delete',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), SheetDeleteFlow)
        flow.build()
        flow.run()

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
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='CREATING',
        )
        self.make_zone_taskflow(zone)
        zone_path = self.irods_backend.get_path(zone)
        self.assertEqual(self.irods.collections.exists(zone_path), True)

        flow_data = {}
        flow = self.taskflow.get_flow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name='sheet_delete',
            flow_data=flow_data,
        )
        self.assertEqual(type(flow), SheetDeleteFlow)
        flow.build()
        flow.run()

        self.assertIsNone(
            Investigation.objects.filter(
                project=self.project, active=True
            ).first()
        )
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertEqual(self.irods.collections.exists(zone_path), False)

    # NOTE: Can't be reverted
