"""Management command tests for the irodsadmin app"""

import os
import sys
import uuid

from io import StringIO

from irods.access import iRODSAccess
from irods.path import iRODSPath

from django.conf import settings
from django.core.management import call_command

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI

# Landingzones dependency
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin
from samplesheets.views import MISC_FILES_COLL

# Taskflowbackend dependency
from taskflowbackend.constants import (
    IRODS_ACCESS_OWN,
    IRODS_ACCESS_MODIFY_OBJ,
    IRODS_ACCESS_READ_OBJ,
)
from taskflowbackend.tests.base import (
    TaskflowViewTestBase,
    IRODS_RODS_USER_TYPE,
)

from irodsadmin.management.commands.checksampleaccess import (
    CHECK_ACCESS_DONE_MSG,
    CHECK_ACCESS_GROUP_MSG,
    CHECK_ACCESS_START_MSG,
    CHECK_ACCESS_USER_MSG,
)
from irodsadmin.management.commands.irodsorphans import Command, DELETED


plugin_api = PluginAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
SHEET_PATH_GERMLINE = os.path.join(SHEET_DIR, 'bih_germline.zip')
ZONE_TITLE = '20180503_172456_test_zone'
ZONE_DESC = 'description'
DUMMY_UUID = '11111111-1111-1111-1111-111111111111'
USER_ADMIN = settings.IRODS_USER
USER_NEW = 'user_new'
LOGGER_PREFIX = 'irodsadmin.management.commands.'
TEST_OBJ = 'test1.txt'
OUT_SUFFIX = '0;0 bytes\n'


class TestCheckSampleAccess(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowViewTestBase
):
    def setUp(self):
        super().setUp()
        # Init project with owner
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Set up investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Set up iRODS data
        self.make_irods_colls(self.investigation)
        self.sample_path = self.irods_backend.get_sample_path(self.project)
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.misc_path = iRODSPath(self.assay_path, MISC_FILES_COLL)
        self.misc_coll = self.irods.collections.create(self.misc_path)
        self.project_group = self.irods_backend.get_group_name(self.project)
        # User with no project roles
        self.irods_user_new = self.irods.users.create(
            USER_NEW, IRODS_RODS_USER_TYPE
        )
        # Set up test vars
        self.cmd_name = 'checksampleaccess'
        self.logger_name = LOGGER_PREFIX + self.cmd_name

    def test_command(self):
        """Test command with default access"""
        # Assert inherited access
        paths = [self.sample_path, self.assay_path, self.misc_path]
        for p in paths:
            self.assert_irods_access(USER_ADMIN, p, IRODS_ACCESS_OWN)
            self.assert_irods_access(
                self.project_group, p, IRODS_ACCESS_READ_OBJ
            )
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
        self.assertEqual(len(cm.output), 2)  # Only startup and end log messages
        self.assertIn(CHECK_ACCESS_START_MSG, cm.output[0])
        self.assertIn(
            CHECK_ACCESS_DONE_MSG.format(count=0, plural='s'), cm.output[1]
        )

    def test_command_extra_user_coll(self):
        """Test command with extra user collection access"""
        acl = iRODSAccess(
            access_name=IRODS_ACCESS_OWN,
            path=self.misc_path,
            user_name=USER_NEW,
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=True)
        self.assert_irods_access(USER_NEW, self.misc_path, IRODS_ACCESS_OWN)
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
        self.assertEqual(len(cm.output), 3)
        self.assertIn(
            f'{CHECK_ACCESS_USER_MSG}: '
            f'{USER_NEW};{IRODS_ACCESS_OWN};{self.misc_path}',
            cm.output[1],
        )
        self.assertIn(
            CHECK_ACCESS_DONE_MSG.format(count=1, plural=''), cm.output[2]
        )

    def test_command_extra_user_obj(self):
        """Test command with extra user data object access"""
        obj = self.make_irods_object(self.misc_coll, TEST_OBJ)
        acl = iRODSAccess(
            access_name=IRODS_ACCESS_OWN,
            path=obj.path,
            user_name=USER_NEW,
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=False)
        self.assert_irods_access(USER_NEW, obj.path, IRODS_ACCESS_OWN)
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
        self.assertEqual(len(cm.output), 3)
        self.assertIn(
            f'{CHECK_ACCESS_USER_MSG}: '
            f'{USER_NEW};{IRODS_ACCESS_OWN};{obj.path}',
            cm.output[1],
        )
        self.assertIn(
            CHECK_ACCESS_DONE_MSG.format(count=1, plural=''), cm.output[2]
        )

    def test_command_invalid_group_coll_access(self):
        """Test command with invalid project group collection access"""
        acl = iRODSAccess(
            access_name=IRODS_ACCESS_MODIFY_OBJ,
            path=self.misc_path,
            user_name=self.project_group,
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=True)
        self.assert_irods_access(
            self.project_group, self.misc_path, IRODS_ACCESS_MODIFY_OBJ
        )
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
        self.assertEqual(len(cm.output), 3)
        self.assertIn(
            f'{CHECK_ACCESS_GROUP_MSG}: '
            f'{IRODS_ACCESS_MODIFY_OBJ};{self.misc_path}',
            cm.output[1],
        )
        self.assertIn(
            CHECK_ACCESS_DONE_MSG.format(count=1, plural=''), cm.output[2]
        )

    def test_command_invalid_group_obj_access(self):
        """Test command with invalid project group data object access"""
        obj = self.make_irods_object(self.misc_coll, TEST_OBJ)
        acl = iRODSAccess(
            access_name=IRODS_ACCESS_MODIFY_OBJ,
            path=obj.path,
            user_name=self.project_group,
            user_zone=self.irods.zone,
        )
        self.irods.acls.set(acl, recursive=False)
        self.assert_irods_access(
            self.project_group, obj.path, IRODS_ACCESS_MODIFY_OBJ
        )
        with self.assertLogs(self.logger_name) as cm:
            call_command(self.cmd_name)
        self.assertEqual(len(cm.output), 3)
        self.assertIn(
            f'{CHECK_ACCESS_GROUP_MSG}: '
            f'{IRODS_ACCESS_MODIFY_OBJ};{obj.path}',
            cm.output[1],
        )
        self.assertIn(
            CHECK_ACCESS_DONE_MSG.format(count=1, plural=''), cm.output[2]
        )


class TestIrodsOrphans(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    LandingZoneMixin,
    LandingZoneTaskflowMixin,
    TaskflowViewTestBase,
):
    """Tests for the irodsorphans management command"""

    def _setup_investigation(self, path: str = SHEET_PATH_GERMLINE):
        """
        Set up investigation with taskflow.

        NOTE: This assumes a single study and a single assay
        """
        self.investigation = self.import_isa_from_file(path, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)

    def _get_zone(self) -> LandingZone:
        """Create and return landing zone for project with taskflow"""
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
        )
        self.make_zone_taskflow(zone)
        return zone

    def _get_expected_colls(self) -> list:
        """Return expected collections"""
        return [
            *self.command._get_assay_colls([self.assay]),
            *self.command._get_study_colls([self.study]),
            *self.command._get_zone_colls(),
            *self.command._get_project_colls(),
            *self.command._get_assay_subcolls([self.study]),
        ]

    @staticmethod
    def _call_output() -> str:
        """Call irodsorphans management command and return output"""
        sys.stdout = StringIO()
        call_command('irodsorphans', stdout=sys.stdout)
        return sys.stdout.getvalue()

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        self.command = Command()

    def test_get_assay_colls(self):
        """Test _get_assay_colls()"""
        self._setup_investigation()
        self.assertListEqual(
            self.command._get_assay_colls([self.assay]),
            [self.irods_backend.get_path(self.assay)],
        )

    def test_get_study_colls(self):
        """Test _get_study_colls()"""
        self._setup_investigation()
        self.assertListEqual(
            self.command._get_study_colls([self.study]),
            [self.irods_backend.get_path(self.study)],
        )

    def test_get_zone_colls(self):
        """Test _get_zone_colls()"""
        self._setup_investigation()
        zone = self._get_zone()
        self.assertListEqual(
            self.command._get_zone_colls(),
            [self.irods_backend.get_path(zone)],
        )

    def test_get_project_colls(self):
        """Test _get_project_colls()"""
        self._setup_investigation()
        self.assertListEqual(
            self.command._get_project_colls(),
            [self.irods_backend.get_path(self.project)],
        )

    def test_get_assay_subcolls(self):
        """Test _get_assay_subcolls()"""
        self._setup_investigation()
        assay_path = self.irods_backend.get_path(self.assay)
        expected = []
        for prefix in ['p1', 'p2']:
            for suffix in ['', '_mother', '_father']:
                expected.append(
                    iRODSPath(assay_path, f'{prefix}{suffix}-N1-DNA1-WES1')
                )
        expected.append(iRODSPath(assay_path, 'TrackHubs'))
        expected.append(iRODSPath(assay_path, 'ResultsReports'))
        expected.append(iRODSPath(assay_path, 'MiscFiles'))
        self.assertListEqual(
            self.command._get_assay_subcolls([self.study]),
            expected,
        )

    def test_is_zone(self):
        """Test _is_zone()"""
        self._setup_investigation()
        zone = self._get_zone()
        coll = self.irods.collections.get(self.irods_backend.get_path(zone))
        self.assertTrue(self.command._is_zone(coll))

    def test_is_assay_or_study_with_assay(self):
        """Test _is_assay_or_study() with assay"""
        self._setup_investigation()
        coll = self.irods.collections.get(
            self.irods_backend.get_path(self.assay)
        )
        self.assertTrue(self.command._is_assay_or_study(coll))

    def test_is_assay_or_study_with_study(self):
        """Test _is_assay_or_study() with study"""
        self._setup_investigation()
        coll = self.irods.collections.get(
            self.irods_backend.get_path(self.study)
        )
        self.assertTrue(self.command._is_assay_or_study(coll))

    def test_is_project(self):
        """Test _is_project()"""
        coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        projects_path = self.irods_backend.get_projects_path()
        self.assertTrue(self.command._is_project(projects_path, coll))

    def test_is_zone_invalid(self):
        """Test _is_zone() with a non-landingzone collection"""
        coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertFalse(self.command._is_zone(coll))

    def test_is_assay_or_study_invalid(self):
        """Test _is_assay_or_study() with non-assay/study collection"""
        coll = self.irods.collections.get(
            self.irods_backend.get_path(self.project)
        )
        self.assertFalse(self.command._is_assay_or_study(coll))

    def test_get_orphans_none(self):
        """Test _get_orphans() with no orphans available"""
        self._setup_investigation()
        expected_colls = self._get_expected_colls()
        # Capture stdout
        sys.stdout = StringIO()
        self.command._get_orphans(self.irods, expected_colls, [self.assay])
        self.assertEqual(sys.stdout.getvalue(), '')

    def test_get_orphans_assay(self):
        """Test _get_orphans() with orphan assay"""
        self._setup_investigation()
        expected_colls = self._get_expected_colls()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.study), f'assay_{uuid.uuid4()}'
        )
        self.irods.collections.create(orphan_path)
        sys.stdout = StringIO()
        self.command._get_orphans(self.irods, expected_colls, [self.assay])
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(sys.stdout.getvalue(), expected)

    def test_get_orphans_study(self):
        """Test _get_orphans() with orphan study"""
        self._setup_investigation()
        expected_colls = self._get_expected_colls()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.project),
            settings.IRODS_SAMPLE_COLL,
            f'study_{uuid.uuid4()}',
        )
        self.irods.collections.create(orphan_path)
        sys.stdout = StringIO()
        self.command._get_orphans(self.irods, expected_colls, [self.assay])
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(sys.stdout.getvalue(), expected)

    def test_get_orphans_zone(self):
        """Test _get_orphans() with orphan landing zone collection"""
        self._setup_investigation()
        # Set up real zone to ensure only orphan is returned
        self._get_zone()
        expected_colls = self._get_expected_colls()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.project),
            settings.IRODS_LANDING_ZONE_COLL,
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            '20201031_123456',
        )
        self.irods.collections.create(orphan_path)
        sys.stdout = StringIO()
        self.command._get_orphans(self.irods, expected_colls, [self.assay])
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(sys.stdout.getvalue(), expected)

    def test_get_output_project(self):
        """Test _get_orphans() with orphan project"""
        self._setup_investigation()
        expected_colls = self._get_expected_colls()
        orphan_path = iRODSPath(
            self.irods_backend.get_projects_path(), '11', DUMMY_UUID
        )
        self.irods.collections.create(orphan_path)
        sys.stdout = StringIO()
        self.command._get_orphans(self.irods, expected_colls, [self.assay])
        expected = f'{DUMMY_UUID};{DELETED};{orphan_path};{OUT_SUFFIX}'
        self.assertEqual(sys.stdout.getvalue(), expected)

    def test_get_output_assay_subs(self):
        """Test _get_orphans() with orphan assay subcollections"""
        self._setup_investigation()
        expected_colls = self._get_expected_colls()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.assay), 'UnexpectedCollection'
        )
        self.irods.collections.create(orphan_path)
        sys.stdout = StringIO()
        self.command._get_orphans(self.irods, expected_colls, [self.assay])
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};0;0 bytes\n'
        )
        self.assertEqual(sys.stdout.getvalue(), expected)

    def test_get_orphans_deleted_project(self):
        """Test _get_orphans() with a deleted project"""
        self._setup_investigation()
        expected_colls = self._get_expected_colls()
        orphan_path = iRODSPath(
            self.irods_backend.get_projects_path(), '11', DUMMY_UUID
        )
        self.irods.collections.create(orphan_path)
        sys.stdout = StringIO()
        self.command._get_orphans(self.irods, expected_colls, [self.assay])
        expected = f'{DUMMY_UUID};{DELETED};{orphan_path};{OUT_SUFFIX}'
        self.assertEqual(sys.stdout.getvalue(), expected)

    def test_command_no_orphans(self):
        """Test command with no orphans"""
        self.assertEqual(self._call_output(), '')

    def test_command_orphan_assay(self):
        """Test command with orphan assay"""
        self._setup_investigation()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.study), f'assay_{uuid.uuid4()}'
        )
        self.irods.collections.create(orphan_path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_orphan_study(self):
        """Test command with orphan study"""
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.project),
            settings.IRODS_SAMPLE_COLL,
            f'study_{uuid.uuid4()}',
        )
        self.irods.collections.create(orphan_path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_orphan_zone(self):
        """Test command with orphan landing zone collection"""
        self._setup_investigation()
        self._get_zone()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.project),
            settings.IRODS_LANDING_ZONE_COLL,
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            '20201031_123456',
        )
        self.irods.collections.create(orphan_path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_orphan_project(self):
        """Test command with orphan project"""
        orphan_path = iRODSPath(
            self.irods_backend.get_projects_path(), '11', DUMMY_UUID
        )
        self.irods.collections.create(orphan_path)
        output = self._call_output()
        expected = f'{DUMMY_UUID};{DELETED};{orphan_path};{OUT_SUFFIX}'
        self.assertEqual(output, expected)

    def test_command_orphan_assay_sub(self):
        """Test command with orphan assay subcollection"""
        self._setup_investigation()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.assay), 'UnexpectedCollection'
        )
        self.irods.collections.create(orphan_path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_multiple(self):
        """Test command with multiple orphans"""
        self._setup_investigation()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.project),
            settings.IRODS_SAMPLE_COLL,
            f'study_{uuid.uuid4()}',
        )
        self.irods.collections.create(orphan_path)
        orphan_path2 = iRODSPath(
            self.irods_backend.get_path(self.project),
            settings.IRODS_LANDING_ZONE_COLL,
            self.user.username,
            self.study.get_display_name().replace(' ', '_').lower(),
            '20201031_123456',
        )
        self.irods.collections.create(orphan_path2)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path2};{OUT_SUFFIX}'
        )
        expected += (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_output_order(self):
        """Test command output order"""
        self.maxDiff = None
        self._setup_investigation()
        orphan_path = iRODSPath(
            self.irods_backend.get_path(self.project),
            settings.IRODS_SAMPLE_COLL,
            f'study_{uuid.uuid4()}',
        )
        self.irods.collections.create(orphan_path)

        project2 = self.make_project(
            'TestProject2', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(project2, self.user, self.role_owner)
        orphan_path2 = iRODSPath(
            self.irods_backend.get_path(project2),
            settings.IRODS_SAMPLE_COLL,
            f'study_{uuid.uuid4()}',
        )
        self.irods.collections.create(orphan_path2)

        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        expected += (
            f'{project2.sodar_uuid};{project2.full_title};'
            f'{orphan_path2};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)
