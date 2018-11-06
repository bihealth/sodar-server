"""Tests for samplesheets.io"""

import os
from zipfile import ZipFile

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import Investigation
from ..io import import_isa


# Local constants
SHEET_DIR = os.path.dirname(__file__) + '/isatab/'


class SampleSheetIOMixin:
    """Helper functions for sample sheet i/o"""

    @classmethod
    def _import_isa_from_file(cls, path, project):
        """
        Import ISA from a zip file
        :param path: Path to zip file in the file system
        :param project: Project object
        :return: Investigation object
        """
        zf = ZipFile(os.fsdecode(path))
        investigation = import_isa(zf, project)
        investigation.active = True     # Must set this explicitly
        investigation.save()
        return investigation


class TestSampleSheetIO(
        ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase):
    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None)
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER'])[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner)

    def test_isa_batch(self):
        """Test ISAtab import in batch"""

        print('\n')     # HACK for no newline for 1st entry with -v 2
        self.assertEqual(Investigation.objects.count(), 0)

        for file in sorted(
                [x for x in os.scandir(SHEET_DIR) if x.is_file()],
                key=lambda x: x.name):
            print('Testing file {}'.format(os.fsdecode(file.name)))
            investigation = self._import_isa_from_file(file.path, self.project)

            self.assertEqual(Investigation.objects.count(), 1)

            # TODO: Compare content

            investigation.delete()
            self.assertEqual(Investigation.objects.count(), 0)
