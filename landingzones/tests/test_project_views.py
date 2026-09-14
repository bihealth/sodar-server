"""Tests for projectroles views with taskflow"""

from typing import Optional

from django.contrib.auth import get_user_model
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.tests.base import UIViewTestBase
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin


app_settings = AppSettingAPI()
User = get_user_model()


# SODAR constants
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']


class TestProjectCreateView(ProjectMixin, RoleAssignmentMixin, UIViewTestBase):
    """Tests for ProjectCreateView with taskflow"""

    # TODO: Replace this with ProjectCreateViewMixin dependency once upgraded to
    #       SODAR Core>=1.4.5 (see bihealth/sodar-core#1983)
    @classmethod
    def _get_project_create_data(
        cls,
        title: str,
        project_type: str,
        parent: Optional[Project],
        owner: User,
    ) -> dict:
        """
        Return POST data for project creation.

        :param title: Project title (string)
        :param project_type: Project type (string)
        :param parent: Parent category (Project or None)
        :param owner: Owner user (User)
        :return: dict
        """
        ret = {
            'title': title,
            'type': project_type,
            'parent': parent.sodar_uuid if parent else '',
            'owner': owner.sodar_uuid,
            'description': 'description',
            'public_access': '',
        }
        # Add settings values
        ret.update(
            app_settings.get_defaults(APP_SETTING_SCOPE_PROJECT, post_safe=True)
        )
        return ret

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
        post_data = self._get_project_create_data(
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
