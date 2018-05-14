"""Tests for views in the landingzones app"""

from test_plus.test import TestCase

from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test import RequestFactory

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from .. import views
from ..models import LandingZone, DEFAULT_STATUS_INFO
from .test_models import LandingZoneMixin, ZONE_TITLE, ZONE_DESC


# Global constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_STATUS = 'VALIDATING'
ZONE_STATUS_INFO = 'Testing'


class TestViewsBase(
        TestCase, LandingZoneMixin,
        SampleSheetIOMixin, ProjectMixin, RoleAssignmentMixin):
    """Base class for view testing"""

    def setUp(self):
        self.req_factory = RequestFactory()

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init superuser
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Init project with owner
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.as_owner = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init contributor user and assignment
        self.user_contrib = self.make_user('user_contrib')
        self.as_contrib = self._make_assignment(
            self.project, self.user_contrib, self.role_contributor)

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create LandingZone
        self.landing_zone = self._make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.as_owner.user,
            assay=self.assay,
            description=ZONE_DESC)


class TestProjectZonesView(TestViewsBase):
    """Tests for the project zones list view"""

    def test_render_owner(self):
        """Test rendering of project zones view as project owner"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'landingzones:list',
                kwargs={'project': self.project.omics_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context['investigation'], self.investigation)
            self.assertEqual(response.context['zones_own'].count(), 1)
            self.assertEqual(response.context['zones_other'].count(), 0)
            self.assertEqual(
                response.context['zones_own'][0], self.landing_zone)

    def test_render_contrib(self):
        """Test rendering of project zones view as project contributor"""
        with self.login(self.user_contrib):
            response = self.client.get(reverse(
                'landingzones:list',
                kwargs={'project': self.project.omics_uuid}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context['investigation'], self.investigation)
            # This user should have no zones
            self.assertEqual(response.context['zones_own'].count(), 0)
            self.assertNotIn('zones_other', response.context)


class TestLandingZoneCreateView(TestViewsBase):
    """Tests for the landing zone creation view"""

    def test_render(self):
        """Test rendering of the landing zone creation view"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'landingzones:create',
                kwargs={'project': self.project.omics_uuid}))
            self.assertEqual(response.status_code, 200)

            # Assert form
            form = response.context['form']
            self.assertIsNotNone(form)
            self.assertIsNotNone(form.fields['title_suffix'])
            self.assertIsNotNone(form.fields['assay'])
            self.assertIsNotNone(form.fields['description'])


class TestLandingStoneSatusGetAPIView(TestViewsBase):
    """Tests for the landing zone status getting API view"""

    def test_get(self):
        """Test GET request for getting a landing zone status"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'landingzones:status',
                kwargs={'landingzone': self.landing_zone.omics_uuid}))

            self.assertEqual(response.status_code, 200)

            expected = {
                'status': self.landing_zone.status,
                'status_info': self.landing_zone.status_info}
            self.assertEquals(response.data, expected)
