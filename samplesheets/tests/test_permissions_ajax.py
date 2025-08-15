"""Tests for Ajax API View permissions in the samplesheets app"""

from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.tests.test_permissions import ProjectPermissionTestBase
from projectroles.utils import build_secret

from samplesheets.models import (
    ISATab,
    IrodsDataRequest,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import IrodsDataRequestMixin


app_settings = AppSettingAPI()


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_SECRET = build_secret()
INVALID_SECRET = build_secret()
IRODS_FILE_PATH = '/sodarZone/path/test1.txt'


class SampleSheetsAjaxPermissionTestBase(
    SampleSheetIOMixin, ProjectPermissionTestBase
):
    """Base test class for samplesheets Ajax view permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Default users for read views
        self.good_users_read = [
            self.superuser,
            self.user_owner_cat,  # Inherited
            self.user_delegate_cat,  # Inherited
            self.user_contributor_cat,  # Inherited
            self.user_guest_cat,  # Inherited
            self.user_viewer_cat,  # Inherited
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_viewer,
        ]
        self.bad_users_read = [
            self.user_finder_cat,
            self.user_no_roles,
            self.anonymous,
        ]
        # Default users for write views
        self.good_users_write = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
        ]
        self.bad_users_write = [
            self.user_guest_cat,
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]


class TestSheetContextAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetContextAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_context',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetContextAjaxView GET"""
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        # Test public project
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        # Test public project
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 403)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 403)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)


class TestStudyTablesAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for StudyTablesAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_study_tables',
            kwargs={'study': self.study.sodar_uuid},
        )
        self.edit_data = {'edit': 1}

    def test_get(self):
        """Test StudyTablesAjaxView GET"""
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 403)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 403)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)

    def test_get_edit(self):
        """Test GET with edit mode"""
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        self.assert_response(
            self.url, self.good_users_write, 200, data=self.edit_data
        )
        self.assert_response(
            self.url, self.bad_users_write, 403, data=self.edit_data
        )
        self.project.set_public()
        self.assert_response(
            self.url, self.no_role_users, 403, data=self.edit_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_edit_anon(self):
        """Test GET with edit mode and anon access"""
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403, data=self.edit_data)

    def test_get_edit_archive(self):
        """Test GET with edit mode and archived project"""
        self.project.set_archive()
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        self.assert_response(self.url, self.superuser, 200, data=self.edit_data)
        self.assert_response(
            self.url, self.non_superusers, 403, data=self.edit_data
        )
        self.project.set_public()
        self.assert_response(
            self.url, self.no_role_users, 403, data=self.edit_data
        )

    def test_get_edit_block(self):
        """Test GET with edit mode and project access block"""
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200, data=self.edit_data)
        self.assert_response(
            self.url, self.non_superusers, 403, data=self.edit_data
        )

    def test_get_edit_read_only(self):
        """Test GET with edit mode and site read-only mode"""
        app_settings.set(
            'samplesheets', 'allow_editing', True, project=self.project
        )
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200, data=self.edit_data)
        self.assert_response(
            self.url, self.non_superusers, 403, data=self.edit_data
        )

    def test_get_not_allowed(self):
        """Test GET with edit mode but disallowed"""
        app_settings.set(
            'samplesheets', 'allow_editing', False, project=self.project
        )
        self.assert_response(self.url, self.all_users, 403, data=self.edit_data)
        self.project.set_public()
        self.assert_response(
            self.url, self.no_role_users, 403, data=self.edit_data
        )

    def test_get_not_allowed_archive(self):
        """Test GET with disallowed edit mode and archived project"""
        self.project.set_archive()
        app_settings.set(
            'samplesheets', 'allow_editing', False, project=self.project
        )
        self.assert_response(self.url, self.all_users, 403, data=self.edit_data)
        self.project.set_public()
        self.assert_response(
            self.url, self.no_role_users, 403, data=self.edit_data
        )


class TestStudyLinksAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for StudyLinksAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_study_links',
            kwargs={'study': self.study.sodar_uuid},
        )

    def test_get(self):
        """Test StudyLinksAjaxView GET"""
        self.assert_response(self.url, self.good_users_read, 404)  # No plugin
        self.assert_response(self.url, self.bad_users_read, 403)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_read, 404)  # No plugin
        self.assert_response(self.url, self.bad_users_read, 403)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 404)
        self.assert_response(self.url, self.non_superusers, 403)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users_read, 404)
        self.assert_response(self.url, self.bad_users_read, 403)


class TestSheetWarningsAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetWarningsAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_warnings',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get(self):
        """Test SheetWarningsAjaxView GET"""
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 403)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 403)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)


class TestSheetCellEditAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetCellEditAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_edit_cell',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test SheetCellEditAjaxView POST"""
        self.assert_response(
            self.url, self.good_users_write, 200, method='POST'
        )
        self.assert_response(self.url, self.bad_users_write, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')


class TestSheetRowInsertAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetRowInsertAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_edit_row_insert',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test SheetRowInsertAjaxView POST"""
        self.assert_response(
            self.url, self.good_users_write, 200, method='POST'
        )
        self.assert_response(self.url, self.bad_users_write, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')


class TestSheetRowDeleteAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetRowDeleteAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_edit_row_delete',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test SheetRowDeleteAjaxView POST"""
        self.assert_response(
            self.url, self.good_users_write, 200, method='POST'
        )
        self.assert_response(self.url, self.bad_users_write, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')


class TestSheetVersionSaveAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetVersionSaveAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_version_save',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test SheetVersionSaveAjaxView POST"""
        self.assert_response(
            self.url, self.good_users_write, 200, method='POST'
        )
        self.assert_response(self.url, self.bad_users_write, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')


class TestSheetEditFinishAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetEditFinishAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_edit_finish',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test SheetEditFinishAjaxView POST"""
        self.assert_response(
            self.url, self.good_users_write, 200, method='POST'
        )
        self.assert_response(self.url, self.bad_users_write, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 200, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')


class TestSheetEditConfigAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetEditConfigAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_config_update',
            kwargs={'project': self.project.sodar_uuid},
        )
        # TODO: Set up request data

    def test_post(self):
        """Test SheetEditConfigAjaxView POST"""
        # NOTE: We need post data for status 200
        self.assert_response(
            self.url, self.good_users_write, 400, method='POST'
        )
        self.assert_response(self.url, self.bad_users_write, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.superuser, 400, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.no_role_users, 403, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 400, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.superuser, 400, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')


class TestStudyDisplayConfigAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for StudyDisplayConfigAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_display_update',
            kwargs={'study': self.study.sodar_uuid},
        )
        # TODO: Set up request data

    def test_post(self):
        """Test StudyDisplayConfigAjaxView POST"""
        # NOTE: We need post data for status 200
        self.assert_response(self.url, self.good_users_read, 400, method='POST')
        self.assert_response(self.url, self.bad_users_read, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.user_guest, 400, method='POST')
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 400, method='POST')

    def test_post_archive(self):
        """Test POST with archived project"""
        # NOTE: This is allowed with archived projects
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_read, 400, method='POST')
        self.assert_response(self.url, self.bad_users_read, 403, method='POST')
        self.project.set_public()
        self.assert_response(self.url, self.user_guest, 400, method='POST')
        self.assert_response(self.url, self.anonymous, 403, method='POST')

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 400, method='POST')
        self.assert_response(self.url, self.non_superusers, 403, method='POST')

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users_read, 400, method='POST')
        self.assert_response(self.url, self.bad_users_read, 403, method='POST')


class TestSheetVersionCompareAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for SheetVersionCompareAjaxView"""

    def setUp(self):
        super().setUp()
        self.isa_version = ISATab.objects.first()
        self.url = '{}?source={}&target={}'.format(
            reverse(
                'samplesheets:ajax_version_compare',
                kwargs={'project': self.project.sodar_uuid},
            ),
            str(self.isa_version.sodar_uuid),
            str(self.isa_version.sodar_uuid),
        )

    def test_get(self):
        """Test SheetVersionCompareAjaxView GET"""
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        self.project.set_public()
        self.assert_response(
            self.url, [self.user_finder_cat, self.user_no_roles], 200
        )
        self.assert_response(self.url, self.anonymous, 403)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_get_anon(self):
        """Test GET with anonymous guest access"""
        self.project.set_public()
        self.assert_response(self.url, self.anonymous, 200)

    def test_get_archive(self):
        """Test GET with archived project"""
        self.project.set_archive()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)
        self.project.set_public()
        self.assert_response(self.url, [self.user_no_roles], 200)
        self.assert_response(self.url, [self.anonymous], 403)

    def test_get_block(self):
        """Test GET with project access block"""
        self.set_access_block(self.project)
        self.assert_response(self.url, self.superuser, 200)
        self.assert_response(self.url, self.non_superusers, 403)

    def test_get_read_only(self):
        """Test GET with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(self.url, self.good_users_read, 200)
        self.assert_response(self.url, self.bad_users_read, 403)


class TestIrodsDataRequestCreateAjaxView(SampleSheetsAjaxPermissionTestBase):
    """Permission tests for IrodsDataRequestCreateAjaxView"""

    @classmethod
    def _cleanup(cls):
        IrodsDataRequest.objects.all().delete()

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {'path': IRODS_FILE_PATH}

    def test_post(self):
        """Test IrodsDataRequestCreateAjaxView POST"""
        self.assert_response(
            self.url,
            self.good_users_write,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url,
            self.bad_users_write,
            403,
            method='POST',
            data=self.post_data,
        )
        self.project.set_public()
        self.assert_response(
            self.url,
            self.user_guest,
            403,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url, self.anonymous, 403, method='POST', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(
            self.url, self.anonymous, 403, method='POST', data=self.post_data
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(
            self.url,
            self.superuser,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url,
            self.non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )
        self.project.set_public()
        self.assert_response(
            self.url,
            self.user_guest,
            403,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url, self.anonymous, 403, method='POST', data=self.post_data
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(
            self.url,
            self.superuser,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url,
            self.non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(
            self.url,
            self.superuser,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url,
            self.non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )


class TestIrodsDataRequestDeleteAjaxView(
    IrodsDataRequestMixin, SampleSheetsAjaxPermissionTestBase
):
    """Permission tests for IrodsDataRequestDeleteAjaxView"""

    def _cleanup(self):
        self._make_request()

    def _make_request(self):
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=IRODS_FILE_PATH,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=self.user_contributor,
        )

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_irods_request_delete',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {'path': IRODS_FILE_PATH}
        self._make_request()

    def test_post(self):
        """Test IrodsDataRequestDeleteAjaxView POST"""
        good_users = [
            self.superuser,
            self.user_contributor,  # Request creator
        ]
        bad_users = [
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_owner,
            self.user_delegate,
            self.user_guest_cat,
            self.user_viewer_cat,
            self.user_finder_cat,
            self.user_guest,
            self.user_viewer,
            self.user_no_roles,
            self.anonymous,
        ]
        self.assert_response(
            self.url,
            good_users,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url, bad_users, 403, method='POST', data=self.post_data
        )
        self.project.set_public()
        self.assert_response(
            self.url,
            self.user_guest,
            403,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url, self.anonymous, 403, method='POST', data=self.post_data
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_post_anon(self):
        """Test POST with anonymous guest access"""
        self.project.set_public()
        self.assert_response(
            self.url, self.anonymous, 403, method='POST', data=self.post_data
        )

    def test_post_archive(self):
        """Test POST with archived project"""
        self.project.set_archive()
        self.assert_response(
            self.url,
            self.superuser,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url,
            self.non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )
        self.project.set_public()
        self.assert_response(
            self.url,
            self.user_guest,
            403,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url, self.anonymous, 403, method='POST', data=self.post_data
        )

    def test_post_block(self):
        """Test POST with project access block"""
        self.set_access_block(self.project)
        self.assert_response(
            self.url,
            self.superuser,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url,
            self.non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )

    def test_post_read_only(self):
        """Test POST with site read-only mode"""
        self.set_site_read_only()
        self.assert_response(
            self.url,
            self.superuser,
            200,
            method='POST',
            data=self.post_data,
            cleanup_method=self._cleanup,
        )
        self.assert_response(
            self.url,
            self.non_superusers,
            403,
            method='POST',
            data=self.post_data,
        )
