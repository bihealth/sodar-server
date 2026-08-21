"""Management command tests for the irodsadmin app"""

import os
import sys
import uuid

from io import StringIO
from typing import Optional

from cubi_isa_templates import IsaTabTemplate, _TEMPLATES as CUBI_TEMPLATES

from irods.access import iRODSAccess
from irods.path import iRODSPath

from django.conf import settings
from django.core.management import call_command

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS
from projectroles.models import Project
from projectroles.plugins import PluginAPI

# Landingzones dependency
from landingzones.models import LandingZone
from landingzones.tests.test_models import LandingZoneMixin
from landingzones.tests.test_views_taskflow import LandingZoneTaskflowMixin

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views import SheetTemplateCreateMixin
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
from irodsadmin.management.commands.irodsorphans import (
    Command,
    OUT_PROJECT_DELETED,
    OUT_NONE,
)


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
CUBI_TPL_DICT = {t.name: t for t in CUBI_TEMPLATES}
RAW_DATA_COLL = 'RawData'
MICROARRAY_COLL = 'alpha-S1-E1-H1'
USER_COLL = 'UserDefinedCollection'


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
            f'{CHECK_ACCESS_GROUP_MSG}: {IRODS_ACCESS_MODIFY_OBJ};{obj.path}',
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
    SheetTemplateCreateMixin,
    TaskflowViewTestBase,
):
    """Tests for the irodsorphans management command"""

    def _setup_investigation(
        self,
        path: str = SHEET_PATH_GERMLINE,
        template: Optional[IsaTabTemplate] = None,
    ):
        """
        Set up investigation with taskflow.

        NOTE: This assumes a single study and a single assay.

        :param path: File path for sheet import (string)
        :param template: IsaTabTemplate object or None. Overrides path if set.
        """
        if template:
            self.investigation = self.make_sheets_from_cubi_tpl(template)
        else:
            self.investigation = self.import_isa_from_file(path, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.assay_path = self.irods_backend.get_path(self.assay)
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

    @staticmethod
    def _call_output(project: Optional[Project] = None) -> str:
        """Call irodsorphans management command and return output"""
        sys.stdout = StringIO()
        options = {}
        if project:
            options['project'] = str(project.sodar_uuid)
        call_command('irodsorphans', stdout=sys.stdout, **options)
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
        self.project_path = self.irods_backend.get_path(self.project)
        self.sample_path = self.irods_backend.get_sample_path(self.project)

    def test_command_orphan_project(self):
        """Test command with orphan project"""
        path = iRODSPath(
            self.irods_backend.get_projects_path(), '11', DUMMY_UUID
        )
        self.irods.collections.create(path)
        output = self._call_output()
        expected = f'{OUT_NONE};{OUT_PROJECT_DELETED};{path};{OUT_SUFFIX}'
        self.assertEqual(output, expected)

    def test_command_no_inv(self):
        """Test command with no investigation"""
        self.assertEqual(self._call_output(), '')

    def test_command_inv(self):
        """Test command with investigation and no orphans"""
        self._setup_investigation()
        self.assertEqual(self._call_output(), '')

    def test_command_orphan_assay(self):
        """Test command with orphan assay"""
        self._setup_investigation()
        path = iRODSPath(
            self.irods_backend.get_path(self.study), f'assay_{uuid.uuid4()}'
        )
        self.irods.collections.create(path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_orphan_study(self):
        """Test command with orphan study"""
        self._setup_investigation()
        path = iRODSPath(self.sample_path, f'study_{uuid.uuid4()}')
        self.irods.collections.create(path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_assay_top(self):
        """Test command with accepted assay top collection"""
        self._setup_investigation()
        self.irods.collections.create(self.assay_path, MISC_FILES_COLL)
        self.assertEqual(self._call_output(), '')

    def test_command_assay_top_orphan(self):
        """Test command with orphan assay top collection"""
        self._setup_investigation()
        path = iRODSPath(self.assay_path, USER_COLL)
        self.irods.collections.create(path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_assay_sub(self):
        """Test command with accepted assay subcollection"""
        self._setup_investigation()
        path = iRODSPath(self.assay_path, MISC_FILES_COLL, USER_COLL)
        self.irods.collections.create(path)
        output = self._call_output()
        self.assertEqual(output, '')

    def test_command_assay_sub_multi_level(self):
        """Test command with multi-level accepted assay subcollection"""
        self._setup_investigation()
        path = iRODSPath(
            self.assay_path, MISC_FILES_COLL, USER_COLL, f'{USER_COLL}2'
        )
        self.irods.collections.create(path)
        output = self._call_output()
        self.assertEqual(output, '')

    def test_command_assay_nested(self):
        """Test command with nested assay plugin paths and no orphans"""
        template = CUBI_TPL_DICT['microarray']
        self._setup_investigation(template=template)
        # NOTE: Yes, the template expects two levels of the same collection name
        path = iRODSPath(
            self.assay_path, RAW_DATA_COLL, MICROARRAY_COLL, MICROARRAY_COLL
        )
        self.irods.collections.create(path)
        output = self._call_output()
        self.assertEqual(output, '')

    def test_command_assay_nested_add(self):
        """Test command with added collection under nested assay plugin path"""
        template = CUBI_TPL_DICT['microarray']
        self._setup_investigation(template=template)
        path = iRODSPath(
            self.assay_path,
            RAW_DATA_COLL,
            MICROARRAY_COLL,
            MICROARRAY_COLL,
            USER_COLL,
        )  # This should be OK
        self.irods.collections.create(path)
        output = self._call_output()
        self.assertEqual(output, '')

    def test_command_assay_nested_orphan_middle(self):
        """Test command with nested assay paths and orphan in middle of path"""
        template = CUBI_TPL_DICT['microarray']
        self._setup_investigation(template=template)
        orphan_path = iRODSPath(self.assay_path, RAW_DATA_COLL, USER_COLL)
        # The last collection name is expected, but the parent one is not
        child_path = iRODSPath(orphan_path, MICROARRAY_COLL)
        self.irods.collections.create(child_path)
        output = self._call_output()
        # Parent collection should be reported
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{orphan_path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_assay_nested_orphan_end(self):
        """Test command with nested assay paths and orphan in end of path"""
        template = CUBI_TPL_DICT['microarray']
        self._setup_investigation(template=template)
        path = iRODSPath(
            self.assay_path, RAW_DATA_COLL, MICROARRAY_COLL, USER_COLL
        )
        self.irods.collections.create(path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_zone(self):
        """Test command with accepted landing zone collection"""
        self._setup_investigation()
        zone = self._get_zone()
        self.assertTrue(
            self.irods.collections.exists(self.irods_backend.get_path(zone))
        )
        output = self._call_output()
        self.assertEqual(output, '')

    def test_command_zone_orphan(self):
        """Test command with orphan landing zone collection"""
        self._setup_investigation()
        path = iRODSPath(
            self.project_path,
            settings.IRODS_LANDING_ZONE_COLL,
            self.user.username,
            self.study.get_name().replace(' ', '_').lower(),
            self.assay.get_display_name().replace(' ', '_').lower(),
            '20201031_123456',
        )
        self.irods.collections.create(path)
        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_multiple(self):
        """Test command with multiple orphans"""
        self._setup_investigation()
        path = iRODSPath(self.sample_path, f'study_{uuid.uuid4()}')
        self.irods.collections.create(path)

        path2 = iRODSPath(
            self.project_path,
            settings.IRODS_LANDING_ZONE_COLL,
            self.user.username,
            self.study.get_name().replace(' ', '_').lower(),
            self.assay.get_display_name().replace(' ', '_').lower(),
            '20201031_123456',
        )
        self.irods.collections.create(path2)

        output = self._call_output()
        expected = (
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path};{OUT_SUFFIX}'
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path2};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_multi_project(self):
        """Test command with orphans in multiple projects"""
        path = iRODSPath(
            self.irods_backend.get_projects_path(), '11', DUMMY_UUID
        )
        self.irods.collections.create(path)

        path2 = iRODSPath(self.sample_path, f'study_{uuid.uuid4()}')
        self.irods.collections.create(path2)

        project2 = self.make_project(
            'TestProject2', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(project2, self.user, self.role_owner)
        path3 = iRODSPath(
            self.irods_backend.get_path(project2),
            settings.IRODS_SAMPLE_COLL,
            f'study_{uuid.uuid4()}',
        )
        self.irods.collections.create(path3)

        output = self._call_output()
        expected = (
            f'{OUT_NONE};{OUT_PROJECT_DELETED};{path};{OUT_SUFFIX}'
            f'{self.project.sodar_uuid};{self.project.full_title};'
            f'{path2};{OUT_SUFFIX}'
            f'{project2.sodar_uuid};{project2.full_title};'
            f'{path3};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)

    def test_command_multi_project_limit(self):
        """Test command with multiple projects and project limit"""
        path = iRODSPath(
            self.irods_backend.get_projects_path(), '11', DUMMY_UUID
        )
        self.irods.collections.create(path)

        path = iRODSPath(self.sample_path, f'study_{uuid.uuid4()}')
        self.irods.collections.create(path)

        project2 = self.make_project(
            'TestProject2', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(project2, self.user, self.role_owner)
        path2 = iRODSPath(
            self.irods_backend.get_path(project2),
            settings.IRODS_SAMPLE_COLL,
            f'study_{uuid.uuid4()}',
        )
        self.irods.collections.create(path2)

        # Output for orphan project and self.project should be missing
        output = self._call_output(project=project2)
        expected = (
            f'{project2.sodar_uuid};{project2.full_title};{path2};{OUT_SUFFIX}'
        )
        self.assertEqual(output, expected)
