"""Tests for UI views in the landingzones app"""

from django.forms import HiddenInput
from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.constants import ZONE_STATUS_ACTIVE, ZONE_STATUS_DELETED
from landingzones.models import LandingZone
from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_STATUS_INFO = 'Testing'


class TestViewsBase(
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    SampleSheetIOMixin,
    LandingZoneMixin,
    TestCase,
):
    """Base class for view testing"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Init superuser
        self.user = self.make_user('superuser')
        self.user.is_superuser = True
        self.user.save()
        # Init project with owner
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user, self.role_owner
        )
        # Init contributor user and assignment
        self.user_contributor = self.make_user('user_contributor')
        self.contributor_as = self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create LandingZone
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )


class TestProjectZonesView(TestViewsBase):
    """Tests for the project zones list view"""

    def test_render_owner(self):
        """Test rendering of project zones view as project owner"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['investigation'], self.investigation)
        self.assertEqual(response.context['zones_own'].count(), 1)
        self.assertEqual(response.context['zones_other'].count(), 0)
        self.assertEqual(response.context['zones_own'][0], self.landing_zone)
        self.assertEqual(response.context['zone_access_disabled'], False)

    def test_render_contrib(self):
        """Test rendering of project zones view as project contributor"""
        with self.login(self.user_contributor):
            response = self.client.get(
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['investigation'], self.investigation)
        # This user should have no zones
        self.assertEqual(response.context['zones_own'].count(), 0)
        self.assertNotIn('zones_other', response.context)
        self.assertEqual(response.context['zone_access_disabled'], False)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_render_disable(self):
        """Test rendering with user access disabled"""
        with self.login(self.user_contributor):
            response = self.client.get(
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.context['zone_access_disabled'], True)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_render_disable_superuser(self):
        """Test rendering with user access disabled as superuser"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.context['zone_access_disabled'], False)


class TestLandingZoneCreateView(TestViewsBase):
    """Tests for the landing zone creation view"""

    def test_render(self):
        """Test rendering of the landing zone creation view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:create',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        # Assert form
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertIsNotNone(form.fields['title_suffix'])
        self.assertIsNotNone(form.fields['assay'])
        self.assertIsNotNone(form.fields['description'])
        self.assertIsNotNone(form.fields['configuration'])


class TestLandingZoneUpdateView(TestViewsBase):
    """Tests for the landing zone update view"""

    def test_render(self):
        """Test rendering of the landing zone update view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:update',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        # Assert form
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertIsNotNone(form.fields['assay'])
        self.assertIsNotNone(form.fields['description'])
        # Make sure to also assert the expected fields
        # are hidden with the HiddenInput widget.
        self.assertIsInstance(form.fields['title_suffix'].widget, HiddenInput)
        self.assertIsInstance(form.fields['configuration'].widget, HiddenInput)
        self.assertIsInstance(form.fields['create_colls'].widget, HiddenInput)
        self.assertIsInstance(form.fields['restrict_colls'].widget, HiddenInput)
        self.assertIsInstance(form.fields['assay'].widget, HiddenInput)

    def test_render_invalid_status(self):
        """Test rendering with an invalid zone status"""
        self.landing_zone.status = ZONE_STATUS_DELETED
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:update',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 302)

    def test_post(self):
        """Test POST request to the landing zone update view"""
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:update',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data={
                    'assay': self.assay.sodar_uuid,
                    'description': 'test description updated',
                    'user_message': 'test user message',
                },
            )
            self.assertRedirects(
                response,
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        landing_zone = LandingZone.objects.get(
            sodar_uuid=self.landing_zone.sodar_uuid
        )
        self.assertEqual(landing_zone.assay, self.assay)
        self.assertEqual(landing_zone.description, 'test description updated')
        self.assertEqual(landing_zone.user_message, 'test user message')

    def test_post_invalid_data(self):
        """Test POST request with invalid data"""
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:update',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                ),
                data={
                    'assay': self.assay.sodar_uuid,
                    'description': 'test description updated',
                    'title_suffix': 'test suffix',
                },
            )
        self.assertEqual(response.status_code, 302)
        landing_zone = LandingZone.objects.get(
            sodar_uuid=self.landing_zone.sodar_uuid
        )
        self.assertEqual(landing_zone.assay, self.assay)
        self.assertEqual(landing_zone.description, 'description')


class TestLandingZoneMoveView(TestViewsBase):
    """Tests for the landing zone validation and moving view"""

    def test_render_invalid_status(self):
        """Test rendering with an invalid zone status"""
        self.landing_zone.status = ZONE_STATUS_DELETED
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:move',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 302)


class TestLandingZoneDeleteView(TestViewsBase):
    """Tests for the landing zone deletion view"""

    def test_render(self):
        """Test rendering of the landing zone deletion view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:delete',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)

    def test_render_invalid_status(self):
        """Test rendering with an invalid zone status"""
        self.landing_zone.status = ZONE_STATUS_DELETED
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:delete',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 302)
