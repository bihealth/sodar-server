"""Tests for plugins in the landingzones app"""

from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint, PluginObjectLink
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

import landingzones.constants as lc
from landingzones.models import LandingZone
from landingzones.plugins import (
    LZ_PROJECT_COL_ACTIVE,
    LZ_PROJECT_COL_CREATE,
    LZ_PROJECT_COL_NO_ZONES,
)
from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']


# Local constants
SHEET_PATH_SMALL2 = SHEET_DIR + 'i_small2.zip'
MODEL_STR = 'LandingZone'
ZONE_COL_ID = 'zones'


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
        # Init users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.save()
        self.user_owner = self.make_user('user_owner')
        self.user_contributor = self.make_user('user_contributor')
        # Init projects and assignments
        self.category = self.make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.owner_as_cat = self.make_assignment(
            self.category, self.user_owner, self.role_owner
        )
        self.project = self.make_project(
            'TestProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        self.contrib_as = self.make_assignment(
            self.project, self.user_contributor, self.role_contributor
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


class TestGetObjectLink(LandingzonesPluginTestBase):
    """Tests for get_object_link()"""

    def setUp(self):
        super().setUp()
        self.zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            description=ZONE_DESC,
            status=lc.ZONE_STATUS_ACTIVE,
        )

    def test_get_object_link_active(self):
        """Test get_object_link() with ACTIVE zone"""
        link = self.plugin.get_object_link(MODEL_STR, self.zone.sodar_uuid)
        self.assertIsInstance(link, PluginObjectLink)
        self.assertEqual(
            link.url,
            reverse(
                'landingzones:list', kwargs={'project': self.project.sodar_uuid}
            )
            + '#'
            + str(self.zone.sodar_uuid),
        )
        self.assertEqual(link.name, self.zone.title)

    def test_get_object_link_moved(self):
        """Test get_object_link() with MOVED zone"""
        self.zone.set_status(lc.ZONE_STATUS_MOVED)
        self.assertIsNone(
            self.plugin.get_object_link(MODEL_STR, self.zone.sodar_uuid)
        )

    def test_get_object_link_deleted(self):
        """Test get_object_link() with DELETED zone"""
        self.zone.set_status(lc.ZONE_STATUS_DELETED)
        self.assertIsNone(
            self.plugin.get_object_link(MODEL_STR, self.zone.sodar_uuid)
        )


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


class TestGetProjectListValue(LandingzonesPluginTestBase):
    """Tests for get_project_list_value()"""

    def setUp(self):
        super().setUp()
        self.url_create = reverse(
            'landingzones:create', kwargs={'project': self.project.sodar_uuid}
        )
        self.url_list = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get_project_list_value_no_zones_owner(self):
        """Test get_project_list_value() with no zones as owner"""
        self.assertEqual(
            LandingZone.objects.filter(project=self.project).count(), 0
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        expected = LZ_PROJECT_COL_CREATE.format(url=self.url_create)
        self.assertEqual(res, expected)

    def test_get_project_list_value_no_zones_superuser(self):
        """Test get_project_list_value() with no zones as superuser"""
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.superuser
        )
        expected = LZ_PROJECT_COL_CREATE.format(url=self.url_create)
        self.assertEqual(res, expected)

    def test_get_project_list_value_own_zone(self):
        """Test get_project_list_value() with own zone"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        self.assertEqual(
            LandingZone.objects.filter(user=self.user_owner).count(), 1
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        expected = LZ_PROJECT_COL_ACTIVE.format(
            url=self.url_list, title='1 landing zone owned by you'
        )
        self.assertEqual(res, expected)

    def test_get_project_list_value_other_zone_owner(self):
        """Test get_project_list_value() with other user's zone as owner"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        expected = LZ_PROJECT_COL_CREATE.format(url=self.url_create)
        self.assertEqual(res, expected)

    def test_get_project_list_value_both_zones_owner(self):
        """Test get_project_list_value() with both own and others' zones as owner"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        self.make_landing_zone(
            title=ZONE_TITLE + '2',
            project=self.project,
            user=self.user_contributor,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        expected = LZ_PROJECT_COL_ACTIVE.format(
            url=self.url_list, title='1 landing zone owned by you'
        )
        self.assertEqual(res, expected)

    def test_get_project_list_value_other_zone_superuser(self):
        """Test get_project_list_value() with other user's zone as superuser"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.superuser
        )
        expected = LZ_PROJECT_COL_ACTIVE.format(
            url=self.url_list, title='1 landing zone in total'
        )
        self.assertEqual(res, expected)

    def test_get_project_list_value_both_zones_superuser(self):
        """Test get_project_list_value() with both own and others' zones as superuser"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        self.make_landing_zone(
            title=ZONE_TITLE + '2',
            project=self.project,
            user=self.superuser,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.superuser
        )
        expected = LZ_PROJECT_COL_ACTIVE.format(
            url=self.url_list, title='2 landing zones in total'
        )
        self.assertEqual(res, expected)

    def test_get_project_list_value_own_zone_multiple(self):
        """Test get_project_list_value() with multiple own zones"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        self.make_landing_zone(
            title=ZONE_TITLE + '2',
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        expected = LZ_PROJECT_COL_ACTIVE.format(
            url=self.url_list, title='2 landing zones owned by you'
        )
        self.assertEqual(res, expected)

    def test_get_project_list_value_own_zone_inactive(self):
        """Test get_project_list_value() with inactive own zone"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_MOVED,
        )
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        expected = LZ_PROJECT_COL_CREATE.format(url=self.url_create)
        self.assertEqual(res, expected)

    def test_get_project_list_value_no_zones_guest(self):
        """Test get_project_list_value() with no zones as guest"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_guest)
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, user_new
        )
        self.assertEqual(res, '')

    def test_get_project_list_value_other_zone_guest(self):
        """Test get_project_list_value() with other user zone as guest"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_guest)
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, user_new
        )
        self.assertEqual(res, '')

    def test_get_project_list_value_no_zones_viewer(self):
        """Test get_project_list_value() with no zones as viewer"""
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_viewer)
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, user_new
        )
        self.assertEqual(res, '')

    def test_get_project_list_value_other_zone_viewer(self):
        """Test get_project_list_value() with other user zone as viewer"""
        self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_owner,
            assay=self.assay,
            status=lc.ZONE_STATUS_ACTIVE,
        )
        user_new = self.make_user('user_new')
        self.make_assignment(self.project, user_new, self.role_viewer)
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, user_new
        )
        self.assertEqual(res, '')

    def test_get_project_list_value_no_zones_anonymous(self):
        """Test get_project_list_value() with no zones as anonymous user"""
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, AnonymousUser()
        )
        self.assertEqual(res, '')

    def test_get_project_list_value_irods_status_false(self):
        """Test get_project_list_value() with irods_status=False"""
        self.investigation.irods_status = False
        self.investigation.save()
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        self.assertEqual(res, LZ_PROJECT_COL_NO_ZONES)

    def test_get_project_list_value_inactive_investigation(self):
        """Test get_project_list_value() with inactive investigation"""
        self.investigation.active = False
        self.investigation.save()
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        self.assertEqual(res, LZ_PROJECT_COL_NO_ZONES)

    def test_get_project_list_value_no_investigation(self):
        """Test get_project_list_value() with no investigation"""
        self.investigation.delete()
        res = self.plugin.get_project_list_value(
            ZONE_COL_ID, self.project, self.user_owner
        )
        self.assertEqual(res, LZ_PROJECT_COL_NO_ZONES)

    def test_get_project_list_value_invalid_column_id(self):
        """Test get_project_list_value() with invalid column ID"""
        res = self.plugin.get_project_list_value(
            'INVALID_COLUMN', self.project, self.user_owner
        )
        self.assertEqual(res, '')
