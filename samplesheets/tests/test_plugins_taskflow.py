"""Tests for plugins in the samplesheets app with Taskflow enabled"""

from datetime import timedelta
from typing import Optional

from irods.models import TicketQuery
from irods.path import iRODSPath
from irods.ticket import Ticket

from django.forms.models import model_to_dict
from django.test import RequestFactory, override_settings
from django.utils import timezone

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, AppSetting, SODAR_CONSTANTS
from projectroles.plugins import ProjectAppPluginPoint, PluginAPI

# Taskflowbackend dependency
from taskflowbackend.constants import IRODS_ACCESS_READ_OBJ
from taskflowbackend.tests.base import TaskflowViewTestBase, IRODS_GROUP_PUBLIC

from samplesheets.models import IrodsAccessTicket
from samplesheets.plugins import (
    IRODS_STATS_CACHE_NAME,
    EMPTY_IRODS_STATS,
    ASSAY_SHORTCUT_CACHE_NAME,
)
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import IrodsAccessTicketMixin
from samplesheets.tests.test_views_taskflow import (
    SampleSheetPublicAccessMixin,
    SampleSheetTaskflowMixin,
)
from samplesheets.views import MISC_FILES_COLL, RESULTS_COLL, TRACK_HUBS_COLL

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
TICKET_MODE_READ = 'read'
SUB_COLL = 'sub_coll'
HUB_COLL = 'hub1'


class SamplesheetsModifyAPITestMixin:
    """
    Mixin with test helpers for the samplesheets project modify API
    implementation.
    """

    def assert_ticket_access(
        self,
        project: Project,
        expected: bool = True,
        ticket_str: Optional[str] = None,
    ):
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
        self.plugin = ProjectAppPluginPoint.get_plugin('samplesheets')


class TestPerformProjectModify(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.perform_project_modify()"""

    def setUp(self):
        super().setUp()
        self._set_up_investigation()
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
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
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
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
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
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
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
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
        )
        self.assert_ticket_access(self.project, True)
        ticket_str = app_settings.get(
            APP_NAME, 'public_access_ticket', project=self.project
        )
        self.assertNotEqual(ticket_str, '')

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
        # AppSetting object should still exist but with an empty value
        s_ticket = AppSetting.objects.get(
            name='public_access_ticket', project=self.project
        )
        self.assertEqual(s_ticket.value, '')

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


class TestPerformProjectSync(
    IrodsAccessTicketMixin, SamplesheetsPluginTaskflowTestBase
):
    """Tests for ProjectAppPlugin.perform_project_sync()"""

    def _get_ticket_res(
        self, ticket_str: str, include_obj: bool = False
    ) -> dict:
        """Return iRODS database ticket query result"""
        q_args = [TicketQuery.Ticket]
        if include_obj:
            q_args.append(TicketQuery.DataObject)
        query = self.irods.query(*q_args).filter(
            TicketQuery.Ticket.string == ticket_str
        )
        return list(query)[0]

    def _get_host_res(self, ticket_id) -> list:
        """Return iRODS database ticket allowed hosts query result"""
        query = self.irods.query(TicketQuery.AllowedHosts).filter(
            TicketQuery.AllowedHosts.ticket_id == ticket_id
        )
        return list(query)

    def _setup_investigation_irods(self, project: Optional[Project] = None):
        """
        Setup investigation with iRODS collections and an additional MiscFiles
        collection.

        :param project: Project object (optional, default=self.project)
        """
        if not project:
            project = self.project
        self.investigation = self.import_isa_from_file(SHEET_PATH, project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.make_irods_colls(self.investigation)
        self.misc_path = iRODSPath(
            self.irods_backend.get_path(self.assay), MISC_FILES_COLL
        )
        self.misc_coll = self.irods.collections.create(self.misc_path)

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
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
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
            IRODS_GROUP_PUBLIC, self.sample_path, IRODS_ACCESS_READ_OBJ
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

    def test_sync_ticket_sodar(self):
        """Test sync with iRODS access ticket in SODAR"""
        self._setup_investigation_irods()
        # Make ticket in SODAR only
        db_ticket = self.make_irods_ticket(
            self.study, self.assay, self.misc_path
        )
        self.assertIsNone(
            self.irods_backend.get_ticket(self.irods, db_ticket.ticket)
        )
        self.plugin.perform_project_sync(self.project)

        self.assertIsNotNone(
            self.irods_backend.get_ticket(self.irods, db_ticket.ticket)
        )
        ticket_res = self._get_ticket_res(db_ticket.ticket)
        self.assertEqual(ticket_res[TicketQuery.Ticket.type], TICKET_MODE_READ)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

    def test_sync_ticket_sodar_expiry_date(self):
        """Test sync with iRODS access ticket in SODAR and expiry date"""
        self._setup_investigation_irods()
        expiry_date = timezone.now() + timedelta(days=1)
        db_ticket = self.make_irods_ticket(
            self.study, self.assay, self.misc_path, date_expires=expiry_date
        )
        self.assertIsNone(
            self.irods_backend.get_ticket(self.irods, db_ticket.ticket)
        )
        self.plugin.perform_project_sync(self.project)
        ticket_res = self._get_ticket_res(db_ticket.ticket)
        self.assertEqual(
            int(ticket_res[TicketQuery.Ticket.expiry_ts]),
            int(expiry_date.timestamp()),
        )

    def test_sync_ticket_sodar_hosts(self):
        """Test sync with iRODS access ticket in SODAR and allowed hosts"""
        self._setup_investigation_irods()
        db_ticket = self.make_irods_ticket(
            self.study, self.assay, self.misc_path, allowed_hosts=['127.0.0.1']
        )
        self.assertIsNone(
            self.irods_backend.get_ticket(self.irods, db_ticket.ticket)
        )
        self.plugin.perform_project_sync(self.project)
        self.assertIsNotNone(
            self.irods_backend.get_ticket(self.irods, db_ticket.ticket)
        )
        ticket_res = self._get_ticket_res(db_ticket.ticket)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 1)
        self.assertEqual(
            host_res[0][TicketQuery.AllowedHosts.host], '127.0.0.1'
        )

    def test_sync_ticket_sodar_obj(self):
        """Test sync with iRODS access ticket in SODAR for data object"""
        self._setup_investigation_irods()
        data_obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        # Make ticket in SODAR only
        db_ticket = self.make_irods_ticket(
            self.study, self.assay, data_obj.path
        )
        self.assertIsNone(
            self.irods_backend.get_ticket(self.irods, db_ticket.ticket)
        )
        self.plugin.perform_project_sync(self.project)

        self.assertIsNotNone(
            self.irods_backend.get_ticket(self.irods, db_ticket.ticket)
        )
        ticket_res = self._get_ticket_res(db_ticket.ticket, include_obj=True)
        self.assertEqual(
            ticket_res[TicketQuery.DataObject.coll], self.misc_path
        )
        self.assertEqual(ticket_res[TicketQuery.DataObject.name], TEST_OBJ_NAME)

    def test_sync_ticket_irods(self):
        """Test sync with iRODS access ticket in iRODS"""
        self._setup_investigation_irods()
        # Make ticket in iRODS only
        i_ticket = self.irods_backend.issue_ticket(
            self.irods, TICKET_MODE_READ, self.misc_path
        )
        ts = i_ticket.string
        self.assertIsNone(IrodsAccessTicket.objects.filter(ticket=ts).first())
        self.assertIsNotNone(self.irods_backend.get_ticket(self.irods, ts))
        self.plugin.perform_project_sync(self.project)
        # Neither SODAR ticket nor iRODS ticket should exist
        self.assertIsNone(IrodsAccessTicket.objects.filter(ticket=ts).first())
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, ts))

    def test_sync_ticket_irods_other_project(self):
        """Test sync with iRODS access ticket in iRODS in other project"""
        project2, _ = self.make_project_taskflow(
            'TestProject2', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        self._setup_investigation_irods()  # self.project
        self._setup_investigation_irods(project2)
        # Make ticket in iRODS only for project2
        i_ticket = self.irods_backend.issue_ticket(
            self.irods, TICKET_MODE_READ, self.misc_path
        )
        ts = i_ticket.string
        self.assertIsNone(IrodsAccessTicket.objects.filter(ticket=ts).first())
        self.assertIsNotNone(self.irods_backend.get_ticket(self.irods, ts))
        # Sync self.project
        self.plugin.perform_project_sync(self.project)
        # iRODS ticket should still exist
        self.assertIsNotNone(self.irods_backend.get_ticket(self.irods, ts))

    def test_sync_ticket_irods_obj(self):
        """Test sync with iRODS access ticket in iRODS for data object"""
        self._setup_investigation_irods()
        data_obj = self.make_irods_object(self.misc_coll, TEST_OBJ_NAME)
        i_ticket = self.irods_backend.issue_ticket(
            self.irods, TICKET_MODE_READ, data_obj.path
        )
        ts = i_ticket.string
        self.assertIsNone(IrodsAccessTicket.objects.filter(ticket=ts).first())
        self.assertIsNotNone(self.irods_backend.get_ticket(self.irods, ts))
        self.plugin.perform_project_sync(self.project)
        self.assertIsNone(IrodsAccessTicket.objects.filter(ticket=ts).first())
        self.assertIsNone(self.irods_backend.get_ticket(self.irods, ts))

    def test_sync_ticket_both(self):
        """Test sync with ticket in SODAR and iRODS with no changes"""
        self._setup_investigation_irods()
        db_ticket = self.make_irods_ticket(
            self.study, self.assay, self.misc_path
        )
        ts = db_ticket.ticket
        self.irods_backend.issue_ticket(
            self.irods, TICKET_MODE_READ, self.misc_path, ticket_str=ts
        )
        self.assertIsNotNone(
            IrodsAccessTicket.objects.filter(ticket=ts).first()
        )
        self.assertIsNotNone(self.irods_backend.get_ticket(self.irods, ts))
        self.plugin.perform_project_sync(self.project)
        # Both SODAR and iRODS tickets should be unchanged
        self.assertIsNotNone(
            IrodsAccessTicket.objects.filter(ticket=ts).first()
        )
        self.assertIsNotNone(self.irods_backend.get_ticket(self.irods, ts))
        ticket_res = self._get_ticket_res(ts)
        self.assertEqual(ticket_res[TicketQuery.Ticket.type], TICKET_MODE_READ)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)

    def test_sync_ticket_both_expiry_date(self):
        """Test sync with ticket in SODAR and iRODS with changed expiry date"""
        self._setup_investigation_irods()
        expiry_date = timezone.now() + timedelta(days=1)
        db_ticket = self.make_irods_ticket(
            self.study, self.assay, self.misc_path, date_expires=expiry_date
        )
        ts = db_ticket.ticket
        # Create without expiry date
        self.irods_backend.issue_ticket(
            self.irods, TICKET_MODE_READ, self.misc_path, ticket_str=ts
        )
        ticket_res = self._get_ticket_res(ts)
        self.assertEqual(ticket_res[TicketQuery.Ticket.expiry_ts], None)
        self.plugin.perform_project_sync(self.project)
        ticket_res = self._get_ticket_res(ts)
        self.assertEqual(
            int(ticket_res[TicketQuery.Ticket.expiry_ts]),
            int(expiry_date.timestamp()),
        )

    def test_sync_ticket_both_hosts(self):
        """Test sync with ticket in SODAR and iRODS with changed allowed hosts"""
        self._setup_investigation_irods()
        db_ticket = self.make_irods_ticket(
            self.study, self.assay, self.misc_path, allowed_hosts=['127.0.0.1']
        )
        ts = db_ticket.ticket
        # Create without allowed hosts
        self.irods_backend.issue_ticket(
            self.irods, TICKET_MODE_READ, self.misc_path, ticket_str=ts
        )
        ticket_res = self._get_ticket_res(ts)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 0)
        self.plugin.perform_project_sync(self.project)
        host_res = self._get_host_res(ticket_res[TicketQuery.Ticket.id])
        self.assertEqual(len(host_res), 1)
        self.assertEqual(
            host_res[0][TicketQuery.AllowedHosts.host], '127.0.0.1'
        )


class TestUpdateIrodsStatsCache(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.update_irods_stats_cache()"""

    def setUp(self):
        super().setUp()
        self._set_up_investigation()
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
            iRODSPath(self.sample_path, MISC_FILES_COLL)
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
            iRODSPath(self.sample_path, MISC_FILES_COLL)
        )
        irods_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        res = self.plugin.update_irods_stats_cache(*self.cache_args)
        self.assertEqual(res.data, {'file_count': 1, 'total_size': 1024})


class TestUpdateAssayShortcutCache(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.update_assay_shortcut_cache()"""

    def _get_cache_item(self):
        """Return cache item for self.assay or None if not found"""
        return self.cache_backend.get_cache_item(
            app_name=APP_NAME,
            name=ASSAY_SHORTCUT_CACHE_NAME.format(uuid=self.assay.sodar_uuid),
            project=self.project,
        )

    def _update_shortcut_cache(self):
        """Call update_assay_shortcut_cache() on self.assay"""
        self.plugin.update_assay_shortcut_cache(
            self.assay,
            self.irods_backend,
            self.cache_backend,
            self.irods,
            self.user,
        )

    def setUp(self):
        super().setUp()
        self.cache_backend = plugin_api.get_backend_api('sodar_cache')
        self._set_up_investigation()
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.misc_path = iRODSPath(self.assay_path, MISC_FILES_COLL)
        self.res_path = iRODSPath(self.assay_path, RESULTS_COLL)
        self.track_hub_root_path = iRODSPath(self.assay_path, TRACK_HUBS_COLL)
        self.track_hub_path = iRODSPath(self.track_hub_root_path, HUB_COLL)

    def test_update_no_colls(self):
        """Test update_assay_shortcut_cache() with no shortcut colls"""
        self.assertEqual(self.irods.collections.exists(self.assay_path), True)
        self.assertEqual(self.irods.collections.exists(self.misc_path), False)
        self.assertEqual(self.irods.collections.exists(self.res_path), False)
        self.assertEqual(self._get_cache_item(), None)
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        self.assertIsNotNone(cache_item)
        expected = {
            'results_reports': False,
            'misc_files': False,
            'track_hubs': [],
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)

    def test_update_empty_coll(self):
        """Test update_assay_shortcut_cache() with empty shortcut coll"""
        self.irods.collections.create(self.misc_path)
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        expected = {
            'results_reports': False,
            'misc_files': False,  # Empty coll, should still be false
            'track_hubs': [],
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)

    def test_update_empty_sub_coll(self):
        """Test update_assay_shortcut_cache() with empty subcoll"""
        self.irods.collections.create(iRODSPath(self.misc_path, SUB_COLL))
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        expected = {
            'results_reports': False,
            'misc_files': False,  # Empty subcoll, should still be false
            'track_hubs': [],
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)

    def test_update_file(self):
        """Test update_assay_shortcut_cache() with file in shortcut coll"""
        misc_coll = self.irods.collections.create(self.misc_path)
        self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        expected = {
            'results_reports': False,
            'misc_files': True,  # Data object in coll, should be True
            'track_hubs': [],
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)

    def test_update_file_subcoll(self):
        """Test update_assay_shortcut_cache() with file in subcoll"""
        sub_coll = self.irods.collections.create(
            iRODSPath(self.misc_path, SUB_COLL)
        )
        self.make_irods_object(sub_coll, TEST_OBJ_NAME)
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        expected = {
            'results_reports': False,
            'misc_files': True,  # Data object in subcoll, should be True
            'track_hubs': [],
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)

    def test_update_track_hub_empty_root(self):
        """Test update_assay_shortcut_cache() with empty track hub root coll"""
        self.irods.collections.create(self.track_hub_root_path)
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        expected = {
            'results_reports': False,
            'misc_files': False,
            'track_hubs': [],  # Should be empty
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)

    def test_update_track_hub_empty(self):
        """Test update_assay_shortcut_cache() with empty track hub coll"""
        self.irods.collections.create(self.track_hub_path)
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        expected = {
            'results_reports': False,
            'misc_files': False,
            'track_hubs': [],  # Should be empty
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)

    def test_update_track_hub_file(self):
        """Test update_assay_shortcut_cache() with file in track hub coll"""
        hub_coll = self.irods.collections.create(self.track_hub_path)
        self.make_irods_object(hub_coll, TEST_OBJ_NAME)
        self._update_shortcut_cache()
        cache_item = self._get_cache_item()
        expected = {
            'results_reports': False,
            'misc_files': False,
            'track_hubs': [self.track_hub_path],  # Track hub should show up
        }
        self.assertEqual(cache_item.data['shortcuts'], expected)


# TODO: Add tests for ProjectAppPlugin.update_cache()


class TestGetCategoryStats(SamplesheetsPluginTaskflowTestBase):
    """Tests for ProjectAppPlugin.get_category_stats()"""

    def setUp(self):
        super().setUp()
        self._set_up_investigation()

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
            iRODSPath(self.sample_path, MISC_FILES_COLL)
        )
        irods_obj = self.make_irods_object(misc_coll, TEST_OBJ_NAME)
        self.make_checksum_object(irods_obj)
        res = self.plugin.get_category_stats(self.category)
        self.assertEqual(res[1].value, 1)
        self.assertEqual(res[1].unit, None)
        self.assertEqual(res[2].value, 1)
        self.assertEqual(res[2].unit, 'KB')
