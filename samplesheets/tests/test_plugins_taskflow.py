"""Tests for plugins in the samplesheets app with Taskflow enabled"""

from irods.ticket import Ticket
from unittest import skipIf

from django.test import RequestFactory, override_settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint

# Taskflowbackend dependency
from taskflowbackend.tests.test_project_views import (
    TestTaskflowBase,
    BACKENDS_ENABLED,
    BACKEND_SKIP_MSG,
)

from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
)
from samplesheets.tests.test_views_taskflow import (
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
)


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']

# Local constants
APP_NAME = 'samplesheets'
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestSamplesheetsModifyAPIMixin:
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
            ticket_str = app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', project=project
            )
        ticket = self.irods_backend.get_ticket(ticket_str)
        if expected:
            self.assertIsNotNone(ticket)
            self.assertEqual(type(ticket), Ticket)
        else:
            self.assertIsNone(ticket)


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestPerformProjectModify(
    TestSamplesheetsModifyAPIMixin,
    SampleSheetIOMixin,
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
    TestTaskflowBase,
):
    """Tests for perform_project_modify()"""

    def setUp(self):
        super().setUp()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')

        # Make project with owner in Taskflow without public guest access
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
            public_guest_access=False,
        )
        self.project_path = self.irods_backend.get_sample_path(self.project)
        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)

        # Create dummy request
        self.req_factory = RequestFactory()
        self.request = self.req_factory.get('/')
        self.request.user = self.user

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_grant_public_access_anon(self):
        """Test enabling anonymous guest access to project in iRODS"""
        self.assert_ticket_access(self.project, False)
        self.project.public_guest_access = True
        self.project.save()
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_settings(self.project),
            old_data={'parent': self.category},
            request=self.request,
        )
        self.assert_ticket_access(self.project, True)

    def test_grant_public_access_no_anon(self):
        """Test enabling guest access in iRODS without anon accesss"""
        self.assert_ticket_access(self.project, False)
        self.project.public_guest_access = True
        self.project.save()
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_settings(self.project),
            old_data={'parent': self.category},
            request=self.request,
        )
        # Access should not be granted
        self.assert_ticket_access(self.project, False)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_revoke_public_access_anon(self):
        """Test revoking anonymous guest access to project from iRODS"""
        self.project.public_guest_access = True
        self.project.save()
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_settings(self.project),
            old_data={'parent': self.category},
            request=self.request,
        )
        self.assert_ticket_access(self.project, True)
        ticket_str = app_settings.get_app_setting(
            APP_NAME, 'public_access_ticket', project=self.project
        )

        self.project.public_guest_access = False
        self.project.save()
        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_settings(self.project),
            old_data={'parent': self.category},
            old_settings={
                'settings.samplesheets.public_access_ticket': ticket_str
            },
            request=self.request,
        )
        self.assert_ticket_access(self.project, False, ticket_str)

    def test_revoke_anon_access(self):
        """Test revoking iRODS guest access if anon site access is disabled"""
        self.project.public_guest_access = True
        self.project.save()

        with override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True):
            self.plugin.perform_project_modify(
                project=self.project,
                action=PROJECT_ACTION_UPDATE,
                project_settings=app_settings.get_all_settings(self.project),
                old_data={'parent': self.category},
                request=self.request,
            )
        self.assert_ticket_access(self.project, True)
        ticket_str = app_settings.get_app_setting(
            APP_NAME, 'public_access_ticket', project=self.project
        )

        self.plugin.perform_project_modify(
            project=self.project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_settings(self.project),
            old_data={'parent': self.category},
            old_settings={
                'settings.samplesheets.public_access_ticket': ticket_str
            },
            request=self.request,
        )
        self.assert_ticket_access(self.project, False, ticket_str)


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestPerformProjectSync(
    TestSamplesheetsModifyAPIMixin,
    SampleSheetIOMixin,
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
    TestTaskflowBase,
):
    """Tests for perform_project_sync()"""

    def setUp(self):
        super().setUp()
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
            public_guest_access=False,
        )
        self.project_path = self.irods_backend.get_sample_path(self.project)

    def test_sync(self):
        """Test perform_project_sync()"""
        self.assertEqual(
            self.irods_session.collections.exists(self.project_path), False
        )
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )
        self.plugin.perform_project_sync(self.project)
        self.assertEqual(
            self.irods_session.collections.exists(self.project_path), False
        )
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )

    def test_sync_colls(self):
        """Test perform_project_sync() with iRODS collections"""
        self.assertEqual(
            self.irods_session.collections.exists(self.project_path), False
        )
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )

        # Import investigation and sync
        investigation = self._import_isa_from_file(SHEET_PATH, self.project)
        investigation.irods_status = True
        investigation.save()
        self.plugin.perform_project_sync(self.project)

        self.assertEqual(
            self.irods_session.collections.exists(self.project_path), True
        )
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )

    def test_sync_public_access(self):
        """Test sync with public access and anon site access disabled"""
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )

        investigation = self._import_isa_from_file(SHEET_PATH, self.project)
        self.make_irods_colls(investigation)
        self.plugin.perform_project_sync(self.project)

        self.assertEqual(
            self.irods_session.collections.exists(self.project_path), True
        )
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_access_anon(self):
        """Test sync with public access and anon site access enabled"""
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )

        investigation = self._import_isa_from_file(SHEET_PATH, self.project)
        self.make_irods_colls(investigation)
        self.project.public_guest_access = True
        self.project.save()
        self.plugin.perform_project_sync(self.project)

        self.assertEqual(
            self.irods_session.collections.exists(self.project_path), True
        )
        ticket_str = app_settings.get_app_setting(
            APP_NAME, 'public_access_ticket', self.project
        )
        self.assertNotEqual(ticket_str, '')
        self.assert_ticket_access(self.project, True, ticket_str)

    @override_settings(PROJECTROLES_ALLOW_ANONYMOUS=True)
    def test_sync_public_access_anon_revoke(self):
        """Test revoking public access with anon site access enabled"""
        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )

        investigation = self._import_isa_from_file(SHEET_PATH, self.project)
        self.make_irods_colls(investigation)
        # NOTE: Project.public_guest_access = False
        ticket_new = self.irods_backend.issue_ticket('read', self.project_path)
        ticket_str = ticket_new.string
        app_settings.set_app_setting(
            APP_NAME, 'public_access_ticket', ticket_str, self.project
        )
        self.plugin.perform_project_sync(self.project)

        self.assertEqual(
            app_settings.get_app_setting(
                APP_NAME, 'public_access_ticket', self.project
            ),
            '',
        )
        self.assert_ticket_access(self.project, False, ticket_str)
