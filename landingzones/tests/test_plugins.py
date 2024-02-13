"""Tests for plugins in the landingzones app"""

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

import landingzones.constants as lc
from landingzones.tests.test_models import LandingZoneMixin


# Local constants
SHEET_PATH_SMALL2 = SHEET_DIR + 'i_small2.zip'


class LandingzonesPluginTestBase(
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    SampleSheetIOMixin,
    LandingZoneMixin,
    TestCase,
):
    """Base class for landingzones plugin tests"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Make owner user
        self.user_owner = self.make_user('owner')
        # Init project and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(
            SHEET_PATH_SMALL2, self.project
        )
        self.investigation.irods_status = True
        self.investigation.save()
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Get plugin
        self.plugin = ProjectAppPluginPoint.get_plugin('landingzones')


class TestGetStatistics(LandingzonesPluginTestBase):
    """Tests for get_statistics()"""

    def _make_zone(self, status):
        self.make_landing_zone(
            'zone_{}'.format(status.lower()),
            self.project,
            self.user_owner,
            self.assay,
            status=status,
        )

    def _assert_stats(self, expected):
        stats = self.plugin.get_statistics()
        for k, v in expected.items():
            self.assertEqual(stats[k]['value'], v)

    def test_get_statistics_active(self):
        """Test get_statistics() with active zones"""
        self._make_zone(lc.ZONE_STATUS_ACTIVE)
        self._make_zone(lc.ZONE_STATUS_FAILED)
        self._assert_stats(
            {
                'zones_total': 2,
                'zones_active': 2,
                'zones_finished': 0,
                'zones_busy': 0,
            }
        )

    def test_get_statistics_finished(self):
        """Test get_statistics() with finished zones"""
        self._make_zone(lc.ZONE_STATUS_MOVED)
        self._make_zone(lc.ZONE_STATUS_DELETED)
        self._assert_stats(
            {
                'zones_total': 2,
                'zones_active': 0,
                'zones_finished': 2,
                'zones_busy': 0,
            }
        )

    def test_get_statistics_busy(self):
        """Test get_statistics() with busy zones"""
        self._make_zone(lc.ZONE_STATUS_MOVING)
        self._make_zone(lc.ZONE_STATUS_DELETING)
        self._assert_stats(
            {
                'zones_total': 2,
                'zones_active': 0,
                'zones_finished': 0,
                'zones_busy': 2,
            }
        )

    def test_get_statistics_mixed(self):
        """Test get_statistics() with mixed zone statuses"""
        self._make_zone(lc.ZONE_STATUS_ACTIVE)
        self._make_zone(lc.ZONE_STATUS_MOVING)
        self._make_zone(lc.ZONE_STATUS_DELETED)
        self._assert_stats(
            {
                'zones_total': 3,
                'zones_active': 1,
                'zones_finished': 1,
                'zones_busy': 1,
            }
        )

    def test_get_statistics_no_zones(self):
        """Test get_statistics() with no zones"""
        self._assert_stats(
            {
                'zones_total': 0,
                'zones_active': 0,
                'zones_finished': 0,
                'zones_busy': 0,
            }
        )
