"""Tests for the API in the irodsbackend app"""

from django.conf import settings
from django.test import override_settings

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

# Landingzones dependency
from landingzones.tests.test_models import LandingZoneMixin

from irodsbackend.api import (
    IrodsAPI,
    USER_GROUP_PREFIX,
    ERROR_PATH_PARENT,
    ERROR_PATH_UNSET,
)


# Global constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE_TITLE = '20180503_172456_test_zone'
ZONE_DESC = 'description'
IRODS_ZONE = settings.IRODS_ZONE
IRODS_ROOT_PATH = 'sodar/root'
SAMPLE_COLL = settings.IRODS_SAMPLE_COLL
LANDING_ZONE_COLL = settings.IRODS_LANDING_ZONE_COLL
IRODS_ENV = {
    "irods_encryption_key_size": 32,
    "irods_encryption_num_hash_rounds": 16,
    "irods_encryption_salt_size": 8,
}


class TestIrodsbackendAPI(
    SampleSheetIOMixin,
    LandingZoneMixin,
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    TestCase,
):
    """Tests for the API in the irodsbackend app"""

    def setUp(self):
        # Init user
        self.user = self.make_user('user')
        self.user.save()
        # Init roles
        self.init_roles()
        # Init project with owner
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user, self.role_owner
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
            configuration=None,
            config_data={},
        )
        self.irods_backend = IrodsAPI()

    def test_format_env(self):
        """Test format_env() to ensure correct formatting"""
        env = {
            'irods_client_server_negotiation': 'off',
            'irods_client_server_policy': 'CS_NEG_REFUSE',
            'irods_default_hash_scheme': 'MD5',
            'irods_encryption_algorithm': 'AES-256-CBC',
            'irods_encryption_key_size': '32',
            'irods_encryption_num_hash_rounds': '16',
            'irods_encryption_salt_size': '8',
            'irods_authentication_scheme': 'native',
            'irods_host': 'irods.example.com',
            'irods_port': '1247',
            'irods_user_name': 'user',
            'irods_zone_name': 'sodarZone',
        }
        env = self.irods_backend.format_env(env)
        self.assertEqual(env['irods_encryption_key_size'], 32)
        self.assertEqual(env['irods_encryption_num_hash_rounds'], 16)
        self.assertEqual(env['irods_encryption_salt_size'], 8)
        self.assertEqual(env['irods_port'], 1247)

    def test_sanitize_path(self):
        """Test sanitize_path()"""
        self.assertEqual(
            self.irods_backend.sanitize_path('/sodarZone/projects'),
            '/sodarZone/projects',
        )
        self.assertEqual(
            self.irods_backend.sanitize_path('sodarZone/projects/'),
            '/sodarZone/projects',
        )
        with self.assertRaises(ValueError) as ex:
            self.irods_backend.sanitize_path('')
            self.assertEqual(ex, ERROR_PATH_UNSET)
        with self.assertRaises(ValueError) as ex:
            self.irods_backend.sanitize_path('/sodarZone/projects/..')
            self.assertEqual(ex, ERROR_PATH_PARENT)
        with self.assertRaises(ValueError) as ex:
            self.irods_backend.sanitize_path('../home')
            self.assertEqual(ex, ERROR_PATH_PARENT)

    def test_get_path_project(self):
        """Test get_irods_path() with Project object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}'.format(
            zone=IRODS_ZONE,
            uuid_prefix=str(self.project.sodar_uuid)[:2],
            uuid=str(self.project.sodar_uuid),
        )
        path = self.irods_backend.get_path(self.project)
        self.assertEqual(expected, path)

    @override_settings(IRODS_ROOT_PATH=IRODS_ROOT_PATH)
    def test_get_path_project_root_path(self):
        """Test get_irods_path() with Project object and root path"""
        expected = '/{zone}/projects/{root_path}/{uuid_prefix}/{uuid}'.format(
            zone=IRODS_ZONE,
            root_path=IRODS_ROOT_PATH,
            uuid_prefix=str(self.project.sodar_uuid)[:2],
            uuid=str(self.project.sodar_uuid),
        )
        path = self.irods_backend.get_path(self.project)
        self.assertEqual(expected, path)

    def test_get_path_study(self):
        """Test get_irods_path() with Study object"""
        expected = (
            '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_coll}'
            '/{study}'.format(
                zone=IRODS_ZONE,
                uuid_prefix=str(self.project.sodar_uuid)[:2],
                uuid=str(self.project.sodar_uuid),
                sample_coll=SAMPLE_COLL,
                study='study_' + str(self.study.sodar_uuid),
            )
        )
        path = self.irods_backend.get_path(self.study)
        self.assertEqual(expected, path)

    def test_get_path_assay(self):
        """Test get_irods_path() with Assay object"""
        expected = (
            '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_coll}'
            '/{study}/{assay}'.format(
                zone=IRODS_ZONE,
                uuid_prefix=str(self.project.sodar_uuid)[:2],
                uuid=str(self.project.sodar_uuid),
                sample_coll=SAMPLE_COLL,
                study='study_' + str(self.study.sodar_uuid),
                assay='assay_' + str(self.assay.sodar_uuid),
            )
        )
        path = self.irods_backend.get_path(self.assay)
        self.assertEqual(expected, path)

    def test_get_path_zone(self):
        """Test get_irods_path() with LandingZone object"""
        expected = (
            '/{zone}/projects/{uuid_prefix}/{uuid}/{zone_dir}'
            '/{user}/{study_assay}/{zone_title}'.format(
                zone=IRODS_ZONE,
                uuid_prefix=str(self.project.sodar_uuid)[:2],
                uuid=str(self.project.sodar_uuid),
                zone_dir=LANDING_ZONE_COLL,
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
        """Test get_sample_path() with Project object"""
        expected = '/{zone}/projects/{uuid_prefix}/{uuid}/{sample_coll}'.format(
            zone=IRODS_ZONE,
            uuid_prefix=str(self.project.sodar_uuid)[:2],
            uuid=str(self.project.sodar_uuid),
            sample_coll=SAMPLE_COLL,
        )
        path = self.irods_backend.get_sample_path(self.project)
        self.assertEqual(expected, path)

    def test_get_sample_path_no_project(self):
        """Test get_sample_path() with wrong object type (should fail)"""
        with self.assertRaises(ValueError):
            self.irods_backend.get_sample_path(self.study)

    def test_get_root_path(self):
        """Test get_root_path() with default settings"""
        expected = '/' + IRODS_ZONE
        self.assertEqual(self.irods_backend.get_root_path(), expected)

    @override_settings(IRODS_ROOT_PATH=IRODS_ROOT_PATH)
    def test_get_root_path_with_path(self):
        """Test get_root_path() with root path setting"""
        expected = '/{}/{}'.format(IRODS_ZONE, IRODS_ROOT_PATH)
        self.assertEqual(self.irods_backend.get_root_path(), expected)

    def test_get_projects_path(self):
        """Test get_projects_path() with default settings"""
        expected = '/{}/projects'.format(IRODS_ZONE)
        self.assertEqual(self.irods_backend.get_projects_path(), expected)

    @override_settings(IRODS_ROOT_PATH=IRODS_ROOT_PATH)
    def test_get_projects_path_with_root_path(self):
        """Test get_projects_path() with root path setting"""
        expected = '/{}/{}/projects'.format(IRODS_ZONE, IRODS_ROOT_PATH)
        self.assertEqual(self.irods_backend.get_projects_path(), expected)

    def test_get_trash_pathg(self):
        """Test get_trash_path()"""
        self.assertEqual(
            self.irods_backend.get_trash_path(), '/{}/trash'.format(IRODS_ZONE)
        )

    def test_get_uuid_from_path_assay(self):
        """Test get_uuid_from_path() with assay path"""
        path = self.irods_backend.get_path(self.assay)
        uuid = self.irods_backend.get_uuid_from_path(path, 'assay')
        self.assertEqual(uuid, str(self.assay.sodar_uuid))

    def test_get_uuid_from_path_project(self):
        """Test get_uuid_from_path() for project UUID with assay path"""
        path = self.irods_backend.get_path(self.assay)
        uuid = self.irods_backend.get_uuid_from_path(path, 'project')
        self.assertEqual(uuid, str(self.project.sodar_uuid))

    def test_get_uuid_from_path_wrong_type(self):
        """Test get_uuid_from_path() with invalid type (should fail)"""
        path = self.irods_backend.get_path(self.study)

        with self.assertRaises(ValueError):
            self.irods_backend.get_uuid_from_path(path, 'investigation')

    def test_get_uuid_from_path_wrong_path(self):
        """Test get_uuid_from_path() on path without uuid (should fail)"""
        path = self.irods_backend.get_path(self.project)
        uuid = self.irods_backend.get_uuid_from_path(path, 'study')
        self.assertIsNone(uuid)

    @override_settings(IRODS_ROOT_PATH=IRODS_ROOT_PATH)
    def test_get_uuid_from_path_root_path(self):
        """Test get_uuid_from_path() including root path"""
        path = self.irods_backend.get_path(self.assay)
        uuid = self.irods_backend.get_uuid_from_path(path, 'assay')
        self.assertEqual(uuid, str(self.assay.sodar_uuid))

    def test_get_user_group_name(self):
        """Test get_user_group_name() with Project object"""
        self.assertEqual(
            self.irods_backend.get_user_group_name(self.project),
            '{}{}'.format(USER_GROUP_PREFIX, self.project.sodar_uuid),
        )

    def test_get_user_group_name_uuid(self):
        """Test get_user_group_name() with UUID object"""
        self.assertEqual(
            self.irods_backend.get_user_group_name(self.project.sodar_uuid),
            '{}{}'.format(USER_GROUP_PREFIX, self.project.sodar_uuid),
        )

    def test_get_user_group_name_uuid_str(self):
        """Test get_user_group_name() with UUID string"""
        self.assertEqual(
            self.irods_backend.get_user_group_name(
                str(self.project.sodar_uuid)
            ),
            '{}{}'.format(USER_GROUP_PREFIX, self.project.sodar_uuid),
        )
