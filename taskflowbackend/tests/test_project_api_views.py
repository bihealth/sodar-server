"""REST API view tests for projectroles with taskflow"""

from irods.collection import iRODSCollection
from irods.user import iRODSUser, iRODSUserGroup

from django.conf import settings
from django.contrib import auth
from django.forms.models import model_to_dict
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, RoleAssignment, SODAR_CONSTANTS

# from projectroles.tests.taskflow_testcase import TestCase
from projectroles.views_api import CORE_API_MEDIA_TYPE, CORE_API_DEFAULT_VERSION

from taskflowbackend.tests.base import TestTaskflowAPIBase
from taskflowbackend.tests.test_project_views import IRODS_ACCESS_READ


app_settings = AppSettingAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']

# Local constants
INVITE_EMAIL = 'test@example.com'
SECRET = 'rsd886hi8276nypuvw066sbvv0rb2a6x'
TASKFLOW_TEST_MODE = getattr(settings, 'TASKFLOW_TEST_MODE', False)
NEW_PROJECT_TITLE = 'New Project'
UPDATED_TITLE = 'Updated Title'
UPDATED_DESC = 'Updated description'
UPDATED_README = 'Updated readme'


# Tests with Taskflow ----------------------------------------------------------


class TestCoreTaskflowAPIBase(TestTaskflowAPIBase):
    """Override of TestTaskflowAPIBase for SODAR Core API views"""

    media_type = CORE_API_MEDIA_TYPE
    api_version = CORE_API_DEFAULT_VERSION


class TestProjectCreateAPIView(TestCoreTaskflowAPIBase):
    """Tests for ProjectCreateAPIView with taskflow"""

    def test_create_project(self):
        """Test project creation"""
        self.assertEqual(Project.objects.all().count(), 1)

        url = reverse('projectroles:api_project_create')
        request_data = {
            'title': NEW_PROJECT_TITLE,
            'type': PROJECT_TYPE_PROJECT,
            'parent': str(self.category.sodar_uuid),
            'description': 'description',
            'readme': 'readme',
            'owner': str(self.user.sodar_uuid),
        }
        response = self.request_knox(url, method='POST', data=request_data)
        project = Project.objects.filter(type=PROJECT_TYPE_PROJECT).first()

        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(Project.objects.all().count(), 2)
        # Assert iRODS collections
        root_coll = self.irods.collections.get(
            self.irods_backend.get_projects_path()
        )
        self.assertIsInstance(root_coll, iRODSCollection)
        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(project)
        )
        self.assertIsInstance(project_coll, iRODSCollection)
        # Assert user group and owner access
        group_name = self.irods_backend.get_user_group_name(project)
        group = self.irods.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(group_name, project_coll, IRODS_ACCESS_READ)
        self.assertIsInstance(
            self.irods.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(project, self.user, True)


class TestProjectUpdateAPIView(TestCoreTaskflowAPIBase):
    """Tests for ProjectUpdateAPIView with taskflow"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )

    def test_put_category(self):
        """Test put() for category updating"""
        self.assertEqual(Project.objects.count(), 2)

        url = reverse(
            'projectroles:api_project_update',
            kwargs={'project': self.category.sodar_uuid},
        )
        request_data = {
            'title': UPDATED_TITLE,
            'type': PROJECT_TYPE_CATEGORY,
            'parent': '',
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
        }
        response = self.request_knox(url, method='PUT', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(Project.objects.count(), 2)

        self.category.refresh_from_db()
        model_dict = model_to_dict(self.category)
        model_dict['readme'] = model_dict['readme'].raw
        expected = {
            'id': self.category.pk,
            'title': UPDATED_TITLE,
            'type': PROJECT_TYPE_CATEGORY,
            'parent': None,
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
            'public_guest_access': False,
            'full_title': UPDATED_TITLE,
            'has_public_children': False,
            'sodar_uuid': self.category.sodar_uuid,
        }
        self.assertEqual(model_dict, expected)

        self.assertEqual(
            RoleAssignment.objects.filter(project=self.category).count(), 1
        )
        self.assertEqual(self.category.get_owner().user, self.user)

    def test_put_project(self):
        """Test put() for project updating"""
        self.assertEqual(Project.objects.count(), 2)

        url = reverse(
            'projectroles:api_project_update',
            kwargs={'project': self.project.sodar_uuid},
        )
        request_data = {
            'title': UPDATED_TITLE,
            'type': PROJECT_TYPE_PROJECT,
            'parent': str(self.category.sodar_uuid),
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
            'public_guest_access': True,
        }
        response = self.request_knox(url, method='PUT', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(Project.objects.count(), 2)

        self.project.refresh_from_db()
        model_dict = model_to_dict(self.project)
        model_dict['readme'] = model_dict['readme'].raw
        expected = {
            'id': self.project.pk,
            'title': UPDATED_TITLE,
            'type': PROJECT_TYPE_PROJECT,
            'parent': self.category.pk,
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
            'public_guest_access': True,
            'full_title': self.category.title + ' / ' + UPDATED_TITLE,
            'has_public_children': False,
            'sodar_uuid': self.project.sodar_uuid,
        }
        self.assertEqual(model_dict, expected)

        self.assertEqual(
            RoleAssignment.objects.filter(project=self.project).count(), 1
        )
        self.assertEqual(self.project.get_owner().user, self.user)

        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('title').value, UPDATED_TITLE
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value,
            UPDATED_DESC,
        )

    def test_patch_category(self):
        """Test patch() for updating category metadata"""
        self.assertEqual(Project.objects.count(), 2)

        url = reverse(
            'projectroles:api_project_update',
            kwargs={'project': self.category.sodar_uuid},
        )
        request_data = {
            'title': UPDATED_TITLE,
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
        }
        response = self.request_knox(url, method='PATCH', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(Project.objects.count(), 2)

        self.category.refresh_from_db()
        model_dict = model_to_dict(self.category)
        model_dict['readme'] = model_dict['readme'].raw
        expected = {
            'id': self.category.pk,
            'title': UPDATED_TITLE,
            'type': PROJECT_TYPE_CATEGORY,
            'parent': None,
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
            'public_guest_access': False,
            'full_title': UPDATED_TITLE,
            'has_public_children': False,
            'sodar_uuid': self.category.sodar_uuid,
        }
        self.assertEqual(model_dict, expected)
        self.assertEqual(self.category.get_owner().user, self.user)

    def test_patch_project(self):
        """Test patch() for updating project metadata"""
        self.assertEqual(Project.objects.count(), 2)

        url = reverse(
            'projectroles:api_project_update',
            kwargs={'project': self.project.sodar_uuid},
        )
        request_data = {
            'title': UPDATED_TITLE,
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
        }
        response = self.request_knox(url, method='PATCH', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(Project.objects.count(), 2)

        self.project.refresh_from_db()
        model_dict = model_to_dict(self.project)
        model_dict['readme'] = model_dict['readme'].raw
        expected = {
            'id': self.project.pk,
            'title': UPDATED_TITLE,
            'type': PROJECT_TYPE_PROJECT,
            'parent': self.category.pk,
            'description': UPDATED_DESC,
            'readme': UPDATED_README,
            'public_guest_access': False,
            'full_title': self.category.title + ' / ' + UPDATED_TITLE,
            'has_public_children': False,
            'sodar_uuid': self.project.sodar_uuid,
        }
        self.assertEqual(model_dict, expected)
        self.assertEqual(self.project.get_owner().user, self.user)
        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('title').value, self.project.title
        )
        self.assertEqual(
            project_coll.metadata.get_one('description').value,
            self.project.description,
        )

    def test_patch_project_move(self):
        """Test patch() for moving project under a different category"""
        new_category = self._make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        self._make_assignment(new_category, self.user, self.role_owner)

        url = reverse(
            'projectroles:api_project_update',
            kwargs={'project': self.project.sodar_uuid},
        )
        request_data = {'parent': str(new_category.sodar_uuid)}
        response = self.request_knox(url, method='PATCH', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.project.refresh_from_db()
        model_dict = model_to_dict(self.project)
        self.assertEqual(model_dict['parent'], new_category.pk)
        self.assertEqual(self.project.get_owner().user, self.user)

        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(new_category.sodar_uuid),
        )


class TestRoleAssignmentCreateAPIView(TestCoreTaskflowAPIBase):
    """Tests for RoleAssignmentCreateAPIView with taskflow"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        # Create user for assignments
        self.assign_user = self.make_user('assign_user')

    def test_create_role(self):
        """Test role assignment creation"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        url = reverse(
            'projectroles:api_role_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        request_data = {
            'role': PROJECT_ROLE_CONTRIBUTOR,
            'user': str(self.assign_user.sodar_uuid),
        }
        response = self.request_knox(url, method='POST', data=request_data)
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.assign_user, True)


class TestRoleAssignmentUpdateAPIView(TestCoreTaskflowAPIBase):
    """Tests for RoleAssignmentUpdateAPIView with taskflow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.assign_user = self.make_user('assign_user')
        # Make extra assignment with Taskflow
        self.update_as = self.make_assignment_taskflow(
            project=self.project,
            user=self.assign_user,
            role=self.role_contributor,
        )

    def test_put_role(self):
        """Test put() for role assignment updating"""
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.assign_user, True)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': self.update_as.sodar_uuid},
        )
        request_data = {
            'role': PROJECT_ROLE_GUEST,
            'user': str(self.assign_user.sodar_uuid),
        }
        response = self.request_knox(url, method='PUT', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.assign_user, True)

    def test_patch_role(self):
        """Test patch() for role assignment updating"""
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.assign_user, True)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': self.update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_GUEST}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.assign_user, True)


class TestRoleAssignmentDestroyAPIView(TestCoreTaskflowAPIBase):
    """Tests for RoleAssignmentDestroyAPIView with taskflow"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.assign_user = self.make_user('assign_user')

    def test_delete_role(self):
        """Test delete() for role assignment deletion"""
        update_as = self.make_assignment_taskflow(
            project=self.project,
            user=self.assign_user,
            role=self.role_contributor,
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.assign_user, True)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.assign_user, False)

    def test_delete_role_category(self):
        """Test delete() for role assignment deletion with category"""
        update_as = self.make_assignment_taskflow(
            project=self.category,
            user=self.assign_user,
            role=self.role_contributor,
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)


class TestRoleAssignmentOwnerTransferAPIView(TestCoreTaskflowAPIBase):
    """Tests for RoleAssignmentOwnerTransferAPIView"""

    def setUp(self):
        super().setUp()
        self.user_owner = self.make_user('user_owner')
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner,
            description='description',
        )
        self.assign_user = self.make_user('assign_user')

    def test_transfer_owner(self):
        """Test transferring ownership for a project"""
        # Make extra assignment with Taskflow
        self.make_assignment_taskflow(
            project=self.project,
            user=self.assign_user,
            role=self.role_contributor,
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner, True)
        self.assert_group_member(self.project, self.assign_user, True)

        url = reverse(
            'projectroles:api_role_owner_transfer',
            kwargs={'project': self.project.sodar_uuid},
        )
        request_data = {
            'new_owner': self.assign_user.username,
            'old_owner_role': self.role_contributor.name,
        }
        response = self.request_knox(url, method='POST', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.project.get_owner().user, self.assign_user)
        self.assertEqual(
            RoleAssignment.objects.get(
                project=self.project, user=self.user_owner
            ).role,
            self.role_contributor,
        )
        self.assert_group_member(self.project, self.user_owner, True)
        self.assert_group_member(self.project, self.assign_user, True)

    def test_transfer_owner_category(self):
        """Test transferring ownership for a category"""
        self.make_assignment_taskflow(
            project=self.category,
            user=self.assign_user,
            role=self.role_contributor,
        )
        self.assertEqual(self.category.get_owner().user, self.user)
        self.assert_group_member(self.project, self.user_owner, True)
        self.assert_group_member(self.project, self.assign_user, False)

        url = reverse(
            'projectroles:api_role_owner_transfer',
            kwargs={'project': self.category.sodar_uuid},
        )
        request_data = {
            'new_owner': self.assign_user.username,
            'old_owner_role': self.role_contributor.name,
        }
        response = self.request_knox(url, method='POST', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.category.get_owner().user, self.assign_user)
        self.assert_group_member(self.project, self.user_owner, True)
        self.assert_group_member(self.project, self.assign_user, True)

    def test_transfer_owner_inherit(self):
        """Test transferring ownership to an inherited owner"""
        self.make_assignment_taskflow(
            project=self.project,
            user=self.assign_user,
            role=self.role_contributor,
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner, True)
        self.assert_group_member(self.project, self.assign_user, True)
        self.assert_group_member(self.project, self.user, True)

        url = reverse(
            'projectroles:api_role_owner_transfer',
            kwargs={'project': self.project.sodar_uuid},
        )
        request_data = {
            'new_owner': self.user.username,  # self.user = category owner
            'old_owner_role': self.role_contributor.name,
        }
        response = self.request_knox(url, method='POST', data=request_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.project.get_owner().user, self.user)
        self.assertEqual(
            RoleAssignment.objects.get(
                project=self.project, user=self.user_owner
            ).role,
            self.role_contributor,
        )
        self.assert_group_member(self.project, self.user_owner, True)
        self.assert_group_member(self.project, self.assign_user, True)
        self.assert_group_member(self.project, self.user, True)
