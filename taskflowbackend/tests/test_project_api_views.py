"""REST API view tests for projectroles with taskflow"""

from irods.collection import iRODSCollection

from django.conf import settings
from django.contrib import auth
from django.forms.models import model_to_dict
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, RoleAssignment, SODAR_CONSTANTS

from projectroles.views_api import (
    PROJECTROLES_API_MEDIA_TYPE,
    PROJECTROLES_API_DEFAULT_VERSION,
)

from taskflowbackend.tests.base import TaskflowAPIViewTestBase


app_settings = AppSettingAPI()
User = auth.get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_VIEWER = SODAR_CONSTANTS['PROJECT_ROLE_VIEWER']
PROJECT_ROLE_FINDER = SODAR_CONSTANTS['PROJECT_ROLE_FINDER']
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


class CoreTaskflowAPITestBase(TaskflowAPIViewTestBase):
    """Override of TestTaskflowAPIBase for SODAR Core API views"""

    media_type = PROJECTROLES_API_MEDIA_TYPE
    api_version = PROJECTROLES_API_DEFAULT_VERSION


class TestProjectCreateAPIView(CoreTaskflowAPITestBase):
    """Tests for ProjectCreateAPIView with taskflow"""

    def test_post(self):
        """Test ProjectCreateAPIView POST with taskflow"""
        self.assertEqual(Project.objects.all().count(), 1)

        url = reverse('projectroles:api_project_create')
        request_data = {
            'title': NEW_PROJECT_TITLE,
            'type': PROJECT_TYPE_PROJECT,
            'parent': str(self.category.sodar_uuid),
            'description': 'description',
            'readme': 'readme',
            'owner': str(self.user.sodar_uuid),
            'public_access': None,
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
        project_group = self.irods_backend.get_group_name(project)
        self.assert_irods_access(
            project_group, project_coll, self.irods_access_read
        )
        self.assert_group_member(project, self.user, True, True)


class TestProjectUpdateAPIView(CoreTaskflowAPITestBase):
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
        """Test PUT for category updating"""
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
            'public_access': None,
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
            'public_access': None,
            'public_guest_access': False,  # DEPRECATED
            'archive': False,
            'full_title': UPDATED_TITLE,
            'has_public_children': False,
            'sodar_uuid': self.category.sodar_uuid,
        }
        self.assertEqual(model_dict, expected)

        self.assertEqual(
            RoleAssignment.objects.filter(project=self.category).count(), 1
        )
        self.assertEqual(self.category.get_owner().user, self.user_owner_cat)

    def test_put_project(self):
        """Test PUT for project updating"""
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
            'public_access': self.role_guest.name,
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
            'public_access': self.role_guest.pk,
            'public_guest_access': True,  # DEPRECATED
            'archive': False,
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
        """Test PATCH for updating category metadata"""
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
            'public_access': None,
            'public_guest_access': False,  # DEPRECATED
            'archive': False,
            'full_title': UPDATED_TITLE,
            'has_public_children': False,
            'sodar_uuid': self.category.sodar_uuid,
        }
        self.assertEqual(model_dict, expected)
        self.assertEqual(self.category.get_owner().user, self.user_owner_cat)

    def test_patch_project(self):
        """Test PATCH for updating project metadata"""
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
            'public_access': None,
            'public_guest_access': False,  # DEPRECATED
            'archive': False,
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
        """Test PATCH for moving project under a different category"""
        new_category = self.make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        new_cat_owner = self.make_user('new_cat_owner')
        new_cat_guest = self.make_user('new_cat_guest')
        self.make_assignment(new_category, new_cat_owner, self.role_owner)
        self.make_assignment(new_category, new_cat_guest, self.role_guest)
        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, new_cat_owner, False, False)
        self.assert_group_member(self.project, new_cat_guest, False, False)

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
        self.assert_group_member(self.project, self.user, True, True)
        self.assert_group_member(self.project, new_cat_owner, True, True)
        self.assert_group_member(self.project, new_cat_guest, True, False)


class TestRoleAssignmentCreateAPIView(CoreTaskflowAPITestBase):
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
        self.user_new = self.make_user('user_new')
        self.url = reverse(
            'projectroles:api_role_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.url_cat = reverse(
            'projectroles:api_role_create',
            kwargs={'project': self.category.sodar_uuid},
        )

    def test_post(self):
        """Test RoleAssignmentCreateAPIView POST"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)
        request_data = {
            'role': PROJECT_ROLE_CONTRIBUTOR,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(self.url, method='POST', data=request_data)
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_post_delegate(self):
        """Test POST with delegate role"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)
        request_data = {
            'role': PROJECT_ROLE_DELEGATE,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(self.url, method='POST', data=request_data)
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_post_viewer(self):
        """Test POST with viewer role"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)
        request_data = {
            'role': PROJECT_ROLE_VIEWER,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(self.url, method='POST', data=request_data)
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        # No iRODS access for viewer
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_post_inherited(self):
        """Test POST with inherited member role"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)
        request_data = {
            'role': PROJECT_ROLE_CONTRIBUTOR,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=request_data
        )
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_post_inherited_delegate(self):
        """Test POST with inherited delegate role"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)
        request_data = {
            'role': PROJECT_ROLE_DELEGATE,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=request_data
        )
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_create_inherited_viewer(self):
        """Test POST with inherited viewer role"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)
        request_data = {
            'role': PROJECT_ROLE_VIEWER,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=request_data
        )
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        # No project access should be granted
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_create_inherited_finder(self):
        """Test POST with inherited finder role"""
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)
        request_data = {
            'role': PROJECT_ROLE_FINDER,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=request_data
        )
        self.assertEqual(response.status_code, 201, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        # No project access should be granted
        self.assert_group_member(self.project, self.user_new, False, False)


class TestRoleAssignmentUpdateAPIView(CoreTaskflowAPITestBase):
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
        self.user_new = self.make_user('user_new')

    def test_put(self):
        """Test RoleAssignmentUpdateAPIView PUT"""
        update_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {
            'role': PROJECT_ROLE_GUEST,
            'user': str(self.user_new.sodar_uuid),
        }
        response = self.request_knox(url, method='PUT', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_patch(self):
        """Test PATCH"""
        update_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_GUEST}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_patch_delegate(self):
        """Test PATCH with delegate role"""
        update_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_DELEGATE}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_patch_viewer(self):
        """Test PATCH with viewer role"""
        update_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_VIEWER}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_patch_inherited(self):
        """Test PATCH with inherited member role"""
        update_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_GUEST}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_patch_inherited_delegate(self):
        """Test PATCH with inherited delegate role"""
        update_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_DELEGATE}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_patch_inherited_viewer(self):
        """Test PATCH with inherited viewer role"""
        update_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_VIEWER}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_patch_inherited_finder(self):
        """Test PATCH with inherited finder role"""
        update_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_update',
            kwargs={'roleassignment': update_as.sodar_uuid},
        )
        request_data = {'role': PROJECT_ROLE_FINDER}
        response = self.request_knox(url, method='PATCH', data=request_data)
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, False, False)


class TestRoleAssignmentOwnerTransferAPIView(CoreTaskflowAPITestBase):
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
        self.user_new = self.make_user('user_new')
        self.url = reverse(
            'projectroles:api_role_owner_transfer',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.url_cat = reverse(
            'projectroles:api_role_owner_transfer',
            kwargs={'project': self.category.sodar_uuid},
        )

    def test_post(self):
        """Test RoleAssignmentOwnerTransferAPIView POST"""
        # Make extra assignment with Taskflow
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, False)

        post_data = {
            'new_owner': self.user_new.username,
            'old_owner_role': PROJECT_ROLE_CONTRIBUTOR,
        }
        response = self.request_knox(self.url, method='POST', data=post_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.project.get_owner().user, self.user_new)
        self.assertEqual(
            RoleAssignment.objects.get(
                project=self.project, user=self.user_owner
            ).role,
            self.role_contributor,
        )
        self.assert_group_member(self.project, self.user_owner, True, False)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_post_delegate(self):
        """Test POST with delegate role for old owner"""
        # Make extra assignment with Taskflow
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, False)

        post_data = {
            'new_owner': self.user_new.username,
            'old_owner_role': PROJECT_ROLE_DELEGATE,
        }
        response = self.request_knox(self.url, method='POST', data=post_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.project.get_owner().user, self.user_new)
        self.assertEqual(
            RoleAssignment.objects.get(
                project=self.project, user=self.user_owner
            ).role,
            self.role_delegate,
        )
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_post_viewer(self):
        """Test POST with viewer role for old owner"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, False)

        post_data = {
            'new_owner': self.user_new.username,
            'old_owner_role': PROJECT_ROLE_VIEWER,
        }
        response = self.request_knox(self.url, method='POST', data=post_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.project.get_owner().user, self.user_new)
        self.assertEqual(
            RoleAssignment.objects.get(
                project=self.project, user=self.user_owner
            ).role,
            self.role_viewer,
        )
        self.assert_group_member(self.project, self.user_owner, False, False)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_post_category(self):
        """Test POST with category"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assertEqual(self.category.get_owner().user, self.user_owner_cat)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, False)

        post_data = {
            'new_owner': self.user_new.username,
            'old_owner_role': PROJECT_ROLE_CONTRIBUTOR,
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=post_data
        )

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.category.get_owner().user, self.user_new)
        self.assertEqual(
            self.category.get_role(self.user_owner_cat).role,
            self.role_contributor,
        )
        self.assert_group_member(self.project, self.user_owner_cat, True, False)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_post_inherit(self):
        """Test POST with inherited owner"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, False)
        self.assert_group_member(self.project, self.user, False, False)

        post_data = {
            'new_owner': self.user_owner_cat.username,  # Category owner
            'old_owner_role': PROJECT_ROLE_CONTRIBUTOR,
        }
        response = self.request_knox(self.url, method='POST', data=post_data)

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(self.project.get_owner().user, self.user_owner_cat)
        self.assertEqual(
            RoleAssignment.objects.get(
                project=self.project, user=self.user_owner
            ).role,
            self.role_contributor,
        )
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, self.user_owner, True, False)
        self.assert_group_member(self.project, self.user_new, True, False)
        self.assert_group_member(self.project, self.user, False, False)

    def test_post_inherit_delegate(self):
        """Test POST with delegate role set for old inherited owner"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(self.project, self.user, False, False)

        post_data = {
            'new_owner': self.user_new.username,
            'old_owner_role': PROJECT_ROLE_DELEGATE,
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=post_data
        )

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(
            self.project.get_role(self.user_new).role, self.role_owner
        )
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, True)
        self.assert_group_member(self.project, self.user, False, False)

    def test_post_inherit_viewer(self):
        """Test POST with viewer role set for old inherited owner"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_viewer
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(self.project, self.user, False, False)

        post_data = {
            'new_owner': self.user_new.username,
            'old_owner_role': PROJECT_ROLE_VIEWER,
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=post_data
        )

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(
            self.project.get_role(self.user_new).role, self.role_owner
        )
        self.assert_group_member(
            self.project, self.user_owner_cat, False, False
        )
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, True)
        self.assert_group_member(self.project, self.user, False, False)

    def test_post_inherit_finder(self):
        """Test POST with finder role set for old inherited owner"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assertEqual(self.project.get_owner().user, self.user_owner)
        self.assert_group_member(self.project, self.user_owner_cat, True, True)
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, False, False)
        self.assert_group_member(self.project, self.user, False, False)

        post_data = {
            'new_owner': self.user_new.username,
            'old_owner_role': PROJECT_ROLE_FINDER,
        }
        response = self.request_knox(
            self.url_cat, method='POST', data=post_data
        )

        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual(
            self.project.get_role(self.user_new).role, self.role_owner
        )
        self.assert_group_member(
            self.project, self.user_owner_cat, False, False
        )
        self.assert_group_member(self.project, self.user_owner, True, True)
        self.assert_group_member(self.project, self.user_new, True, True)
        self.assert_group_member(self.project, self.user, False, False)


class TestRoleAssignmentDestroyAPIView(CoreTaskflowAPITestBase):
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
        self.user_new = self.make_user('user_new')

    def test_delete(self):
        """Test RoleAssignmentDestroyAPIView DELETE"""
        role_as = self.make_assignment_taskflow(
            project=self.project,
            user=self.user_new,
            role=self.role_contributor,
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_delete_delegate(self):
        """Test DELETE with delegate role"""
        role_as = self.make_assignment_taskflow(
            project=self.project,
            user=self.user_new,
            role=self.role_delegate,
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, True)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_delete_inherited(self):
        """Test DELETE with inherited role"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_delete_inherited_delegate(self):
        """Test DELETE with inherited delegate role"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_delegate
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, True)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 2)
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_delete_inherited_with_local(self):
        """Test DELETE for inherited role with local member role"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 4)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        # Access should remain due to local role
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_delete_inherited_delegate_with_local(self):
        """Test DELETE for inherited delegate role with local member role"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_delegate
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 4)
        self.assert_group_member(self.project, self.user_new, True, True)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_delete_local_with_inherited(self):
        """Test DELETE for local role with inherited member role"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 4)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, False)

    def test_delete_local_with_inherited_delegate(self):
        """Test DELETE for local role with inherited delegate role"""
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_delegate
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 4)
        self.assert_group_member(self.project, self.user_new, True, True)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        self.assert_group_member(self.project, self.user_new, True, True)

    def test_delete_local_with_inherited_viewer(self):
        """Test DELETE for local role with inherited viewer role"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_viewer
        )
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 4)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        # No access should remain because inherited role is viewer
        self.assert_group_member(self.project, self.user_new, False, False)

    def test_delete_local_with_inherited_finder(self):
        """Test DELETE for local role with inherited finder role"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assertEqual(RoleAssignment.objects.all().count(), 4)
        self.assert_group_member(self.project, self.user_new, True, False)
        url = reverse(
            'projectroles:api_role_destroy',
            kwargs={'roleassignment': role_as.sodar_uuid},
        )
        response = self.request_knox(url, method='DELETE')
        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertEqual(RoleAssignment.objects.all().count(), 3)
        # No access should remain because inherited role is finder
        self.assert_group_member(self.project, self.user_new, False, False)
