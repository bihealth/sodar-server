"""Tests for views in the samplesheets app"""

from test_plus.test import TestCase

from django.urls import reverse

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import Investigation
from .test_io import SampleSheetIOMixin, SHEET_DIR


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestViewsBase(
        TestCase, ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin):
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
        self.user = self.make_user('superuser')
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
        super(TestProjectSheetsView, self).setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_render(self):
        """Test rendering the project sheets view"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project.omics_uuid}))
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
                kwargs={'study': self.study.omics_uuid}))
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
                kwargs={'project': self.project.omics_uuid}))
            self.assertEqual(response.status_code, 200)

            # Assert context data
            self.assertIsNone(response.context['investigation'])
            self.assertNotIn('study', response.context)
            self.assertNotIn('table_data', response.context)


class TestProjectSheetsOverviewView(TestViewsBase):
    """Tests for the project sheets view"""

    def setUp(self):
        super(TestProjectSheetsOverviewView, self).setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_render(self):
        """Test rendering the project sheets overview view"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:overview',
                kwargs={'project': self.project.omics_uuid}))
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
                kwargs={'project': self.project.omics_uuid}))
            self.assertEqual(response.status_code, 200)

    # TODO: Test import POST


class TestSampleSheetTableExportView(TestViewsBase):
    """Tests for the sample sheet TSV export view"""

    def setUp(self):
        super(TestSampleSheetTableExportView, self).setUp()

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
                kwargs={'study': self.study.omics_uuid}))
            self.assertEqual(response.status_code, 200)

    def test_render_assay(self):
        """Test rendering the TSV file for a assay table"""
        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:export_tsv',
                kwargs={'assay': self.assay.omics_uuid}))
            self.assertEqual(response.status_code, 200)


class TestSampleSheetDeleteView(TestViewsBase):
    """Tests for the investigation delete view"""

    def setUp(self):
        super(TestSampleSheetDeleteView, self).setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()

    def test_render(self):
        """Test rendering the project sheets view"""

        with self.login(self.user):
            response = self.client.get(reverse(
                'samplesheets:delete',
                kwargs={'project': self.project.omics_uuid}))
            self.assertEqual(response.status_code, 200)

    def test_delete(self):
        """Test deleting the project sample sheets"""

        self.assertEqual(Investigation.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(reverse(
                'samplesheets:delete',
                kwargs={'project': self.project.omics_uuid}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse(
                'samplesheets:project_sheets',
                kwargs={'project': self.project.omics_uuid}))

        self.assertEqual(Investigation.objects.all().count(), 0)
