"""Tests for UI view permissions in the landingzones app"""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.tests.base import ProjectPermissionTestBase

# Samplesheets dependency
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR

from landingzones.tests.test_models import (
    LandingZoneMixin,
    ZONE_TITLE,
    ZONE_DESC,
)
from landingzones.tests.test_views import LandingzonesViewTestMixin


app_settings = AppSettingAPI()
User = get_user_model()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'landingzones'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TEST_OBJ_NAME = 'test1.txt'


class LandingzonesPermissionTestBase(
    LandingZoneMixin,
    SampleSheetIOMixin,
    LandingzonesViewTestMixin,
    ProjectPermissionTestBase,
):
    """Base class for landingzones permissions tests"""

    def setUp(self):
        super().setUp()
        # Default users for read views
        self.good_users_read = [
            self.superuser,
            self.user_owner_cat,  # Inherited
            self.user_delegate_cat,  # Inherited
            self.user_contributor_cat,  # Inherited
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        self.bad_users_read = [
            self.user_guest_cat,  # Inherited
            self.user_viewer_cat,  # Inherited
            self.user_finder_cat,  # Inherited
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]
        # Default users for write views
        self.good_users_write = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        self.bad_users_write = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]


class TestProjectZoneView(LandingzonesPermissionTestBase):
    """Tests for ProjectZoneView permissions"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:list', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get(self):
        """Test ProjectZoneView GET"""
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self.project.set_public_access(self.role_guest)
        self.assert_response(self.url, self.anonymous, 302)
        self.project.set_public_access(self.role_viewer)
        self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_disable(self):
        """Test GET with disabled non-superuser access"""
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    def test_get_restrict(self):
        """Test GET with zone_access_restrict"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        # NOTE: New user should be able to access list view
        self.assert_response(
            self.url, self.good_users_read + [user_contrib2], 200
        )
        self.assert_response(self.url, self.bad_users_read, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_restrict_disable(self):
        """Test GET with zone_access_restrict and disabled non-superuser access"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        self.assert_response(
            self.url, self.good_users_read + [user_contrib2], 200
        )
        self.assert_response(self.url, self.bad_users_read, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)


class TestZoneCreateView(LandingzonesPermissionTestBase):
    """Tests for ZoneCreateView permissions"""

    def _setup_investigation(self, colls: bool = False):
        """set up investigation and optional iRODS colls"""
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        if colls:
            self.investigation.irods_status = True
            self.investigation.save()

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'landingzones:create', kwargs={'project': self.project.sodar_uuid}
        )

    def test_get_no_sheets(self):
        """Test ZoneCreateView GET with no sheets"""
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    def test_get_investigation(self):
        """Test GET with investigation"""
        self._setup_investigation()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    def test_get_colls(self):
        """Test GET with investigation and collections"""
        self._setup_investigation(True)
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        self._setup_investigation(True)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self._setup_investigation(True)
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    def test_get_block(self):
        """Test GET with project access block"""
        self._setup_investigation(True)
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self._setup_investigation(True)
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_disable(self):
        """Test ZoneCreateView with disabled non-superuser access"""
        self._setup_investigation(True)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    def test_get_restrict(self):
        """Test GET with zone_access_restrict"""
        self._setup_investigation(True)
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        self.assert_response(self.url, self.good_users_write, 200)
        self.assert_response(
            self.url, self.bad_users_write + [user_contrib2], 302
        )
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_restrict_disable(self):
        """Test GET with zone_access_restrict and disabled non-superuser access"""
        self._setup_investigation(True)
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(
            self.url, self.non_superusers + [user_contrib2], 302
        )


class TestZoneUpdateView(LandingzonesPermissionTestBase):
    """Tests for ZoneUpdateView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,  # NOTE: Zone owner = user_contributor
            assay=self.assay,
            description=ZONE_DESC,
            status='ACTIVE',
            configuration=None,
            config_data={},
        )
        self.url = reverse(
            'landingzones:update', kwargs={'landingzone': zone.sodar_uuid}
        )
        self.redirect_url = reverse(
            'landingzones:list', kwargs={'project': zone.project.sodar_uuid}
        )

    def test_get(self):
        """Test ZoneUpdateView GET"""
        self.assert_response(self.url, self.good_users_write, 200)
        self.assert_response(
            self.url, self.bad_users_write, 302, redirect_user=self.redirect_url
        )
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(
                self.url,
                self.no_role_users,
                302,
                redirect_user=self.redirect_url,
            )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(
                self.url, self.anonymous, 302, redirect_user=self.redirect_url
            )

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(
            self.url, self.non_superusers, 302, redirect_user=self.redirect_url
        )
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(
                self.url,
                self.no_role_users,
                302,
                redirect_user=self.redirect_url,
            )

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(
            self.url, self.non_superusers, 302, redirect_user=self.redirect_url
        )

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(
            self.url, self.non_superusers, 302, redirect_user=self.redirect_url
        )

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_disable(self):
        """Test GET with disabled non-superuser access"""
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(
            self.url, self.non_superusers, 302, redirect_user=self.redirect_url
        )

    def test_get_restrict(self):
        """Test GET with zone_access_restrict"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(user_contrib2)
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_contributor,
            user_contrib2,
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(
            self.url, bad_users, 302, redirect_user=self.redirect_url
        )
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(
                self.url,
                self.no_role_users,
                302,
                redirect_user=self.redirect_url,
            )

    def test_get_restrict_own_zone(self):
        """Test GET with zone_access_restrict and own zone"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        self.assert_response(self.url, self.good_users_write, 200)
        self.assert_response(
            self.url,
            self.bad_users_write + [user_contrib2],
            302,
            redirect_user=self.redirect_url,
        )
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(
                self.url,
                self.no_role_users,
                302,
                redirect_user=self.redirect_url,
            )

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_restrict_own_zone_disable(self):
        """Test GET with zone_access_restrict, own zone and disabled non-superuser access"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(
            self.url,
            self.non_superusers + [user_contrib2],
            302,
            redirect_user=self.redirect_url,
        )


class TestZoneDeleteView(LandingzonesPermissionTestBase):
    """Tests for ZoneDeleteView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        zone = self.make_landing_zone(
            title=ZONE_TITLE,
            project=self.project,
            user=self.user_contributor,  # NOTE: Zone owner = user_contributor
            assay=self.assay,
            description=ZONE_DESC,
            status='ACTIVE',
            configuration=None,
            config_data={},
        )
        self.url = reverse(
            'landingzones:delete', kwargs={'landingzone': zone.sodar_uuid}
        )

    def test_get(self):
        """Test ZoneDeleteView GET"""
        self.assert_response(self.url, self.good_users_write, 200)
        self.assert_response(self.url, self.bad_users_write, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous access"""
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.anonymous, 302)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_write, 200)
        self.assert_response(self.url, self.bad_users_write, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_disable(self):
        """Test GET with disabled non-superuser access"""
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 302)

    def test_get_restrict(self):
        """Test GET with zone_access_restrict"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(user_contrib2)
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_owner,
            self.user_delegate,
        ]
        bad_users = [
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_contributor,
            user_contrib2,
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    def test_get_restrict_own_zone(self):
        """Test GET with zone_access_restrict and own zone"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        self.assert_response(self.url, self.good_users_write, 200)
        self.assert_response(
            self.url, self.bad_users_write + [user_contrib2], 302
        )
        for role in self.guest_roles:
            self.project.set_public_access(role)
            self.assert_response(self.url, self.no_role_users, 302)

    @override_settings(LANDINGZONES_DISABLE_FOR_USERS=True)
    def test_get_restrict_own_zone_disable(self):
        """Test GET with zone_access_restrict, own zone and disabled non-superuser access"""
        user_contrib2 = self.make_extra_contributor()
        self.restrict_zone_access(self.user_contributor)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(
            self.url, self.non_superusers + [user_contrib2], 302
        )
