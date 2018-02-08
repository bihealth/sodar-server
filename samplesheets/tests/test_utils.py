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
from ..utils import import_isa_json, export_isa_json


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

    def _compare_isa_data(self, investigation, json_data):
        """Compare imported/exported ISA JSON data to Investigation"""

        def compare_process_seq(parent, json_parent):
            process = parent.get_first_process()

            for json_process in json_parent['processSequence']:
                self.assertEqual(process.json_id, json_process['@id'])
                self.assertEqual(
                    process.inputs.all().count(), len(json_process['inputs']))
                self.assertEqual(
                    process.outputs.all().count(), len(json_process['outputs']))

                if hasattr(process, 'next_process') and process.next_process:
                    process = process.next_process

        self.assertEqual(
            investigation.studies.all().count(), len(json_data['studies']))

        # Studies
        for json_study in json_data['studies']:
            study = investigation.studies.get(
                identifier=json_study['identifier'])

            # Protocols
            self.assertEqual(
                study.protocols.all().count(), len(json_study['protocols']))

            # Materials
            self.assertEqual(
                study.materials.filter(item_type='SOURCE').count(),
                len(json_study['materials']['sources']))

            self.assertEqual(
                study.materials.filter(item_type='SAMPLE').count(),
                len(json_study['materials']['samples']))

            self.assertEqual(
                study.materials.filter(item_type='MATERIAL').count(),
                len(json_study['materials']['otherMaterials']))

            # Processes
            compare_process_seq(study, json_study)

            # Assays
            self.assertEqual(
                study.assays.all().count(), len(json_study['assays']))

            for json_assay in json_study['assays']:
                assay = study.assays.get(file_name=json_assay['filename'])

                self.assertEqual(
                    assay.materials.filter(item_type='MATERIAL').count(),
                    len(json_assay['materials']['otherMaterials']))

                self.assertEqual(
                    assay.materials.filter(item_type='DATA').count(),
                    len(json_assay['dataFiles']))

                # Processes
                compare_process_seq(assay, json_assay)

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
                investigation = import_isa_json(json_data, file_name, self.project)
                self.assertEqual(Investigation.objects.count(), 1)

                # Check investigation content
                self._compare_isa_data(investigation, json_data)

                # Export Django model into JSON data
                json_data = export_isa_json(investigation)

                # Check exported data content
                self._compare_isa_data(investigation, json_data)

                # Validate export
                isa_report = isajson.validate(json_data)
                self.assertEqual(len(isa_report['errors']), 0)
                self.assertEqual(
                    isa_report['validation_finished'], True)

                investigation.delete()
                self.assertEqual(Investigation.objects.count(), 0)
