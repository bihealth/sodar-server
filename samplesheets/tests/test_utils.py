"""Tests for utils in the samplesheets app"""

from collections import OrderedDict
from isatools import isajson
import json
import os
from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import Investigation
from ..utils import import_isa, export_isa


class TestSampleSheetUtils(TestCase, ProjectMixin, RoleAssignmentMixin):
    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', OMICS_CONSTANTS['PROJECT_TYPE_PROJECT'], None)
        self.role_owner = Role.objects.get_or_create(
            name=OMICS_CONSTANTS['PROJECT_ROLE_OWNER'])[0]
        self.role_delegate = Role.objects.get_or_create(
            name=OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE'])[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner)

    def test_json_batch(self):
        """Test ISA JSON import and export in batch"""
        json_dir = os.fsencode(os.path.dirname(__file__) + '/isa_json/')
        print('\n')     # HACK for no newline for 1st entry with -v 2
        self.assertEqual(Investigation.objects.count(), 0)

        for file in sorted(
                [x for x in os.scandir(json_dir) if x.is_file()],
                key=lambda x: x.name):
            with open(file.path, 'r') as f:
                file_name = os.fsdecode(file.name)
                print('Testing file "{}"'.format(file_name))

                json_data = json.loads(f.read(), object_pairs_hook=OrderedDict)

                # Validate input just in case
                isa_report = isajson.validate(json_data)

                self.assertEqual(len(isa_report['errors']), 0)
                self.assertEqual(
                    isa_report['validation_finished'], True)

                # Import JSON into Django
                investigation = import_isa(json_data, file_name, self.project)
                self.assertEqual(Investigation.objects.count(), 1)

                # Export Django model into JSON data
                export_data = export_isa(investigation)

                # Validate export
                isa_report = isajson.validate(export_data)
                self.assertEqual(len(isa_report['errors']), 0)
                self.assertEqual(
                    isa_report['validation_finished'], True)

                investigation.delete()
                self.assertEqual(Investigation.objects.count(), 0)
