"""Tests for management commands in the samplesheets app"""

from django.core.management import call_command

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.models import GenericMaterial
from samplesheets.tests.test_io import (
    SampleSheetIOMixin,
    SHEET_DIR,
    SHEET_DIR_SPECIAL,
)
from samplesheets.utils import get_alt_names


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'
SHEET_PATH_ALT = SHEET_DIR + 'i_small2.zip'
ALT_NAMES_INVALID = ['XXX', 'YYY', 'ZZZ']


class TestSyncnamesCommand(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Tests for the syncnames command"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner
        )

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

        # Clear alt names from imported materials
        for m in GenericMaterial.objects.all():
            m.alt_names = ALT_NAMES_INVALID
            m.save()

    def test_command(self):
        """Test syncnames command"""
        for m in GenericMaterial.objects.all():
            self.assertEqual(m.alt_names, ALT_NAMES_INVALID)
        call_command('syncnames')
        for m in GenericMaterial.objects.all():
            self.assertEqual(m.alt_names, get_alt_names(m.name))
