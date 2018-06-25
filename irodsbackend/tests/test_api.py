"""Tests for the API in the irodsbackend app"""

from django.conf import settings

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

from ..api import IrodsAPI


# Global constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20180503_1724_test_zone'
ZONE_DESC = 'description'
IRODS_ZONE = settings.IRODS_ZONE
SAMPLE_DIR = settings.IRODS_SAMPLE_DIR
LANDING_ZONE_DIR = settings.IRODS_LANDING_ZONE_DIR


class TestIrodsBackendAPI(
        TestCase, ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin,
        LandingZoneMixin):
    """Tests for the API in the irodsbackend app"""

    def setUp(self):
        # Init user
        self.user = self.make_user('user')
        self.user.save()

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init project with owner
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.as_owner = self._make_assignment(
            self.project, self.user, self.role_owner)

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

        self.irods_backend = IrodsAPI()

    def test_get_path_project(self):
        """Test get_irods_path() with a Project object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}'.format(
            zone=IRODS_ZONE,
            uuid_prefix=str(self.project.omics_uuid)[:2],
            uuid=str(self.project.omics_uuid))
        path = self.irods_backend.get_path(self.project)
        self.assertEqual(expected, path)

    def test_get_path_study(self):
        """Test get_irods_path() with a Study object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_dir}' \
                   '/{study}'.format(
                    zone=IRODS_ZONE,
                    uuid_prefix=str(self.project.omics_uuid)[:2],
                    uuid=str(self.project.omics_uuid),
                    sample_dir=SAMPLE_DIR,
                    study='study_' + str(self.study.omics_uuid))
        path = self.irods_backend.get_path(self.study)
        self.assertEqual(expected, path)

    def test_get_path_assay(self):
        """Test get_irods_path() with an Assay object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_dir}' \
                   '/{study}/{assay}'.format(
                    zone=IRODS_ZONE,
                    uuid_prefix=str(self.project.omics_uuid)[:2],
                    uuid=str(self.project.omics_uuid),
                    sample_dir=SAMPLE_DIR,
                    study='study_' + str(self.study.omics_uuid),
                    assay='assay_' + str(self.assay.omics_uuid))
        path = self.irods_backend.get_path(self.assay)
        self.assertEqual(expected, path)

    def test_get_path_zone(self):
        """Test get_irods_path() with a LandingZone object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}/{zone_dir}' \
                   '/{user}/{study_assay}/{zone_title}'.format(
                    zone=IRODS_ZONE,
                    uuid_prefix=str(self.project.omics_uuid)[:2],
                    uuid=str(self.project.omics_uuid),
                    zone_dir=LANDING_ZONE_DIR,
                    user=self.user.username,
                    study_assay=self.irods_backend.get_subdir(
                        self.landing_zone.assay, landing_zone=True),
                    zone_title=ZONE_TITLE)
        path = self.irods_backend.get_path(self.landing_zone)
        self.assertEqual(expected, path)
