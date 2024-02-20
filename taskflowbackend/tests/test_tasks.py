"""Tests for Taskflow tasks in the taskflowbackend app"""

import uuid

from irods.collection import iRODSCollection
from irods.data_object import iRODSDataObject
from irods.exception import CollectionDoesNotExist, DataObjectDoesNotExist
from irods.meta import iRODSMeta
from irods.ticket import Ticket
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tests.base import TaskflowViewTestBase, TICKET_STR
from taskflowbackend.tasks.irods_tasks import *  # noqa


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
USER_PREFIX = 'omics_'
IRODS_ZONE = settings.IRODS_ZONE
DEFAULT_USER_GROUP = USER_PREFIX + 'group1'
GROUP_USER = USER_PREFIX + 'user1'
GROUPLESS_USER = USER_PREFIX + 'user2'

TEST_COLL_NAME = 'test'
NEW_COLL_NAME = 'test_new'
NEW_COLL2_NAME = 'test_new2'
TEST_OBJ_NAME = 'move_obj'
SUB_COLL_NAME = 'sub'
SUB_COLL_NAME2 = 'sub2'
MOVE_COLL_NAME = 'move_coll'

TEST_USER = USER_PREFIX + 'user3'
TEST_USER_TYPE = 'rodsuser'
TEST_KEY = 'test_key'
TEST_VAL = 'test_val'
TEST_UNITS = 'test_units'
TEST_USER_GROUP = USER_PREFIX + 'group2'

# iRODS access control values
# NOTE: input values set in base class for iRODS 4.2/4.3 support
IRODS_ACCESS_READ_IN = 'read'
IRODS_ACCESS_WRITE_IN = 'write'
IRODS_ACCESS_NULL = 'null'

BATCH_SRC_NAME = 'batch_src'
BATCH_DEST_NAME = 'batch_dest'
BATCH_OBJ_NAME = 'batch_obj'
BATCH_OBJ2_NAME = 'batch_obj2'


class IRODSTaskTestBase(TaskflowViewTestBase):
    """Base test class for iRODS tasks"""

    def _run_flow(self):
        return self.flow.run(verbose=False)

    def _init_flow(self):
        return BaseLinearFlow(
            irods_backend=self.irods_backend,
            project=self.project,
            flow_name=str(uuid.uuid4()),
            flow_data={},
        )

    def _add_task(self, cls, name, inject, force_fail=False):
        self.flow.add_task(
            cls(
                name=name,
                irods=self.irods,
                verbose=False,
                inject=inject,
                force_fail=force_fail,
            )
        )

    def _get_test_coll(self):
        return self.irods.collections.get(self.test_coll_path)

    def _get_user_access(self, target, user_name):
        target_access = self.irods.permissions.get(target=target)
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
            description='description',
        )
        # Init vars and iRODS collections
        self.project_path = self.irods_backend.get_path(self.project)
        self.test_coll = self.irods.collections.create(
            os.path.join(self.project_path, TEST_COLL_NAME)
        )
        self.test_coll_path = self.test_coll.path
        self.new_coll_path = os.path.join(self.project_path, NEW_COLL_NAME)
        # Init flow
        self.flow = self._init_flow()


class TestCreateCollectionTask(IRODSTaskTestBase):
    """Tests for CreateCollectionTask"""

    def test_execute(self):
        """Test collection creation"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self._run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

    def test_execute_twice(self):
        """Test collection creation twice"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        self._run_flow()
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.flow = self._init_flow()
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self._run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

    def test_revert_created(self):
        """Test collection creation reverting after creating"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()
        self.assertFalse(result)
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_revert_not_modified(self):
        """Test collection creation reverting without modification"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self._run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

        self.flow = self._init_flow()
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()
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

        self._add_task(
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
        result = self._run_flow()

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

        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={
                'path': os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            },
        )
        result = self._run_flow()

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

        self.flow = self._init_flow()
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={
                'path': os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            },
        )
        result = self._run_flow()

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

        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={
                'path': os.path.join(self.new_coll_path, 'subcoll1', 'subcoll2')
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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
        self._add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
        )
        coll = self.irods.collections.get(self.test_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

        result = self._run_flow()

        self.assertEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.test_coll_path,
        )

    def test_execute_twice(self):
        """Test collection removal twice"""
        self._add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.test_coll_path,
        )

    def test_revert_removed(self):
        """Test collection removal reverting after removing"""
        self._add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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
        self.flow = self._init_flow()
        self._add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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
        self._add_task(
            cls=RemoveDataObjectTask,
            name='Remove data object',
            inject={'path': self.obj_path},
        )
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)
        result = self._run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(self.obj_path)

    def test_execute_twice(self):
        """Test data object removal twice"""
        self._add_task(
            cls=RemoveDataObjectTask,
            name='Remove data object',
            inject={'path': self.obj_path},
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=RemoveDataObjectTask,
            name='Remove data_object',
            inject={'path': self.obj_path},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(self.obj_path)

    def test_revert_removed(self):
        """Test data object removal reverting after removing"""
        self._add_task(
            cls=RemoveDataObjectTask,
            name='Remove data_object',
            inject={'path': self.obj_path},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)

    def test_revert_not_modified(self):
        """Test data object removal reverting without modification"""
        obj_path2 = os.path.join(self.test_coll_path, 'move_obj2')
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(obj_path2)

        self.flow = self._init_flow()
        self._add_task(
            cls=RemoveDataObjectTask,
            name='Remove data object',
            inject={'path': obj_path2},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(obj_path2)


class TestSetCollectionMetadataTask(IRODSTaskTestBase):
    """Tests for SetCollectionMetadataTask"""

    def test_execute(self):
        """Test setting metadata"""
        self._add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        test_coll = self._get_test_coll()
        self.assertRaises(Exception, test_coll.metadata.get_one, TEST_KEY)
        result = self._run_flow()

        self.assertEqual(result, True)
        # NOTE: We must retrieve collection again to refresh its metadata
        test_coll = self._get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.name, TEST_KEY)
        self.assertEqual(meta_item.value, TEST_VAL)
        self.assertEqual(meta_item.units, TEST_UNITS)

    def test_execute_twice(self):
        """Test setting metadata twice"""
        self._add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        test_coll = self._get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)

    def test_revert_created(self):
        """Test metadata setting reverting after creating a new item"""
        self._add_task(
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
        result = self._run_flow()

        self.assertNotEqual(result, True)
        test_coll = self._get_test_coll()
        self.assertRaises(KeyError, test_coll.metadata.get_one, TEST_KEY)

    def test_revert_modified(self):
        """Test metadata setting reverting after modification"""
        self._add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        self._run_flow()

        self.flow = self._init_flow()
        new_val = 'new value'
        self._add_task(
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
        result = self._run_flow()

        self.assertNotEqual(result, True)
        test_coll = self._get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.value, TEST_VAL)  # Original value

    def test_revert_not_modified(self):
        """Test metadata setting reverting without modification"""
        self._add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        )
        result = self._run_flow()
        self.assertEqual(result, True)

        self.flow = self._init_flow()
        self._add_task(
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
        result = self._run_flow()

        self.assertNotEqual(result, True)
        test_coll = self._get_test_coll()
        self.assertIsInstance(test_coll, iRODSCollection)

    def test_execute_empty(self):
        """Test setting an empty value for metadata"""
        self._add_task(
            cls=SetCollectionMetadataTask,
            name='Set metadata',
            inject={
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': '',
                'units': TEST_UNITS,
            },
        )
        test_coll = self._get_test_coll()
        self.assertRaises(Exception, test_coll.metadata.get_one, TEST_KEY)
        result = self._run_flow()

        self.assertEqual(result, True)
        test_coll = self._get_test_coll()
        meta_item = test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.name, TEST_KEY)
        self.assertEqual(meta_item.value, META_EMPTY_VALUE)
        self.assertEqual(meta_item.units, TEST_UNITS)


class TestCreateUserGroupTask(IRODSTaskTestBase):
    """Tests for CreateUserGroupTask"""

    def test_execute(self):
        """Test user group creation"""
        self._add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        self.assertRaises(
            UserGroupDoesNotExist,
            self.irods.user_groups.get,
            TEST_USER_GROUP,
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)

    def test_execute_twice(self):
        """Test user group creation twice"""
        self._add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.flow = self._init_flow()
        self._add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)

    def test_revert_created(self):
        """Test collection creation reverting after creation"""
        self._add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            UserGroupDoesNotExist,
            self.irods.user_groups.get,
            TEST_USER_GROUP,
        )

    def test_revert_not_modified(self):
        """Test collection creation reverting without modification"""
        self._add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
        )
        result = self._run_flow()
        self.assertEqual(result, True)

        self.flow = self._init_flow()
        self._add_task(
            cls=CreateUserGroupTask,
            name='Create user group',
            inject={'name': TEST_USER_GROUP},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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
        self.access_lookup = self.irods_backend.get_access_lookup(self.irods)

    def test_execute_read(self):
        """Test access setting for read"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)
        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_execute_write(self):
        """Test access setting for write/modify"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)

        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_write)

    def test_execute_twice(self):
        """Test access setting twice"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_revert_created(self):
        """Test reverting created access"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsNone(user_access)
        # self.assertEqual(user_access.access_name, TEST_ACCESS_NULL)

    def test_revert_modified(self):
        """Test reverting modified access"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_revert_not_modified(self):
        """Test access setting reverting without modification"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

    def test_execute_no_recursion(self):
        """Test access setting for a collection with recursive=False"""
        # Set up subcollection and test user
        sub_coll = self.irods.collections.create(self.sub_coll_path)
        self.irods.users.create(
            user_name=TEST_USER,
            user_type=TEST_USER_TYPE,
            user_zone=self.irods.zone,
        )
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': TEST_USER,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
                'recursive': False,
            },
        )

        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=TEST_USER
        )
        self.assertEqual(user_access, None)
        user_access = self._get_user_access(
            target=sub_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=TEST_USER
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, self.irods_access_read)

        user_access = self._get_user_access(
            target=sub_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

    def test_revert_no_recursion(self):
        """Test access setting reverting for a collection with recursive=False"""
        sub_coll = self.irods.collections.create(self.sub_coll_path)
        self.irods.users.create(
            user_name=TEST_USER,
            user_type=TEST_USER_TYPE,
            user_zone=self.irods.zone,
        )

        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': TEST_USER,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
                'recursive': False,
            },
            force_fail=True,
        )  # FAIL

        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

        user_access = self._get_user_access(
            target=sub_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

        result = self._run_flow()

        self.assertEqual(result, False)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

        user_access = self._get_user_access(
            target=sub_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)


class TestIssueTicketTask(IRODSTaskTestBase):
    """Tests for IssueTicketTask"""

    def setUp(self):
        super().setUp()

    def test_execute(self):
        """Test issuing a ticket"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self._add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_execute_twice(self):
        """Test issuing a ticket_twice"""
        self._add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

        self.flow = self._init_flow()
        self._add_task(
            cls=IssueTicketTask,
            name='Issue ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_revert_modified(self):
        """Test reverting a ticket issuing"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self._add_task(
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
        result = self._run_flow()
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
        self._add_task(
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
        result = self._run_flow()
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
        self._add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()
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
        self._add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()
        self.assertEqual(result, True)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

        self.flow = self._init_flow()
        self._add_task(
            cls=DeleteTicketTask,
            name='Delete ticket',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()
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
        self._add_task(
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
        result = self._run_flow()
        self.assertEqual(result, False)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_revert_not_modified(self):
        """Test reverting ticket deletion with no modification"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self._add_task(
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
        result = self._run_flow()
        self.assertEqual(result, False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))


class TestCreateUserTask(IRODSTaskTestBase):
    """Tests for CreateUserTask"""

    def test_execute(self):
        """Test user creation"""
        self._add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': TEST_USER_TYPE},
        )
        self.assertRaises(UserDoesNotExist, self.irods.users.get, TEST_USER)
        result = self._run_flow()

        self.assertEqual(result, True)
        user = self.irods.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)

    def test_execute_twice(self):
        """Test user creation twice"""
        self._add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': TEST_USER_TYPE},
        )
        result = self._run_flow()
        self.assertEqual(result, True)

        self.flow = self._init_flow()
        self._add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': TEST_USER_TYPE},
        )
        self._run_flow()

        user = self.irods.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)

    def test_revert_created(self):
        """Test user creation reverting after creating"""
        self._add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': TEST_USER_TYPE},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(UserDoesNotExist, self.irods.users.get, TEST_USER)

    def test_revert_not_modified(self):
        """Test user creation reverting without modification"""
        self._add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': TEST_USER_TYPE},
        )
        result = self._run_flow()
        self.assertEqual(result, True)

        # Init and run new flow
        self.flow = self._init_flow()
        self._add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': TEST_USER_TYPE},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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
            user_name=GROUP_USER, user_type='rodsuser', user_zone=IRODS_ZONE
        )
        group.addmember(GROUP_USER)
        self.irods.users.create(
            user_name=GROUPLESS_USER,
            user_type='rodsuser',
            user_zone=IRODS_ZONE,
        )

    def test_execute(self):
        """Test user addition"""
        self._add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), False)
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)

    def test_execute_twice(self):
        """Test user addition twice"""
        self._add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        result = self._run_flow()
        self.assertEqual(result, True)

        self.flow = self._init_flow()
        self._add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)

    def test_revert_modified(self):
        """Test user addition reverting after modification"""
        self._add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
            force_fail=True,
        )  # FAILS
        result = self._run_flow()

        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), False)

    def test_revert_not_modified(self):
        """Test user addition reverting without modification"""
        self._add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=AddUserToGroupTask,
            name='Add user to group',
            inject={
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
            force_fail=True,
        )  # FAILS
        result = self._run_flow()

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
            user_name=GROUP_USER, user_type='rodsuser', user_zone=IRODS_ZONE
        )
        group.addmember(GROUP_USER)

    def test_execute(self):
        """Test user removal"""
        self._add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), True)
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)

    def test_execute_twice(self):
        """Test user removal twice"""
        self._add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.flow = self._init_flow()
        self._add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)

    def test_revert_modified(self):
        """Test user ramoval reverting after modification"""
        self._add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
            force_fail=True,
        )  # FAILS
        result = self._run_flow()
        self.assertNotEqual(result, True)

        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), True)

    def test_revert_not_modified(self):
        """Test user removal reverting without modification"""
        self._add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=RemoveUserFromGroupTask,
            name='Remove user from group',
            inject={'group_name': DEFAULT_USER_GROUP, 'user_name': GROUP_USER},
            force_fail=True,
        )  # FAILS
        result = self._run_flow()

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
        self._add_task(
            cls=MoveDataObjectTask,
            name='Move data object',
            inject={
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
        )
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(move_obj_path)
        result = self._run_flow()
        self.assertEqual(result, True)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), False)
        self.assertEqual(self.irods.data_objects.exists(move_obj_path), True)

    def test_revert(self):
        """Test reverting the moving of a data object"""
        move_obj_path = os.path.join(self.move_coll_path, TEST_OBJ_NAME)
        self._add_task(
            cls=MoveDataObjectTask,
            name='Move data object',
            inject={
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
            force_fail=True,
        )  # FAILS
        result = self._run_flow()
        self.assertEqual(result, False)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)
        self.assertEqual(self.irods.data_objects.exists(move_obj_path), False)

    def test_overwrite_failure(self):
        """Test moving a data object when a similarly named file exists"""
        new_obj_path = os.path.join(self.move_coll_path, TEST_OBJ_NAME)
        # Create object already in target
        new_obj = self.irods.data_objects.create(new_obj_path)
        self._add_task(
            cls=MoveDataObjectTask,
            name='Move data object',
            inject={
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
        )
        with self.assertRaises(Exception):
            self._run_flow()

        # Assert state of both objects after attempted move
        # TODO: Better way to compare file objects than checksum?
        # TODO: obj1 != obj2 even if they point to the same thing in iRODS..
        move_obj2 = self.irods.data_objects.get(self.obj_path)
        self.assertEqual(self.move_obj.checksum, move_obj2.checksum)
        new_obj2 = self.irods.data_objects.get(new_obj_path)
        self.assertEqual(new_obj.checksum, new_obj2.checksum)


# TODO: Test Checksum verifying


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
        self.access_lookup = self.irods_backend.get_access_lookup(self.irods)

    def test_execute_read(self):
        """Test access setting for read"""
        self._add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self._run_flow()

        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_read
        )

    def test_execute_write(self):
        """Test access setting for write/modify"""
        self._add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self._run_flow()

        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_write
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_write
        )

    def test_execute_mixed(self):
        """Test access setting for both new and previously set access levels"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.sub_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        self._run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

        self.flow = self._init_flow()
        self._add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_write
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_write
        )

    def test_revert_created(self):
        """Test reverting created access"""
        self._add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

    def test_revert_modified(self):
        """Test reverting modified access"""
        self._add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        self._run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_read
        )

        self.flow = self._init_flow()
        self._add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, self.irods_access_read
        )

    def test_revert_mixed(self):
        """Test reverting access for both new and existing access levels"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_IN,
                'path': self.sub_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        self._run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

        self.flow = self._init_flow()
        self._add_task(
            cls=BatchSetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_WRITE_IN,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, self.irods_access_read
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)


class TestBatchCreateCollectionsTask(IRODSTaskTestBase):
    """Tests for BatchCreateCollectionsTask"""

    def setUp(self):
        super().setUp()
        self.new_coll_path2 = os.path.join(self.project_path, NEW_COLL2_NAME)

    def test_execute(self):
        """Test batch collection creation"""
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'paths': [self.new_coll_path, self.new_coll_path2]},
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
        result = self._run_flow()

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
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'paths': [self.new_coll_path, self.new_coll_path2]},
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'paths': [self.new_coll_path, self.new_coll_path2]},
        )
        result = self._run_flow()

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
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'paths': [self.new_coll_path, self.new_coll_path2]},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'paths': [self.new_coll_path, self.new_coll_path2]},
        )
        result = self._run_flow()
        self.assertEqual(result, True)

        # Init and run new flow
        self.flow = self._init_flow()
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'paths': [self.new_coll_path, self.new_coll_path2]},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'paths': [
                    os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a'),
                    os.path.join(self.new_coll_path, 'subcoll2', 'subcoll2a'),
                ]
            },
        )
        result = self._run_flow()

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
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'paths': [
                    os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a'),
                    os.path.join(self.new_coll_path, 'subcoll1'),
                ]
            },
        )
        result = self._run_flow()

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
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'paths': [
                    os.path.join(self.new_coll_path, 'subcoll1', 'subcoll1a'),
                    os.path.join(self.new_coll_path, 'subcoll2', 'subcoll2a'),
                ]
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

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


class TestBatchMoveDataObjectsTask(IRODSTaskTestBase):
    """Tests for BatchMoveDataObjectsTask"""

    def setUp(self):
        super().setUp()
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
        self.access_lookup = self.irods_backend.get_access_lookup(self.irods)

    def test_execute(self):
        """Test moving data objects and setting access"""
        self._add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': IRODS_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj_path))
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj2_path))
        self.assertEqual(
            self._get_user_access(
                target=self.irods.data_objects.get(self.batch_obj_path),
                user_name=DEFAULT_USER_GROUP,
            ),
            None,
        )
        self.assertEqual(
            self._get_user_access(
                target=self.irods.data_objects.get(self.batch_obj2_path),
                user_name=DEFAULT_USER_GROUP,
            ),
            None,
        )

        result = self._run_flow()

        self.assertEqual(result, True)
        self.assertFalse(self.irods.data_objects.exists(self.batch_obj_path))
        self.assertFalse(self.irods.data_objects.exists(self.batch_obj2_path))
        self.assertTrue(self.irods.data_objects.exists(self.dest_obj_path))
        self.assertTrue(self.irods.data_objects.exists(self.dest_obj2_path))
        obj_access = self._get_user_access(
            target=self.irods.data_objects.get(
                '{}/batch_obj'.format(self.batch_dest_path)
            ),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsInstance(obj_access, iRODSAccess)
        self.assertEqual(obj_access.access_name, self.irods_access_read)
        obj_access = self._get_user_access(
            target=self.irods.data_objects.get(self.dest_obj_path),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsInstance(obj_access, iRODSAccess)
        self.assertEqual(obj_access.access_name, self.irods_access_read)

    def test_revert(self):
        """Test reverting the moving of data objects"""
        self._add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': IRODS_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
            force_fail=True,
        )  # FAILS
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj_path))
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj2_path))
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj_path))
        self.assertFalse(self.irods.data_objects.exists(self.dest_obj2_path))
        obj_access = self._get_user_access(
            target=self.irods.data_objects.get(self.batch_obj_path),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsNone(obj_access)
        obj_access = self._get_user_access(
            target=self.irods.data_objects.get(self.batch_obj2_path),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsNone(obj_access)

    def test_overwrite_failure(self):
        """Test moving data objects when a similarly named file exists"""
        new_obj_path = os.path.join(self.batch_dest_path, 'batch_obj2')
        # Create object already in target
        new_obj = self.irods.data_objects.create(new_obj_path)
        self._add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': IRODS_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
                'access_lookup': self.access_lookup,
                'irods_backend': self.irods_backend,
            },
        )
        with self.assertRaises(Exception):
            self._run_flow()

        # Assert state of objects after attempted move
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj_path))
        self.assertTrue(self.irods.data_objects.exists(self.batch_obj2_path))
        self.assertTrue(self.irods.data_objects.exists(new_obj_path))
        move_obj = self.irods.data_objects.get(self.batch_obj2_path)
        self.assertEqual(self.batch_obj.checksum, move_obj.checksum)
        existing_obj = self.irods.data_objects.get(new_obj_path)
        self.assertEqual(new_obj.checksum, existing_obj.checksum)


class TestBatchCalculateChecksumTask(IRODSTaskTestBase):
    """Tests for BatchCalculateChecksumTask"""

    def setUp(self):
        super().setUp()
        self.obj_name = 'test1.txt'
        self.obj_path = os.path.join(self.test_coll_path, self.obj_name)

    def test_calculate(self):
        """Test calculating checksum for a data object"""
        obj = self.make_irods_object(
            self.test_coll, self.obj_name, checksum=False
        )
        self.assertIsNone(obj.replicas[0].checksum)

        self._add_task(
            cls=BatchCalculateChecksumTask,
            name='Calculate checksums',
            inject={'file_paths': [self.obj_path], 'force': False},
        )
        self._run_flow()

        # Object must be reloaded to refresh replica info
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_md5_checksum(obj))

    def test_calculate_twice(self):
        """Test calculating with existing checksum"""
        obj = self.make_irods_object(self.test_coll, self.obj_name)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_md5_checksum(obj))

        self._add_task(
            cls=BatchCalculateChecksumTask,
            name='Calculate checksums',
            inject={'file_paths': [self.obj_path], 'force': False},
        )
        self._run_flow()

        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_md5_checksum(obj))
