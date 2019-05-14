"""Tests for the API in the irodsbackend app"""

from django.conf import settings

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

from ..api import IrodsAPI


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
IRODS_ZONE = settings.IRODS_ZONE
SAMPLE_DIR = settings.IRODS_SAMPLE_DIR
LANDING_ZONE_DIR = settings.IRODS_LANDING_ZONE_DIR


class TestIrodsBackendAPI(
    ProjectMixin,
    RoleAssignmentMixin,
    SampleSheetIOMixin,
    LandingZoneMixin,
    TestCase,
):
    """Tests for the API in the irodsbackend app"""

    def setUp(self):
        # Init user
        self.user = self.make_user('user')
        self.user.save()

        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE
        )[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR
        )[0]
        self.role_guest = Role.objects.get_or_create(name=PROJECT_ROLE_GUEST)[0]

        # Init project with owner
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.as_owner = self._make_assignment(
            self.project, self.user, self.role_owner
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
            configuration=None,
            config_data={},
        )

        self.irods_backend = IrodsAPI()

    def test_get_path_project(self):
        """Test get_irods_path() with a Project object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}'.format(
            zone=IRODS_ZONE,
            uuid_prefix=str(self.project.sodar_uuid)[:2],
            uuid=str(self.project.sodar_uuid),
        )
        path = self.irods_backend.get_path(self.project)
        self.assertEqual(expected, path)

    def test_get_path_study(self):
        """Test get_irods_path() with a Study object"""
        expected = (
            '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_dir}'
            '/{study}'.format(
                zone=IRODS_ZONE,
                uuid_prefix=str(self.project.sodar_uuid)[:2],
                uuid=str(self.project.sodar_uuid),
                sample_dir=SAMPLE_DIR,
                study='study_' + str(self.study.sodar_uuid),
            )
        )
        path = self.irods_backend.get_path(self.study)
        self.assertEqual(expected, path)

    def test_get_path_assay(self):
        """Test get_irods_path() with an Assay object"""
        expected = (
            '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_dir}'
            '/{study}/{assay}'.format(
                zone=IRODS_ZONE,
                uuid_prefix=str(self.project.sodar_uuid)[:2],
                uuid=str(self.project.sodar_uuid),
                sample_dir=SAMPLE_DIR,
                study='study_' + str(self.study.sodar_uuid),
                assay='assay_' + str(self.assay.sodar_uuid),
            )
        )
        path = self.irods_backend.get_path(self.assay)
        self.assertEqual(expected, path)

    def test_get_path_zone(self):
        """Test get_irods_path() with a LandingZone object"""
        expected = (
            '/{zone}/projects/{uuid_prefix}/{uuid}/{zone_dir}'
            '/{user}/{study_assay}/{zone_title}'.format(
                zone=IRODS_ZONE,
                uuid_prefix=str(self.project.sodar_uuid)[:2],
                uuid=str(self.project.sodar_uuid),
                zone_dir=LANDING_ZONE_DIR,
                user=self.user.username,
                study_assay=self.irods_backend.get_sub_path(
                    self.landing_zone.assay, landing_zone=True
                ),
                zone_title=ZONE_TITLE,
            )
        )
        path = self.irods_backend.get_path(self.landing_zone)
        self.assertEqual(expected, path)

    def test_get_sample_path(self):
        """Test get_sample_path() with a Project object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_dir}'.format(
            zone=IRODS_ZONE,
            uuid_prefix=str(self.project.sodar_uuid)[:2],
            uuid=str(self.project.sodar_uuid),
            sample_dir=SAMPLE_DIR,
        )
        path = self.irods_backend.get_sample_path(self.project)
        self.assertEqual(expected, path)

    def test_get_sample_path_no_project(self):
        """Test get_sample_path() with a wrong type of object (should fail)"""
        with self.assertRaises(ValueError):
            self.irods_backend.get_sample_path(self.study)

    def test_get_uuid_from_path_assay(self):
        """Test get_uuid_from_path() with an assay path"""
        path = self.irods_backend.get_path(self.assay)
        uuid = self.irods_backend.get_uuid_from_path(path, 'assay')
        self.assertEqual(uuid, str(self.assay.sodar_uuid))

    def test_get_uuid_from_path_project(self):
        """Test get_uuid_from_path() for project UUID with an assay path"""
        path = self.irods_backend.get_path(self.assay)
        uuid = self.irods_backend.get_uuid_from_path(path, 'project')
        self.assertEqual(uuid, str(self.project.sodar_uuid))

    def test_get_uuid_from_path_wrong_type(self):
        """Test get_uuid_from_path() with an invalid type (should fail)"""
        path = self.irods_backend.get_path(self.study)

        with self.assertRaises(ValueError):
            self.irods_backend.get_uuid_from_path(path, 'investigation')

    def test_get_uuid_from_path_wrong_path(self):
        """Test get_uuid_from_path() with a path not containing the uuid (should fail)"""
        path = self.irods_backend.get_path(self.project)
        uuid = self.irods_backend.get_uuid_from_path(path, 'study')
        self.assertIsNone(uuid)
