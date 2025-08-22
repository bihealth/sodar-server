"""Tests for plugins in the samplesheets app with Taskflow enabled"""

import os

from irods.ticket import Ticket

from django.forms.models import model_to_dict
from django.test import RequestFactory, override_settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint, PluginAPI

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase, IRODS_GROUP_PUBLIC

from samplesheets.plugins import IRODS_STATS_CACHE_NAME, EMPTY_IRODS_STATS
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import (
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
)
from samplesheets.views import MISC_FILES_COLL


app_settings = AppSettingAPI()
plugin_api = PluginAPI()


# SODAR constants
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']
APP_SETTING_SCOPE_PROJECT = SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'
TEST_OBJ_NAME = 'test1.txt'


class SamplesheetsModifyAPITestMixin:
    """
    Mixin with test helpers for the samplesheets project modify API
    implementation.
    """

    def assert_ticket_access(self, project, expected=True, ticket_str=None):
        """
        Assert ticket access in the SODAR database and iRODS.

        :param project: Project object
        :param expected: Boolean
        :param ticket_str: Ticket ID string or None. If None, it is read from
                           app settings.
        """
        if not ticket_str:
            ticket_str = app_settings.get(
                APP_NAME, 'public_access_ticket', project=project
            )
        ticket = self.irods_backend.get_ticket(self.irods, ticket_str)
        if expected:
            self.assertIsNotNone(ticket)
            self.assertEqual(type(ticket), Ticket)
        else:
            self.assertIsNone(ticket)


class SamplesheetsPluginTaskflowTestBase(
    SamplesheetsModifyAPITestMixin,
    SampleSheetIOMixin,
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
    TaskflowViewTestBase,
):
    """Base class for samplesheets plugin tests with taskflow and iRODS"""

    def _set_up_investigation(self):
        """Set up investigation with iRODS collections"""
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        self.sample_path = self.irods_backend.get_sample_path(self.project)


class TestPerformProjectModify(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.perform_project_modify()"""

    def setUp(self):
        super().setUp()
        self._set_up_investigation()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')
        # Create dummy request
        self.req_factory = RequestFactory()
        self.request = self.req_factory.get('/')
        self.request.user = self.user

    def test_grant_public_access_guest(self):
        """Test enabling guest access in iRODS without anon accesss"""
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)
        self.project.set_public_access(self.role_guest)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={'parent': self.category, 'public_access': None},
            request=self.request,
        )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, self.irods_access_read
        )
        # Access should not be granted
        self.assert_ticket_access(self.project, False)

    def test_grant_public_access_viewer(self):
        """Test enabling viewer access in iRODS without anon accesss"""
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)
        self.project.set_public_access(self.role_viewer)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={'parent': self.category, 'public_access': None},
            request=self.request,
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_grant_public_access_anon_guest(self):
        """Test enabling anonymous guest access to project in iRODS"""
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)
        self.project.set_public_access(self.role_guest)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={'parent': self.category, 'public_access': None},
            request=self.request,
        )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, self.irods_access_read
        )
        # Access should be granted for anonymous
        self.assert_ticket_access(self.project, True)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_grant_public_access_anon_viewer(self):
        """Test enabling anonymous viewer access to project in iRODS"""
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)
        self.project.set_public_access(self.role_viewer)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={'parent': self.category, 'public_access': None},
            request=self.request,
        )
        # No public group access for viewer
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        # Access should not be granted to viewer
        self.assert_ticket_access(self.project, False)

    def test_revoke_public_access_guest(self):
        """Test revoking public guest access with no anon access"""
        self.project.set_public_access(self.role_guest)
        with override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True):
            self.plugin.perform_project_modify(
                project=self.project,
                action=PROJECT_ACTION_UPDATE,
                project_settings=app_settings.get_all_by_scope(
                    APP_SETTING_SCOPE_PROJECT, project=self.project
                ),
                old_data={'parent': self.category, 'public_access': None},
                request=self.request,
            )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, self.irods_access_read
        )
        self.assert_ticket_access(self.project, True)
        ticket_str = app_settings.get(
            APP_NAME, 'public_access_ticket', project=self.project
        )

        self.project.set_public_access(None)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={
                'parent': self.category,
                'public_access': self.role_guest.name,
            },
            old_settings={
                'settings.samplesheets.public_access_ticket': ticket_str
            },
            request=self.request,
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False, ticket_str)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_revoke_public_access_guest_anon(self):
        """Test revoking public guest access with anon access"""
        self.project.set_public_access(self.role_guest)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={'parent': self.category, 'public_access': None},
            request=self.request,
        )
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, self.irods_access_read
        )
        self.assert_ticket_access(self.project, True)
        ticket_str = app_settings.get(
            APP_NAME, 'public_access_ticket', project=self.project
        )

        self.project.set_public_access(None)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={
                'parent': self.category,
                'public_access': self.role_guest.name,
            },
            old_settings={
                'settings.samplesheets.public_access_ticket': ticket_str
            },
            request=self.request,
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False, ticket_str)

    def test_revoke_public_access_viewer(self):
        """Test revoking public viewer access with no anon access"""
        self.project.set_public_access(self.role_viewer)
        with override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True):
            self.plugin.perform_project_modify(
                project=self.project,
                action=PROJECT_ACTION_UPDATE,
                project_settings=app_settings.get_all_by_scope(
                    APP_SETTING_SCOPE_PROJECT, project=self.project
                ),
                old_data={'parent': self.category, 'public_access': None},
                request=self.request,
            )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)

        self.project.set_public_access(None)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={
                'parent': self.category,
                'public_access': self.role_viewer.name,
            },
            request=self.request,
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_revoke_public_access_viewer_anon(self):
        """Test revoking public viewer access with anon access"""
        self.project.set_public_access(self.role_viewer)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={'parent': self.category, 'public_access': None},
            request=self.request,
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)

        self.project.set_public_access(None)
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_by_scope(
                APP_SETTING_SCOPE_PROJECT, project=self.project
            ),
            old_data={
                'parent': self.category,
                'public_access': self.role_viewer.name,
            },
            request=self.request,
        )
        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assert_ticket_access(self.project, False)


class TestPerformProjectSync(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.perform_project_sync()"""

    def setUp(self):
        super().setUp()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')

    def test_sync(self):
        """Test perform_project_sync()"""
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )
        self.plugin.perform_project_sync(self.project)
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )

    def test_sync_colls(self):
        """Test perform_project_sync() with iRODS collections"""
        self.assertEqual(self.irods.collections.exists(self.sample_path), False)
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )

        # Import investigation and sync
        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        investigation.irods_status = True
        investigation.save()
        self.plugin.perform_project_sync(self.project)

        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )

    def test_sync_public_access(self):
        """Test sync with public access and anon site access disabled"""
        self.project.set_public_access(self.role_guest)
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )

        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.make_irods_colls(investigation)
        self.plugin.perform_project_sync(self.project)

        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, self.irods_access_read
        )
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_access_anon(self):
        """Test sync with public access and anon site access enabled"""
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )

        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.make_irods_colls(investigation)
        self.project.set_public_access(self.role_guest)
        self.plugin.perform_project_sync(self.project)

        self.assertEqual(self.irods.collections.exists(self.sample_path), True)
        self.assert_irods_access(
            IRODS_GROUP_PUBLIC, self.sample_path, self.irods_access_read
        )
        ticket_str = app_settings.get(
            APP_NAME, 'public_access_ticket', self.project
        )
        self.assertNotEqual(ticket_str, '')
        self.assert_ticket_access(self.project, True, ticket_str)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_access_anon_revoke(self):
        """Test revoking public access with anon site access enabled"""
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )

        investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.make_irods_colls(investigation)
        # NOTE: Project.public_access = None
        ticket_new = self.irods_backend.issue_ticket(
            self.irods, 'read', self.sample_path
        )
        ticket_str = ticket_new.string
        app_settings.set(
            APP_NAME, 'public_access_ticket', ticket_str, self.project
        )
        self.plugin.perform_project_sync(self.project)

        self.assert_irods_access(IRODS_GROUP_PUBLIC, self.sample_path, None)
        self.assertEqual(
            app_settings.get(APP_NAME, 'public_access_ticket', self.project),
            '',
        )
        self.assert_ticket_access(self.project, False, ticket_str)


class TestUpdateIrodsStatsCache(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.update_irods_stats_cache()"""

    def setUp(self):
        super().setUp()
        self._set_up_investigation()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self.cache_args = [
            self.project,
            self.irods_backend,
            self.cache_backend,
            self.irods,
            self.user,
        ]

    def test_update_irods_stats_cache(self):
        """Test update_irods_stats_cache() with no file in project"""
        res = self.plugin.update_irods_stats_cache(*self.cache_args)
        expected = {
            'id': res.pk,
            'project': self.project.pk,
            'app_name': APP_NAME,
            'name': IRODS_STATS_CACHE_NAME.format(uuid=self.project.sodar_uuid),
            'user': self.user.pk,
            'sodar_uuid': res.sodar_uuid,
            'data': EMPTY_IRODS_STATS,
        }
        self.assertEqual(model_to_dict(res), expected)

    def test_update_irods_stats_cache_file(self):
        """Test update_irods_stats_cache() with file in project"""
        misc_coll = self.irods.collections.create(
            os.path.join(self.sample_path, MISC_FILES_COLL)
        )
        irods_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        res = self.plugin.update_irods_stats_cache(*self.cache_args)
        self.assertEqual(res.data, {'file_count': 1, 'total_size': 1024})

    def test_update_irods_stats_no_coll(self):
        """Test update_irods_stats_cache() with no sample collection"""
        self.irods.collections.remove(self.sample_path)
        res = self.plugin.update_irods_stats_cache(*self.cache_args)
        self.assertEqual(res.data, EMPTY_IRODS_STATS)

    def test_update_irods_stats_cache_existing(self):
        """Test update_irods_stats_cache() with existing item"""
        self.cache_backend.set_cache_item(
            app_name=APP_NAME,
            name=IRODS_STATS_CACHE_NAME.format(uuid=self.project.sodar_uuid),
            data=EMPTY_IRODS_STATS,
            project=self.project,
            user=self.user,
        )
        misc_coll = self.irods.collections.create(
            os.path.join(self.sample_path, MISC_FILES_COLL)
        )
        irods_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        res = self.plugin.update_irods_stats_cache(*self.cache_args)
        self.assertEqual(res.data, {'file_count': 1, 'total_size': 1024})


# TODO: Add tests for ProjectAppPlugin.update_assay_shortcut_cache()
# TODO: Add tests for ProjectAppPlugin.update_cache()


class TestGetCategoryStats(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.get_category_stats()"""

    def setUp(self):
        super().setUp()
        self._set_up_investigation()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')

    # NOTE: For sample count tests, see test_plugins

    def test_get_category_stats(self):
        """Test get_category_stats()"""
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0].title, 'Samples')
        self.assertEqual(res[1].title, 'Files')
        self.assertEqual(res[1].value, 0)
        self.assertEqual(res[1].unit, None)
        self.assertEqual(res[2].title, 'Data')
        self.assertEqual(res[2].value, 0)
        self.assertEqual(res[2].unit, 'bytes')

    def test_get_category_stats_file(self):
        """Test get_category_stats() with file in project"""
        misc_coll = self.irods.collections.create(
            os.path.join(self.sample_path, MISC_FILES_COLL)
        )
        irods_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(res[1].value, 1)
        self.assertEqual(res[1].unit, None)
        self.assertEqual(res[2].value, 1)
        self.assertEqual(res[2].unit, 'KB')
