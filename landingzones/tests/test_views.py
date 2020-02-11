"""Tests for UI views in the landingzones app"""

from test_plus.test import TestCase

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import RequestFactory

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from ..models import LandingZone
from .test_models import LandingZoneMixin, ZONE_TITLE, ZONE_DESC

# Global constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_STATUS = 'VALIDATING'
ZONE_STATUS_INFO = 'Testing'


IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


class TestViewsBase(
    LandingZoneMixin,
    SampleSheetIOMixin,
    ProjectMixin,
    RoleAssignmentMixin,
    TestCase,
):
    """Base class for view testing"""

    def setUp(self):
        self.req_factory = RequestFactory()

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

        # Init contributor user and assignment
        self.user_contrib = self.make_user('user_contrib')
        self.as_contrib = self._make_assignment(
            self.project, self.user_contrib, self.role_contributor
        )

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create LandingZone
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC,
            status='ACTIVE',
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

    def test_render_contrib(self):
        """Test rendering of project zones view as project contributor"""
        with self.login(self.user_contrib):
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


class TestLandingZoneMoveView(TestViewsBase):
    """Tests for the landing zone validation and moving view"""

    def test_render(self):
        """Test rendering of the landing zone validation and moving view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:move',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

    def test_render_invalid_status(self):
        """Test rendering with an invalid zone status"""
        self.landing_zone.status = 'DELETED'
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
        self.landing_zone.status = 'DELETED'
        self.landing_zone.save()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:delete',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 302)


class TestLandingZoneClearView(TestViewsBase):
    """Tests for the landing zone clearing view"""

    def setUp(self):
        super().setUp()
        self.landing_zone.status = 'DELETED'
        self.landing_zone.save()

    def test_render(self):
        """Test rendering of the landing zone clearing view"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:clear',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

    def test_post(self):
        """Test POST on the landing zone clearing view"""

        # Assert precondition
        self.assertEqual(LandingZone.objects.count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'landingzones:clear',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

            # Assert redirect
            self.assertRedirects(
                response,
                reverse(
                    'landingzones:list',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        # Assert postcondition
        self.assertEqual(LandingZone.objects.count(), 0)


class TestLandingZoneStatusGetAPIView(TestViewsBase):
    """Tests for the landing zone status getting API view"""

    def test_get(self):
        """Test GET request for getting a landing zone status"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'landingzones:ajax_status',
                    kwargs={'landingzone': self.landing_zone.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        expected = {
            'status': self.landing_zone.status,
            'status_info': self.landing_zone.status_info,
        }
        self.assertEquals(response.data, expected)
