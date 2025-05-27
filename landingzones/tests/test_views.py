"""Tests for UI views in the landingzones app"""

from django.contrib.messages import get_messages
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

# Taskflowbackend dependency
from taskflowbackend.tests.base import ProjectLockMixin

from landingzones.constants import (
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_VALIDATING,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_DELETED,
)
from landingzones.models import LandingZone
from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)
from landingzones.views import ZONE_CREATE_LIMIT_MSG


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
        self.user_owner = self.make_user('user_owner')
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )

        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create landing zone
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )


class TestProjectZoneView(ProjectLockMixin, ViewTestBase):
    """Tests for ProjectZoneView"""

    def setUp(self):
        super().setUp()
        # Init additional users and assignments
        self.user_contributor = self.make_user('user_contributor')
        self.contributor_as = self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
        )
        self.user_no_zones = self.make_user('user_no_zones')
        self.no_zones_as = self.make_assignment(
            self.project, self.user_no_zones, self.role_contributor
        )
        # Create additional landing zone
        self.zone_contrib = self.make_landing_zone(
            title=ZONE_TITLE + '2',
            project=self.project,
            user=self.user_contributor,
            assay=self.assay,
            description=ZONE_DESC,
            status=ZONE_STATUS_ACTIVE,
        )
        self.url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get_owner(self):
        """Test ProjectZoneView GET as owner"""
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['investigation'], self.investigation)
        self.assertEqual(rc['zones'].count(), 2)
        self.assertEqual(rc['zones'][0], self.zone)
        self.assertEqual(rc['zones'][1], self.zone_contrib)
        self.assertEqual(rc['zone_access_disabled'], False)
        self.assertEqual(rc['prohibit_files'], None)
        self.assertEqual(rc['project_lock'], False)
        self.assertEqual(rc['zone_active_count'], 2)
        self.assertEqual(rc['zone_create_limit'], None)
        self.assertEqual(rc['zone_create_limit_reached'], False)
        self.assertEqual(rc['zone_validate_count'], 0)
        self.assertEqual(rc['zone_validate_limit'], 4)
        self.assertEqual(rc['zone_validate_limit_reached'], False)

    def test_get_contrib(self):
        """Test GET as contributor"""
        with self.login(self.user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['zones'].count(), 1)
        self.assertEqual(rc['zones'][0], self.zone_contrib)
        self.assertEqual(rc['zone_active_count'], 2)
        self.assertEqual(rc['zone_create_limit'], None)
        self.assertEqual(rc['zone_create_limit_reached'], False)
        self.assertEqual(rc['zone_validate_count'], 0)
        self.assertEqual(rc['zone_validate_limit'], 4)
        self.assertEqual(rc['zone_validate_limit_reached'], False)

    def test_get_user_no_zones(self):
        """Test GET as contributor user with no zones"""
        with self.login(self.user_no_zones):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['zones'].count(), 0)
        self.assertEqual(rc['zone_active_count'], 2)
        self.assertEqual(rc['zone_create_limit'], None)
        self.assertEqual(rc['zone_create_limit_reached'], False)
        self.assertEqual(rc['zone_validate_count'], 0)
        self.assertEqual(rc['zone_validate_limit'], 4)
        self.assertEqual(rc['zone_validate_limit_reached'], False)

    def test_get_superuser(self):
        """Test GET as superuser"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['zones'].count(), 2)
        self.assertEqual(response.context['zones'][0], self.zone)
        self.assertEqual(response.context['zones'][1], self.zone_contrib)

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

    def test_get_locked(self):
        """Test GET with locked project"""
        self.lock_project(self.project)
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project_lock'], True)

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=2)
    def test_get_create_limit(self):
        """Test GET with zone creation limit reached"""
        self.assertEqual(
            LandingZone.objects.filter(project=self.project).count(), 2
        )
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['zone_active_count'], 2)
        self.assertEqual(rc['zone_create_limit'], 2)
        self.assertEqual(rc['zone_create_limit_reached'], True)
        self.assertEqual(rc['zone_validate_limit_reached'], False)

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=2)
    def test_get_create_limit_existing_finished(self):
        """Test GET with zone creation limit and finished zone"""
        self.zone.set_status(ZONE_STATUS_MOVED)
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['zone_active_count'], 1)
        self.assertEqual(rc['zone_create_limit'], 2)
        self.assertEqual(rc['zone_create_limit_reached'], False)
        self.assertEqual(rc['zone_validate_limit_reached'], False)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_get_validate_limit(self):
        """Test GET with zone validation limit reached"""
        self.zone.set_status(ZONE_STATUS_VALIDATING)
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['zone_validate_count'], 1)
        self.assertEqual(rc['zone_validate_limit'], 1)
        self.assertEqual(rc['zone_validate_limit_reached'], True)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=None)
    def test_get_validate_limit_none(self):
        """Test GET with zone validation limit set to None (counts as 1)"""
        self.zone.set_status(ZONE_STATUS_VALIDATING)
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['zone_validate_count'], 1)
        self.assertEqual(rc['zone_validate_limit'], 1)
        self.assertEqual(rc['zone_validate_limit'], True)

    @override_settings(LANDINGZONES_ZONE_VALIDATE_LIMIT=1)
    def test_get_validate_limit_other_zone_moved(self):
        """Test GET with zone validation limit reached and other zone moved"""
        self.zone.set_status(ZONE_STATUS_MOVED)
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rc = response.context
        self.assertEqual(rc['zone_validate_count'], 0)
        self.assertEqual(rc['zone_validate_limit'], 1)
        self.assertEqual(rc['zone_validate_limit_reached'], False)


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

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_get_limit(self):
        """Test GET with zone creation limit reached (should fail)"""
        with self.login(self.user):
            response = self.client.get(self.url)
            self.assertRedirects(
                response,
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )
        self.assertEqual(
            list(get_messages(response.wsgi_request))[0].message,
            ZONE_CREATE_LIMIT_MSG.format(limit=1) + '.',
        )

    @override_settings(LANDINGZONES_ZONE_CREATE_LIMIT=1)
    def test_get_limit_existing_finished(self):
        """Test GET with zone creation limit and finished zone"""
        self.zone.set_status(ZONE_STATUS_MOVED)
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


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
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Should not be included for update
        self.assertNotIn('prohibit_files', response.context)

    def test_get_invalid_status(self):
        """Test GET with invalid zone status"""
        self.zone.status = ZONE_STATUS_DELETED
        self.zone.save()
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post(self):
        """Test POST"""
        with self.login(self.user_owner):
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
        with self.login(self.user_owner):
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
        with self.login(self.user_owner):
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
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_invalid_status(self):
        """Test GET with invalid zone status"""
        self.zone.status = ZONE_STATUS_DELETED
        self.zone.save()
        with self.login(self.user_owner):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
