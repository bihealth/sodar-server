"""Tests for Taskflow tasks in the taskflowbackend app"""

import uuid

from typing import Any, Optional, Union

from irods.collection import iRODSCollection
from irods.exception import CollectionDoesNotExist, DataObjectDoesNotExist
from irods.meta import iRODSMeta
from irods.ticket import Ticket
from irods.user import iRODSUser, iRODSUserGroup

from django.core import mail
from django.forms.models import model_to_dict
from django.test import override_settings

from djangoplugins.models import Plugin

from test_plus import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin

# Appalerts dependency
from appalerts.models import AppAlert

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
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin

from taskflowbackend.constants import (
    IRODS_ACCESS_MODIFY_OBJ,
    IRODS_ACCESS_READ_OBJ,
    IRODS_TICKET_MODE_READ,
)
from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tests.base import TaskflowViewTestBase, TICKET_STR
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
MISC_FILES_COLL = 'MiscFiles'

TEST_USER = USER_PREFIX + 'user3'
TEST_KEY = 'test_key'
TEST_VAL = 'test_val'
TEST_UNITS = 'test_units'
TEST_USER_GROUP = USER_PREFIX + 'group2'
RODS_USER_TYPE = 'rodsuser'

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
DUMMY_MD5 = '66666666666666666666666666666666'
VERIFY_ALERT_NAME = 'sample_data_verify'


class TaskTestMixin:
    """Helpers for taskflow task tests"""

    flow = None
    irods = None
    irods_backend = None
    project = None

    def run_flow(self) -> bool:
        return self.flow.run(verbose=False)

    def init_flow(self) -> BaseLinearFlow:
        return BaseLinearFlow(
            irods_backend=self.irods_backend,
            project=self.project,
            user=None,
            flow_name=str(uuid.uuid4()),
            flow_data={},
        )


class IRODSTaskTestBase(TaskTestMixin, TaskflowViewTestBase):
    """Base test class for iRODS tasks"""

    def add_task(
        self,
        cls: Any,
        name: str,
        inject: Optional[dict],
        force_fail: bool = False,
    ):
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

    def get_test_coll(self) -> iRODSCollection:
        """
        Return iRODS collection for test collection path. Shortcut when e.g.
        needing to refresh the collection object for metadata changes.

        :return: iRODSCollecton
        """
        return self.irods.collections.get(self.test_coll_path)

    def get_user_access(
        self, target: Union[iRODSCollection, iRODSDataObject], user_name: str
    ) -> Optional[iRODSAccess]:
        """
        Return access object for user in a target collection or object. Returns
        None if access is not set.

        :param target: iRODSCollection or iRODSDataObject
        :param user_name: String
        :return: iRODSAccess or None
        """
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
        self.test_coll = self.get_test_coll()
        self.new_coll_path = os.path.join(self.project_path, NEW_COLL_NAME)
        # Init flow
        self.flow = self.init_flow()
        self.task_kw = {
            'cls': CreateCollectionTask,
            'name': 'Create collection',
            'inject': {'path': self.new_coll_path},
        }


class TestCreateCollectionTask(IRODSTaskTestBase):
    """Tests for CreateCollectionTask"""

    def test_execute(self):
        """Test collection creation"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

    def test_execute_twice(self):
        """Test collection creation twice"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.add_task(**self.task_kw)
        self.run_flow()
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

    def test_revert_created(self):
        """Test collection creation reverting after creating"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertFalse(result)
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_revert_not_modified(self):
        """Test collection creation reverting without modification"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))

        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertFalse(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_execute_nested(self):
        """Test collection creation with nested collections"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, '/subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.task_kw['inject']['path'] = iRODSPath(
            self.new_coll_path, 'subcoll1', 'subcoll2'
        )
        self.add_task(**self.task_kw)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.new_coll_path,
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            iRODSPath(self.new_coll_path, 'subcoll1'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2'),
        )
        result = self.run_flow()

        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_execute_nested_twice(self):
        """Test collection creation twice with nested collections"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.task_kw['inject']['path'] = iRODSPath(
            self.new_coll_path, 'subcoll1', 'subcoll2'
        )
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.flow = self.init_flow()
        self.task_kw['inject']['path'] = iRODSPath(
            self.new_coll_path, 'subcoll1', 'subcoll2'
        )
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertTrue(result)
        self.assertTrue(self.irods.collections.exists(self.new_coll_path))
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

    def test_revert_created_nested(self):
        """Test creation reverting with nested collections"""
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))

        self.task_kw['inject']['path'] = iRODSPath(
            self.new_coll_path, 'subcoll1', 'subcoll2'
        )
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertFalse(result)
        self.assertFalse(self.irods.collections.exists(self.new_coll_path))
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1')
            )
        )
        self.assertFalse(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll2')
            )
        )
        self.assertTrue(self.irods.collections.exists(self.test_coll_path))


class TestRemoveCollectionTask(IRODSTaskTestBase):
    """Tests for RemoveCollectionTask"""

    def setUp(self):
        super().setUp()
        self.task_kw = {
            'cls': RemoveCollectionTask,
            'name': 'Remove collection',
            'inject': {'path': self.test_coll_path},
        }

    def test_execute(self):
        """Test collection removal"""
        self.add_task(**self.task_kw)
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
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            self.test_coll_path,
        )

    def test_revert_removed(self):
        """Test collection removal reverting after removing"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
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
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
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
        self.obj_path = iRODSPath(self.test_coll_path, TEST_OBJ_NAME)
        self.obj = self.irods.data_objects.create(self.obj_path)
        self.task_kw = {
            'cls': RemoveDataObjectTask,
            'name': 'Remove data object',
            'inject': {'path': self.obj_path},
        }

    def test_execute(self):
        """Test data object removal"""
        self.add_task(**self.task_kw)
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)
        result = self.run_flow()
        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(self.obj_path)

    def test_execute_twice(self):
        """Test data object removal twice"""
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(self.obj_path)

    def test_revert_removed(self):
        """Test data object removal reverting after removing"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsInstance(obj, iRODSDataObject)

    def test_revert_not_modified(self):
        """Test data object removal reverting without modification"""
        obj_path2 = iRODSPath(self.test_coll_path, 'move_obj2')
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(obj_path2)
        self.flow = self.init_flow()
        self.task_kw['inject']['path'] = obj_path2
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(obj_path2)


class TestSetCollectionMetadataTask(IRODSTaskTestBase):
    """Tests for SetCollectionMetadataTask"""

    def setUp(self):
        super().setUp()
        self.task_kw = {
            'cls': SetCollectionMetadataTask,
            'name': 'Set metadata',
            'inject': {
                'path': self.test_coll_path,
                'name': TEST_KEY,
                'value': TEST_VAL,
                'units': TEST_UNITS,
            },
        }

    def test_execute(self):
        """Test setting metadata"""
        self.add_task(**self.task_kw)
        self.assertRaises(Exception, self.test_coll.metadata.get_one, TEST_KEY)
        result = self.run_flow()
        self.assertEqual(result, True)
        # NOTE: We must retrieve collection again to refresh its metadata
        self.test_coll = self.get_test_coll()
        meta_item = self.test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.name, TEST_KEY)
        self.assertEqual(meta_item.value, TEST_VAL)
        self.assertEqual(meta_item.units, TEST_UNITS)

    def test_execute_twice(self):
        """Test setting metadata twice"""
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.test_coll = self.get_test_coll()
        meta_item = self.test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)

    def test_revert_created(self):
        """Test metadata setting reverting after creating new item"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertNotEqual(result, True)
        self.test_coll = self.get_test_coll()
        self.assertRaises(KeyError, self.test_coll.metadata.get_one, TEST_KEY)

    def test_revert_modified(self):
        """Test metadata setting reverting after modification"""
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.task_kw['inject']['value'] = 'new value'
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.test_coll = self.get_test_coll()
        meta_item = self.test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.value, TEST_VAL)  # Original value

    def test_revert_not_modified(self):
        """Test metadata setting reverting without modification"""
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.test_coll = self.get_test_coll()
        self.assertIsInstance(self.test_coll, iRODSCollection)

    def test_execute_empty(self):
        """Test setting empty value for metadata"""
        self.task_kw['inject']['value'] = ''
        self.add_task(**self.task_kw)
        self.assertRaises(Exception, self.test_coll.metadata.get_one, TEST_KEY)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.test_coll = self.get_test_coll()
        meta_item = self.test_coll.metadata.get_one(TEST_KEY)
        self.assertIsInstance(meta_item, iRODSMeta)
        self.assertEqual(meta_item.name, TEST_KEY)
        self.assertEqual(meta_item.value, IRODS_META_EMPTY_VALUE)
        self.assertEqual(meta_item.units, TEST_UNITS)


class TestCreateUserGroupTask(IRODSTaskTestBase):
    """Tests for CreateUserGroupTask"""

    def setUp(self):
        super().setUp()
        self.task_kw = {
            'cls': CreateUserGroupTask,
            'name': 'Create user group',
            'inject': {'name': TEST_USER_GROUP},
        }

    def test_execute(self):
        """Test user group creation"""
        self.add_task(**self.task_kw)
        self.assertRaises(
            GroupDoesNotExist, self.irods.user_groups.get, TEST_USER_GROUP
        )
        result = self.run_flow()
        self.assertEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)

    def test_execute_twice(self):
        """Test user group creation twice"""
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)

    def test_revert_created(self):
        """Test collection creation reverting after creation"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertNotEqual(result, True)
        self.assertRaises(
            GroupDoesNotExist, self.irods.user_groups.get, TEST_USER_GROUP
        )

    def test_revert_not_modified(self):
        """Test collection creation reverting without modification"""
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(TEST_USER_GROUP)
        self.assertIsInstance(group, iRODSUserGroup)


class TestSetAccessTask(IRODSTaskTestBase):
    """Tests for SetAccessTask"""

    def setUp(self):
        super().setUp()
        self.sub_coll_path = iRODSPath(self.test_coll_path, SUB_COLL_NAME)
        # Init default user group
        self.irods.user_groups.create(DEFAULT_USER_GROUP)
        self.task_kw = {
            'cls': SetAccessTask,
            'name': 'Set access',
            'inject': {
                'access_name': IRODS_ACCESS_READ_OBJ,
                'path': self.test_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        }

    def test_execute_read_object(self):
        """Test access setting for read_object"""
        self.add_task(**self.task_kw)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)
        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, IRODS_ACCESS_READ_OBJ)

    def test_execute_modify_object(self):
        """Test access setting for modify_object"""
        self.task_kw['inject']['access_name'] = IRODS_ACCESS_MODIFY_OBJ
        self.add_task(**self.task_kw)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertEqual(user_access, None)
        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, IRODS_ACCESS_MODIFY_OBJ)

    def test_execute_twice(self):
        """Test access setting twice"""
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, IRODS_ACCESS_READ_OBJ)

    def test_revert_created(self):
        """Test reverting created access"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertNotEqual(result, True)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertIsNone(user_access)

    def test_revert_modified(self):
        """Test reverting modified access"""
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.task_kw['inject']['access_name'] = IRODS_ACCESS_MODIFY_OBJ
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, IRODS_ACCESS_READ_OBJ)

    def test_revert_not_modified(self):
        """Test access setting reverting without modification"""
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=DEFAULT_USER_GROUP
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, IRODS_ACCESS_READ_OBJ)

    def test_execute_no_recursion(self):
        """Test access setting for a collection with recursive=False"""
        # Set up subcollection and test user
        sub_coll = self.irods.collections.create(self.sub_coll_path)
        self.irods.users.create(
            user_name=TEST_USER,
            user_type=RODS_USER_TYPE,
            user_zone=self.irods.zone,
        )
        self.task_kw['inject']['user_name'] = TEST_USER
        self.task_kw['inject']['recursive'] = False
        self.add_task(**self.task_kw)

        user_access = self.get_user_access(
            target=self.test_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)
        user_access = self.get_user_access(target=sub_coll, user_name=TEST_USER)
        self.assertEqual(user_access, None)
        result = self.run_flow()

        self.assertEqual(result, True)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=TEST_USER
        )
        self.assertIsInstance(user_access, iRODSAccess)
        self.assertEqual(user_access.access_name, IRODS_ACCESS_READ_OBJ)
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
        self.task_kw['inject']['user_name'] = TEST_USER
        self.task_kw['inject']['recursive'] = False
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL

        user_access = self.get_user_access(
            target=self.test_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)
        user_access = self.get_user_access(target=sub_coll, user_name=TEST_USER)
        self.assertEqual(user_access, None)
        result = self.run_flow()

        self.assertEqual(result, False)
        user_access = self.get_user_access(
            target=self.test_coll, user_name=TEST_USER
        )
        self.assertEqual(user_access, None)
        user_access = self.get_user_access(target=sub_coll, user_name=TEST_USER)
        self.assertEqual(user_access, None)


class TestIssueTicketTask(IRODSTaskTestBase):
    """Tests for IssueTicketTask"""

    def setUp(self):
        super().setUp()
        self.task_kw = {
            'cls': IssueTicketTask,
            'name': 'Issue ticket',
            'inject': {
                'access_name': IRODS_TICKET_MODE_READ,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        }

    def test_execute(self):
        """Test issuing a ticket"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_execute_twice(self):
        """Test issuing a ticket_twice"""
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_revert_modified(self):
        """Test reverting a ticket issuing"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

    def test_revert_not_modified(self):
        """Test reverting a ticket issuing with no modification"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_TICKET_MODE_READ, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )


class TestDeleteTicketTask(IRODSTaskTestBase):
    """Tests for DeleteTicketTask"""

    def setUp(self):
        super().setUp()
        self.task_kw = {
            'cls': DeleteTicketTask,
            'name': 'Delete ticket',
            'inject': {
                'access_name': IRODS_TICKET_MODE_READ,
                'path': self.test_coll_path,
                'ticket_str': TICKET_STR,
                'irods_backend': self.irods_backend,
            },
        }

    def test_execute(self):
        """Test deleting a ticket"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_TICKET_MODE_READ, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

    def test_execute_twice(self):
        """Test deleting a ticket twice"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_TICKET_MODE_READ, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))

    def test_revert_modified(self):
        """Test reverting ticket deletion"""
        self.irods_backend.issue_ticket(
            self.irods, IRODS_TICKET_MODE_READ, self.test_coll_path, TICKET_STR
        )
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsInstance(
            self.irods_backend.get_ticket(self.irods, TICKET_STR), Ticket
        )

    def test_revert_not_modified(self):
        """Test reverting ticket deletion with no modification"""
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, TICKET_STR))


class TestCreateUserTask(IRODSTaskTestBase):
    """Tests for CreateUserTask"""

    def setUp(self):
        super().setUp()
        self.task_kw = {
            'cls': CreateUserTask,
            'name': 'Create user',
            'inject': {'user_name': TEST_USER, 'user_type': RODS_USER_TYPE},
        }

    def test_execute(self):
        """Test user creation"""
        self.add_task(**self.task_kw)
        self.assertRaises(UserDoesNotExist, self.irods.users.get, TEST_USER)
        result = self.run_flow()
        self.assertEqual(result, True)
        user = self.irods.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)

    def test_execute_twice(self):
        """Test user creation twice"""
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        self.run_flow()

        user = self.irods.users.get(TEST_USER)
        self.assertIsInstance(user, iRODSUser)

    def test_revert_created(self):
        """Test user creation reverting after creating"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertNotEqual(result, True)
        self.assertRaises(UserDoesNotExist, self.irods.users.get, TEST_USER)

    def test_revert_not_modified(self):
        """Test user creation reverting without modification"""
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

        # Init and run new flow
        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
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
        self.task_kw = {
            'cls': AddUserToGroupTask,
            'name': 'Add user to group',
            'inject': {
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUPLESS_USER,
            },
        }

    def test_execute(self):
        """Test user addition"""
        self.add_task(**self.task_kw)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), False)
        result = self.run_flow()
        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)

    def test_execute_twice(self):
        """Test user addition twice"""
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), True)

    def test_revert_modified(self):
        """Test user addition reverting after modification"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUPLESS_USER), False)

    def test_revert_not_modified(self):
        """Test user addition reverting without modification"""
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
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
        self.task_kw = {
            'cls': RemoveUserFromGroupTask,
            'name': 'Remove user from group',
            'inject': {
                'group_name': DEFAULT_USER_GROUP,
                'user_name': GROUP_USER,
            },
        }

    def test_execute(self):
        """Test user removal"""
        self.add_task(**self.task_kw)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), True)
        result = self.run_flow()
        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)

    def test_execute_twice(self):
        """Test user removal twice"""
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)

    def test_execute_no_group(self):
        """Test user removal with no existing group"""
        self.irods.users.remove(DEFAULT_USER_GROUP)
        with self.assertRaises(GroupDoesNotExist):
            self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

    def test_revert_modified(self):
        """Test user ramoval reverting after modification"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertNotEqual(result, True)

        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), True)

    def test_revert_not_modified(self):
        """Test user removal reverting without modification"""
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        group = self.irods.user_groups.get(DEFAULT_USER_GROUP)
        self.assertEqual(group.hasmember(GROUP_USER), False)


class TestMoveDataObjectTask(IRODSTaskTestBase):
    """Tests for MoveDataObjectTask"""

    def setUp(self):
        super().setUp()
        self.obj_path = iRODSPath(self.test_coll_path, TEST_OBJ_NAME)
        self.move_coll_path = iRODSPath(self.test_coll_path, MOVE_COLL_NAME)
        # Init object to be copied
        self.move_obj = self.irods.data_objects.create(self.obj_path)
        # Init collection for copying
        self.move_coll = self.irods.collections.create(self.move_coll_path)
        self.task_kw = {
            'cls': MoveDataObjectTask,
            'name': 'Move data object',
            'inject': {
                'src_path': self.obj_path,
                'dest_path': self.move_coll_path,
            },
        }

    def test_execute(self):
        """Test moving a data object"""
        move_obj_path = iRODSPath(self.move_coll_path, TEST_OBJ_NAME)
        self.add_task(**self.task_kw)
        with self.assertRaises(DataObjectDoesNotExist):
            self.irods.data_objects.get(move_obj_path)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), False)
        self.assertEqual(self.irods.data_objects.exists(move_obj_path), True)

    def test_revert(self):
        """Test reverting the moving of a data object"""
        move_obj_path = iRODSPath(self.move_coll_path, TEST_OBJ_NAME)
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertEqual(result, False)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), True)
        self.assertEqual(self.irods.data_objects.exists(move_obj_path), False)

    def test_overwrite_failure(self):
        """Test moving a data object when a similarly named file exists"""
        new_obj_path = iRODSPath(self.move_coll_path, TEST_OBJ_NAME)
        # Create object already in target
        new_obj = self.irods.data_objects.create(new_obj_path)
        self.add_task(**self.task_kw)
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
        self.obj_path = iRODSPath(self.zone_path, TEST_OBJ_NAME)
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

    @override_settings(IRODS_HASH_SCHEME=IRODS_HASH_SCHEME_SHA256)
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

    @override_settings(IRODS_HASH_SCHEME=IRODS_HASH_SCHEME_SHA256)
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

    @override_settings(IRODS_HASH_SCHEME=IRODS_HASH_SCHEME_SHA256)
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


class TestBatchValidateZoneChecksumsTask(
    SampleSheetIOMixin, LandingZoneMixin, IRODSTaskTestBase
):
    """Tests for BatchValidateZoneChecksumsTask"""

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
        self.data_obj = self.make_irods_object(self.zone_coll, self.obj_name)
        self.obj_path = self.data_obj.path
        self.task_kw = {
            'cls': BatchValidateZoneChecksumsTask,
            'name': 'Validate checksums',
            'inject': {
                'landing_zone': self.zone,
                'file_paths': [self.obj_path],
                'zone_path': self.zone_path,
                'irods_backend': self.irods_backend,
            },
        }

    def test_execute(self):
        """Test BatchValidateZoneChecksumsTask execute()"""
        self.make_checksum_object(self.data_obj)
        self.assertIsNotNone(self.data_obj.replicas[0].checksum)
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

    def test_exceute_invalid_in_file(self):
        """Test execute with invalid checksum in file"""
        self.make_checksum_object(self.data_obj, content='xxx')
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
            f'iRODS: {self.data_obj.replicas[0].checksum}'
        )
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        self.assertIn(expected, str(cm.exception))

    def test_execute_invalid_in_irods(self):
        """Test execute with invalid checksum in iRODS iCAT database"""
        self.make_checksum_object(self.data_obj)
        real_md5 = self.data_obj.replicas[0].checksum
        self.assertNotEqual(real_md5, DUMMY_MD5)
        self.data_obj = self.set_icat_checksum(self.data_obj, DUMMY_MD5)
        self.assertEqual(self.data_obj.replicas[0].checksum, DUMMY_MD5)
        self.add_task(**self.task_kw)
        zone_path_len = len(self.zone_path.split('/'))
        ex_path = '/'.join(self.obj_path.split('/')[zone_path_len:])
        expected = (
            f'Checksums do not match for 1 file:\n'
            f'Path: {ex_path}\n'
            f'Resource: demoResc\n'
            f'File: {real_md5}\n'
            f'iRODS: {DUMMY_MD5}'
        )
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        self.assertIn(expected, str(cm.exception))


class TestBatchVerifySampleChecksumsTask(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, IRODSTaskTestBase
):
    """Tests for BatchVerifySampleChecksumsTask"""

    @classmethod
    def _get_app_alert(cls) -> AppAlert:
        """Get AppAlert from task execution"""
        return AppAlert.objects.filter(alert_name='sample_data_verify').first()

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.misc_path = iRODSPath(self.assay_path, MISC_FILES_COLL)
        self.misc_coll = self.irods.collections.create(self.misc_path)
        self.data_obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        self.obj_path = self.data_obj.path
        self.ex_path = self.data_obj.path.split(self.assay_path + '/')[1]
        self.task_kw = {
            'cls': BatchVerifySampleChecksumsTask,
            'name': 'Validate checksums',
            'inject': {
                'file_paths': [self.obj_path],
                'assay': self.assay,
                'user': self.user,
                'irods_backend': self.irods_backend,
            },
        }
        mail.outbox = []  # Clear mail outbox to simplify testing

    def test_execute(self):
        """Test BatchValidateSampleChecksumsTask execute()"""
        self.make_checksum_object(self.data_obj)
        self.assertIsNone(self._get_app_alert())
        self.assertEqual(len(mail.outbox), 0)
        self.add_task(**self.task_kw)
        self.run_flow()
        # No alert or email should be created
        self.assertIsNone(self._get_app_alert())
        self.assertEqual(len(mail.outbox), 0)

    def test_execute_invalid_in_file(self):
        """Test execute with invalid checksum in file"""
        self.make_checksum_object(self.data_obj, content='xxx')
        self.assertIsNone(self._get_app_alert())
        self.assertEqual(len(mail.outbox), 0)
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()

        # Assert exception
        ex_msg = (
            f'Checksums do not match for 1 file:\n'
            f'Path: {self.ex_path}\n'
            f'Resource: demoResc\n'
            f'File: xxx\n'
            f'iRODS: {self.data_obj.replicas[0].checksum}'
        )
        self.assertIn(ex_msg, str(cm.exception))

        # Assert alert
        alert = self._get_app_alert()
        self.assertIsInstance(alert, AppAlert)
        alert_msg = (
            f'{VERIFY_ERR_MSG}:\n' f'Assay: {self.assay.get_display_name()}\n'
        ) + ex_msg
        expected = {
            'id': alert.pk,
            'app_plugin': Plugin.objects.get(name=APP_NAME).pk,
            'alert_name': VERIFY_ALERT_NAME,
            'user': self.user.pk,
            'message': alert_msg,
            'level': 'DANGER',
            'active': True,
            'url': reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project.sodar_uuid},
            ),
            'project': self.project.pk,
            'sodar_uuid': alert.sodar_uuid,
        }
        self.assertEqual(model_to_dict(alert), expected)

        # Assert email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients(), [self.user.email])
        self.assertIn(VERIFY_ERR_MSG, mail.outbox[0].subject)

    def test_execute_invalid_in_irods(self):
        """Test execute with invalid checksum in iRODS iCAT database"""
        self.make_checksum_object(self.data_obj)
        real_md5 = self.data_obj.replicas[0].checksum
        self.assertNotEqual(real_md5, DUMMY_MD5)
        self.data_obj = self.set_icat_checksum(self.data_obj, DUMMY_MD5)
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception) as cm:
            self.run_flow()
        ex_msg = (
            f'Checksums do not match for 1 file:\n'
            f'Path: {self.ex_path}\n'
            f'Resource: demoResc\n'
            f'File: {real_md5}\n'
            f'iRODS: {DUMMY_MD5}'
        )
        self.assertIn(ex_msg, str(cm.exception))
        self.assertIsInstance(self._get_app_alert(), AppAlert)
        self.assertEqual(len(mail.outbox), 1)

    def test_execute_disable_alerts(self):
        """Test execute with disabled user alert notifications"""
        app_settings.set(
            APP_NAME_LZ, 'notify_alert_zone_status', False, user=self.user
        )
        self.make_checksum_object(self.data_obj, content='xxx')
        self.assertIsNone(self._get_app_alert())
        self.assertEqual(len(mail.outbox), 0)
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception):
            self.run_flow()
        self.assertIsNone(self._get_app_alert())  # No alert
        self.assertEqual(len(mail.outbox), 1)  # Email should still be sent

    def test_execute_disable_email(self):
        """Test execute with disabled user email notifications"""
        app_settings.set(
            APP_NAME_LZ, 'notify_email_zone_status', False, user=self.user
        )
        self.make_checksum_object(self.data_obj, content='xxx')
        self.assertIsNone(self._get_app_alert())
        self.assertEqual(len(mail.outbox), 0)
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception):
            self.run_flow()
        self.assertIsInstance(self._get_app_alert(), AppAlert)
        self.assertEqual(len(mail.outbox), 0)  # No email

    @override_settings(PROJECTROLES_SEND_EMAIL=False)
    def test_execute_disable_email_site(self):
        """Test execute with disabled email sending on site"""
        self.make_checksum_object(self.data_obj, content='xxx')
        self.assertIsNone(self._get_app_alert())
        self.assertEqual(len(mail.outbox), 0)
        self.add_task(**self.task_kw)
        with self.assertRaises(Exception):
            self.run_flow()
        self.assertIsInstance(self._get_app_alert(), AppAlert)
        self.assertEqual(len(mail.outbox), 0)


class TestBatchSetAccessTask(IRODSTaskTestBase):
    """Tests for BatchSetAccessTask"""

    def setUp(self):
        super().setUp()
        self.sub_coll_path = iRODSPath(self.test_coll_path, SUB_COLL_NAME)
        self.sub_coll_path2 = iRODSPath(self.test_coll_path, SUB_COLL_NAME2)
        self.irods.collections.create(self.sub_coll_path)
        self.irods.collections.create(self.sub_coll_path2)
        self.paths = [self.sub_coll_path, self.sub_coll_path2]
        # Init default user group
        self.irods.user_groups.create(DEFAULT_USER_GROUP)
        self.task_kw = {
            'cls': BatchSetAccessTask,
            'name': 'Set access',
            'inject': {
                'access_name': IRODS_ACCESS_READ_OBJ,
                'paths': self.paths,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        }

    def test_execute_read_object(self):
        """Test access setting for read_object"""
        self.add_task(**self.task_kw)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, IRODS_ACCESS_READ_OBJ
        )

    def test_execute_modify_object(self):
        """Test access setting for modify_object"""
        self.task_kw['inject']['access_name'] = IRODS_ACCESS_MODIFY_OBJ
        self.add_task(**self.task_kw)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_MODIFY_OBJ
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, IRODS_ACCESS_MODIFY_OBJ
        )

    def test_execute_mixed(self):
        """Test access setting for both new and previously set access levels"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_OBJ,
                'path': self.sub_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

        self.flow = self.init_flow()
        self.task_kw['inject']['access_name'] = IRODS_ACCESS_MODIFY_OBJ
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_MODIFY_OBJ
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, IRODS_ACCESS_MODIFY_OBJ
        )

    def test_revert_created(self):
        """Test reverting created access"""
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()
        self.assertNotEqual(result, True)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path, None)
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

    def test_revert_modified(self):
        """Test reverting modified access"""
        self.add_task(**self.task_kw)
        self.run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, IRODS_ACCESS_READ_OBJ
        )

        self.flow = self.init_flow()
        self.task_kw['inject']['access_name'] = IRODS_ACCESS_MODIFY_OBJ
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path2, IRODS_ACCESS_READ_OBJ
        )

    def test_revert_mixed(self):
        """Test reverting access for both new and existing access levels"""
        self.add_task(
            cls=SetAccessTask,
            name='Set access',
            inject={
                'access_name': IRODS_ACCESS_READ_OBJ,
                'path': self.sub_coll_path,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        )
        self.run_flow()
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_irods_access(DEFAULT_USER_GROUP, self.sub_coll_path2, None)

        self.flow = self.init_flow()
        self.task_kw['inject']['access_name'] = IRODS_ACCESS_MODIFY_OBJ
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assert_irods_access(
            DEFAULT_USER_GROUP, self.sub_coll_path, IRODS_ACCESS_READ_OBJ
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
        self.new_coll_path2 = iRODSPath(self.project_path, NEW_COLL2_NAME)
        self.task_kw = {
            'cls': BatchCreateCollectionsTask,
            'name': 'Create collections',
            'inject': {'coll_paths': [self.new_coll_path, self.new_coll_path2]},
        }

    def test_execute(self):
        """Test batch collection creation"""
        self.add_task(**self.task_kw)
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
        self.add_task(**self.task_kw)
        self.run_flow()

        self.flow = self.init_flow()
        self.add_task(**self.task_kw)
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
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
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
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)

        # Init and run new flow
        self.flow = self.init_flow()
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
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
        self.task_kw['inject']['coll_paths'] = [
            iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll1a'),
            iRODSPath(self.new_coll_path, 'subcoll2', 'subcoll2a'),
        ]
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll1a')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll2', 'subcoll2a')
            )
        )

    def test_execute_nested_existing(self):
        """Test batch collection creation with existing collection"""
        self.task_kw['inject']['coll_paths'] = [
            iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll1a'),
            iRODSPath(self.new_coll_path, 'subcoll1'),
        ]
        self.add_task(**self.task_kw)
        result = self.run_flow()
        self.assertEqual(result, True)
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll1a')
            )
        )
        self.assertTrue(
            self.irods.collections.exists(
                iRODSPath(self.new_coll_path, 'subcoll1')
            )
        )

    def test_revert_created_nested(self):
        """Test batch creation reverting with nested collections"""
        self.task_kw['inject']['coll_paths'] = [
            iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll1a'),
            iRODSPath(self.new_coll_path, 'subcoll2', 'subcoll2a'),
        ]
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
        result = self.run_flow()

        self.assertNotEqual(result, True)
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            iRODSPath(self.new_coll_path, 'subcoll1'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            iRODSPath(self.new_coll_path, 'subcoll1', 'subcoll1a'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            iRODSPath(self.new_coll_path, 'subcoll2'),
        )
        self.assertRaises(
            CollectionDoesNotExist,
            self.irods.collections.get,
            iRODSPath(self.new_coll_path, 'subcoll2', 'subcoll2a'),
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
        self.batch_src_path = iRODSPath(self.test_coll_path, BATCH_SRC_NAME)
        self.batch_dest_path = iRODSPath(self.test_coll_path, BATCH_DEST_NAME)
        self.src_coll = self.irods.collections.create(self.batch_src_path)
        self.dest_coll = self.irods.collections.create(self.batch_dest_path)
        # Init objects to be copied
        self.batch_obj_path = iRODSPath(self.batch_src_path, BATCH_OBJ_NAME)
        self.batch_obj2_path = iRODSPath(self.batch_src_path, BATCH_OBJ2_NAME)
        self.batch_obj = self.irods.data_objects.create(self.batch_obj_path)
        self.batch_obj2 = self.irods.data_objects.create(self.batch_obj2_path)
        self.dest_obj_path = iRODSPath(self.batch_dest_path, BATCH_OBJ_NAME)
        self.dest_obj2_path = iRODSPath(self.batch_dest_path, BATCH_OBJ2_NAME)
        # Set up default task kwargs
        self.task_kw = {
            'cls': BatchMoveDataObjectsTask,
            'name': 'Move data objects',
            'inject': {
                'landing_zone': self.zone,
                'src_root': self.batch_src_path,
                'dest_root': self.batch_dest_path,
                'src_paths': [self.batch_obj_path, self.batch_obj2_path],
                'access_name': IRODS_ACCESS_READ_OBJ,
                'user_name': DEFAULT_USER_GROUP,
                'irods_backend': self.irods_backend,
            },
        }

    def test_execute(self):
        """Test moving data objects and setting access"""
        self.add_task(**self.task_kw)
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
        self.assertEqual(obj_access.access_name, IRODS_ACCESS_READ_OBJ)
        obj_access = self.get_user_access(
            target=self.irods.data_objects.get(self.dest_obj_path),
            user_name=DEFAULT_USER_GROUP,
        )
        self.assertIsInstance(obj_access, iRODSAccess)
        self.assertEqual(obj_access.access_name, IRODS_ACCESS_READ_OBJ)

    def test_revert(self):
        """Test reverting the moving of data objects"""
        self.task_kw['force_fail'] = True
        self.add_task(**self.task_kw)  # FAIL
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
        new_obj_path = iRODSPath(self.batch_dest_path, 'batch_obj2')
        # Create object already in target
        new_obj = self.irods.data_objects.create(new_obj_path)
        self.add_task(**self.task_kw)
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
        self.task_kw['inject']['src_paths'] = [
            self.batch_obj_path,
            chk_obj.path,
            self.batch_obj2_path,
            chk_obj2.path,
        ]
        self.add_task(**self.task_kw)
        result = self.run_flow()

        self.assertEqual(result, True)
        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.status_info,
            DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE] + ' (2/2: 100%)',
        )  # Checksum files should not be counted


class TestBatchCalculateChecksumTask(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    IRODSTaskTestBase,
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
        self.obj_path = iRODSPath(self.test_coll_path, self.obj_name)
        self.task_kw = {
            'cls': BatchCalculateChecksumTask,
            'name': 'Calculate checksums',
            'inject': {
                'landing_zone': self.zone,
                'file_paths': [self.obj_path],
                'force': False,
            },
        }

    def test_calculate(self):
        """Test calculating checksum for a data object"""
        obj = self.make_irods_object(
            self.test_coll, self.obj_name, checksum=False
        )
        self.assertIsNone(obj.replicas[0].checksum)
        self.add_task(**self.task_kw)
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
        self.add_task(**self.task_kw)
        self.run_flow()
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))

    def test_calculate_existing_different(self):
        """Test calculating with existing different checksum"""
        obj = self.make_irods_object(
            self.test_coll, self.obj_name, checksum=False
        )
        self.assertIsNone(obj.replicas[0].checksum)
        obj = self.set_icat_checksum(obj, DUMMY_MD5)
        self.assertEqual(obj.replicas[0].checksum, DUMMY_MD5)
        self.add_task(**self.task_kw)
        self.run_flow()
        obj = self.irods.data_objects.get(self.obj_path)
        # Even though the sum is invalid, it is not updated without force=True
        self.assertEqual(obj.replicas[0].checksum, DUMMY_MD5)

    def test_calculate_force(self):
        """Test calculating with existing checksum and force=True"""
        obj = self.make_irods_object(
            self.test_coll, self.obj_name, checksum=False
        )
        self.assertIsNone(obj.replicas[0].checksum)
        obj = self.set_icat_checksum(obj, DUMMY_MD5)
        self.assertEqual(obj.replicas[0].checksum, DUMMY_MD5)
        self.task_kw['inject']['force'] = True
        self.add_task(**self.task_kw)
        self.run_flow()
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))
        self.assertNotEqual(obj.replicas[0].checksum, DUMMY_MD5)

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
        self.add_task(**self.task_kw)
        self.run_flow()
        obj = self.irods.data_objects.get(self.obj_path)
        self.assertIsNotNone(obj.replicas[0].checksum)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))
        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.status_info,
            DEFAULT_STATUS_INFO[ZONE_STATUS_ACTIVE] + ' (1/1: 100%)',
        )

    def test_calculate_sample_data(self):
        """Test calculating in sample data collection without zone"""
        self.make_irods_colls(self.investigation)
        assay_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.assay)
        )
        obj = self.make_irods_object(assay_coll, self.obj_name, checksum=False)
        self.assertIsNone(obj.replicas[0].checksum)
        self.task_kw['inject']['landing_zone'] = None
        self.task_kw['inject']['file_paths'] = [obj.path]
        self.add_task(**self.task_kw)
        self.run_flow()
        obj = self.irods.data_objects.get(obj.path)
        self.assertEqual(obj.replicas[0].checksum, self.get_checksum(obj))


class TestTimelineEventExtraDataUpdateTask(
    ProjectMixin, TimelineEventMixin, TaskTestMixin, TestCase
):
    """Tests for TimelineEventExtraDataUpdateTask"""

    def add_task(
        self,
        inject: Optional[dict] = None,
        force_fail: bool = False,
    ):
        """Add task based on SODARBaseTask"""
        if not inject:
            inject = {'tl_event': self.event, 'extra_data': EXTRA_DATA}
        self.flow.add_task(
            TimelineEventExtraDataUpdateTask(
                name='Update timeline event',
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
        self.inject = {'tl_event': self.event, 'extra_data': EXTRA_DATA}

    def test_execute(self):
        """Test TimelineEventExtraDataUpdateTask execute"""
        self.assertEqual(self.event.extra_data, {})
        self.add_task()
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, EXTRA_DATA)

    def test_execute_update_same_field(self):
        """Test execute with same field in existing extra data"""
        og_data = {'test': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.assertNotEqual(self.event.extra_data, EXTRA_DATA)
        self.add_task()
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, EXTRA_DATA)

    def test_execute_update_other_field(self):
        """Test execute with other field in existing extra data"""
        og_data = {'other': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.add_task()
        self.run_flow()
        self.event.refresh_from_db()
        updated_data = EXTRA_DATA
        updated_data.update(og_data)
        self.assertEqual(self.event.extra_data, updated_data)

    def test_revert(self):
        """Test revert"""
        self.assertEqual(self.event.extra_data, {})
        self.add_task(force_fail=True)
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, {})

    def test_revert_update_same_field(self):
        """Test revert with same field in existing extra data"""
        og_data = {'test': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.assertNotEqual(self.event.extra_data, EXTRA_DATA)
        self.add_task(force_fail=True)
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, og_data)

    def test_revert_update_other_field(self):
        """Test revert with other field in existing extra data"""
        og_data = {'other': 0}
        self.event.extra_data = og_data
        self.event.save()
        self.add_task(force_fail=True)
        self.run_flow()
        self.event.refresh_from_db()
        self.assertEqual(self.event.extra_data, og_data)
