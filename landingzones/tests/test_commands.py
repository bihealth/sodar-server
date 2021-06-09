from datetime import timedelta
import io

from django.conf import settings
from django.core.management import call_command
from django.utils.timezone import localtime

from test_plus.test import TestCase
from unittest import mock, skipIf

# Projectroles dependency
from projectroles.constants import SODAR_CONSTANTS
from projectroles.models import Role
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from landingzones.management.commands.inactivezones import (
    get_inactive_zones,
    get_output,
)
from landingzones.tests.test_models import LandingZoneMixin
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
SHEET_PATH = SHEET_DIR + 'i_small.zip'
ZONE1_TITLE = '20180503_172456_test_zone'
ZONE1_DESC = 'description'
ZONE2_TITLE = '20201123_143323_test_zone'
ZONE2_DESC = 'description'
ZONE3_TITLE = '20201218_172740_test_zone_moved'
ZONE3_DESC = 'description'
ZONE4_TITLE = '20201218_172743_test_zone_deleted'
ZONE4_DESC = 'description'
IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestInactiveZones(
    ProjectMixin,
    SampleSheetIOMixin,
    RoleAssignmentMixin,
    LandingZoneMixin,
    TestCase,
):
    """Test functions for the inactivezones command"""

    def setUp(self):
        super().setUp()

        # Init super user
        self.user = self.make_user('user')
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()

        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]

        # Init project with owner
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None
        )
        self.as_owner = self._make_assignment(
            self.project, self.user, self.role_owner
        )

        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        testtime1 = localtime() - timedelta(weeks=3)
        testtime2 = localtime() - timedelta(weeks=1)

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = testtime1

            # Create LandingZone 1 from 3 weeks ago
            self.landing_zone1 = self._make_landing_zone(
                title=ZONE1_TITLE,
                project=self.project,
                user=self.as_owner.user,
                assay=self.assay,
                description=ZONE1_DESC,
                configuration=None,
                config_data={},
            )

            # Create LandingZone 3 from 3 weeks ago but status MOVED
            self.landing_zone3 = self._make_landing_zone(
                title=ZONE3_TITLE,
                project=self.project,
                user=self.as_owner.user,
                assay=self.assay,
                description=ZONE3_DESC,
                configuration=None,
                config_data={},
                status='MOVED',
            )

            # Create LandingZone 3 from 3 weeks ago but status DELETED
            self.landing_zone4 = self._make_landing_zone(
                title=ZONE4_TITLE,
                project=self.project,
                user=self.as_owner.user,
                assay=self.assay,
                description=ZONE4_DESC,
                configuration=None,
                config_data={},
                status='DELETED',
            )

            mock_now.return_value = testtime2

            # Create LandingZone 2 from 1 week ago
            self.landing_zone2 = self._make_landing_zone(
                title=ZONE2_TITLE,
                project=self.project,
                user=self.as_owner.user,
                assay=self.assay,
                description=ZONE2_DESC,
                configuration=None,
                config_data={},
            )

        self.irods_backend = get_backend_api('omics_irods')
        self.irods_session = self.irods_backend.get_session()

        # Create the irods collections
        self.irods_session.collections.create(
            self.irods_backend.get_path(self.landing_zone1)
        )
        self.irods_session.collections.create(
            self.irods_backend.get_path(self.landing_zone2)
        )
        self.irods_session.collections.create(
            self.irods_backend.get_path(self.landing_zone3)
        )
        self.irods_session.collections.create(
            self.irods_backend.get_path(self.landing_zone4)
        )

    def tearDown(self):
        self.irods_session.collections.get('/omicsZone/projects').remove(
            force=True
        )

    def test_get_inactive_zones(self):
        """Test get_inactive_zones()"""
        zones = get_inactive_zones()
        self.assertEqual(zones.count(), 1)

    def test_get_output(self):
        """Test get_output()"""
        zones = get_inactive_zones()
        self.assertListEqual(
            get_output(zones, self.irods_backend),
            [
                '{};{};{};{};0;0 bytes'.format(
                    str(self.project.sodar_uuid),
                    self.project.full_title,
                    self.landing_zone1.user.username,
                    self.irods_backend.get_path(self.landing_zone1),
                )
            ],
        )

    def test_command_inactivezones(self):
        """Test command"""
        out = io.StringIO()
        call_command('inactivezones', stdout=out)
        expected = '{};{};{};{};0;0 bytes\n'.format(
            str(self.project.sodar_uuid),
            self.project.full_title,
            self.landing_zone1.user.username,
            self.irods_backend.get_path(self.landing_zone1),
        )
        self.assertEqual(expected, out.getvalue())
