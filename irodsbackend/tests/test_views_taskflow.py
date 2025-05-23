"""Tests for views in the irodsbackend app with taskflow enabled"""

import os

from irods.test.helpers import make_object

from django.conf import settings
from django.test import RequestFactory, override_settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase, HASH_SCHEME_SHA256


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
    """Tests for IrodsStatisticsAjaxView"""

    def setUp(self):
        super().setUp()
        self.get_url = self.irods_backend.get_url(
            view='stats', project=self.project, path=self.irods_path
        )
        self.post_url = self.irods_backend.get_url(
            view='stats', project=self.project, method='POST'
        )

    def test_get_empty_coll(self):
        """Test IrodsStatisticsAjaxView GET with empty collection"""
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
        """Test GET with invalid collection (should fail)"""
        with self.login(self.user):
            response = self.client.get(self.get_url + '%2F..')
        self.assertEqual(response.status_code, 400)

    def test_get_obj(self):
        """Test GET with data object"""
        self.make_irods_object(self.irods_coll, IRODS_OBJ_NAME)
        with self.login(self.user):
            response = self.client.get(self.get_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['file_count'], 1)
        self.assertEqual(response.data['total_size'], IRODS_OBJ_SIZE)

    def test_get_checksum_md5(self):
        """Test GET with MD5 checksum file"""
        obj = self.make_irods_object(self.irods_coll, IRODS_OBJ_NAME)
        self.make_checksum_object(obj)
        with self.login(self.user):
            response = self.client.get(self.get_url)
        self.assertEqual(response.status_code, 200)
        # Checksum file not counted
        self.assertEqual(response.data['file_count'], 1)
        self.assertEqual(response.data['total_size'], IRODS_OBJ_SIZE)

    @override_settings(IRODS_HASH_SCHEME=HASH_SCHEME_SHA256)
    def test_get_checksum_sha256(self):
        """Test GET with SHA256 checksum file"""
        obj = self.make_irods_object(self.irods_coll, IRODS_OBJ_NAME)
        self.make_checksum_object(obj, scheme=HASH_SCHEME_SHA256)
        with self.login(self.user):
            response = self.client.get(self.get_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['file_count'], 1)
        self.assertEqual(response.data['total_size'], IRODS_OBJ_SIZE)

    def test_get_coll_not_found(self):
        """Test GET with non-existing collection"""
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
        """Test GET with collection not belonging to project"""
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
        """Test GET with no access for iRODS collection"""
        new_user = self.make_user('new_user')
        self.make_assignment(
            self.project, new_user, self.role_contributor
        )  # No taskflow
        with self.login(new_user):
            response = self.client.get(self.get_url)
        self.assertEqual(response.status_code, 403)

    def test_post_empty_coll(self):
        """Test POST with empty iRODS collection"""
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

    def test_post_obj(self):
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

    def test_post_checksum_file_md5(self):
        """Test POST with MD5 checksum file"""
        obj_path = os.path.join(self.irods_path, IRODS_OBJ_NAME)
        obj = make_object(self.irods, obj_path, IRODS_OBJ_CONTENT)
        self.make_checksum_object(obj)
        self.assert_irods_obj(
            os.path.join(self.irods_path, IRODS_OBJ_NAME + '.md5')
        )
        post_data = {'paths': [self.irods_path]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        response_data = response.data['irods_stats']
        self.assertEqual(len(response_data.values()), 1)  # MD5 not included
        expected = {
            self.irods_path: {
                'status': 200,
                'file_count': 1,
                'total_size': IRODS_OBJ_SIZE,  # MD5 file size not included
            }
        }
        self.assertEqual(response_data, expected)

    @override_settings(IRODS_HASH_SCHEME=HASH_SCHEME_SHA256)
    def test_post_checksum_file_sha256(self):
        """Test POST with SHA256 checksum file"""
        obj_path = os.path.join(self.irods_path, IRODS_OBJ_NAME)
        obj = make_object(self.irods, obj_path, IRODS_OBJ_CONTENT)
        self.make_checksum_object(obj, scheme=HASH_SCHEME_SHA256)
        self.assert_irods_obj(
            os.path.join(self.irods_path, IRODS_OBJ_NAME + '.sha256')
        )
        post_data = {'paths': [self.irods_path]}
        with self.login(self.user):
            response = self.client.post(self.post_url, post_data)
        response_data = response.data['irods_stats']
        self.assertEqual(len(response_data.values()), 1)
        expected = {
            self.irods_path: {
                'status': 200,
                'file_count': 1,
                'total_size': IRODS_OBJ_SIZE,
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
        """Test POST with non-existing collections"""
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
