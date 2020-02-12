"""Tests for views in the samplesheets app"""
import json
import os
from test_plus.test import TestCase
from unittest import skipIf
from zipfile import ZipFile

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleAssignmentMixin,
    RemoteSiteMixin,
    RemoteProjectMixin,
)
from projectroles.utils import build_secret

# Timeline dependency
from timeline.models import ProjectEvent

from samplesheets.io import SampleSheetIO
from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    GenericMaterial,
    Protocol,
    Process,
    ISATab,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)
from samplesheets.tests.test_utils import (
    SheetConfigMixin,
    CONFIG_PATH_DEFAULT,
    CONFIG_STUDY_UUID,
)
from samplesheets.utils import build_sheet_config


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
                )
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
        self.assertEqual(response.context['sheet_versions'].count(), 1)
        self.assertEqual(
            response.context['current_version'],
            response.context['sheet_versions'][0],
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
        self.assertIsNone(response.context['sheet_versions'])
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


class TestInvestigationRetrieveAPIView(TestViewsBase):
    """Tests for InvestigationRetrieveAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test get() in InvestigationRetrieveAPIView"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_investigation_retrieve',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        expected = {
            'sodar_uuid': str(self.investigation.sodar_uuid),
            'identifier': self.investigation.identifier,
            'file_name': self.investigation.file_name,
            'project': str(self.project.sodar_uuid),
            'title': self.investigation.title,
            'description': self.investigation.description,
            'irods_status': False,
            'parser_version': self.investigation.parser_version,
            'archive_name': self.investigation.archive_name,
            'comments': self.investigation.comments,
            'studies': {
                str(self.study.sodar_uuid): {
                    'identifier': self.study.identifier,
                    'file_name': self.study.file_name,
                    'title': self.study.title,
                    'description': self.study.description,
                    'comments': self.study.comments,
                    'assays': {
                        str(self.assay.sodar_uuid): {
                            'file_name': self.assay.file_name,
                            'technology_platform': self.assay.technology_platform,
                            'technology_type': self.assay.technology_type,
                            'measurement_type': self.assay.measurement_type,
                            'comments': self.assay.comments,
                        }
                    },
                }
            },
        }
        self.assertEqual(response.data, expected)


# TODO: Test with realistic ISAtab examples using BIH configs (see #434)
@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestContextGetAPIView(TestViewsBase):
    """Tests for SampleSheetContextGetAPIView"""

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods')

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test context retrieval with example sheet"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_context_get',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        response_data.pop('csrf_token')  # HACK

        expected = {
            'configuration': self.investigation.get_configuration(),
            'inv_file_name': self.investigation.file_name.split('/')[-1],
            'irods_status': False,
            'parser_version': self.investigation.parser_version,
            'irods_backend_enabled': True if self.irods_backend else False,
            'parser_warnings': True
            if self.investigation.parser_warnings
            else False,
            'irods_webdav_enabled': settings.IRODS_WEBDAV_ENABLED,
            'irods_webdav_url': settings.IRODS_WEBDAV_URL,
            'external_link_labels': settings.SHEETS_EXTERNAL_LINK_LABELS,
            'table_height': settings.SHEETS_TABLE_HEIGHT,
            'min_col_width': settings.SHEETS_MIN_COLUMN_WIDTH,
            'max_col_width': settings.SHEETS_MAX_COLUMN_WIDTH,
            'allow_editing': app_settings.get_default_setting(
                'samplesheets', 'allow_editing'
            ),
            'alerts': [],
            'investigation': {
                'identifier': self.investigation.identifier,
                'title': self.investigation.title,
                'description': None,
                'comments': None,
            },
            'studies': {
                str(self.study.sodar_uuid): {
                    'display_name': self.study.get_display_name(),
                    'description': self.study.description,
                    'comments': self.study.comments,
                    'irods_path': self.irods_backend.get_path(self.study),
                    'table_url': response.wsgi_request.build_absolute_uri(
                        reverse(
                            'samplesheets:api_study_tables_get',
                            kwargs={'study': str(self.study.sodar_uuid)},
                        )
                    ),
                    'plugin': None,
                    'assays': {
                        str(self.assay.sodar_uuid): {
                            'name': self.assay.get_name(),
                            'display_name': self.assay.get_display_name(),
                            'irods_path': self.irods_backend.get_path(
                                self.assay
                            ),
                            'display_row_links': True,
                            'plugin': None,
                        }
                    },
                }
            },
            'perms': {
                'edit_sheet': True,
                'manage_sheet': True,
                'create_dirs': True,
                'export_sheet': True,
                'delete_sheet': True,
                'is_superuser': True,
            },
            'sheet_stats': {
                'study_count': Study.objects.filter(
                    investigation=self.investigation
                ).count(),
                'assay_count': Assay.objects.filter(
                    study__investigation=self.investigation
                ).count(),
                'protocol_count': Protocol.objects.filter(
                    study__investigation=self.investigation
                ).count(),
                'process_count': Process.objects.filter(
                    protocol__study__investigation=self.investigation
                ).count(),
                'source_count': self.investigation.get_material_count('SOURCE'),
                'material_count': self.investigation.get_material_count(
                    'MATERIAL'
                ),
                'sample_count': self.investigation.get_material_count('SAMPLE'),
                'data_count': self.investigation.get_material_count('DATA'),
            },
        }
        self.assertEqual(response_data, expected)


# TODO: Test with realistic ISAtab examples using BIH configs (see #434)
class TestStudyTablesGetAPIView(TestViewsBase):
    """Tests for SampleSheetStudyTablesGetAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Allow sample sheet editing in project
        app_settings.set_app_setting(
            'samplesheets', 'allow_editing', True, project=self.project
        )

    def test_get(self):
        """Test study tables retrieval"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_study_tables_get',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        # Assert return data correctness
        ret_data = response.data
        self.assertIn('study', ret_data)
        self.assertIn('tables', ret_data)
        self.assertNotIn('render_error', ret_data)
        self.assertNotIn('shortcuts', ret_data['tables']['study'])
        self.assertEqual(len(ret_data['tables']['assays']), 1)
        self.assertNotIn(
            'uuid', ret_data['tables']['study']['table_data'][0][0]
        )

    def test_get_edit(self):
        """Test study tables retrieval with edit mode enabled"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_study_tables_get',
                    kwargs={'study': self.study.sodar_uuid},
                ),
                {'edit': 1},
            )

        self.assertEqual(response.status_code, 200)

        # Assert return data correctness
        ret_data = response.data
        self.assertIn('study', ret_data)
        self.assertIn('tables', ret_data)
        self.assertNotIn('render_error', ret_data)
        self.assertNotIn('shortcuts', ret_data['tables']['study'])
        self.assertEqual(len(ret_data['tables']['assays']), 1)
        self.assertIn('uuid', ret_data['tables']['study']['table_data'][0][0])
        self.assertIn('study_config', ret_data)


# TODO: Test with realistic ISAtab examples using BIH configs (see #434)
class TestStudyLinksGetAPIView(TestViewsBase):
    """Tests for SampleSheetStudyLinksGetAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test study links retrieval without plugin"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_study_links_get',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 404)  # No plugin for test ISAtab


# TODO: Test with realistic ISAtab examples using BIH configs (see #434)
class TestSampleSheetWarningsGetAPIView(TestViewsBase):
    """Tests for SampleSheetWarningsGetAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )

    def test_get(self):
        """Test study tables retrieval"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:api_warnings_get',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['warnings'], self.investigation.parser_warnings
        )


# TODO: Test with multiple cells
# TODO: Test with realistic ISAtab examples using BIH configs (see #434)
# TODO: Add helper to create update data
# TODO: Test all value types
# TODO: Unify tests once saving a list of values is implemented
class TestSampleSheetEditPostAPIView(TestViewsBase):
    """Tests for SampleSheetEditPostAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

        # Set up POST data
        self.values = {'updated_cells': []}

    def test_edit_characteristics_str(self):
        """Test editing a characteristics string value in a material"""
        obj = GenericMaterial.objects.get(study=self.study, name='0816')
        header_name = 'organism'

        # Assert preconditions
        self.assertNotEqual(
            obj.characteristics[header_name], EDIT_NEW_VALUE_STR
        )

        # TODO: Add complete set of params once they have been refactored
        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': header_name,
                'header_type': 'characteristics',
                'obj_cls': 'GenericMaterial',
                'value': EDIT_NEW_VALUE_STR,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:api_edit_post',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Asert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(
            obj.characteristics[header_name],
            {'unit': None, 'value': EDIT_NEW_VALUE_STR},
        )

    def test_edit_param_values_str(self):
        """Test editing a parameter values string value in a process"""
        obj = Process.objects.filter(study=self.study, assay=None).first()
        header_name = 'instrument'

        # Assert preconditions
        self.assertNotEqual(
            obj.parameter_values[header_name], EDIT_NEW_VALUE_STR
        )

        # TODO: Add complete set of params once they have been refactored
        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': header_name,
                'header_type': 'parameter_values',
                'obj_cls': 'Process',
                'value': EDIT_NEW_VALUE_STR,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:api_edit_post',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Asert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(
            obj.parameter_values[header_name],
            {'unit': None, 'value': EDIT_NEW_VALUE_STR},
        )


class TestSampleSheetEditFinishAPIView(TestViewsBase):
    """Tests for SampleSheetEditFinishAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

    def test_post(self):
        """Test POST with updates=True"""
        # Assert preconditions
        self.assertEqual(ISATab.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:api_edit_finish',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps({'updated': True}),
                content_type='application/json',
            )

        # Asert postconditions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ISATab.objects.all().count(), 2)

    def test_post_no_updates(self):
        """Test POST with updates=False"""
        # Assert preconditions
        self.assertEqual(ISATab.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:api_edit_finish',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps({'updated': False}),
                content_type='application/json',
            )

        # Asert postconditions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ISATab.objects.all().count(), 1)


# TODO: Test with assay updates (needs a better test ISAtab)
class TestSampleSheetManagePostAPIView(SheetConfigMixin, TestViewsBase):
    """Tests for SampleSheetManagePostAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        # Set up UUIDs and default config
        self._update_uuids(self.investigation, CONFIG_DATA_DEFAULT)
        app_settings.set_app_setting(
            'samplesheets',
            'sheet_config',
            build_sheet_config(self.investigation),
            project=self.project,
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_post_update_study_column(self):
        """Test posting a study column update"""

        # Assert preconditions
        sheet_config = app_settings.get_app_setting(
            'samplesheets', 'sheet_config', project=self.project
        )
        self.assertEqual(sheet_config, CONFIG_DATA_DEFAULT)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project,
                app='samplesheets',
                event_name='field_update',
            ).count(),
            0,
        )

        values = {
            'fields': [
                {
                    'action': 'update',
                    'study': CONFIG_STUDY_UUID,
                    'assay': None,
                    'node_idx': 0,
                    'field_idx': 2,
                    'config': {
                        'name': 'age',
                        'type': 'characteristics',
                        'editable': True,
                        'format': 'integer',
                        'range': [None, None],
                        'regex': '',
                        'default': '',
                        'unit': ['day'],
                        'unit_default': 'day',
                    },
                }
            ]
        }

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:api_manage_post',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)

        sheet_config = app_settings.get_app_setting(
            'samplesheets', 'sheet_config', project=self.project
        )
        expected = {
            'name': 'age',
            'type': 'characteristics',
            'editable': True,
            'format': 'integer',
            'regex': '',
            'default': '',
            'unit': ['day'],
            'unit_default': 'day',
        }
        self.assertEqual(
            sheet_config['studies'][CONFIG_STUDY_UUID]['nodes'][0]['fields'][2],
            expected,
        )
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project,
                app='samplesheets',
                event_name='field_update',
            ).count(),
            1,
        )


class TestRemoteSheetGetAPIView(
    RemoteSiteMixin, RemoteProjectMixin, TestViewsBase
):
    """Tests for RemoteSheetGetAPIView"""

    def setUp(self):
        super().setUp()

        # Create target site
        self.target_site = self._make_site(
            name=REMOTE_SITE_NAME,
            url=REMOTE_SITE_URL,
            mode=SODAR_CONSTANTS['SITE_MODE_TARGET'],
            description=REMOTE_SITE_DESC,
            secret=REMOTE_SITE_SECRET,
        )

        # Create target project
        self.target_project = self._make_remote_project(
            project_uuid=self.project.sodar_uuid,
            site=self.target_site,
            level=SODAR_CONSTANTS['REMOTE_LEVEL_READ_ROLES'],
        )

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

    def test_get_tables(self):
        """Test getting the investigation as rendered tables"""
        response = self.client.get(
            reverse(
                'samplesheets:api_remote_get',
                kwargs={
                    'project': self.project.sodar_uuid,
                    'secret': REMOTE_SITE_SECRET,
                },
            )
        )

        tb = SampleSheetTableBuilder()
        expected = {
            'studies': {
                str(self.study.sodar_uuid): tb.build_study_tables(self.study)
            }
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)

    def test_get_isatab(self):
        """Test getting the investigation as ISAtab"""
        response = self.client.get(
            reverse(
                'samplesheets:api_remote_get',
                kwargs={
                    'project': self.project.sodar_uuid,
                    'secret': REMOTE_SITE_SECRET,
                },
            ),
            {'isa': '1'},
        )

        sheet_io = SampleSheetIO()
        expected = sheet_io.export_isa(self.investigation)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)
