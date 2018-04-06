"""Tests for samplesheets.io"""

import os
from zipfile import ZipFile

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import Investigation
from ..io import import_isa


class TestSampleSheetIO(TestCase, ProjectMixin, RoleAssignmentMixin):
    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', OMICS_CONSTANTS['PROJECT_TYPE_PROJECT'], None)
        self.role_owner = Role.objects.get_or_create(
            name=OMICS_CONSTANTS['PROJECT_ROLE_OWNER'])[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner)

    def test_isa_batch(self):
        """Test ISAtab import in batch"""

        isa_dir = os.fsencode(os.path.dirname(__file__) + '/isatab/')
        print('\n')     # HACK for no newline for 1st entry with -v 2
        self.assertEqual(Investigation.objects.count(), 0)

        for file in sorted(
                [x for x in os.scandir(isa_dir) if x.is_file()],
                key=lambda x: x.name):
            print('Testing file {}'.format(os.fsdecode(file.name)))

            zf = ZipFile(os.fsdecode(file.path))
            investigation = import_isa(zf, self.project)

            self.assertEqual(Investigation.objects.count(), 1)

            # TODO: Compare content
            # TODO: Test export

            investigation.delete()
            self.assertEqual(Investigation.objects.count(), 0)
