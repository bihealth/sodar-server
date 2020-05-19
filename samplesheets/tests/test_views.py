"""Tests for UI views in the samplesheets app"""

import json
import os
from test_plus.test import TestCase
from zipfile import ZipFile

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.utils import build_secret

from samplesheets.io import SampleSheetIO
from samplesheets.models import Investigation, ISATab
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)
from samplesheets.tests.test_utils import CONFIG_PATH_DEFAULT

# App settings API
app_settings = AppSettingAPI()


# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = SODAR_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = SODAR_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = SODAR_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW'
]


# Local constants
SHEET_NAME = 'i_small.zip'
SHEET_PATH = SHEET_DIR + SHEET_NAME
SHEET_NAME_SMALL2 = 'i_small2.zip'
SHEET_PATH_SMALL2 = SHEET_DIR + SHEET_NAME_SMALL2
SHEET_NAME_MINIMAL = 'i_minimal.zip'
SHEET_PATH_MINIMAL = SHEET_DIR + SHEET_NAME_MINIMAL
SHEET_NAME_CRITICAL = 'BII-I-1_critical.zip'
SHEET_PATH_CRITICAL = SHEET_DIR_SPECIAL + SHEET_NAME_CRITICAL
SOURCE_NAME = '0815'
SOURCE_NAME_FAIL = 'oop5Choo'
USER_PASSWORD = 'password'
API_INVALID_VERSION = '9.9.9'
REMOTE_SITE_NAME = 'Test site'
REMOTE_SITE_URL = 'https://sodar.bihealth.org'
REMOTE_SITE_DESC = 'description'
REMOTE_SITE_SECRET = build_secret()
EDIT_NEW_VALUE_STR = 'edited value'

with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)

IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


class TestViewsBase(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Base view for samplesheets views tests"""

    def setUp(self):
        # Init roles
        self.role_owner = Role.objects.get_or_create(name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE
        )[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR
        )[0]
        self.role_guest = Role.objects.get_or_create(name=PROJECT_ROLE_GUEST)[0]

        # Init superuser
        self.user = self.make_user('superuser', password=USER_PASSWORD)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Init projects
        self.category = self._make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.owner_as = self._make_assignment(
            self.category, self.user, self.role_owner
        )
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner
        )


class TestProjectSheetsView(TestViewsBase):
    """Tests for the project sheets view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

    def test_render_no_sheets(self):
        """Test rendering the project sheets view without an investigation"""
        self.investigation.delete()
        self.investigation = None
        self.study = None

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

            # Assert context data
            self.assertIsNone(response.context['investigation'])
            self.assertNotIn('study', response.context)
            self.assertNotIn('tables', response.context)


class TestSampleSheetImportView(TestViewsBase):
    """Tests for the investigation import view"""

    def test_render(self):
        """Test rendering the investigation import view"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_post(self):
        """Test posting an ISAtab zip file in the import form"""

        # Assert preconditions
        self.assertEqual(Investigation.objects.all().count(), 0)
        self.assertEqual(ISATab.objects.all().count(), 0)

        with open(SHEET_PATH, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 1)

        isa_version = ISATab.objects.first()
        self.assertListEqual(isa_version.tags, ['IMPORT'])
        self.assertIsNotNone(isa_version.data['sheet_config'])
        self.assertIsNotNone(isa_version.data['display_config'])

    def test_post_replace(self):
        """Test replacing an existing investigation by posting"""
        inv = self._import_isa_from_file(SHEET_PATH, self.project)
        uuid = inv.sodar_uuid

        # Assert preconditions
        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 1)

        with open(SHEET_PATH_SMALL2, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(uuid, Investigation.objects.first().sodar_uuid)
        self.assertEqual(ISATab.objects.all().count(), 2)
        self.assertListEqual(
            ISATab.objects.all().order_by('-pk').first().tags,
            ['IMPORT', 'REPLACE'],
        )
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['sheet_config']
        )
        self.assertIsNotNone(
            ISATab.objects.all().order_by('-pk').first().data['display_config']
        )

    def test_post_replace_not_allowed(self):
        """Test replacing an iRODS-enabled investigation with missing data"""
        inv = self._import_isa_from_file(SHEET_PATH, self.project)
        inv.irods_status = True
        inv.save()
        uuid = inv.sodar_uuid

        # Assert precondition
        self.assertEqual(Investigation.objects.all().count(), 1)

        with open(SHEET_PATH_MINIMAL, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.all().count(), 1)
        new_inv = Investigation.objects.first()
        self.assertEqual(uuid, new_inv.sodar_uuid)  # Should not have changed

    def test_post_critical_warnings(self):
        """Test posting an ISAtab which raises critical warnings in altamISA"""
        timeline = get_backend_api('timeline_backend')

        # Assert precondition
        self.assertEqual(Investigation.objects.all().count(), 0)

        with open(SHEET_PATH_CRITICAL, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.all().count(), 0)

        # Assert timeline event
        tl_event = timeline.get_project_events(self.project).order_by('-pk')[0]
        tl_status = tl_event.get_current_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    @override_settings(SHEETS_ALLOW_CRITICAL=True)
    def test_post_critical_warnings_allowed(self):
        """Test posting an ISAtab with critical warnings allowed"""
        timeline = get_backend_api('timeline_backend')

        # Assert precondition
        self.assertEqual(Investigation.objects.all().count(), 0)

        with open(SHEET_PATH_CRITICAL, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(
                    reverse(
                        'samplesheets:import',
                        kwargs={'project': self.project.sodar_uuid},
                    ),
                    values,
                )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.all().count(), 1)

        # Assert timeline event
        tl_event = timeline.get_project_events(self.project).order_by('-pk')[0]
        tl_status = tl_event.get_current_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    def test_post_multiple(self):
        """Test posting an ISAtab as multiple files"""

        # Assert preconditions
        self.assertEqual(Investigation.objects.all().count(), 0)
        self.assertEqual(ISATab.objects.all().count(), 0)

        zf = ZipFile(os.fsdecode(SHEET_PATH))

        with self.login(self.user):
            values = {
                'file_upload': [
                    zf.open(f.filename) for f in zf.filelist if f.file_size > 0
                ]
            }
            response = self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 1)
        self.assertListEqual(ISATab.objects.first().tags, ['IMPORT'])

    def test_post_multiple_no_study(self):
        """Test posting an ISAtab as multiple files without required study"""

        # Assert preconditions
        self.assertEqual(Investigation.objects.all().count(), 0)
        self.assertEqual(ISATab.objects.all().count(), 0)

        zf = ZipFile(os.fsdecode(SHEET_PATH))

        with self.login(self.user):
            values = {
                'file_upload': [
                    zf.open(f.filename)
                    for f in zf.filelist
                    if f.file_size > 0
                    and not f.filename.split('/')[-1].startswith('s_')
                ]
            }
            response = self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Investigation.objects.all().count(), 0)

    def test_post_multiple_no_assay(self):
        """Test posting an ISAtab as multiple files without required assay"""

        # Assert preconditions
        self.assertEqual(Investigation.objects.all().count(), 0)
        self.assertEqual(ISATab.objects.all().count(), 0)

        zf = ZipFile(os.fsdecode(SHEET_PATH))

        with self.login(self.user):
            values = {
                'file_upload': [
                    zf.open(f.filename)
                    for f in zf.filelist
                    if f.file_size > 0
                    and not f.filename.split('/')[-1].startswith('a_')
                ]
            }
            response = self.client.post(
                reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                values,
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Investigation.objects.all().count(), 0)


class TestSampleSheetExcelExportView(TestViewsBase):
    """Tests for the sample sheet Excel export view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_render_study(self):
        """Test rendering the Excel file for a study table"""
        timeline = get_backend_api('timeline_backend')

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_excel',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

            # Assert data in timeline event
            tl_event = timeline.get_project_events(
                self.project, classified=True
            ).order_by('-pk')[0]
            self.assertEqual(tl_event.event_name, 'sheet_export_excel')

    def test_render_assay(self):
        """Test rendering the Excel file for a assay table"""
        timeline = get_backend_api('timeline_backend')

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_excel',
                    kwargs={'assay': self.assay.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

            # Assert data in timeline event
            tl_event = timeline.get_project_events(
                self.project, classified=True
            ).order_by('-pk')[0]
            self.assertEqual(tl_event.event_name, 'sheet_export_excel')


class TestSampleSheetISAExportView(TestViewsBase):
    """Tests for the investigation ISAtab export view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )

    def test_get(self):
        """Test requesting a file from the ISAtab export view"""
        timeline = get_backend_api('timeline_backend')

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_isa',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename="{}"'.format(self.investigation.archive_name),
        )

        # Assert data in timeline event
        tl_event = timeline.get_project_events(
            self.project, classified=True
        ).order_by('-pk')[0]
        tl_status = tl_event.get_current_status()
        self.assertIsNotNone(tl_status.extra_data['warnings'])

    def test_get_no_investigation(self):
        """Test requesting an ISAtab export with no investigation provided"""
        self.investigation.delete()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_isa',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 302)

    def test_get_version(self):
        """Test requesting export of an ISATab version"""
        isa_version = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )
        filename = (
            self.investigation.archive_name.split('.zip')[0]
            + '_'
            + isa_version.date_created.strftime('%Y-%m-%d_%H%M%S')
            + '.zip'
        )

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_isa',
                    kwargs={'isatab': isa_version.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename="{}"'.format(filename),
        )


class TestSampleSheetDeleteView(TestViewsBase):
    """Tests for the investigation delete view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

    def test_render(self):
        """Test rendering the project sheets view"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_delete(self):
        """Test deleting the project sample sheets"""

        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'delete_host_confirm': 'testserver'},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.url,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(Investigation.objects.all().count(), 0)
        self.assertEqual(ISATab.objects.all().count(), 0)

    def test_delete_invalid_host(self):
        """Test deleting with an invalid host name supplied in form"""

        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'delete_host_confirm': ''},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.url,
                reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': self.project.sodar_uuid},
                ),
            )

        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 1)


class TestSampleSheetVersionListView(TestViewsBase):
    """Tests for the sample sheet version list view"""

    def test_render(self):
        """Test rendering the sheet version list view"""
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:versions',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        # Assert context data
        self.assertEqual(response.context['object_list'].count(), 1)
        self.assertEqual(
            response.context['current_version'],
            ISATab.objects.filter(
                project=self.project,
                investigation_uuid=self.investigation.sodar_uuid,
            )
            .order_by('-date_created')
            .first(),
        )

    def test_render_no_sheets(self):
        """Test rendering the sheet version list view with no versions available"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:versions',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        # Assert context data
        self.assertEqual(response.context['object_list'].count(), 0)
        self.assertIsNone(response.context['current_version'])


class TestSampleSheetVersionRestoreView(TestViewsBase):
    """Tests for the sample sheet version restore view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )

    def test_render(self):
        """Test rendering the sheet version restore view"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:version_restore',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        # Assert context data
        self.assertIsNotNone(response.context['sheet_version'])

    def test_post(self):
        """Test issuing a POST request for the sheet version restore view"""
        sheet_io = SampleSheetIO()
        isatab_new = sheet_io.save_isa(
            project=self.project,
            inv_uuid=self.investigation.sodar_uuid,
            isa_data=sheet_io.export_isa(self.investigation),
        )

        # Assert preconditions
        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 2)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:version_restore',
                    kwargs={'isatab': isatab_new.sodar_uuid},
                )
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)

        isatab_latest = ISATab.objects.all().order_by('-date_created').first()
        self.assertNotEqual(
            isatab_latest.date_created, self.isatab.date_created
        )
        self.assertEqual(Investigation.objects.all().count(), 1)
        self.assertEqual(ISATab.objects.all().count(), 2)


class TestSampleSheetVersionDeleteView(TestViewsBase):
    """Tests for the sample sheet version delete view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.isatab = ISATab.objects.get(
            investigation_uuid=self.investigation.sodar_uuid
        )

    def test_render(self):
        """Test rendering the sheet version delete view"""

        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:version_delete',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        # Assert context data
        self.assertIsNotNone(response.context['sheet_version'])

    def test_post(self):
        """Test issuing a POST request for the sheet version delete view"""
        self.assertEqual(ISATab.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:version_delete',
                    kwargs={'isatab': self.isatab.sodar_uuid},
                )
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ISATab.objects.all().count(), 0)
