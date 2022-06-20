"""Tests for views in the irodsbackend app"""

import base64
from unittest import skipIf

from irods.test.helpers import make_object

from django.conf import settings
from django.test import RequestFactory, override_settings
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.plugins import get_backend_api


# Global constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
IRODS_TEMP_COLL = 'temp'
IRODS_OBJ_SIZE = 1024
IRODS_OBJ_CONTENT = ''.join('x' for _ in range(IRODS_OBJ_SIZE))
IRODS_OBJ_NAME = 'test1.txt'
IRODS_MD5_NAME = 'test1.txt.md5'
IRODS_NON_PROJECT_PATH = (
    '/' + settings.IRODS_ZONE + '/home/' + settings.IRODS_USER
)
IRODS_FAIL_COLL = 'xeiJ1Vie'
IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'
LOCAL_USER_NAME = 'local_user'
LOCAL_USER_PASS = 'password'


class TestViewsBase(ProjectMixin, RoleAssignmentMixin, TestCase):
    """Base class for view testing"""

    def setUp(self):
        self.req_factory = RequestFactory()

        # Get iRODS backend
        self.irods_backend = get_backend_api('omics_irods')
        self.assertIsNotNone(self.irods_backend)

        # Get iRODS session
        self.irods_session = self.irods_backend.get_session()

        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE
        )[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR
        )[0]
        self.role_guest = Role.objects.get_or_create(name=PROJECT_ROLE_GUEST)[0]

        # Init superuser
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Init project with owner
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.as_owner = self._make_assignment(
            self.project, self.user, self.role_owner
        )

        # Build path for test collection
        self.project_path = self.irods_backend.get_path(self.project)
        self.irods_path = self.project_path + '/' + IRODS_TEMP_COLL

        # Create test collection in iRODS
        self.irods_coll = self.irods_session.collections.create(self.irods_path)

    def tearDown(self):
        if self.irods_session.collections.exists(self.project_path):
            self.irods_session.collections.get(self.project_path).remove(
                force=True
            )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsStatisticsAjaxView(TestViewsBase):
    """Tests for the landing zone collection statistics Ajax view"""

    def test_get_empty_coll(self):
        """Test GET request for stats on an empty collection in iRODS"""
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=self.irods_path
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['file_count'], 0)
        self.assertEqual(response.data['total_size'], 0)

    def test_get_coll_obj(self):
        """Test GET for stats on a collection with a data object"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods_session, obj_path, IRODS_OBJ_CONTENT)

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
        """Test GET for stats on a collection with a data object and md5"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods_session, obj_path, IRODS_OBJ_CONTENT)
        # Put MD5 data object in iRODS
        md5_path = self.irods_path + '/' + IRODS_MD5_NAME
        make_object(
            self.irods_session, md5_path, IRODS_OBJ_CONTENT
        )  # Not actual md5

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
        """Test GET for stats on a collection which doesn't exist"""
        fail_path = self.irods_path + '/' + IRODS_FAIL_COLL
        self.assertEqual(
            self.irods_session.collections.exists(fail_path), False
        )

        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=fail_path
                )
            )
        self.assertEqual(response.status_code, 404)

    def test_get_coll_not_in_project(self):
        """Test GET for stats on a collection not belonging to project"""
        self.assertEqual(
            self.irods_session.collections.exists(IRODS_NON_PROJECT_PATH), True
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
        """Test GET for stats with no access for the iRODS folder"""
        new_user = self.make_user('new_user')
        self._make_assignment(
            self.project, new_user, self.role_contributor
        )  # No taskflow

        with self.login(new_user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='stats', project=self.project, path=self.irods_path
                )
            )
        self.assertEqual(response.status_code, 403)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsObjectListAjaxView(TestViewsBase):
    """Tests for the landing zone data object listing Ajax view"""

    def setUp(self):
        super().setUp()

        # Build path for test collection
        self.irods_path = (
            self.irods_backend.get_path(self.project) + '/' + IRODS_TEMP_COLL
        )

        # Create test collection in iRODS
        self.irods_coll = self.irods_session.collections.create(self.irods_path)

    def test_get_empty_coll(self):
        """Test GET for listing an empty collection in iRODS"""
        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='list',
                    path=self.irods_path,
                    project=self.project,
                    md5=0,
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 0)

    def test_get_coll_obj(self):
        """Test GET for listing a collection with a data object"""

        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        data_obj = make_object(self.irods_session, obj_path, IRODS_OBJ_CONTENT)

        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='list',
                    path=self.irods_path,
                    project=self.project,
                    md5=0,
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 1)

        list_obj = response.data['irods_data'][0]
        self.assertNotIn('md5_file', list_obj)
        self.assertEqual(data_obj.name, list_obj['name'])
        self.assertEqual(data_obj.path, list_obj['path'])
        self.assertEqual(data_obj.size, IRODS_OBJ_SIZE)

    def test_get_coll_md5(self):
        """Test GET for listing a collection with a data object and md5"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods_session, obj_path, IRODS_OBJ_CONTENT)
        # Put MD5 data object in iRODS
        md5_path = self.irods_path + '/' + IRODS_MD5_NAME
        make_object(
            self.irods_session, md5_path, IRODS_OBJ_CONTENT
        )  # Not actual md5

        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='list',
                    path=self.irods_path,
                    project=self.project,
                    md5=1,
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 1)  # Still 1
        self.assertEqual(response.data['irods_data'][0]['md5_file'], True)

    def test_get_coll_md5_no_file(self):
        """Test GET with md5 set True but no md5 file"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods_session, obj_path, IRODS_OBJ_CONTENT)

        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='list',
                    path=self.irods_path,
                    project=self.project,
                    md5=1,
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 1)
        self.assertEqual(response.data['irods_data'][0]['md5_file'], False)

    def test_get_coll_not_found(self):
        """Test GET for listing a collection which doesn't exist"""
        fail_path = self.irods_path + '/' + IRODS_FAIL_COLL
        self.assertEqual(
            self.irods_session.collections.exists(fail_path), False
        )

        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='list', path=fail_path, project=self.project, md5=0
                )
            )
        self.assertEqual(response.status_code, 404)

    def test_get_coll_not_in_project(self):
        """Test GET for listing a collection not belonging to project"""
        self.assertEqual(
            self.irods_session.collections.exists(IRODS_NON_PROJECT_PATH), True
        )

        with self.login(self.user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='list',
                    path=IRODS_NON_PROJECT_PATH,
                    project=self.project,
                    md5=0,
                )
            )
        self.assertEqual(response.status_code, 400)

    def test_get_no_access(self):
        """Test GET for listing with no acces for the iRODS folder"""
        new_user = self.make_user('new_user')
        self._make_assignment(
            self.project, new_user, self.role_contributor
        )  # No taskflow

        with self.login(new_user):
            response = self.client.get(
                self.irods_backend.get_url(
                    view='list',
                    path=self.irods_path,
                    project=self.project,
                    md5=0,
                )
            )
        self.assertEqual(response.status_code, 403)


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsBatchStatisticsAjaxView(TestViewsBase):
    """Tests for the batch statistics Ajax view"""

    def test_post_empty_coll_stats(self):
        """Test POST for batch stats on empty collections in iRODS"""
        post_data = {
            'paths': [self.irods_path, self.irods_path],
            'md5': ['0', '0'],
        }

        with self.login(self.user):
            response = self.client.post(
                self.irods_backend.get_url(view='stats', project=self.project),
                post_data,
            )
        self.assertEqual(response.status_code, 200)
        for idx in range(len(response.data['coll_objects'])):
            self.assertEqual(
                response.data['coll_objects'][idx]['status'], '200'
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['file_count'], 0
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['total_size'], 0
            )

    def test_post_coll_stats(self):
        """Test POST for batch stats on collections with a data object"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods_session, obj_path, IRODS_OBJ_CONTENT)
        post_data = {
            'paths': [self.irods_path, self.irods_path],
            'md5': ['0', '0'],
        }

        with self.login(self.user):
            response = self.client.post(
                self.irods_backend.get_url(view='stats', project=self.project),
                post_data,
            )
        self.assertEqual(response.status_code, 200)
        for idx in range(len(response.data['coll_objects'])):
            self.assertEqual(
                response.data['coll_objects'][idx]['status'], '200'
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['file_count'], 1
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['total_size'],
                IRODS_OBJ_SIZE,
            )

    def test_post_coll_md5_stats(self):
        """Test POST for batch stats on collections with a data object and md5"""
        # Put data object in iRODS
        obj_path = self.irods_path + '/' + IRODS_OBJ_NAME
        make_object(self.irods_session, obj_path, IRODS_OBJ_CONTENT)
        # Put MD5 data object in iRODS
        md5_path = self.irods_path + '/' + IRODS_MD5_NAME
        make_object(
            self.irods_session, md5_path, IRODS_OBJ_CONTENT
        )  # Not actual md5
        post_data = {
            'paths': [self.irods_path, self.irods_path],
            'md5': ['1', '1'],
        }

        with self.login(self.user):
            response = self.client.post(
                self.irods_backend.get_url(view='stats', project=self.project),
                post_data,
            )
        self.assertEqual(response.status_code, 200)
        for idx in range(len(response.data['coll_objects'])):
            self.assertEqual(
                response.data['coll_objects'][idx]['status'], '200'
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['file_count'], 1
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['total_size'],
                IRODS_OBJ_SIZE,
            )

    def test_post_coll_not_found(self):
        """Test POST for stats on collections which don't exist"""
        fail_path = self.irods_path + '/' + IRODS_FAIL_COLL
        self.assertEqual(
            self.irods_session.collections.exists(fail_path), False
        )
        post_data = {'paths': [fail_path, fail_path], 'md5': ['0', '0']}

        with self.login(self.user):
            response = self.client.post(
                self.irods_backend.get_url(view='stats', project=self.project),
                post_data,
            )
        self.assertEqual(response.status_code, 200)
        for idx in range(len(response.data['coll_objects'])):
            self.assertEqual(
                response.data['coll_objects'][idx]['status'], '404'
            )
            self.assertEqual(response.data['coll_objects'][idx]['stats'], {})

    def test_post_coll_not_in_project(self):
        """Test POST for stats on collections not belonging to project"""
        self.assertEqual(
            self.irods_session.collections.exists(IRODS_NON_PROJECT_PATH), True
        )
        post_data = {
            'paths': [IRODS_NON_PROJECT_PATH, IRODS_NON_PROJECT_PATH],
            'md5': ['0', '0'],
        }

        with self.login(self.user):
            response = self.client.post(
                self.irods_backend.get_url(view='stats', project=self.project),
                post_data,
            )
        self.assertEqual(response.status_code, 200)
        for idx in range(len(response.data['coll_objects'])):
            self.assertEqual(
                response.data['coll_objects'][idx]['status'], '400'
            )
            self.assertEqual(response.data['coll_objects'][idx]['stats'], {})

    def test_post_no_access(self):
        """Test POST for batch stats with no access for the iRODS collections"""
        new_user = self.make_user('new_user')
        self._make_assignment(
            self.project, new_user, self.role_contributor
        )  # No taskflow
        post_data = {
            'paths': [self.irods_path, self.irods_path],
            'md5': ['0', '0'],
        }

        with self.login(new_user):
            response = self.client.post(
                self.irods_backend.get_url(view='stats', project=self.project),
                post_data,
            )

        self.assertEqual(response.status_code, 200)
        for idx in range(len(response.data['coll_objects'])):
            self.assertEqual(response.data['coll_objects'][idx]['stats'], {})

    def test_post_one_empty_coll(self):
        """Test POST for batch stats on only one (empty) collection in iRODS"""
        post_data = {'paths': [self.irods_path], 'md5': ['0']}

        with self.login(self.user):
            response = self.client.post(
                self.irods_backend.get_url(view='stats', project=self.project),
                post_data,
            )
        self.assertEqual(response.status_code, 200)
        for idx in range(len(response.data['coll_objects'])):
            self.assertEqual(
                response.data['coll_objects'][idx]['status'], '200'
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['file_count'], 0
            )
            self.assertEqual(
                response.data['coll_objects'][idx]['stats']['total_size'], 0
            )


class TestLocalAuthAPIView(TestCase):
    """Tests for LocalAuthAPIView"""

    @staticmethod
    def _get_auth_header(username, password):
        """Return basic auth header"""
        credentials = base64.b64encode(
            '{}:{}'.format(username, password).encode('utf-8')
        ).strip()
        return {
            'HTTP_AUTHORIZATION': 'Basic {}'.format(credentials.decode('utf-8'))
        }

    def setUp(self):
        self.user = self.make_user(LOCAL_USER_NAME, LOCAL_USER_PASS)

    def test_auth(self):
        """Test auth with existing user and auth check enabled"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header(LOCAL_USER_NAME, LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(IRODS_SODAR_AUTH=False)
    def test_auth_disabled(self):
        """Test auth with existing user and auth check disabled"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header(LOCAL_USER_NAME, LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 500)

    def test_auth_invalid_user(self):
        """Test auth with invalid user"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header(LOCAL_USER_NAME, 'invalid_password')
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_invalid_password(self):
        """Test auth with invalid password"""
        response = self.client.post(
            reverse('irodsbackend:api_auth'),
            **self._get_auth_header('invalid_user', LOCAL_USER_PASS)
        )
        self.assertEqual(response.status_code, 401)
