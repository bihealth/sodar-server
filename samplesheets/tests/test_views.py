"""Tests for views in the samplesheets app"""

from test_plus.test import TestCase

from django.urls import reverse

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.tests.test_views import KnoxAuthMixin

from ..models import Investigation
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
    'SUBMIT_STATUS_PENDING_TASKFLOW']


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


class TestViewsBase(
        ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase):
    """Base view for samplesheets views tests"""

    def setUp(self):
        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init superuser
        self.user = self.make_user('superuser', password=USER_PASSWORD)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Init projects
        self.category = self._make_project(
            'TestCategory', PROJECT_TYPE_CATEGORY, None)
        self.owner_as = self._make_assignment(
            self.category, self.user, self.role_owner)
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, self.category)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)


class TestProjectSheetsView(TestViewsBase):
    """Tests for the project sheets view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_render(self):
        """Test rendering the project sheets view"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)

            # Assert context data
            self.assertIsNotNone(response.context['study'])
            self.assertEquals(response.context['study'].pk, self.study.pk)
            self.assertIsNotNone(response.context['table_data'])

    def test_render_study_id(self):
        """Test rendering the project sheets view with a study UUID"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:project_sheets',
                kwargs={'study': self.study.sodar_uuid}))
            self.assertEqual(response.status_code, 200)

            # Assert context data
            self.assertIsNotNone(response.context['investigation'])
            self.assertIsNotNone(response.context['study'])
            self.assertEquals(response.context['study'].pk, self.study.pk)
            self.assertIsNotNone(response.context['table_data'])

    def test_render_no_sheets(self):
        """Test rendering the project sheets view without an investigation"""
        self.investigation.delete()
        self.investigation = None
        self.study = None

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)

            # Assert context data
            self.assertIsNone(response.context['investigation'])
            self.assertNotIn('study', response.context)
            self.assertNotIn('table_data', response.context)


class TestProjectSheetsOverviewView(TestViewsBase):
    """Tests for the project sheets view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_render(self):
        """Test rendering the project sheets overview view"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:overview',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)

            # Assert context data
            self.assertIsNotNone(response.context['investigation'])
            self.assertNotIn('study', response.context)
            self.assertIsNotNone(response.context['sheet_stats'])


class TestSampleSheetImportView(TestViewsBase):
    """Tests for the investigation import view"""

    def test_render(self):
        """Test rendering the project sheets view"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:import',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)

    def test_post(self):
        """Test posting an ISAtab zip file in the import form"""

        # Assert precondition
        self.assertEqual(Investigation.objects.all().count(), 0)

        with open(SHEET_PATH, 'rb') as file:
            with self.login(self.user):
                values = {'file_upload': file}
                response = self.client.post(reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid}), values)

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
                response = self.client.post(reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid}), values)

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
                response = self.client.post(reverse(
                    'samplesheets:import',
                    kwargs={'project': self.project.sodar_uuid}), values)

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
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_render_study(self):
        """Test rendering the TSV file for a study table"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:export_tsv',
                kwargs={'study': self.study.sodar_uuid}))
            self.assertEqual(response.status_code, 200)

    def test_render_assay(self):
        """Test rendering the TSV file for a assay table"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:export_tsv',
                kwargs={'assay': self.assay.sodar_uuid}))
            self.assertEqual(response.status_code, 200)


class TestSampleSheetDeleteView(TestViewsBase):
    """Tests for the investigation delete view"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_render(self):
        """Test rendering the project sheets view"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:delete',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 200)

    def test_delete(self):
        """Test deleting the project sample sheets"""

        self.assertEqual(Investigation.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(reverse(
                'samplesheets:delete',
                kwargs={'project': self.project.sodar_uuid}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project.sodar_uuid}))

        self.assertEqual(Investigation.objects.all().count(), 0)


class TestSourceIDQueryAPIView(KnoxAuthMixin, TestViewsBase):
    """Tests for SourceIDQueryAPIView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)

        # Login with Knox
        self.token = self.knox_login(self.user, USER_PASSWORD)

    def test_get(self):
        """Test HTTP GET request with an existing ID"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME}),
            token=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id_found'], True)

    def test_get_not_found(self):
        """Test HTTP GET request with a non-existing ID"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME_FAIL}),
            token=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id_found'], False)

    def test_get_partial_id(self):
        """Test HTTP GET request with a partial ID (should fail)"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME[:-1]}),
            token=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id_found'], False)

    def test_get_unauthorized(self):
        """Test HTTP GET request without a token (should fail)"""
        response = self.client.get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME[:-1]}))
        self.assertEqual(response.status_code, 401)

    def test_get_wrong_version(self):
        """Test HTTP GET request with an unaccepted API version (should fail)"""
        response = self.knox_get(
            reverse(
                'samplesheets:source_get',
                kwargs={'source_id': SOURCE_NAME}),
            token=self.token,
            version=API_INVALID_VERSION)
        self.assertEqual(response.status_code, 406)
