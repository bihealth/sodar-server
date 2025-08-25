"""Tests for Taskflow tasks in the taskflowbackend app"""

import uuid

from irods.collection import iRODSCollection
from irods.data_object import iRODSDataObject
from irods.exception import CollectionDoesNotExist, DataObjectDoesNotExist
from irods.meta import iRODSMeta
from irods.ticket import Ticket
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings
from django.test import override_settings

from test_plus import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI
from projectroles.tests.test_models import ProjectMixin

# Timeline dependency
from timeline.tests.test_models import TimelineEventMixin

# Landingzones dependency
from landingzones.constants import ZONE_STATUS_ACTIVE, DEFAULT_STATUS_INFO
from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tests.base import (
    TaskflowViewTestBase,
    HASH_SCHEME_SHA256,
    TICKET_STR,
)
from taskflowbackend.tasks.irods_tasks import *  # noqa
from taskflowbackend.tasks.sodar_tasks import TimelineEventExtraDataUpdateTask


plugin_api = PluginAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
USER_PREFIX = 'omics_'
IRODS_ZONE = settings.IRODS_ZONE
SHEET_PATH = SHEET_DIR + 'i_small.zip'
DEFAULT_USER_GROUP = USER_PREFIX + 'group1'
GROUP_USER = USER_PREFIX + 'user1'
GROUPLESS_USER = USER_PREFIX + 'user2'
ADMIN_USER = settings.IRODS_USER

TEST_COLL_NAME = 'test'
NEW_COLL_NAME = 'test_new'
NEW_COLL2_NAME = 'test_new2'
TEST_OBJ_NAME = 'test1.txt'
SUB_COLL_NAME = 'sub'
SUB_COLL_NAME2 = 'sub2'
MOVE_COLL_NAME = 'move_coll'

TEST_USER = USER_PREFIX + 'user3'
TEST_KEY = 'test_key'
TEST_VAL = 'test_val'
TEST_UNITS = 'test_units'
TEST_USER_GROUP = USER_PREFIX + 'group2'
RODS_USER_TYPE = 'rodsuser'

# iRODS access control values
# NOTE: input values set in base class for iRODS 4.2/4.3 support
IRODS_ACCESS_READ_IN = 'read'
IRODS_ACCESS_WRITE_IN = 'write'
IRODS_ACCESS_NULL = 'null'

BATCH_SRC_NAME = 'batch_src'
BATCH_DEST_NAME = 'batch_dest'
BATCH_OBJ_NAME = 'batch_obj'
BATCH_OBJ2_NAME = 'batch_obj2'

SUFFIX_OBJ_NAME_BAM = 'test.bam'
SUFFIX_OBJ_NAME_VCF = 'test.vcf.gz'
SUFFIX_OBJ_NAME_TXT = 'test.txt'

EXTRA_DATA = {'test': 1}
MD5_SUFFIX = '.md5'
SHA256_SUFFIX = '.sha256'


class TaskTestMixin:
    """Helpers for taskflow task tests"""

    flow = None
    irods = None
    irods_backend = None
    project = None

    def run_flow(self):
        return self.flow.run(verbose=False)

    def init_flow(self):
        return BaseLinearFlow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name=str(uuid.uuid4()),
            flow_data={},
        )


class IRODSTaskTestBase(TaskTestMixin, TaskflowViewTestBase):
    """Base test class for iRODS tasks"""

    def add_task(self, cls, name, inject, force_fail=False):
        """Add task based on IrodsBaseTask"""
        self.flow.add_task(
            cls(
                name=name,
                irods=self.irods,
                verbose=False,
                inject=inject,
                force_fail=force_fail,
            )
        )

    def get_test_coll(self):
        return self.irods.collections.get(self.test_coll_path)

    def get_user_access(self, target, user_name):
        target_access = self.irods.acls.get(target=target)
        return next(
            (x for x in target_access if x.user_name == user_name), None
        )

    def setUp(self):
        super().setUp()
        # Init project
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Init vars and iRODS collections
        self.project_path = self.irods_backend.get_path(self.project)
        self.test_coll = self.irods.collections.create(
            os.path.join(self.project_path, TEST_COLL_NAME)
        )
        self.test_coll_path = self.test_coll.path
        self.new_coll_path = os.path.join(self.project_path, NEW_COLL_NAME)
        # Init flow
        self.flow = self.init_flow()


class TestCreateCollectionTask(IRODSTaskTestBase):
    """Tests for CreateCollectionTask"""

    def test_execute(self):
        """Test collection creation"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self.run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

    def test_execute_twice(self):
        """Test collection creation twice"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        self.run_flow()
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.flow = self.init_flow()
        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self.run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

    def test_revert_created(self):
        """Test collection creation reverting after creating"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))
        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()
        self.assertFalse(result)
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_revert_not_modified(self):
        """Test collection creation reverting without modification"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))
        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self.run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

        self.flow = self.init_flow()
        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()
        self.assertFalse(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_execute_nested(self):
        """Test collection creation with nested collections"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, '/subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={
                'path': os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            },
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            os.path.join(self.new_coll_path, 'subcoll1'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2'),
        )
        result = self.run_flow()

        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_execute_nested_twice(self):
        """Test collection creation twice with nested collections"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={
                'path': os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            },
        )
        result = self.run_flow()

        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.flow = self.init_flow()
        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={
                'path': os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            },
        )
        result = self.run_flow()

        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_revert_created_nested(self):
        """Test creation reverting with nested collections"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={
                'path': os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertFalse(result)
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))


class TestRemoveCollectionTask(IRODSTaskTestBase):
    """Tests for RemoveCollectionTask"""

    def test_execute(self):
        """Test collection removal"""
        self.add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
        )
        coll = self.irods.collections.get(self.test_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.test_coll_path,
        )

    def test_execute_twice(self):
        """Test collection removal twice"""
        self.add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
        )
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.test_coll_path,
        )

    def test_revert_removed(self):
        """Test collection removal reverting after removing"""
        self.add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        coll = self.irods.collections.get(self.test_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

    def test_revert_not_modified(self):
        """Test collection removal reverting without modification"""
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path,
        )
        self.flow = self.init_flow()
        self.add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path,
        )


class TestRemoveDataObjectTask(IRODSTaskTestBase):
    """Tests for RemoveDataObjectTask"""

    def setUp(self):
        super().setUp()
        # Init object to be removed
        self.obj_path = os.path.join(self.test_coll_path, TEST_OBJ_NAME)
        self.obj = self.irods.data_objects.create(self.obj_path)

    def test_execute(self):
        """Test data object removal"""
        self.add_task(
            cls=RemoveDataObjectTask,
            name='Remove data object',
            inject={'path': self.obj_path},
        )
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)
        result = self.run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(self.obj_path)

    def test_execute_twice(self):
        """Test data object removal twice"""
        self.add_task(
            cls=RemoveDataObjectTask,
            name='Remove data object',
            inject={'path': self.obj_path},
        )
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(
            cls=RemoveDataObjectTask,
            name='Remove data_object',
            inject={'path': self.obj_path},
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(self.obj_path)

    def test_revert_removed(self):
        """Test data object removal reverting after removing"""
        self.add_task(
            cls=RemoveDataObjectTask,
            name='Remove data_object',
            inject={'path': self.obj_path},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)

    def test_revert_not_modified(self):
        """Test data object removal reverting without modification"""
        obj_path2 = os.path.join(self.test_coll_path, 'move_obj2')
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(obj_path2)

        self.flow = self.init_flow()
        self.add_task(
            cls=RemoveDataObjectTask,
            name='Remove data object',
            inject={'path': obj_path2},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(obj_path2)


class TestSetCollectionMetadataTask(IRODSTaskTestBase):
    """Tests for SetCollectionMetadataTask"""

    def test_execute(self):
        """Test setting metadata"""
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        test_coll = self.get_test_coll()
        self.assertRaises(Exception, test_coll.metadata.get_one, TEST_KEY)
        result = self.run_flow()

        self.assertEqual(result, True)
        # NOTE: We must retrieve collection again to refresh its metadata
        test_coll = self.get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.name, TEST_KEY)
        self.assertEqual(meta_item.value, TEST_VAL)
        self.assertEqual(meta_item.units, TEST_UNITS)

    def test_execute_twice(self):
        """Test setting metadata twice"""
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        test_coll = self.get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)

    def test_revert_created(self):
        """Test metadata setting reverting after creating a new item"""
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        test_coll = self.get_test_coll()
        self.assertRaises(KeyError, test_coll.metadata.get_one, TEST_KEY)

    def test_revert_modified(self):
        """Test metadata setting reverting after modification"""
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        self.run_flow()

        self.flow = self.init_flow()
        new_val = 'new value'
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': new_val,
                'units': TEST_UNITS,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        test_coll = self.get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.value, TEST_VAL)  # Original value

    def test_revert_not_modified(self):
        """Test metadata setting reverting without modification"""
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
            force_fail=True,
        )
        result = self.run_flow()

        self.assertNotEqual(result, True)
        test_coll = self.get_test_coll()
        self.assertIsInstance(test_coll, iRODSCollection)

    def test_execute_empty(self):
        """Test setting an empty value for metadata"""
        self.add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': '',
                'units': TEST_UNITS,
            },
        )
        test_coll = self.get_test_coll()
        self.assertRaises(Exception, test_coll.metadata.get_one, TEST_KEY)
        result = self.run_flow()

        self.assertEqual(result, True)
        test_coll = self.get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.name, TEST_KEY)
        self.assertEqual(meta_item.value, META_EMPTY_VALUE)
        self.assertEqual(meta_item.units, TEST_UNITS)


class TestCreateUserGroupTask(IRODSTaskTestBase):
    """Tests for CreateUserGroupTask"""

    def test_execute(self):
        """Test user group creation"""
        self.add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        self.assertRaises(
            GroupDoesNotExist, self.irods.user_groups.get, TEST_USER_GROUP
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)

    def test_execute_twice(self):
        """Test user group creation twice"""
        self.add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)

    def test_revert_created(self):
        """Test collection creation reverting after creation"""
        self.add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            GroupDoesNotExist, self.irods.user_groups.get, TEST_USER_GROUP
        )

    def test_revert_not_modified(self):
        """Test collection creation reverting without modification"""
        self.add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)


class TestSetAccessTask(IRODSTaskTestBase):
    """Tests for SetAccessTask"""

    def setUp(self):
        super().setUp()
        self.sub_coll_path = os.path.join(self.test_coll_path, SUB_COLL_NAME)
        # Init default user group
        self.irods.user_groups.create(DEFAULT_USER_GROUP)

    def test_execute_read(self):
        """Test access setting for read"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)
        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_execute_write(self):
        """Test access setting for write/modify"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)

        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_write)

    def test_execute_twice(self):
        """Test access setting twice"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_revert_created(self):
        """Test reverting created access"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsNone(user_access)
        # self.assertEqual(user_access.access_name, TEST_ACCESS_NULL)

    def test_revert_modified(self):
        """Test reverting modified access"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_revert_not_modified(self):
        """Test access setting reverting without modification"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_execute_no_recursion(self):
        """Test access setting for a collection with recursive=False"""
        # Set up subcollection and test user
        sub_coll = self.irods.collections.create(self.sub_coll_path)
        self.irods.users.create(
            user_name=TEST_USER,
            user_type=RODS_USER_TYPE,
            user_zone=self.irods.zone,
        )
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': TEST_USER,
                'irods_backend': self.irods_backend,
                'recursive': False,
            },
        )

        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=TEST_USER
        )
        self.assertEqual(user_access, None)
        user_access = self.get_user_access(target=sub_coll, user_name=TEST_USER)
        self.assertEqual(user_access, None)

        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=TEST_USER
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

        user_access = self.get_user_access(target=sub_coll, user_name=TEST_USER)
        self.assertEqual(user_access, None)

    def test_revert_no_recursion(self):
        """Test access setting reverting for a collection with recursive=False"""
        sub_coll = self.irods.collections.create(self.sub_coll_path)
        self.irods.users.create(
            user_name=TEST_USER,
            user_type=RODS_USER_TYPE,
            user_zone=self.irods.zone,
        )

        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': TEST_USER,
                'irods_backend': self.irods_backend,
                'recursive': False,
            },
            force_fail=True,
        )  # FAIL

        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

        user_access = self.get_user_access(target=sub_coll, user_name=TEST_USER)
        self.assertEqual(user_access, None)

        result = self.run_flow()

        self.assertEqual(result, False)
        user_access = self.get_user_access(
            target=self.get_test_coll(), user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

        user_access = self.get_user_access(target=sub_coll, user_name=TEST_USER)
        self.assertEqual(user_access, None)


class TestCleanupAccessTask(IRODSTaskTestBase):
    """Tests for CleanupccessTask"""

    def set_irods_access(self, path, user_name, access, recursive=True):
        """Set iRODS access"""
        if recursive and self.irods.data_objects.exists(path):
            recursive = False
        acl = iRODSAccess(
            access_name=access,
            path=path,
            user_name=user_name,
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=recursive)

    def setUp(self):
        super().setUp()
        self.user_test = self.make_user(TEST_USER)
        self.irods.users.create(TEST_USER, RODS_USER_TYPE)
        self.task_name = 'Cleanup access'

    def test_execute_coll(self):
        """Test execute() with collection access"""
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        self.assertIsNone(self.get_user_access(self.test_coll, TEST_USER))

        # Set test user access to coll
        self.set_irods_access(
            self.test_coll.path, TEST_USER, self.irods_access_write
        )
        ua = self.get_user_access(self.test_coll, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)

        self.add_task(
            cls=CleanupAccessTask,
            name=self.task_name,
            inject={
                'path': self.test_coll.path,
                'user_names': [ADMIN_USER],  # No test user
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        # Admin should still have access
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        # Test user should not have access
        self.assertIsNone(self.get_user_access(self.test_coll, TEST_USER))

    def test_execute_coll_allowed(self):
        """Test execute() with collection access and all users allowed"""
        self.set_irods_access(
            self.test_coll.path, TEST_USER, self.irods_access_write
        )
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        ua = self.get_user_access(self.test_coll, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)
        self.add_task(
            cls=CleanupAccessTask,
            name=self.task_name,
            inject={
                'path': self.test_coll.path,
                'user_names': [ADMIN_USER, TEST_USER],
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        # Both users should still have access
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        ua = self.get_user_access(self.test_coll, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)

    def test_execute_coll_non_existent_user(self):
        """Test execute() with collection access aand non-existent user"""
        self.set_irods_access(
            self.test_coll.path, TEST_USER, self.irods_access_write
        )
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        ua = self.get_user_access(self.test_coll, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)
        self.add_task(
            cls=CleanupAccessTask,
            name=self.task_name,
            inject={
                'path': self.test_coll.path,
                'user_names': [ADMIN_USER, TEST_USER, 'NON-EXISTENT-USER'],
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)  # We should not fail
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        ua = self.get_user_access(self.test_coll, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)

    def test_execute_group(self):
        """Test execute() with user group"""
        self.irods.user_groups.create(DEFAULT_USER_GROUP)
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        self.assertIsNone(
            self.get_user_access(self.test_coll, DEFAULT_USER_GROUP)
        )
        self.set_irods_access(
            self.test_coll.path, DEFAULT_USER_GROUP, self.irods_access_write
        )
        ua = self.get_user_access(self.test_coll, DEFAULT_USER_GROUP)
        self.assertEqual(ua.access_name, self.irods_access_write)
        self.add_task(
            cls=CleanupAccessTask,
            name=self.task_name,
            inject={
                'path': self.test_coll.path,
                'user_names': [ADMIN_USER],  # No user group
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        ua = self.get_user_access(self.test_coll, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        self.assertIsNone(
            self.get_user_access(self.test_coll, DEFAULT_USER_GROUP)
        )

    def test_execute_obj(self):
        """Test execute() with data object access"""
        obj = self.make_irods_object(self.test_coll, TEST_OBJ_NAME)
        self.set_irods_access(obj.path, TEST_USER, self.irods_access_write)
        ua = self.get_user_access(obj, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        ua = self.get_user_access(obj, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)
        self.add_task(
            cls=CleanupAccessTask,
            name=self.task_name,
            inject={
                'path': self.test_coll.path,
                'user_names': [ADMIN_USER],  # No test user
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        ua = self.get_user_access(obj, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        self.assertIsNone(self.get_user_access(obj, TEST_USER))

    def test_execute_obj_allowed(self):
        """Test execute() with data object access and all users allowed"""
        obj = self.make_irods_object(self.test_coll, TEST_OBJ_NAME)
        self.set_irods_access(obj.path, TEST_USER, self.irods_access_write)
        ua = self.get_user_access(obj, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        ua = self.get_user_access(obj, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)
        self.add_task(
            cls=CleanupAccessTask,
            name=self.task_name,
            inject={
                'path': self.test_coll.path,
                'user_names': [ADMIN_USER, TEST_USER],
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        ua = self.get_user_access(obj, ADMIN_USER)
        self.assertEqual(ua.access_name, self.irods_access_own)
        ua = self.get_user_access(obj, TEST_USER)
        self.assertEqual(ua.access_name, self.irods_access_write)


class TestIssueTicketTask(IRODSTaskTestBase):
    """Tests for IssueTicketTask"""

    def setUp(self):
        super().setUp()

    def test_execute(self):
        """Test issuing a ticket"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self.add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_execute_twice(self):
        """Test issuing a ticket_twice"""
        self.add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

        self.flow = self.init_flow()
        self.add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_revert_modified(self):
        """Test reverting a ticket issuing"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self.add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

    def test_revert_not_modified(self):
        """Test reverting a ticket issuing with no modification"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_ACCESS_READ_IN, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )


class TestDeleteTicketTask(IRODSTaskTestBase):
    """Tests for DeleteTicketTask"""

    def test_execute(self):
        """Test deleting a ticket"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_ACCESS_READ_IN, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

    def test_execute_twice(self):
        """Test deleting a ticket twice"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_ACCESS_READ_IN, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

        self.flow = self.init_flow()
        self.add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

    def test_revert_modified(self):
        """Test reverting ticket deletion"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_ACCESS_READ_IN, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_revert_not_modified(self):
        """Test reverting ticket deletion with no modification"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self.add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))


class TestCreateUserTask(IRODSTaskTestBase):
    """Tests for CreateUserTask"""

    def test_execute(self):
        """Test user creation"""
        self.add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': RODS_USER_TYPE},
        )
        self.assertRaises(UserDoesNotExist, self.irods.users.get, TEST_USER)
        result = self.run_flow()

        self.assertEqual(result, True)
        user = self.irods.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)

    def test_execute_twice(self):
        """Test user creation twice"""
        self.add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': RODS_USER_TYPE},
        )
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': RODS_USER_TYPE},
        )
        self.run_flow()

        user = self.irods.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)

    def test_revert_created(self):
        """Test user creation reverting after creating"""
        self.add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': RODS_USER_TYPE},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(UserDoesNotExist, self.irods.users.get, TEST_USER)

    def test_revert_not_modified(self):
        """Test user creation reverting without modification"""
        self.add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': RODS_USER_TYPE},
        )
        result = self.run_flow()
        self.assertEqual(result, True)

        # Init and run new flow
        self.flow = self.init_flow()
        self.add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': RODS_USER_TYPE},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        user = self.irods.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)


class TestAddUserToGroupTask(IRODSTaskTestBase):
    """Tests for AddUserToGroupTask"""

    def setUp(self):
        super().setUp()
        # Init default user group
        group = self.irods.user_groups.create(DEFAULT_USER_GROUP)
        # Init default users
        self.irods.users.create(
            user_name=GROUP_USER, user_type=RODS_USER_TYPE, user_zone=IRODS_ZONE
        )
        group.addmember(GROUP_USER)
        self.irods.users.create(
            user_name=GROUPLESS_USER,
            user_type=RODS_USER_TYPE,
            user_zone=IRODS_ZONE,
        )

    def test_execute(self):
        """Test user addition"""
        self.add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), False)
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)

    def test_execute_twice(self):
        """Test user addition twice"""
        self.add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)

    def test_revert_modified(self):
        """Test user addition reverting after modification"""
        self.add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
            force_fail=True,
        )  # FAILS
        result = self.run_flow()

        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), False)

    def test_revert_not_modified(self):
        """Test user addition reverting without modification"""
        self.add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
            force_fail=True,
        )  # FAILS
        result = self.run_flow()

        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)


class TestRemoveUserFromGroupTask(IRODSTaskTestBase):
    """Tests for RemoveUserFromGroupTask"""

    def setUp(self):
        super().setUp()
        # Init default user group
        group = self.irods.user_groups.create(DEFAULT_USER_GROUP)
        # Init default users
        self.irods.users.create(
            user_name=GROUP_USER, user_type=RODS_USER_TYPE, user_zone=IRODS_ZONE
        )
        group.addmember(GROUP_USER)

    def test_execute(self):
        """Test user removal"""
        self.add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), True)
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)

    def test_execute_twice(self):
        """Test user removal twice"""
        self.add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)

    def test_execute_no_group(self):
        """Test user removal with no existing group"""
        self.irods.users.remove(DEFAULT_USER_GROUP)
        with self.assertRaises(GroupDoesNotExist):
            self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        result = self.run_flow()
        self.assertEqual(result, True)

    def test_revert_modified(self):
        """Test user ramoval reverting after modification"""
        self.add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
            force_fail=True,
        )  # FAILS
        result = self.run_flow()
        self.assertNotEqual(result, True)

        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), True)

    def test_revert_not_modified(self):
        """Test user removal reverting without modification"""
        self.add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
            force_fail=True,
        )  # FAILS
        result = self.run_flow()

        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)


class TestMoveDataObjectTask(IRODSTaskTestBase):
    """Tests for MoveDataObjectTask"""

    def setUp(self):
        super().setUp()
        self.obj_path = os.path.join(self.test_coll_path, TEST_OBJ_NAME)
        self.move_coll_path = os.path.join(self.test_coll_path, MOVE_COLL_NAME)
        # Init object to be copied
        self.move_obj = self.irods.data_objects.create(self.obj_path)
        # Init collection for copying
        self.move_coll = self.irods.collections.create(self.move_coll_path)

    def test_execute(self):
        """Test moving a data object"""
        move_obj_path = os.path.join(self.move_coll_path, TEST_OBJ_NAME)
        self.add_task(
            cls=MoveDataObjectTask,
            name='Move data object',
            inject={
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
        )
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(move_obj_path)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), False)
        self.assertEqual(self.irods.data_objects.exists(move_obj_path), True)

    def test_revert(self):
        """Test reverting the moving of a data object"""
        move_obj_path = os.path.join(self.move_coll_path, TEST_OBJ_NAME)
        self.add_task(
            cls=MoveDataObjectTask,
            name='Move data object',
            inject={
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
            force_fail=True,
        )  # FAILS
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)
        self.assertEqual(self.irods.data_objects.exists(move_obj_path), False)

    def test_overwrite_failure(self):
        """Test moving a data object when a similarly named file exists"""
        new_obj_path = os.path.join(self.move_coll_path, TEST_OBJ_NAME)
        # Create object already in target
        new_obj = self.irods.data_objects.create(new_obj_path)
        self.add_task(
            cls=MoveDataObjectTask,
            name='Move data object',
            inject={
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
        )
        with self.assertRaises(Exception):
            self.run_flow()

        # Assert state of both objects after attempted move
        # TODO: Better way to compare file objects than checksum?
        # TODO: obj1 != obj2 even if they point to the same thing in iRODS..
        move_obj2 = self.irods.data_objects.get(self.obj_path)
        self.assertEqual(self.move_obj.checksum, move_obj2.checksum)
        new_obj2 = self.irods.data_objects.get(new_obj_path)
        self.assertEqual(new_obj.checksum, new_obj2.checksum)


class TestBatchCheckFileExistTask(
    SampleSheetIOMixin, LandingZoneMixin, IRODSTaskTestBase
):
    """Tests for BatchCheckFileExistTask"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create zone without taskflow
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.zone_path_len = len(self.zone_path.split('/'))
        # NOTE: We don't have to actually upload files for this task
        self.obj_path = os.path.join(self.zone_path, TEST_OBJ_NAME)
        # Default MD5 suffix
        self.chk_suffix = self.irods_backend.get_checksum_file_suffix()
        self.task_kw = {
            'cls': BatchCheckFileExistTask,
            'name': 'Check for file existence',
            'inject': {
                'file_paths': [self.obj_path],
                'chk_paths': [],
                'zone_path': self.zone_path,
                'chk_suffix': self.irods_backend.get_checksum_file_suffix(),
            },
        }
        self.ex_prefix = 'BatchCheckFileExistTask failed: Exception'

    def test_task_md5(self):
        """Test task with MD5 checksum file"""
        self.task_kw['inject']['chk_paths'] = [self.obj_path + self.chk_suffix]
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.status_info, DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE]
        )

    @override_settings(IRODS_HASH_SCHEME=HASH_SCHEME_SHA256)
    def test_task_sha256(self):
        """Test task with SHA256 checksum file"""
        chk_suffix = self.irods_backend.get_checksum_file_suffix()
        self.assertEqual(chk_suffix, '.sha256')
        self.task_kw['inject']['chk_suffix'] = chk_suffix
        self.task_kw['inject']['chk_paths'] = [self.obj_path + chk_suffix]
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.status_info, DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE]
        )

    def test_task_no_checksum(self):
        """Test task with no checksum file"""
        self.assertEqual(self.task_kw['inject']['chk_paths'], [])
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        ex_path = (
            '/'.join(self.obj_path.split('/')[self.zone_path_len :])
            + self.chk_suffix
        )
        expected = f'{self.ex_prefix}\n1 expected file missing:\n{ex_path}'
        self.assertEqual(expected, str(cm.exception))

    def test_task_md5_no_file(self):
        """Test task with MD5 checksum file and no data file"""
        self.task_kw['inject']['file_paths'] = []
        self.task_kw['inject']['chk_paths'] = [self.obj_path + self.chk_suffix]
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        ex_path = '/'.join(self.obj_path.split('/')[self.zone_path_len :])
        expected = f'{self.ex_prefix}\n1 expected file missing:\n{ex_path}'
        self.assertEqual(expected, str(cm.exception))

    @override_settings(IRODS_HASH_SCHEME=HASH_SCHEME_SHA256)
    def test_task_sha256_no_file(self):
        """Test task with SHA256 checksum file and no data file"""
        chk_suffix = self.irods_backend.get_checksum_file_suffix()
        self.task_kw['inject']['file_paths'] = []
        self.task_kw['inject']['chk_suffix'] = chk_suffix
        self.task_kw['inject']['chk_paths'] = [self.obj_path + chk_suffix]
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        ex_path = '/'.join(self.obj_path.split('/')[self.zone_path_len :])
        expected = f'{self.ex_prefix}\n1 expected file missing:\n{ex_path}'
        self.assertEqual(expected, str(cm.exception))

    @override_settings(IRODS_HASH_SCHEME=HASH_SCHEME_SHA256)
    def test_task_sha256_unexpected_md5(self):
        """Test task unexpected MD5 checksum file"""
        self.task_kw['inject'][
            'chk_suffix'
        ] = self.irods_backend.get_checksum_file_suffix()
        self.task_kw['inject']['chk_paths'] = [self.obj_path + MD5_SUFFIX]
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        ex_path = (
            '/'.join(self.obj_path.split('/')[self.zone_path_len :])
            + SHA256_SUFFIX
        )
        expected = f'{self.ex_prefix}\n1 expected file missing:\n{ex_path}'
        self.assertEqual(expected, str(cm.exception))

    def test_task_md5_unexpected_sha256(self):
        """Test task unexpected SHA256 checksum file"""
        self.task_kw['inject']['chk_paths'] = [self.obj_path + SHA256_SUFFIX]
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        ex_path = (
            '/'.join(self.obj_path.split('/')[self.zone_path_len :])
            + MD5_SUFFIX
        )
        expected = f'{self.ex_prefix}\n1 expected file missing:\n{ex_path}'
        self.assertEqual(expected, str(cm.exception))


class TestBatchValidateChecksumsTask(
    SampleSheetIOMixin, LandingZoneMixin, IRODSTaskTestBase
):
    """Tests for BatchValidateChecksumsTask"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create zone without taskflow
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.obj_name = 'test1.txt'  # TODO: Replace with TEST_OBJ_NAME
        self.zone_coll = self.irods.collections.create(self.zone_path)
        self.obj = self.make_irods_object(self.zone_coll, self.obj_name)
        self.obj_path = self.obj.path
        self.task_kw = {
            'cls': BatchValidateChecksumsTask,
            'name': 'Validate checksums',
            'inject': {
                'landing_zone': self.zone,
                'file_paths': [self.obj_path],
                'zone_path': self.zone_path,
                'irods_backend': self.irods_backend,
            },
        }

    def test_validate(self):
        """Test validating checksums"""
        self.make_checksum_object(self.obj)
        self.assertIsNotNone(self.obj.replicas[0].checksum)
        self.assertEqual(
            self.zone.status_info, DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE]
        )
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.status_info,
            DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE] + ' (1/1: 100%)',
        )

    # TODO: Test with SHA256 checksum (see #2170)

    def test_validate_invalid_in_file(self):
        """Test validating checksums with invalid checksum in file"""
        self.make_checksum_object(self.obj, content='xxx')
        self.assertEqual(
            self.zone.status_info, DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE]
        )
        self.add_task(**self.task_kw)
        zone_path_len = len(self.zone_path.split('/'))
        ex_path = '/'.join(self.obj_path.split('/')[zone_path_len:])
        expected = (
            f'Checksums do not match for 1 file:\n'
            f'Path: {ex_path}\n'
            f'Resource: demoResc\n'
            f'File: xxx\n'
            f'iRODS: {self.obj.replicas[0].checksum}'
        )
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        self.assertIn(expected, str(cm.exception))


class TestBatchSetAccessTask(IRODSTaskTestBase):
    """Tests for BatchSetAccessTask"""

    def setUp(self):
        super().setUp()
        self.sub_coll_path = os.path.join(self.test_coll_path, SUB_COLL_NAME)
        self.sub_coll_path2 = os.path.join(self.test_coll_path, SUB_COLL_NAME2)
        self.irods.collections.create(self.sub_coll_path)
        self.irods.collections.create(self.sub_coll_path2)
        self.paths = [self.sub_coll_path, self.sub_coll_path2]
        # Init default user group
        self.irods.user_groups.create(DEFAULT_USER_GROUP)

    def test_execute_read(self):
        """Test access setting for read"""
        self.add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_read
        )

    def test_execute_write(self):
        """Test access setting for write/modify"""
        self.add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_write
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_write
        )

    def test_execute_mixed(self):
        """Test access setting for both new and previously set access levels"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.sub_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

        self.flow = self.init_flow()
        self.add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_write
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_write
        )

    def test_revert_created(self):
        """Test reverting created access"""
        self.add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

    def test_revert_modified(self):
        """Test reverting modified access"""
        self.add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_read
        )

        self.flow = self.init_flow()
        self.add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_read
        )

    def test_revert_mixed(self):
        """Test reverting access for both new and existing access levels"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.sub_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

        self.flow = self.init_flow()
        self.add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)


class TestBatchCheckFileSuffixTask(
    SampleSheetIOMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    IRODSTaskTestBase,
):
    """Tests for BatchCheckFileSuffixTask"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
        )
        self.make_zone_taskflow(zone=self.zone)
        self.zone_path = self.irods_backend.get_path(self.zone)
        self.zone_coll = self.irods.collections.get(self.zone_path)
        self.obj_bam = self.make_irods_object(
            self.zone_coll, SUFFIX_OBJ_NAME_BAM
        )
        self.obj_vcf = self.make_irods_object(
            self.zone_coll, SUFFIX_OBJ_NAME_VCF
        )
        self.obj_txt = self.make_irods_object(
            self.zone_coll, SUFFIX_OBJ_NAME_TXT
        )
        self.obj_paths = [
            self.obj_bam.path,
            self.obj_vcf.path,
            self.obj_txt.path,
        ]
        self.task_kw = {
            'cls': BatchCheckFileSuffixTask,
            'name': 'Check file suffixes',
            'inject': {
                'file_paths': self.obj_paths,
                'zone_path': self.zone_path,
            },
        }

    def test_check_bam(self):
        """Test batch file suffix check with prohibited BAM type"""
        self.task_kw['inject']['suffixes'] = 'bam'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_vcf(self):
        """Test check with prohibited VCF type"""
        self.task_kw['inject']['suffixes'] = 'vcf.gz'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertNotIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_multiple(self):
        """Test check with multiple prohibited types"""
        self.task_kw['inject']['suffixes'] = 'bam,vcf.gz'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_multiple_not_found(self):
        """Test check with multiple types not found in files"""
        self.task_kw['inject']['suffixes'] = 'mp3,rar'
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

    def test_check_empty_list(self):
        """Test check with empty prohibition list"""
        self.task_kw['inject']['suffixes'] = ''
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

    def test_check_notation_dot(self):
        """Test check with dot notation in list"""
        self.task_kw['inject']['suffixes'] = '.bam'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_notation_asterisk(self):
        """Test check with asterisk notation in list"""
        self.task_kw['inject']['suffixes'] = '*bam'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_notation_combined(self):
        """Test check with combined notation in list"""
        self.task_kw['inject']['suffixes'] = '*.bam'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_extra_spaces(self):
        """Test check with extra spaces"""
        self.task_kw['inject']['suffixes'] = ' bam '
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_not_end_of_file(self):
        """Test check with given string not in end of file name"""
        self.task_kw['inject']['suffixes'] = 'test'
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

    def test_check_upper_case(self):
        """Test check with upper case string"""
        self.task_kw['inject']['suffixes'] = 'BAM'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)

    def test_check_invalid_strings(self):
        """Test check with invalid strings"""
        self.task_kw['inject']['suffixes'] = ',*,*.*'
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

    def test_check_invalid_valid(self):
        """Test check with mixed invalid and valid strings"""
        self.task_kw['inject']['suffixes'] = ',*,bam'
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
            ex = cm.exception
            self.assertIn(SUFFIX_OBJ_NAME_BAM, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_VCF, ex)
            self.assertNotIn(SUFFIX_OBJ_NAME_TXT, ex)


class TestBatchCreateCollectionsTask(IRODSTaskTestBase):
    """Tests for BatchCreateCollectionsTask"""

    def setUp(self):
        super().setUp()
        self.new_coll_path2 = os.path.join(self.project_path, NEW_COLL2_NAME)

    def test_execute(self):
        """Test batch collection creation"""
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'coll_paths': [self.new_coll_path, self.new_coll_path2]},
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path2,
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods.collections.get(self.new_coll_path),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods.collections.get(self.new_coll_path2),
            iRODSCollection,
        )

    def test_execute_twice(self):
        """Test batch collection creation twice"""
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'coll_paths': [self.new_coll_path, self.new_coll_path2]},
        )
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'coll_paths': [self.new_coll_path, self.new_coll_path2]},
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods.collections.get(self.new_coll_path),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods.collections.get(self.new_coll_path2),
            iRODSCollection,
        )

    def test_revert_created(self):
        """Test batch collection creation reverting after creating"""
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'coll_paths': [self.new_coll_path, self.new_coll_path2]},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path2,
        )

    def test_revert_not_modified(self):
        """Test batch collection creation reverting without modification"""
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'coll_paths': [self.new_coll_path, self.new_coll_path2]},
        )
        result = self.run_flow()
        self.assertEqual(result, True)

        # Init and run new flow
        self.flow = self.init_flow()
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'coll_paths': [self.new_coll_path, self.new_coll_path2]},
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertIsInstance(
            self.irods.collections.get(self.new_coll_path),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods.collections.get(self.new_coll_path2),
            iRODSCollection,
        )

    def test_execute_nested(self):
        """Test batch collection creation with nested collections"""
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'coll_paths': [
                    os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a'),
                    os.path.join(self.new_coll_path, 'subcoll2', 'subcoll2a'),
                ]
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll2', 'subcoll2a')
            )
        )

    def test_execute_nested_existing(self):
        """Test batch collection creation with existing collection"""
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'coll_paths': [
                    os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a'),
                    os.path.join(self.new_coll_path, 'subcoll1'),
                ]
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                os.path.join(self.new_coll_path, 'subcoll1')
            )
        )

    def test_revert_created_nested(self):
        """Test batch creation reverting with nested collections"""
        self.add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'coll_paths': [
                    os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a'),
                    os.path.join(self.new_coll_path, 'subcoll2', 'subcoll2a'),
                ]
            },
            force_fail=True,
        )  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            os.path.join(self.new_coll_path, 'subcoll1'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            os.path.join(self.new_coll_path, 'subcoll2'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            os.path.join(self.new_coll_path, 'subcoll2', 'subcoll2a'),
        )


class TestBatchMoveDataObjectsTask(
    SampleSheetIOMixin, LandingZoneMixin, IRODSTaskTestBase
):
    """Tests for BatchMoveDataObjectsTask"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create zone without taskflow
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )
        # Init default user group
        self.irods.user_groups.create(DEFAULT_USER_GROUP)
        # Init batch collections
        self.batch_src_path = os.path.join(self.test_coll_path, BATCH_SRC_NAME)
        self.batch_dest_path = os.path.join(
            self.test_coll_path, BATCH_DEST_NAME
        )
        self.src_coll = self.irods.collections.create(self.batch_src_path)
        self.dest_coll = self.irods.collections.create(self.batch_dest_path)
        # Init objects to be copied
        self.batch_obj_path = os.path.join(self.batch_src_path, BATCH_OBJ_NAME)
        self.batch_obj2_path = os.path.join(
            self.batch_src_path, BATCH_OBJ2_NAME
        )
        self.batch_obj = self.irods.data_objects.create(self.batch_obj_path)
        self.batch_obj2 = self.irods.data_objects.create(self.batch_obj2_path)
        self.dest_obj_path = os.path.join(self.batch_dest_path, BATCH_OBJ_NAME)
        self.dest_obj2_path = os.path.join(
            self.batch_dest_path, BATCH_OBJ2_NAME
        )

    def test_execute(self):
        """Test moving data objects and setting access"""
        self.add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'landing_zone': self.zone,
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': IRODS_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj_path))
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj2_path))
        self.assertEqual(
            self.get_user_access(
                target=self.irods.data_objects.get(self.batch_obj_path),
                user_name=DEFAULT_USER_GROUP,
            ),
            None,
        )
        self.assertEqual(
            self.get_user_access(
                target=self.irods.data_objects.get(self.batch_obj2_path),
                user_name=DEFAULT_USER_GROUP,
            ),
            None,
        )

        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertFalse(self.irods.data_objects.exists(self.batch_obj_path))
        self.assertFalse(self.irods.data_objects.exists(self.batch_obj2_path))
        self.assertTrue(self.irods.data_objects.exists(self.dest_obj_path))
        self.assertTrue(self.irods.data_objects.exists(self.dest_obj2_path))
        obj_access = self.get_user_access(
            target=self.irods.data_objects.get(
                f'{self.batch_dest_path}/batch_obj'
            ),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsInstance(obj_access, iRODSAccess)
        self.assertEqual(obj_access.access_name, self.irods_access_read)
        obj_access = self.get_user_access(
            target=self.irods.data_objects.get(self.dest_obj_path),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsInstance(obj_access, iRODSAccess)
        self.assertEqual(obj_access.access_name, self.irods_access_read)

    def test_revert(self):
        """Test reverting the moving of data objects"""
        self.add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'landing_zone': self.zone,
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': IRODS_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAILS
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj_path))
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj2_path))
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj_path))
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj2_path))
        obj_access = self.get_user_access(
            target=self.irods.data_objects.get(self.batch_obj_path),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsNone(obj_access)
        obj_access = self.get_user_access(
            target=self.irods.data_objects.get(self.batch_obj2_path),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsNone(obj_access)

    def test_overwrite_failure(self):
        """Test moving data objects when a similarly named file exists"""
        new_obj_path = os.path.join(self.batch_dest_path, 'batch_obj2')
        # Create object already in target
        new_obj = self.irods.data_objects.create(new_obj_path)
        self.add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'landing_zone': self.zone,
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': IRODS_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        with self.assertRaises(Exception):
            self.run_flow()

        # Assert state of objects after attempted move
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj_path))
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj2_path))
        self.assertTrue(self.irods.data_objects.exists(new_obj_path))
        move_obj = self.irods.data_objects.get(self.batch_obj2_path)
        self.assertEqual(self.batch_obj.checksum, move_obj.checksum)
        existing_obj = self.irods.data_objects.get(new_obj_path)
        self.assertEqual(new_obj.checksum, existing_obj.checksum)

    @override_settings(TASKFLOW_ZONE_PROGRESS_INTERVAL=0)
    def test_execute_progress(self):
        """Test moving with progress indicator"""
        # Create checksum objects
        chk_obj = self.make_checksum_object(self.batch_obj)
        chk_obj2 = self.make_checksum_object(self.batch_obj2)
        self.assertEqual(
            self.zone.status_info, DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE]
        )
        self.add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'landing_zone': self.zone,
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [
                    self.batch_obj_path,
                    chk_obj.path,
                    self.batch_obj2_path,
                    chk_obj2.path,
                ],
                'access_name': IRODS_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        result = self.run_flow()

        self.assertEqual(result, True)
        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.status_info,
            DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE] + ' (2/2: 100%)',
        )  # Checksum files should not be counted


class TestBatchCalculateChecksumTask(
    SampleSheetIOMixin, LandingZoneMixin, IRODSTaskTestBase
):
    """Tests for BatchCalculateChecksumTask"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create zone without taskflow
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )
        self.obj_name = 'test1.txt'
        self.obj_path = os.path.join(self.test_coll_path, self.obj_name)

    def test_calculate(self):
        """Test calculating checksum for a data object"""
        obj = self.make_irods_object(
            self.test_coll, self.obj_name, checksum=False
        )
        self.assertIsNone(obj.replicas[0].checksum)

        self.add_task(
            cls=BatchCalculateChecksumTask,
            name='Calculate checksums',
            inject={
                'landing_zone': self.zone,
                'file_paths': [self.obj_path],
                'force': False,
            },
        )
        self.run_flow()

        # Object must be reloaded to refresh replica info
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))
        self.zone.refresh_from_db()
        self.assertIn(
            DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE], self.zone.status_info
        )

    def test_calculate_twice(self):
        """Test calculating with existing checksum"""
        obj = self.make_irods_object(self.test_coll, self.obj_name)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))

        self.add_task(
            cls=BatchCalculateChecksumTask,
            name='Calculate checksums',
            inject={
                'landing_zone': self.zone,
                'file_paths': [self.obj_path],
                'force': False,
            },
        )
        self.run_flow()

        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))

    @override_settings(TASKFLOW_ZONE_PROGRESS_INTERVAL=0)
    def test_calculate_progress(self):
        """Test calculating checksum with progress indicator"""
        obj = self.make_irods_object(
            self.test_coll, self.obj_name, checksum=False
        )
        self.assertIsNone(obj.replicas[0].checksum)
        self.assertEqual(
            self.zone.status_info, DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE]
        )

        self.add_task(
            cls=BatchCalculateChecksumTask,
            name='Calculate checksums',
            inject={
                'landing_zone': self.zone,
                'file_paths': [self.obj_path],
                'force': False,
            },
        )
        self.run_flow()

        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))
        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.status_info,
            DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE] + ' (1/1: 100%)',
        )


class TestTimelineEventExtraDataUpdateTask(
    ProjectMixin, TimelineEventMixin, TaskTestMixin, TestCase
):
    """Tests for TimelineEventExtraDataUpdateTask"""

    def add_task(self, cls, name, inject, force_fail=False):
        """Add task based on SODARBaseTask"""
        self.flow.add_task(
            cls(
                name=name,
                project=self.project,
                verbose=False,
                inject=inject,
                force_fail=force_fail,
            )
        )

    def setUp(self):
        self.irods_backend = plugin_api.get_backend_api('omics_irods')
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.flow = self.init_flow()
        self.event = self.make_event(
            project=self.project,
            app='taskflowbackend',
            user=None,
            event_name='test_event',
            extra_data={},
        )

    def test_execute(self):
        """Test TimelineEventExtraDataUpdateTask execute"""
        self.assertEqual(self.event.extra_data, {})
        self.add_task(
            cls=TimelineEventExtraDataUpdateTask,
            name='Update timeline event',
            inject={
                'tl_event': self.event,
                'extra_data': EXTRA_DATA,
            },
        )
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, EXTRA_DATA)

    def test_execute_update_same_field(self):
        """Test execute with same field in existing extra data"""
        og_data = {'test': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.assertNotEqual(self.event.extra_data, EXTRA_DATA)
        self.add_task(
            cls=TimelineEventExtraDataUpdateTask,
            name='Update timeline event',
            inject={
                'tl_event': self.event,
                'extra_data': EXTRA_DATA,
            },
        )
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, EXTRA_DATA)

    def test_execute_update_other_field(self):
        """Test execute with other field in existing extra data"""
        og_data = {'other': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.add_task(
            cls=TimelineEventExtraDataUpdateTask,
            name='Update timeline event',
            inject={
                'tl_event': self.event,
                'extra_data': EXTRA_DATA,
            },
        )
        self.run_flow()
        self.event.refresh_from_db()
        updated_data = EXTRA_DATA
        updated_data.update(og_data)
        self.assertEqual(self.event.extra_data, updated_data)

    def test_revert(self):
        """Test revert"""
        self.assertEqual(self.event.extra_data, {})
        self.add_task(
            cls=TimelineEventExtraDataUpdateTask,
            name='Update timeline event',
            inject={
                'tl_event': self.event,
                'extra_data': EXTRA_DATA,
            },
            force_fail=True,
        )
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, {})

    def test_revert_update_same_field(self):
        """Test revert with same field in existing extra data"""
        og_data = {'test': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.assertNotEqual(self.event.extra_data, EXTRA_DATA)
        self.add_task(
            cls=TimelineEventExtraDataUpdateTask,
            name='Update timeline event',
            inject={
                'tl_event': self.event,
                'extra_data': EXTRA_DATA,
            },
            force_fail=True,
        )
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, og_data)

    def test_revert_update_other_field(self):
        """Test revert with other field in existing extra data"""
        og_data = {'other': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.add_task(
            cls=TimelineEventExtraDataUpdateTask,
            name='Update timeline event',
            inject={
                'tl_event': self.event,
                'extra_data': EXTRA_DATA,
            },
            force_fail=True,
        )
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, og_data)
