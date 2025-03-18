"""Tests for UI views in the landingzones app"""

from django.forms import HiddenInput
from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
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


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'landingzones'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_STATUS_INFO = 'Testing'
PROHIBIT_NAME = 'file_name_prohibit'
PROHIBIT_VAL = 'bam,vcf.gz'


class ViewTestBase(
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    SampleSheetIOMixin,
    LandingZoneMixin,
    TestCase,
):
    """Base class for landingzones view testing"""

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
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )


class TestProjectZonesView(ViewTestBase):
    """Tests for ProjectZonesView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:list',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get_owner(self):
        """Test ProjectZonesView GET as owner"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['investigation'], self.investigation)
        self.assertEqual(response.context['zones_own'].count(), 1)
        self.assertEqual(response.context['zones_other'].count(), 0)
        self.assertEqual(response.context['zones_own'][0], self.zone)
        self.assertEqual(response.context['zone_access_disabled'], False)
        self.assertEqual(response.context['prohibit_files'], None)

    def test_get_contrib(self):
        """Test GET as contributor"""
        with self.login(self.user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['investigation'], self.investigation)
        # This user should have no zones
        self.assertEqual(response.context['zones_own'].count(), 0)
        self.assertNotIn('zones_other', response.context)
        self.assertEqual(response.context['zone_access_disabled'], False)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_disable(self):
        """Test GET with user access disabled"""
        with self.login(self.user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.context['zone_access_disabled'], True)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_disable_superuser(self):
        """Test GET with user access disabled as superuser"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.context['zone_access_disabled'], False)

    def test_get_prohibit(self):
        """Test GET with file_name_prohibit enabled"""
        app_settings.set(
            APP_NAME, PROHIBIT_NAME, PROHIBIT_VAL, project=self.project
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['prohibit_files'],
            ', '.join(PROHIBIT_VAL.split(',')),
        )


class TestZoneCreateView(ViewTestBase):
    """Tests for ZoneCreateView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:create',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneCreateView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertIsNotNone(form.fields['title_suffix'])
        self.assertIsNotNone(form.fields['assay'])
        self.assertIsNotNone(form.fields['description'])
        self.assertIsNotNone(form.fields['configuration'])
        self.assertEqual(response.context['prohibit_files'], None)

    def test_get_prohibit(self):
        """Test GET with file_name_prohibit enabled"""
        app_settings.set(
            APP_NAME, PROHIBIT_NAME, PROHIBIT_VAL, project=self.project
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['prohibit_files'],
            ', '.join(PROHIBIT_VAL.split(',')),
        )


class TestZoneUpdateView(ViewTestBase):
    """Tests for ZoneUpdateView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:update',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneUpdateView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertIsNotNone(form.fields['assay'])
        self.assertIsNotNone(form.fields['description'])
        # Make sure to also assert the expected fields are hidden with the
        # HiddenInput widget
        self.assertIsInstance(form.fields['title_suffix'].widget, HiddenInput)
        self.assertIsInstance(form.fields['configuration'].widget, HiddenInput)
        self.assertIsInstance(form.fields['create_colls'].widget, HiddenInput)
        self.assertIsInstance(form.fields['restrict_colls'].widget, HiddenInput)
        self.assertIsInstance(form.fields['assay'].widget, HiddenInput)
        self.assertNotIn('prohibit_files', response.context)

    def test_get_prohibit(self):
        """Test GET with file_name_prohibit enabled"""
        app_settings.set(
            APP_NAME, PROHIBIT_NAME, PROHIBIT_VAL, project=self.project
        )
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Should not be included for update
        self.assertNotIn('prohibit_files', response.context)

    def test_get_invalid_status(self):
        """Test GET with invalid zone status"""
        self.zone.status = ZONE_STATUS_DELETED
        self.zone.save()
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post(self):
        """Test POST"""
        with self.login(self.user):
            response = self.client.post(
                self.url,
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
        zone = LandingZone.objects.get(sodar_uuid=self.zone.sodar_uuid)
        self.assertEqual(zone.assay, self.assay)
        self.assertEqual(zone.description, 'test description updated')
        self.assertEqual(zone.user_message, 'test user message')

    def test_post_invalid_data(self):
        """Test POST with invalid data"""
        with self.login(self.user):
            response = self.client.post(
                self.url,
                data={
                    'assay': self.assay.sodar_uuid,
                    'description': 'test description updated',
                    'title_suffix': 'test suffix',
                },
            )
        self.assertEqual(response.status_code, 302)
        zone = LandingZone.objects.get(sodar_uuid=self.zone.sodar_uuid)
        self.assertEqual(zone.assay, self.assay)
        self.assertEqual(zone.description, 'description')


class TestZoneMoveView(ViewTestBase):
    """Tests for ZoneMoveView"""

    def test_get_invalid_status(self):
        """Test ZoneMoveView GET with invalid zone status"""
        self.zone.status = ZONE_STATUS_DELETED
        self.zone.save()
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:move',
                    kwargs={'landingzone': self.zone.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 302)


class TestZoneDeleteView(ViewTestBase):
    """Tests for ZoneDeleteView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:delete',
            kwargs={'landingzone': self.zone.sodar_uuid},
        )

    def test_get(self):
        """Test ZoneDeleteView GET"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_invalid_status(self):
        """Test GET with invalid zone status"""
        self.zone.status = ZONE_STATUS_DELETED
        self.zone.save()
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
