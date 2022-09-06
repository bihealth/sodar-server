"""Tests for Taskflow tasks in the taskflowbackend app"""

import uuid

from irods.collection import iRODSCollection
from irods.data_object import iRODSDataObject
from irods.exception import CollectionDoesNotExist, DataObjectDoesNotExist
from irods.meta import iRODSMeta
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tests.base import TaskflowbackendTestBase
from taskflowbackend.tasks.irods_tasks import *  # noqa


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
USER_PREFIX = 'omics_'
IRODS_ZONE = settings.IRODS_ZONE
DEFAULT_USER_GROUP = USER_PREFIX + 'group1'
GROUP_USER = USER_PREFIX + 'user1'
GROUPLESS_USER = USER_PREFIX + 'user2'

TEST_COLL_NAME = '/test'
NEW_COLL_NAME = '/test_new'
NEW_COLL2_NAME = '/test_new2'
TEST_OBJ_NAME = '/move_obj'
SUB_COLL_NAME = '/sub'
MOVE_COLL_NAME = '/move_coll'

TEST_USER = USER_PREFIX + 'user3'
TEST_USER_TYPE = 'rodsuser'
TEST_KEY = 'test_key'
TEST_VAL = 'test_val'
TEST_UNITS = 'test_units'
TEST_USER_GROUP = USER_PREFIX + 'group2'

# NOTE: Yes, we really need this for the python irods client
TEST_ACCESS_READ_IN = 'read'
TEST_ACCESS_READ_OUT = 'read object'
TEST_ACCESS_WRITE_IN = 'write'
TEST_ACCESS_WRITE_OUT = 'modify object'
TEST_ACCESS_NULL = 'null'

BATCH_SRC_NAME = '/batch_src'
BATCH_DEST_NAME = '/batch_dest'
BATCH_OBJ_NAME = '/batch_obj'
BATCH_OBJ2_NAME = '/batch_obj2'


class IRODSTestBase(TaskflowbackendTestBase):
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
                irods=self.irods_session,
                verbose=False,
                inject=inject,
                force_fail=force_fail,
            )
        )

    def _get_test_coll(self):
        return self.irods_session.collections.get(self.test_coll_path)

    def _get_user_access(self, target, user_name):
        target_access = self.irods_session.permissions.get(target=target)
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
        self.test_coll = self.irods_session.collections.create(
            self.project_path + '/' + TEST_COLL_NAME
        )
        self.test_coll_path = self.test_coll.path
        self.new_coll_path = self.project_path + NEW_COLL_NAME

        # Init flow
        self.flow = self._init_flow()


class TestCreateCollectionTask(IRODSTestBase):
    """Tests for CreateCollectionTask"""

    def test_execute(self):
        """Test collection creation"""
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path,
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        coll = self.irods_session.collections.get(self.new_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

    def test_execute_twice(self):
        """Test collection creation twice"""
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        coll = self.irods_session.collections.get(self.new_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

    def test_revert_created(self):
        """Test collection creation reverting after creating"""
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path,
        )

    def test_revert_not_modified(self):
        """Test collection creation reverting without modification"""
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.flow = self._init_flow()
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        coll = self.irods_session.collections.get(self.new_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

    def test_execute_nested(self):
        """Test collection creation with nested collections"""
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path + '/subcoll1/subcoll2'},
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll1',
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll1/subcoll2',
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        coll = self.irods_session.collections.get(self.new_coll_path)
        self.assertIsInstance(coll, iRODSCollection)
        coll = self.irods_session.collections.get(
            self.new_coll_path + '/subcoll1'
        )
        self.assertIsInstance(coll, iRODSCollection)
        coll = self.irods_session.collections.get(
            self.new_coll_path + '/subcoll1/subcoll2'
        )
        self.assertIsInstance(coll, iRODSCollection)

    def test_execute_nested_twice(self):
        """Test collection creation twice with nested collections"""
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path + '/subcoll1/subcoll2'},
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path + '/subcoll1/subcoll2'},
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        coll = self.irods_session.collections.get(self.new_coll_path)
        self.assertIsInstance(coll, iRODSCollection)
        coll = self.irods_session.collections.get(
            self.new_coll_path + '/subcoll1'
        )
        self.assertIsInstance(coll, iRODSCollection)
        coll = self.irods_session.collections.get(
            self.new_coll_path + '/subcoll1/subcoll2'
        )
        self.assertIsInstance(coll, iRODSCollection)

    def test_revert_created_nested(self):
        """Test creation reverting with nested collections"""
        self._add_task(
            cls=CreateCollectionTask,
            name='Create collection',
            inject={'path': self.new_coll_path + '/subcoll1/subcoll2'},
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll1',
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll1/subcoll2',
        )


class TestRemoveCollectionTask(IRODSTestBase):
    """Tests for RemoveCollectionTask"""

    def test_execute(self):
        """Test collection removal"""
        self._add_task(
            cls=RemoveCollectionTask,
            name='Remove collection',
            inject={'path': self.test_coll_path},
        )
        coll = self.irods_session.collections.get(self.test_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

        result = self._run_flow()

        self.assertEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
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
            self.irods_session.collections.get,
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
        coll = self.irods_session.collections.get(self.test_coll_path)
        self.assertIsInstance(coll, iRODSCollection)

    def test_revert_not_modified(self):
        """Test collection removal reverting without modification"""
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
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
            self.irods_session.collections.get,
            self.new_coll_path,
        )


class TestRemoveDataObjectTask(IRODSTestBase):
    """Tests for RemoveDataObjectTask"""

    def setUp(self):
        super().setUp()
        # Init object to be removed
        self.obj_path = self.test_coll_path + TEST_OBJ_NAME
        self.obj = self.irods_session.data_objects.create(self.obj_path)

    def test_execute(self):
        """Test data object removal"""
        self._add_task(
            cls=RemoveDataObjectTask,
            name='Remove data object',
            inject={'path': self.obj_path},
        )
        obj = self.irods_session.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)
        result = self._run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(self.obj_path)

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
            self.irods_session.data_objects.get(self.obj_path)

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
        obj = self.irods_session.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)

    def test_revert_not_modified(self):
        """Test data object removal reverting without modification"""
        obj_path2 = self.test_coll_path + '/move_obj2'
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(obj_path2)

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
            self.irods_session.data_objects.get(obj_path2)


class TestSetCollectionMetadataTask(IRODSTestBase):
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


class TestCreateUserGroupTask(IRODSTestBase):
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
            self.irods_session.user_groups.get,
            TEST_USER_GROUP,
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods_session.user_groups.get(TEST_USER_GROUP)
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
        group = self.irods_session.user_groups.get(TEST_USER_GROUP)
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
            self.irods_session.user_groups.get,
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
        group = self.irods_session.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)


class TestSetCollAccessTask(IRODSTestBase):
    """Tests for SetCollAccessTask"""

    def setUp(self):
        super().setUp()
        self.sub_coll_path = self.test_coll_path + SUB_COLL_NAME
        # Init default user group
        self.irods_session.user_groups.create(DEFAULT_USER_GROUP)

    def test_execute_read(self):
        """Test access setting for read"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
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
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

    def test_execute_write(self):
        """Test access setting for write/modify"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_WRITE_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
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
        self.assertEqual(user_access.access_name, TEST_ACCESS_WRITE_OUT)

    def test_execute_twice(self):
        """Test access setting twice"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

    def test_revert_created(self):
        """Test access setting"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
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
        """Test access setting reverting after modification"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
            },
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_WRITE_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)

        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

    def test_revert_not_modified(self):
        """Test access setting reverting without modification"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_coll(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

    def test_execute_no_recursion(self):
        """Test access setting for a collection with recursive=False"""
        # Set up subcollection and test user
        sub_coll = self.irods_session.collections.create(self.sub_coll_path)
        self.irods_session.users.create(
            user_name=TEST_USER,
            user_type=TEST_USER_TYPE,
            user_zone=self.irods_session.zone,
        )
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': TEST_USER,
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
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

        user_access = self._get_user_access(
            target=sub_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)

    def test_revert_no_recursion(self):
        """Test access setting reverting for a collection with recursive=False"""
        sub_coll = self.irods_session.collections.create(self.sub_coll_path)
        self.irods_session.users.create(
            user_name=TEST_USER,
            user_type=TEST_USER_TYPE,
            user_zone=self.irods_session.zone,
        )

        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.test_coll_path,
                'user_name': TEST_USER,
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


class TestSetDataObjAccessTask(IRODSTestBase):
    """Tests for SetDataObjAccessTask"""

    def _get_test_obj(self):
        return self.irods_session.data_objects.get(self.obj_path)

    def setUp(self):
        super().setUp()
        # Init default user group
        self.irods_session.user_groups.create(DEFAULT_USER_GROUP)
        # Init object to be copied
        self.obj_path = self.test_coll_path + TEST_OBJ_NAME
        self.obj = self.irods_session.data_objects.create(self.obj_path)

    def test_execute_read(self):
        """Test access setting for read"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
        )
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)

        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

    def test_execute_write(self):
        """Test access setting for write/modify"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_WRITE_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
        )
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)

        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_WRITE_OUT)

    def test_execute_twice(self):
        """Test access setting twice"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)

        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

    def test_revert_created(self):
        """Test access setting"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsNone(user_access)

    def test_revert_modified(self):
        """Test access setting reverting after modification"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
        )
        self._run_flow()

        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_WRITE_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)

    def test_revert_not_modified(self):
        """Test access setting reverting without modification"""
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
        )
        result = self._run_flow()
        self.assertEqual(result, True)

        self.flow = self._init_flow()
        self._add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': TEST_ACCESS_READ_IN,
                'path': self.obj_path,
                'user_name': DEFAULT_USER_GROUP,
                'obj_target': True,
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        user_access = self._get_user_access(
            target=self._get_test_obj(), user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, TEST_ACCESS_READ_OUT)


class TestCreateUserTask(IRODSTestBase):
    """Tests for CreateUserTask"""

    def test_execute(self):
        """Test user creation"""
        self._add_task(
            cls=CreateUserTask,
            name='Create user',
            inject={'user_name': TEST_USER, 'user_type': TEST_USER_TYPE},
        )
        self.assertRaises(
            UserDoesNotExist, self.irods_session.users.get, TEST_USER
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        user = self.irods_session.users.get(TEST_USER)
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

        user = self.irods_session.users.get(TEST_USER)
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
        self.assertRaises(
            UserDoesNotExist, self.irods_session.users.get, TEST_USER
        )

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
        user = self.irods_session.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)


class TestAddUserToGroupTask(IRODSTestBase):
    """Tests for AddUserToGroupTask"""

    def setUp(self):
        super().setUp()
        # Init default user group
        group = self.irods_session.user_groups.create(DEFAULT_USER_GROUP)
        # Init default users
        self.irods_session.users.create(
            user_name=GROUP_USER, user_type='rodsuser', user_zone=IRODS_ZONE
        )
        group.addmember(GROUP_USER)
        self.irods_session.users.create(
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
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), False)
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
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
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
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
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
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
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)


class TestRemoveUserFromGroupTask(IRODSTestBase):
    """Tests for RemoveUserFromGroupTask"""

    def setUp(self):
        super().setUp()
        # Init default user group
        group = self.irods_session.user_groups.create(DEFAULT_USER_GROUP)
        # Init default users
        self.irods_session.users.create(
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
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), True)
        result = self._run_flow()

        self.assertEqual(result, True)
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
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
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
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

        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
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
        group = self.irods_session.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)


class TestMoveDataObjectTask(IRODSTestBase):
    def setUp(self):
        super().setUp()
        self.obj_path = self.test_coll_path + TEST_OBJ_NAME
        self.move_coll_path = self.test_coll_path + MOVE_COLL_NAME
        # Init object to be copied
        self.move_obj = self.irods_session.data_objects.create(self.obj_path)
        # Init collection for copying
        self.move_coll = self.irods_session.collections.create(
            self.move_coll_path
        )

    def test_execute(self):
        """Test moving a data object"""
        self._add_task(
            cls=MoveDataObjectTask,
            name='Move data object',
            inject={
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
        )
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(
                '{}/move_obj'.format(self.move_coll_path)
            )
        result = self._run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(self.obj_path)

        move_obj = self.irods_session.data_objects.get(
            '{}/move_obj'.format(self.move_coll_path)
        )
        self.assertIsInstance(move_obj, iRODSDataObject)

    def test_revert(self):
        """Test reverting the moving of a data object"""
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

        self.assertNotEqual(result, True)
        move_obj = self.irods_session.data_objects.get(self.obj_path)
        self.assertIsInstance(move_obj, iRODSDataObject)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(
                '{}/move_obj'.format(self.move_coll_path)
            )

    def test_overwrite_failure(self):
        """Test moving a data object when a similarly named file exists"""
        new_obj_path = self.move_coll_path + '/move_obj'
        # Create object already in target
        new_obj = self.irods_session.data_objects.create(new_obj_path)
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
        move_obj2 = self.irods_session.data_objects.get(self.obj_path)
        self.assertEqual(self.move_obj.checksum, move_obj2.checksum)
        new_obj2 = self.irods_session.data_objects.get(new_obj_path)
        self.assertEqual(new_obj.checksum, new_obj2.checksum)


# TODO: Test Checksum verifying


class TestBatchCreateCollectionsTask(IRODSTestBase):
    """Tests for BatchCreateCollectionsTask"""

    def setUp(self):
        super().setUp()
        self.new_coll_path2 = self.project_path + NEW_COLL2_NAME

    def test_execute(self):
        """Test batch collection creation"""
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={'paths': [self.new_coll_path, self.new_coll_path2]},
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path2,
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_session.collections.get(self.new_coll_path),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods_session.collections.get(self.new_coll_path2),
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
            self.irods_session.collections.get(self.new_coll_path),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods_session.collections.get(self.new_coll_path2),
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
            self.irods_session.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
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
            self.irods_session.collections.get(self.new_coll_path),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods_session.collections.get(self.new_coll_path2),
            iRODSCollection,
        )

    def test_execute_nested(self):
        """Test batch collection creation with nested collections"""
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'paths': [
                    self.new_coll_path + '/subcoll1/subcoll1a',
                    self.new_coll_path + '/subcoll2/subcoll2a',
                ]
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_session.collections.get(
                self.new_coll_path + '/subcoll1/subcoll1a'
            ),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods_session.collections.get(
                self.new_coll_path + '/subcoll2/subcoll2a'
            ),
            iRODSCollection,
        )

    def test_execute_nested_existing(self):
        """Test batch collection creation with existing collection"""
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'paths': [
                    self.new_coll_path + '/subcoll1/subcoll1a',
                    self.new_coll_path + '/subcoll1',
                ]
            },
        )
        result = self._run_flow()

        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_session.collections.get(
                self.new_coll_path + '/subcoll1/subcoll1a'
            ),
            iRODSCollection,
        )
        self.assertIsInstance(
            self.irods_session.collections.get(
                self.new_coll_path + '/subcoll1'
            ),
            iRODSCollection,
        )

    def test_revert_created_nested(self):
        """Test batch creation reverting with nested collections"""
        self._add_task(
            cls=BatchCreateCollectionsTask,
            name='Create collections',
            inject={
                'paths': [
                    self.new_coll_path + '/subcoll1/subcoll1a',
                    self.new_coll_path + '/subcoll2/subcoll2a',
                ]
            },
            force_fail=True,
        )  # FAIL
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll1',
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll1/subcoll1a',
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll2',
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods_session.collections.get,
            self.new_coll_path + '/subcoll2/subcoll2a',
        )


class TestBatchMoveDataObjectsTask(IRODSTestBase):
    """Tests for BatchMoveDataObjectsTask"""

    def setUp(self):
        super().setUp()
        # Init default user group
        self.irods_session.user_groups.create(DEFAULT_USER_GROUP)
        # Init batch collections
        self.batch_src_path = self.test_coll_path + BATCH_SRC_NAME
        self.batch_dest_path = self.test_coll_path + BATCH_DEST_NAME
        self.src_coll = self.irods_session.collections.create(
            self.batch_src_path
        )
        self.dest_coll = self.irods_session.collections.create(
            self.batch_dest_path
        )
        # Init objects to be copied
        self.batch_obj_path = self.batch_src_path + BATCH_OBJ_NAME
        self.batch_obj2_path = self.batch_src_path + BATCH_OBJ2_NAME
        self.batch_obj = self.irods_session.data_objects.create(
            self.batch_obj_path
        )
        self.batch_obj2 = self.irods_session.data_objects.create(
            self.batch_obj2_path
        )

    def test_execute(self):
        """Test moving data objects and setting access"""
        self._add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': TEST_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
            },
        )
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(
                '{}/batch_obj'.format(self.batch_dest_path)
            )
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(
                '{}/batch_obj2'.format(self.batch_dest_path)
            )
        self.assertEqual(
            self._get_user_access(
                target=self.irods_session.data_objects.get(self.batch_obj_path),
                user_name=DEFAULT_USER_GROUP,
            ),
            None,
        )
        self.assertEqual(
            self._get_user_access(
                target=self.irods_session.data_objects.get(
                    self.batch_obj2_path
                ),
                user_name=DEFAULT_USER_GROUP,
            ),
            None,
        )

        result = self._run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(self.batch_obj_path)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(self.batch_obj2_path)
        self.assertIsInstance(
            self.irods_session.data_objects.get(
                '{}/batch_obj'.format(self.batch_dest_path)
            ),
            iRODSDataObject,
        )
        self.assertIsInstance(
            self.irods_session.data_objects.get(
                '{}/batch_obj2'.format(self.batch_dest_path)
            ),
            iRODSDataObject,
        )
        obj_access = self._get_user_access(
            target=self.irods_session.data_objects.get(
                '{}/batch_obj'.format(self.batch_dest_path)
            ),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsInstance(obj_access, iRODSAccess)
        self.assertEqual(obj_access.access_name, TEST_ACCESS_READ_OUT)
        obj_access = self._get_user_access(
            target=self.irods_session.data_objects.get(
                '{}/batch_obj2'.format(self.batch_dest_path)
            ),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsInstance(obj_access, iRODSAccess)
        self.assertEqual(obj_access.access_name, TEST_ACCESS_READ_OUT)

    def test_revert(self):
        """Test reverting the moving of data objects"""
        self._add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': TEST_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
            },
            force_fail=True,
        )  # FAILS
        result = self._run_flow()

        self.assertNotEqual(result, True)
        self.assertIsInstance(
            self.irods_session.data_objects.get(
                '{}/batch_obj'.format(self.batch_src_path)
            ),
            iRODSDataObject,
        )
        self.assertIsInstance(
            self.irods_session.data_objects.get(
                '{}/batch_obj2'.format(self.batch_src_path)
            ),
            iRODSDataObject,
        )
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(
                '{}/batch_obj'.format(self.batch_dest_path)
            )
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods_session.data_objects.get(
                '{}/batch_obj2'.format(self.batch_dest_path)
            )
        obj_access = self._get_user_access(
            target=self.irods_session.data_objects.get(
                '{}/batch_obj'.format(self.batch_src_path)
            ),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsNone(obj_access)
        obj_access = self._get_user_access(
            target=self.irods_session.data_objects.get(
                '{}/batch_obj2'.format(self.batch_src_path)
            ),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsNone(obj_access)

    def test_overwrite_failure(self):
        """Test moving data objects when a similarly named file exists"""
        new_obj_path = self.batch_dest_path + '/batch_obj2'
        # Create object already in target
        new_obj = self.irods_session.data_objects.create(new_obj_path)
        self._add_task(
            cls=BatchMoveDataObjectsTask,
            name='Move data objects',
            inject={
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': TEST_ACCESS_READ_IN,
                'user_name': DEFAULT_USER_GROUP,
            },
        )
        with self.assertRaises(Exception):
            self._run_flow()

        # Assert state of objects after attempted move
        self.assertIsInstance(
            self.irods_session.data_objects.get(
                '{}/batch_obj'.format(self.batch_src_path)
            ),
            iRODSDataObject,
        )
        self.assertIsInstance(
            self.irods_session.data_objects.get(
                '{}/batch_obj2'.format(self.batch_src_path)
            ),
            iRODSDataObject,
        )
        self.assertIsInstance(
            self.irods_session.data_objects.get(new_obj_path), iRODSDataObject
        )
        move_obj = self.irods_session.data_objects.get(
            '{}/batch_obj2'.format(self.batch_src_path)
        )
        self.assertEqual(self.batch_obj.checksum, move_obj.checksum)
        existing_obj = self.irods_session.data_objects.get(new_obj_path)
        self.assertEqual(new_obj.checksum, existing_obj.checksum)
