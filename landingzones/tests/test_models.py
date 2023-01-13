"""Tests for models in the landingzones app"""

from django.forms.models import model_to_dict

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.models import LandingZone, DEFAULT_STATUS_INFO


# Global constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20180503_1724_test_zone'
ZONE_DESC = 'description'
ZONE_MSG = 'user message'
ZONE_STATUS_INIT = 'CREATING'
ZONE_STATUS_INFO_INIT = DEFAULT_STATUS_INFO['CREATING']


class LandingZoneMixin:
    """
    Helper mixin for creation of LandingZone objects.
    NOTE: Only creates an object in the database, not actually in iRODS
    """

    @classmethod
    def make_landing_zone(
        cls,
        title,
        project,
        user,
        assay,
        description='',
        user_message='',
        status='CREATING',
        configuration=None,
        config_data={},
    ):
        values = {
            'title': title,
            'project': project,
            'user': user,
            'assay': assay,
            'description': description,
            'user_message': user_message,
            'status': status,
            'configuration': configuration,
            'config_data': config_data,
        }
        result = LandingZone(**values)
        result.save()
        return result


class TestLandingZoneBase(
    LandingZoneMixin,
    SampleSheetIOMixin,
    ProjectMixin,
    RoleAssignmentMixin,
    TestCase,
):
    """Base tests for LandingZone"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        self.assignment_owner = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )

        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Create LandingZone
        self.landing_zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            user_message=ZONE_MSG,
            configuration=None,
            config_data={},
        )


class TestLandingZone(TestLandingZoneBase):
    """Tests for LandingZone"""

    def setUp(self):
        super().setUp()

    def test_initialization(self):
        """Test LandingZone initialization"""
        expected = {
            'id': self.landing_zone.pk,
            'title': ZONE_TITLE,
            'project': self.project.pk,
            'user': self.user_owner.pk,
            'assay': self.assay.pk,
            'description': ZONE_DESC,
            'user_message': ZONE_MSG,
            'configuration': None,
            'config_data': {},
            'status': ZONE_STATUS_INIT,
            'status_info': ZONE_STATUS_INFO_INIT,
            'sodar_uuid': self.landing_zone.sodar_uuid,
        }

        self.assertEqual(model_to_dict(self.landing_zone), expected)

    def test__str__(self):
        """Test LandingZone __str__ rendering"""
        expected = '{}: {}/{}'.format(
            self.landing_zone.project.title,
            self.landing_zone.user.username,
            self.landing_zone.title,
        )
        self.assertEqual(str(self.landing_zone), expected)

    def test__repr__(self):
        expected = "LandingZone('{}', '{}', '{}')".format(
            self.landing_zone.project.title,
            self.landing_zone.user.username,
            self.landing_zone.title,
        )
        self.assertEqual(repr(self.landing_zone), expected)

    def test_set_status(self):
        """Test set_status() with status and status_info"""
        status = 'ACTIVE'
        status_info = 'ok'

        # Assert preconditions
        self.assertNotEqual(self.landing_zone.status, status)
        self.assertNotEqual(self.landing_zone.status_info, status_info)

        self.landing_zone.set_status(status, status_info)
        self.landing_zone.refresh_from_db()

        # Assert postconditions
        self.assertEqual(self.landing_zone.status, status)
        self.assertEqual(self.landing_zone.status_info, status_info)

    def test_set_status_no_info(self):
        """Test set_status() without status_info"""
        status = 'ACTIVE'
        status_info = DEFAULT_STATUS_INFO[status]

        # Assert preconditions
        self.assertNotEqual(self.landing_zone.status, status)
        self.assertNotEqual(self.landing_zone.status_info, status_info)

        self.landing_zone.set_status(status)
        self.landing_zone.refresh_from_db()

        # Assert postconditions
        self.assertEqual(self.landing_zone.status, status)
        self.assertEqual(self.landing_zone.status_info, status_info)

    def test_set_status_invalid(self):
        """Test set_status() with invalid status type"""
        status = 'Ib0ciemiahqu6Ooj'
        with self.assertRaises(TypeError):
            self.landing_zone.set_status(status)

    def test_is_locked_false(self):
        """Test is_locked() with ACTIVE status"""
        self.assertEqual(self.landing_zone.is_locked(), False)

    def test_is_locked_true(self):
        """Test is_locked() with MOVING status"""
        self.landing_zone.status = 'MOVING'
        self.assertEqual(self.landing_zone.is_locked(), True)

    def test_can_display_files_true(self):
        """Test can_display_files() with a valid zone status"""
        self.landing_zone.status = 'ACTIVE'
        self.assertEqual(self.landing_zone.can_display_files(), True)

    def test_can_display_files_false(self):
        """Test display_files() with an invalid zone status"""
        self.landing_zone.status = 'CREATING'
        self.assertEqual(self.landing_zone.can_display_files(), False)
