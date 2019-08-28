"""Tests for views in the samplesheets app"""
import json

from test_plus.test import TestCase
from unittest import skipIf

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.tests.test_views import KnoxAuthMixin

from ..models import Investigation, Study, Assay, Protocol, Process
from .test_io import SampleSheetIOMixin, SHEET_DIR


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
SOURCE_NAME = '0815'
SOURCE_NAME_FAIL = 'oop5Choo'
USER_PASSWORD = 'password'
API_INVALID_VERSION = '5.0'

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
            self.assertNotIn('table_data', response.context)


class TestSampleSheetImportView(TestViewsBase):
    """Tests for the investigation import view"""

    def test_render(self):
        """Test rendering the project sheets view"""

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

        # Assert precondition
        self.assertEqual(Investigation.objects.all().count(), 0)

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

    def test_post_replace(self):
        """Test replacing an existing investigation by posting"""
        inv = self._import_isa_from_file(SHEET_PATH, self.project)
        uuid = inv.sodar_uuid

        # Assert precondition
        self.assertEqual(Investigation.objects.all().count(), 1)

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
        new_inv = Investigation.objects.first()
        self.assertEqual(uuid, new_inv.sodar_uuid)

    def test_post_replace_not_allowed(self):
        """Test replacing an iRODS-enabled investigation with missing studies or assays"""
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


class TestSampleSheetTableExportView(TestViewsBase):
    """Tests for the sample sheet TSV export view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_render_study(self):
        """Test rendering the TSV file for a study table"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_tsv',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_render_assay(self):
        """Test rendering the TSV file for a assay table"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:export_tsv',
                    kwargs={'assay': self.assay.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)


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
        self.maxDiff = None
        expected = {
            'configuration': self.investigation.get_configuration(),
            'inv_file_name': self.investigation.file_name.split('/')[-1],
            'irods_status': False,
            'parser_version': self.investigation.parser_version,
            'irods_backend_enabled': True
            if get_backend_api('omics_irods')
            else False,
            'parser_warnings': True
            if self.investigation.parser_warnings
            else False,
            'irods_webdav_enabled': settings.IRODS_WEBDAV_ENABLED,
            'irods_webdav_url': settings.IRODS_WEBDAV_URL,
            'external_link_labels': settings.SHEETS_EXTERNAL_LINK_LABELS,
            'table_height': settings.SHEETS_TABLE_HEIGHT,
            'min_col_width': settings.SHEETS_MIN_COLUMN_WIDTH,
            'max_col_width': settings.SHEETS_MAX_COLUMN_WIDTH,
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
        self.assertEqual(json.loads(response.data), expected)


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
        self.assertIn('table_data', ret_data)
        self.assertNotIn('render_error', ret_data)
        self.assertNotIn('shortcuts', ret_data['table_data']['study'])
        self.assertEqual(len(ret_data['table_data']['assays']), 1)


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


class TestSourceIDQueryAPIView(KnoxAuthMixin, TestViewsBase):
    """Tests for SourceIDQueryAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )

        # Login with Knox
        self.token = self.knox_login(self.user, USER_PASSWORD)

    def test_get(self):
        """Test HTTP GET request with an existing ID"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get', kwargs={'source_id': SOURCE_NAME}
            ),
            token=self.token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id_found'], True)

    def test_get_not_found(self):
        """Test HTTP GET request with a non-existing ID"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME_FAIL},
            ),
            token=self.token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id_found'], False)

    def test_get_partial_id(self):
        """Test HTTP GET request with a partial ID (should fail)"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME[:-1]},
            ),
            token=self.token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id_found'], False)

    def test_get_unauthorized(self):
        """Test HTTP GET request without a token (should fail)"""
        response = self.client.get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME[:-1]},
            )
        )
        self.assertEqual(response.status_code, 401)

    def test_get_wrong_version(self):
        """Test HTTP GET request with an unaccepted API version (should fail)"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get', kwargs={'source_id': SOURCE_NAME}
            ),
            token=self.token,
            version=API_INVALID_VERSION,
        )
        self.assertEqual(response.status_code, 406)
