"""Tests for views in the irodsbackend app with taskflow enabled"""

import os

from irods.test.helpers import make_object

from django.conf import settings
from django.test import RequestFactory

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
IRODS_TEMP_COLL = 'temp'
IRODS_TEMP_COLL2 = 'temp2'
IRODS_OBJ_SIZE = 1024
IRODS_OBJ_CONTENT = ''.join('x' for _ in range(IRODS_OBJ_SIZE))
IRODS_OBJ_NAME = 'test1.txt'
IRODS_MD5_NAME = 'test1.txt.md5'
IRODS_NON_PROJECT_PATH = (
    '/' + settings.IRODS_ZONE + '/home/' + settings.IRODS_USER
)
IRODS_FAIL_COLL = 'xeiJ1Vie'


class IrodsbackendViewTestBase(TaskflowViewTestBase):
    """Base class for irodsbackend UI view testing"""

    def setUp(self):
        super().setUp()
        self.req_factory = RequestFactory()
        # Init project with owner in taskflow
        self.project, self.owner_as = self.make_project_taskflow(
            'TestProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        # Create test collection in iRODS
        # NOTE: Not fully valid sample paths, needs make_irods_colls() for that
        self.project_path = self.irods_backend.get_path(self.project)
        self.irods_path = os.path.join(self.project_path, IRODS_TEMP_COLL)
        self.irods_coll = self.irods.collections.create(self.irods_path)


class TestIrodsStatisticsAjaxView(IrodsbackendViewTestBase):
    """Tests for the landing zone collection statistics Ajax view"""

    def setUp(self):
        super().setUp()
        self.post_url = self.irods_backend.get_url(
            view='stats', project=self.project, method='POST'
        )

    def test_get_empty_coll(self):
        """Test GET request for stats on empty iRODS collection"""
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=self.irods_path
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['file_count'], 0)
        self.assertEqual(response.data['total_size'], 0)

    def test_get_invalid_coll(self):
        """Test GET request with invalid collection (should fail)"""
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=self.irods_path
                )
                + '%2F..'
            )
        self.assertEqual(response.status_code, 400)

    def test_get_coll_obj(self):
        """Test GET for stats on collection with data object"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods, obj_path, IRODS_OBJ_CONTENT)
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=self.irods_path
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['file_count'], 1)
        self.assertEqual(response.data['total_size'], IRODS_OBJ_SIZE)

    def test_get_coll_md5(self):
        """Test GET for stats on collection with data object and md5"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods, obj_path, IRODS_OBJ_CONTENT)
        # Put MD5 data object in iRODS
        md5_path = self.irods_path + '/' + IRODS_MD5_NAME
        make_object(self.irods, md5_path, IRODS_OBJ_CONTENT)  # Not actual md5
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=self.irods_path
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['file_count'], 1)  # md5 not counted
        self.assertEqual(response.data['total_size'], IRODS_OBJ_SIZE)

    def test_get_coll_not_found(self):
        """Test GET for stats on non-existing collection"""
        fail_path = self.irods_path + '/' + IRODS_FAIL_COLL
        self.assertEqual(self.irods.collections.exists(fail_path), False)
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=fail_path
                )
            )
        self.assertEqual(response.status_code, 404)

    def test_get_coll_not_in_project(self):
        """Test GET for stats on collection not belonging to project"""
        self.assertEqual(
            self.irods.collections.exists(IRODS_NON_PROJECT_PATH), True
        )
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats',
                    project=self.project,
                    path=IRODS_NON_PROJECT_PATH,
                )
            )
        self.assertEqual(response.status_code, 400)

    def test_get_no_access(self):
        """Test GET for stats with no access for iRODS collection"""
        new_user = self.make_user('new_user')
        self.make_assignment(
            self.project, new_user, self.role_contributor
        )  # No taskflow
        with self.login(new_user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=self.irods_path
                )
            )
        self.assertEqual(response.status_code, 403)

    def test_post_empty_coll(self):
        """Test POST on empty iRODS collection"""
        post_data = {'paths': [self.irods_path]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        self.assertEqual(response.status_code, 200)
        response_data = response.data['irods_stats']
        self.assertEqual(len(response_data.values()), 1)
        expected = {
            self.irods_path: {'status': 200, 'file_count': 0, 'total_size': 0}
        }
        self.assertEqual(response_data, expected)

    def test_post_non_empty_coll(self):
        """Test POST with data object in collection"""
        obj_path = os.path.join(self.irods_path, IRODS_OBJ_NAME)
        make_object(self.irods, obj_path, IRODS_OBJ_CONTENT)
        post_data = {'paths': [self.irods_path]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        expected = {
            self.irods_path: {
                'status': 200,
                'file_count': 1,
                'total_size': IRODS_OBJ_SIZE,
            }
        }
        self.assertEqual(response.data['irods_stats'], expected)

    def test_post_md5_file(self):
        """Test POST with .md5 file in collection"""
        obj_path = os.path.join(self.irods_path, IRODS_OBJ_NAME)
        obj = make_object(self.irods, obj_path, IRODS_OBJ_CONTENT)
        self.make_irods_md5_object(obj)
        self.assert_irods_obj(
            os.path.join(self.irods_path, IRODS_OBJ_NAME + '.md5')
        )
        post_data = {'paths': [self.irods_path]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        response_data = response.data['irods_stats']
        self.assertEqual(len(response_data.values()), 1)  # md5 not included
        expected = {
            self.irods_path: {
                'status': 200,
                'file_count': 1,
                'total_size': IRODS_OBJ_SIZE,  # md5 file size not included
            }
        }
        self.assertEqual(response_data, expected)

    def test_post_multiple_paths(self):
        """Test POST with multiple paths"""
        irods_path_new = os.path.join(self.project_path, IRODS_TEMP_COLL2)
        self.irods.collections.create(irods_path_new)
        obj_path = os.path.join(self.irods_path, IRODS_OBJ_NAME)
        make_object(self.irods, obj_path, IRODS_OBJ_CONTENT)
        post_data = {'paths': [self.irods_path, irods_path_new]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        expected = {
            self.irods_path: {
                'status': 200,
                'file_count': 1,
                'total_size': IRODS_OBJ_SIZE,
            },
            irods_path_new: {'status': 200, 'file_count': 0, 'total_size': 0},
        }
        self.assertEqual(response.data['irods_stats'], expected)

    def test_post_dupe_path(self):
        """Test POST with duplicate path"""
        # This should not happen in the UI, but testing in case of view abuse
        post_data = {'paths': [self.irods_path, self.irods_path]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        # We should only get one result
        self.assertEqual(len(response.data['irods_stats'].values()), 1)

    def test_post_coll_not_found(self):
        """Test POST for stats on non-existing collections"""
        fail_path = os.path.join(self.irods_path, IRODS_FAIL_COLL)
        self.assertEqual(self.irods.collections.exists(fail_path), False)
        post_data = {'paths': [fail_path]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        self.assertEqual(response.status_code, 200)
        expected = {fail_path: {'status': 404}}
        self.assertEqual(response.data['irods_stats'], expected)

    def test_post_non_project_path(self):
        """Test POST with path not belonging to project"""
        self.assertEqual(
            self.irods.collections.exists(IRODS_NON_PROJECT_PATH), True
        )
        post_data = {'paths': [IRODS_NON_PROJECT_PATH]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        self.assertEqual(response.status_code, 200)
        expected = {IRODS_NON_PROJECT_PATH: {'status': 400}}
        self.assertEqual(response.data['irods_stats'], expected)
