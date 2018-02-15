"""Tests for utils in the samplesheets app"""

from collections import OrderedDict
from isatools import isajson, isatab
import json
import os
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import Investigation
from ..io import import_isa, get_inv_file_name


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

    '''
    def _compare_isa_data(self, investigation, json_data):
        """Compare imported/exported ISA JSON data to Investigation"""

        def compare_process_seq(parent, json_parent):
            process = parent.get_first_process()

            for json_process in json_parent['processSequence']:
                self.assertEqual(process.api_id, json_process['@id'])
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
    '''

    def test_isa_batch(self):
        """Test ISAtab import in batch"""

        isa_dir = os.fsencode(os.path.dirname(__file__) + '/isatab/')
        print('\n')     # HACK for no newline for 1st entry with -v 2
        self.assertEqual(Investigation.objects.count(), 0)

        for file in sorted(
                [x for x in os.scandir(isa_dir) if x.is_file()],
                key=lambda x: x.name):
            with ZipFile(os.fsdecode(file.path)) as zf:
                with TemporaryDirectory() as temp_dir:
                    file_name = os.fsdecode(file.name)
                    print('Testing file {}'.format(file_name))
                    inv_file_name = get_inv_file_name(zf)
                    zf.extractall(temp_dir)
                    isa_data = None

                    # Parse ISAtab
                    try:
                        isa_data = isatab.load(temp_dir)

                    # ISA-API parsing fails -> give up, not our problem :)
                    except Exception as ex:
                        print('ISA-API parsing failed: {}'.format(ex))

                    if isa_data:
                        # Import isatools object structure into Django
                        investigation = import_isa(
                            isa_data, inv_file_name, self.project)
                        self.assertEqual(Investigation.objects.count(), 1)

                        # TODO: Test content
                        # TODO: Test export

                        investigation.delete()
                        self.assertEqual(Investigation.objects.count(), 0)
