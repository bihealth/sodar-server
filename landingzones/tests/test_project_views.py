"""Tests for projectroles views with taskflow"""

from django.contrib.auth import get_user_model
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.tests.base import ProjectCreateViewMixin, UIViewTestBase
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin


app_settings = AppSettingAPI()
User = get_user_model()


# SODAR constants
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']


class TestProjectCreateView(
    ProjectMixin, RoleAssignmentMixin, ProjectCreateViewMixin, UIViewTestBase
):
    """Tests for ProjectCreateView with taskflow"""

    def setUp(self):
        super().setUp()
        self.user_owner = self.make_user('user_owner')
        self.category = self.make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.owner_as_cat = self.make_assignment(
            self.category, self.user_owner, self.role_owner
        )
        self.user_assign = self.make_user('user_assign')
        self.url = reverse('projectroles:create')

    def test_post_validate_restrict_no_role(self):
        """Test ProjectCreateView POST with zone_access_restrict and no role"""
        self.assertEqual(Project.objects.count(), 1)
        post_data = self.get_project_create_data(
            title='TestProject',
            project_type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user_owner,
        )
        # Set user with no project role for zone_access_restrict
        # (No role can exist since the project doesn't exist yet)
        post_data['settings.landingzones.zone_access_restrict'] = (
            self.user_assign.username
        )
        with self.login(self.user_owner):
            response = self.client.post(
                reverse(
                    'projectroles:create',
                    kwargs={'project': self.category.sodar_uuid},
                ),
                post_data,
            )
        # Project creation should be successful even though user lacks role
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Project.objects.count(), 2)
        self.assertIsNotNone(
            Project.objects.filter(title='TestProject').first()
        )
