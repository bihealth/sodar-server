"""Tests for template tags in the irodsbackend app"""

from django.conf import settings

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleAssignmentMixin,
    ProjectInviteMixin,
)

from irodsbackend.templatetags import irodsbackend_tags as tags


# App settings API
app_settings = AppSettingAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
IRODS_TICKET_STR = 'ooChaa1t'


class TestTemplatetags(
    ProjectMixin, RoleAssignmentMixin, ProjectInviteMixin, TestCase
):
    """Tests for irodsbackend class for testing template tags"""

    def setUp(self):
        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        # Init users
        self.user = self.make_user('user_owner')
        # Init category
        self.category = self._make_project(
            title='TestCategoryTop', type=PROJECT_TYPE_CATEGORY, parent=None
        )
        # Init project under category
        self.project = self._make_project(
            title='TestProjectSub',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
        )
        # Init role assignments
        self.owner_as_cat = self._make_assignment(
            self.category, self.user, self.role_owner
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )

    def test_get_webdav_url(self):
        """Test get_webdav_url() with a project user"""
        self.assertEqual(
            tags.get_webdav_url(self.project, self.user),
            settings.IRODS_WEBDAV_URL,
        )

    def test_get_webdav_url_anon(self):
        """Test get_webdav_url() with anonymous access"""
        # Mock public project update
        self.project.public_guest_access = True
        self.project.save()
        app_settings.set_app_setting(
            'samplesheets',
            'public_access_ticket',
            IRODS_TICKET_STR,
            project=self.project,
        )
        self.assertEqual(
            tags.get_webdav_url(self.project, self.user),
            settings.IRODS_WEBDAV_URL_ANON.format(
                user='ticket', ticket=IRODS_TICKET_STR
            ),
        )
