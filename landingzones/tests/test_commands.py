"""Management command tests for the landingzones app"""

import io

from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.utils.timezone import localtime

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

from landingzones.management.commands.inactivezones import (
    get_inactive_zones,
    get_output,
)
from landingzones.models import (
    ZONE_STATUS_MOVED,
    ZONE_STATUS_DELETED,
    ZONE_STATUS_ACTIVE,
    ZONE_STATUS_MOVING,
)
from landingzones.tests.test_models import LandingZoneMixin
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE1_TITLE = '20180503_172456_test_zone'
ZONE_DESC = 'description'
ZONE2_TITLE = '20201123_143323_test_zone'
ZONE3_TITLE = '20201218_172740_test_zone_moved'
ZONE4_TITLE = '20201218_172743_test_zone_deleted'
LOGGER_BUSY_ZONES = 'landingzones.management.commands.busyzones'


class TestCommandBase(
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    SampleSheetIOMixin,
    LandingZoneMixin,
    TestCase,
):
    """Base class for command tests"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Init superuser
        self.user = self.make_user('user')
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        # Init project with owner
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user, self.role_owner
        )
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()


class TestInactiveZones(TestCommandBase):
    """Tests for the inactivezones command"""

    def setUp(self):
        super().setUp()
        testtime1 = localtime() - timedelta(weeks=3)
        testtime2 = localtime() - timedelta(weeks=1)

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = testtime1
            # Create landing zone 1 from 3 weeks ago
            self.zone = self.make_landing_zone(
                title=ZONE1_TITLE,
                project=self.project,
                user=self.user,
                assay=self.assay,
                description=ZONE_DESC,
                configuration=None,
                config_data={},
            )
            # Create landing zone 3 from 3 weeks ago but status MOVED
            self.zone3 = self.make_landing_zone(
                title=ZONE3_TITLE,
                project=self.project,
                user=self.user,
                assay=self.assay,
                description=ZONE_DESC,
                configuration=None,
                config_data={},
                status=ZONE_STATUS_MOVED,
            )
            # Create landing zone 3 from 3 weeks ago but status DELETED
            self.zone4 = self.make_landing_zone(
                title=ZONE4_TITLE,
                project=self.project,
                user=self.user,
                assay=self.assay,
                description=ZONE_DESC,
                configuration=None,
                config_data={},
                status=ZONE_STATUS_DELETED,
            )
            mock_now.return_value = testtime2
            # Create landing zone 2 from 1 week ago
            self.zone2 = self.make_landing_zone(
                title=ZONE2_TITLE,
                project=self.project,
                user=self.user,
                assay=self.assay,
                description=ZONE_DESC,
                configuration=None,
                config_data={},
            )

        self.irods_backend = get_backend_api('omics_irods')
        self.irods = self.irods_backend.get_session_obj()

        # Create iRODS collections
        self.irods.collections.create(self.irods_backend.get_path(self.zone))
        self.irods.collections.create(self.irods_backend.get_path(self.zone2))
        self.irods.collections.create(self.irods_backend.get_path(self.zone3))
        self.irods.collections.create(self.irods_backend.get_path(self.zone4))

    def tearDown(self):
        self.irods.collections.get('/sodarZone/projects').remove(force=True)
        self.irods.cleanup()

    def test_get_inactive_zones(self):
        """Test get_inactive_zones()"""
        zones = get_inactive_zones()
        self.assertEqual(zones.count(), 1)

    def test_get_output(self):
        """Test get_output()"""
        zones = get_inactive_zones()
        self.assertListEqual(
            get_output(zones, self.irods_backend, self.irods),
            [
                '{};{};{};{};0;0 bytes'.format(
                    str(self.project.sodar_uuid),
                    self.project.full_title,
                    self.zone.user.username,
                    self.irods_backend.get_path(self.zone),
                )
            ],
        )

    def test_command_inactivezones(self):
        """Test command"""
        with self.assertLogs(
            'landingzones.management.commands.inactivezones', level='INFO'
        ) as cm:
            call_command('inactivezones')
        expected = '{};{};{};{};0;0 bytes'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            self.zone.user.username,
            self.irods_backend.get_path(self.zone),
        )
        self.assertIn(expected, cm.output[0])


class TestBusyZones(TestCommandBase):
    """Tests for the busyzones command"""

    def setUp(self):
        super().setUp()
        # Create zones
        self.zone = self.make_landing_zone(
            title=ZONE1_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
            status=ZONE_STATUS_ACTIVE,
        )
        self.zone2 = self.make_landing_zone(
            title=ZONE2_TITLE,
            project=self.project,
            user=self.user,
            assay=self.assay,
            description=ZONE_DESC,
            configuration=None,
            config_data={},
            status=ZONE_STATUS_ACTIVE,
        )

    def test_active_zones(self):
        """Test command with active zones"""
        out = io.StringIO()
        call_command('busyzones', stdout=out)
        self.assertEqual(out.getvalue(), '')

    def test_command(self):
        """Test command with a busy zone"""
        self.zone2.status = ZONE_STATUS_MOVING
        self.zone2.save()
        with self.assertLogs(LOGGER_BUSY_ZONES, level='INFO') as cm:
            call_command('busyzones')
        self.assertIn(
            ';'.join(
                [
                    str(self.zone2.project.sodar_uuid),
                    self.zone2.project.full_title,
                    self.zone2.user.username,
                    self.zone2.title,
                    self.zone2.status,
                    str(self.zone2.sodar_uuid),
                ]
            ),
            cm.output[0],
        )

    def test_command_no_busy_zones(self):
        """Test command with no busy zones"""
        with self.assertLogs(LOGGER_BUSY_ZONES, level='INFO') as cm:
            call_command('busyzones')
        self.assertIn('Found 0 busy zones', cm.output[0])
