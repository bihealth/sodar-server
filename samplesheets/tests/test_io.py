"""Tests for samplesheets.io"""

from altamisa.isatab import (
    InvestigationReader,
    StudyReader,
    AssayReader,
    models as isa_models,
)
import csv
import io
import os
import warnings
from zipfile import ZipFile

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.models import Investigation, ISATab
from samplesheets.io import SampleSheetIO


# Local constants
SHEET_DIR = os.path.dirname(__file__) + '/isatab/'
SHEET_DIR_SPECIAL = os.path.dirname(__file__) + '/isatab_special/'
SHEET_NAME = 'BII-I-1_edited.zip'
SHEET_PATH = SHEET_DIR + SHEET_NAME


class SampleSheetIOMixin:
    """Helper functions for sample sheet i/o"""

    @classmethod
    def _import_isa_from_file(cls, path, project, user=None):
        """
        Import ISA from a zip file.

        :param path: Path to zip file
        :param project: Project object
        :param user: User object or None
        :return: Investigation object
        """
        sheet_io = SampleSheetIO(warn=False, allow_critical=True)
        zf = ZipFile(os.fsdecode(path))
        investigation = sheet_io.import_isa(
            sheet_io.get_isa_from_zip(zf),
            project,
            archive_name=zf.filename,
            user=user,
        )
        investigation.active = True  # Must set this explicitly
        investigation.save()
        return investigation

    @classmethod
    def _read_isa(cls, path, project):
        """
        Read ISA-Tab into the altamISA API

        :param path: Path to zip file
        :param project: Project object
        :return: InvestigationInfo, dict[path: Study], dict[path: Assay]
        """
        sheet_io = SampleSheetIO(warn=False, allow_critical=True)
        zf = ZipFile(os.fsdecode(path))
        inv_file_path = sheet_io.get_inv_paths(zf)[0]
        inv_dir = '/'.join(inv_file_path.split('/')[:-1])

        # Read investigation
        input_file = sheet_io.get_import_file(zf, inv_file_path)

        with warnings.catch_warnings(record=True):
            isa_inv = InvestigationReader.from_stream(
                input_file=input_file
            ).read()

        # Read studies
        isa_studies = {}
        isa_assays = {}
        study_count = 0
        assay_count = 0

        # Read studies
        for study_info in isa_inv.studies:
            study_id = 'p{}-s{}'.format(project.pk, study_count)

            with warnings.catch_warnings(record=True):
                isa_studies[
                    str(study_info.info.path)
                ] = StudyReader.from_stream(
                    input_file=sheet_io.get_import_file(
                        zf,
                        sheet_io._get_zip_path(inv_dir, study_info.info.path),
                    ),
                    study_id=study_id,
                ).read()

            # Read studies for assay
            assay_paths = sorted([a.path for a in study_info.assays])

            for assay_path in assay_paths:
                isa_assay = next(
                    (
                        a_i
                        for a_i in study_info.assays
                        if a_i.path == assay_path
                    ),
                    None,
                )
                assay_id = 'a{}'.format(assay_count)

                with warnings.catch_warnings(record=True):
                    isa_assays[str(assay_path)] = AssayReader.from_stream(
                        study_id=study_id,
                        assay_id=assay_id,
                        input_file=sheet_io.get_import_file(
                            zf, sheet_io._get_zip_path(inv_dir, isa_assay.path)
                        ),
                    ).read()

                assay_count += 1

            study_count += 1

        return isa_inv, isa_studies, isa_assays

    @classmethod
    def _get_isatab_files(cls):
        """
        Return all test ISA-Tab files.

        :return: Dict
        """
        return {
            os.fsdecode(file.name): file
            for file in sorted(
                [x for x in os.scandir(SHEET_DIR) if x.is_file()],
                key=lambda x: x.name,
            )
        }

    def _fail_isa(self, zip_name, ex):
        """Fail with exception message and ISA-Tab zip file name"""
        self.fail('Exception in {}: {}'.format(zip_name, ex))


class TestSampleSheetIOBase(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
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

    @classmethod
    def _get_flat_export_data(cls, export_data):
        """Return export ISA data as a flat list"""
        ret = {
            export_data['investigation']['path'].split('/')[-1]: export_data[
                'investigation'
            ]['tsv']
        }
        for k, v in export_data['studies'].items():
            ret[k] = v['tsv']
        for k, v in export_data['assays'].items():
            ret[k] = v['tsv']
        return ret


class TestSampleSheetIOBatch(TestSampleSheetIOBase):
    """Batch import/export tests for sample sheets"""

    def test_isa_import_batch(self):
        """Test ISA-Tab import in batch"""
        self.assertEqual(Investigation.objects.count(), 0)
        self.assertEqual(ISATab.objects.count(), 0)

        for zip_name, zip_file in self._get_isatab_files().items():
            msg = 'file={}'.format(zip_name)

            try:
                investigation = self._import_isa_from_file(
                    zip_file.path, self.project
                )
            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            self.assertEqual(Investigation.objects.count(), 1, msg=msg)
            self.assertEqual(ISATab.objects.count(), 1, msg=msg)

            investigation.delete()
            ISATab.objects.first().delete()
            self.assertEqual(Investigation.objects.count(), 0, msg=msg)
            self.assertEqual(ISATab.objects.count(), 0, msg=msg)

    def test_isa_export_batch(self):
        """Test ISA-Tab export in batch"""
        sheet_io = SampleSheetIO(warn=False, allow_critical=True)

        for zip_name, zip_file in self._get_isatab_files().items():
            investigation = self._import_isa_from_file(
                zip_file.path, self.project
            )

            try:
                export_data = self._get_flat_export_data(
                    sheet_io.export_isa(investigation)
                )
            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            zf = ZipFile(zip_file.path, 'r')

            for isa_path in [n for n in zf.namelist() if not n.endswith('/')]:
                isa_name = isa_path.split('/')[-1]
                import_file = zf.read(isa_path)
                export_file = export_data[isa_name]
                msg = 'file = {} / {}'.format(zip_name, isa_name)

                # Get import file statistics
                ib = io.StringIO(import_file.decode('utf-8'))
                ir = csv.reader(ib, delimiter='\t')
                # Ignore commented/empty lines
                import_rows = len(
                    [x for x in list(ir) if len(x) > 0 and x[0][0] != '#']
                )
                ib.seek(0)
                import_headers = next(ir)
                import_cols = len(import_headers)

                # Get export file statistics
                eb = io.StringIO(export_file)
                er = csv.reader(eb, delimiter='\t')
                export_rows = len(list(er))
                eb.seek(0)
                export_headers = next(er)
                export_cols = len(export_headers)

                # Compare row and column lengths
                self.assertEqual(import_rows, export_rows, msg=msg)
                self.assertEqual(import_cols, export_cols, msg=msg)

                # Compare headers
                for i in range(len(import_headers)):
                    self.assertEqual(
                        import_headers[i], export_headers[i], msg=msg
                    )

                # Compare rows
                def _get_row(row):
                    # HACK for missing tabs for empty fields in certain files
                    # TODO: Fix input files instead
                    if (len(row) == 2 and not row[1]) or (
                        row[0].startswith('Term Source')
                        and not row[len(row) - 1]
                    ):
                        return sorted(row[: len(row) - 1])

                    return sorted(row)

                ib.seek(0)
                eb.seek(0)
                # Ignore commented/empty lines
                import_cmp = [
                    _get_row(x)
                    for x in list(ir)
                    if len(x) > 0 and x[0][0] != '#'
                ]
                export_cmp = [_get_row(x) for x in list(er)]

                for i in range(len(import_cmp)):
                    self.assertIn(import_cmp[i], export_cmp, msg=msg)

                for i in range(len(export_cmp)):
                    self.assertIn(export_cmp[i], import_cmp, msg=msg)

            investigation.delete()

    def test_isa_saving_batch(self):
        """Test original ISA-Tab saving in batch"""
        for zip_name, zip_file in self._get_isatab_files().items():
            try:
                investigation = self._import_isa_from_file(
                    zip_file.path, self.project
                )
            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            saved_isatab = ISATab.objects.first()
            zf = ZipFile(zip_file.path)

            for f in [f for f in zf.filelist if f.file_size > 0]:
                msg = 'zip={}, file={}'.format(zip_name, f.filename)
                zip_data = zf.open(f.filename).read().decode('utf-8')
                file_name = f.filename.split('/')[-1]

                if file_name.startswith('i_'):
                    self.assertEqual(
                        saved_isatab.data['investigation']['tsv'], zip_data, msg
                    )
                elif file_name.startswith('s_'):
                    self.assertEqual(
                        saved_isatab.data['studies'][file_name]['tsv'],
                        zip_data,
                        msg,
                    )
                elif file_name.startswith('a_'):
                    self.assertEqual(
                        saved_isatab.data['assays'][file_name]['tsv'],
                        zip_data,
                        msg,
                    )

            investigation.delete()
            ISATab.objects.first().delete()


class TestSampleSheetIOImport(TestSampleSheetIOBase):
    """Sample sheet import tests"""

    def setUp(self):
        super().setUp()
        self.sheet_io = SampleSheetIO(warn=False, allow_critical=True)
        (self.isa_inv, self.isa_studies, self.isa_assays) = self._read_isa(
            SHEET_PATH, self.project
        )
        self.p_id = 'p{}'.format(self.project.pk)

    def test_import_ref_val(self):
        """Test _import_ref_val()"""

        # Ontology value
        in_data = (
            self.isa_studies['s_BII-S-1.txt']
            .materials['{}-s0-source-culture1'.format(self.p_id)]
            .characteristics[0]
            .value[0]
        )
        out_data = self.sheet_io._import_ref_val(in_data)
        expected = {
            'name': in_data.name,
            'accession': in_data.accession,
            'ontology_name': in_data.ontology_name,
        }
        self.assertEqual(out_data, expected)

        # String value
        in_data = (
            self.isa_studies['s_BII-S-2.txt']
            .materials[
                '{}-s1-sample-NZ_4hrs_Grow1_Drug_Sample_1'.format(self.p_id)
            ]
            .factor_values[0]
            .value
        )
        out_data = self.sheet_io._import_ref_val(in_data)
        self.assertEqual(out_data, in_data)

    def test_import_multi_val(self):
        """Test _import_multi_val()"""

        # List with a single ontology value (should return just a single dict)
        in_data = (
            self.isa_studies['s_BII-S-1.txt']
            .materials['{}-s0-source-culture1'.format(self.p_id)]
            .characteristics[0]
            .value
        )
        out_data = self.sheet_io._import_multi_val(in_data)
        expected = {
            'name': in_data[0].name,
            'accession': in_data[0].accession,
            'ontology_name': in_data[0].ontology_name,
        }
        self.assertEqual(out_data, expected)

        # TODO: List with multiple values (see issue #434)

        # Single ontology value
        in_data = (
            self.isa_studies['s_BII-S-1.txt']
            .materials['{}-s0-sample-C-0.07-aliquot9'.format(self.p_id)]
            .factor_values[0]
            .value
        )
        out_data = self.sheet_io._import_multi_val(in_data)
        expected = {
            'name': in_data.name,
            'accession': in_data.accession,
            'ontology_name': in_data.ontology_name,
        }
        self.assertEqual(out_data, expected)

        # Ontology unit
        in_data = (
            self.isa_studies['s_BII-S-1.txt']
            .materials['{}-s0-sample-C-0.07-aliquot9'.format(self.p_id)]
            .factor_values[1]
            .unit
        )
        out_data = self.sheet_io._import_multi_val(in_data)
        expected = {
            'name': in_data.name,
            'accession': in_data.accession,
            'ontology_name': in_data.ontology_name,
        }
        self.assertEqual(out_data, expected)

    def test_import_ontology_vals(self):
        """Test _import_ontology_vals()"""
        in_data = (
            self.isa_studies['s_BII-S-1.txt']
            .materials['{}-s0-source-culture1'.format(self.p_id)]
            .characteristics
        )
        out_data = self.sheet_io._import_ontology_vals(in_data)
        expected = {
            in_data[i].name: {
                'value': {
                    'name': in_data[i].value[0].name,
                    'accession': in_data[i].value[0].accession,
                    'ontology_name': in_data[i].value[0].ontology_name,
                },
                'unit': in_data[i].unit,
            }
            for i in range(len(in_data))
        }
        self.assertEqual(out_data, expected)

    def test_import_comments(self):
        """Test _import_comments()"""
        in_data = self.isa_inv.studies[0].info.comments
        out_data = self.sheet_io._import_comments(in_data)
        self.assertEqual(len(out_data.values()), len(in_data))

    def test_import_tuple_list(self):
        """Test _import_tuple_list()"""
        in_data = self.isa_inv.ontology_source_refs
        out_data = self.sheet_io._import_tuple_list(in_data)
        expected = [
            self.sheet_io._import_multi_val(v) for v in in_data.values()
        ]
        self.assertListEqual(out_data, expected)

    def test_import_publications(self):
        """Test _import_publications()"""
        in_data = self.isa_inv.publications
        out_data = self.sheet_io._import_publications(in_data)
        self.assertEqual(len(out_data), len(in_data))

    def test_import_contacts(self):
        """Test _import_contacts()"""
        in_data = self.isa_inv.publications
        out_data = self.sheet_io._import_publications(in_data)
        self.assertEqual(len(out_data), len(in_data))


class TestSampleSheetIOExport(TestSampleSheetIOBase):
    """Sample sheet export tests"""

    def setUp(self):
        super().setUp()
        self.sheet_io = SampleSheetIO(warn=False, allow_critical=True)
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.p_id = 'p{}'.format(self.project.pk)

    def test_export_value(self):
        """Test _export_value()"""

        # TODO: String value (see issue #434)
        # TODO: List value (see issue #434)

        # Dict value (ontology term reference)
        in_data = self.investigation.studies.first().study_design[0]['type']
        out_data = self.sheet_io._export_val(in_data)
        expected = isa_models.OntologyTermRef(
            name=in_data['name'],
            accession=in_data['accession'],
            ontology_name=in_data['ontology_name'],
        )
        self.assertEqual(out_data, expected)

    def test_export_comments(self):
        """Test _export_comments()"""
        in_data = self.investigation.studies.first().comments
        out_data = self.sheet_io._export_comments(in_data)
        expected = tuple(
            isa_models.Comment(name=k, value=v) for k, v in in_data.items()
        )
        self.assertEqual(out_data, expected)

    def test_export_publications(self):
        """Test _export_publication()"""
        in_data = self.investigation.publications
        out_data = self.sheet_io._export_publications(in_data)
        expected = tuple(
            isa_models.PublicationInfo(
                pubmed_id=v['pubmed_id'],
                doi=v['doi'],
                authors=v['authors'],
                title=v['title'],
                status=self.sheet_io._export_val(v['status']),
                comments=self.sheet_io._export_comments(v['comments']),
                headers=v['headers'],
            )
            for v in in_data
        )
        self.assertEqual(out_data, expected)

    def test_export_contacts(self):
        """Test _export_contacts()"""
        in_data = self.investigation.contacts
        out_data = self.sheet_io._export_contacts(in_data)
        expected = tuple(
            isa_models.ContactInfo(
                last_name=v['last_name'],
                first_name=v['first_name'],
                mid_initial=v['mid_initial'],
                email=v['email'],
                phone=v['phone'],
                fax=v['fax'],
                address=v['address'],
                affiliation=v['affiliation'],
                role=self.sheet_io._export_val(v['role']),
                comments=self.sheet_io._export_comments(v['comments']),
                headers=v['headers'],
            )
            for v in in_data
        )
        self.assertEqual(out_data, expected)

    def test_export_source_refs(self):
        """Test _export_source_refs()"""
        in_data = self.investigation.ontology_source_refs
        out_data = self.sheet_io._export_source_refs(in_data)
        expected = {
            v['name']: isa_models.OntologyRef(
                name=v['name'],
                file=v['file'],
                version=v['version'],
                comments=self.sheet_io._export_comments(v['comments']),
                description=v['description'],
                headers=v['headers'],
            )
            for v in in_data
        }
        self.assertEqual(out_data, expected)

    def test_export_study_design(self):
        """Test _export_study_design()"""
        study = self.investigation.studies.get(identifier='BII-S-1')
        in_data = study.study_design
        out_data = self.sheet_io._export_study_design(in_data)
        expected = tuple(
            isa_models.DesignDescriptorsInfo(
                type=self.sheet_io._export_val(v['type']),
                comments=self.sheet_io._export_comments(v['comments']),
                headers=v['headers'],
            )
            for v in in_data
        )
        self.assertEqual(out_data, expected)

    # TODO: Test _export_components()

    def test_export_characteristics(self):
        """Test _export_characteristics()"""
        study = self.investigation.studies.get(identifier='BII-S-1')
        in_data = study.materials.get(
            unique_name='{}-s0-source-culture1'.format(self.p_id)
        ).characteristics
        out_data = self.sheet_io._export_characteristics(in_data)
        expected = tuple(
            isa_models.Characteristics(
                name=k,
                value=[self.sheet_io._export_val(v['value'])]
                if not isinstance(v['value'], list)
                else self.sheet_io._export_val(v['value']),
                unit=self.sheet_io._export_val(v['unit']),
            )
            for k, v in in_data.items()
        )
        self.assertEqual(out_data, expected)

    def test_export_factors(self):
        """Test _export_factors()"""
        in_data = self.investigation.studies.get(identifier='BII-S-1').factors
        out_data = self.sheet_io._export_factors(in_data)
        expected = {
            k: isa_models.FactorInfo(
                name=k,
                type=self.sheet_io._export_val(v['type']),
                comments=self.sheet_io._export_comments(v['comments']),
                headers=v['headers'],
            )
            for k, v in in_data.items()
        }
        self.assertEqual(out_data, expected)

    def test_export_factor_values(self):
        """Test _export_factor_values()"""
        study = self.investigation.studies.get(identifier='BII-S-1')
        in_data = study.materials.get(
            unique_name='{}-s0-sample-C-0.07-aliquot1'.format(self.p_id)
        ).factor_values
        out_data = self.sheet_io._export_factor_vals(in_data)
        expected = tuple(
            isa_models.FactorValue(
                name=k,
                value=self.sheet_io._export_val(v['value']),
                unit=self.sheet_io._export_val(v['unit']),
            )
            for k, v in in_data.items()
        )
        self.assertEqual(out_data, expected)

    def test_export_parameters(self):
        """Test _export_parameters()"""
        study = self.investigation.studies.get(identifier='BII-S-1')
        in_data = study.protocols.get(name='metabolite extraction').parameters
        out_data = self.sheet_io._export_parameters(in_data)
        expected = {p['name']: self.sheet_io._export_val(p) for p in in_data}
        self.assertEqual(out_data, expected)

    def test_export_param_values(self):
        """Test _export_param_values()"""
        study = self.investigation.studies.get(identifier='BII-S-1')
        in_data = study.processes.get(
            unique_name='{}-s0-a0-metabolite extraction-2-1'.format(self.p_id)
        ).parameter_values
        out_data = self.sheet_io._export_param_values(in_data)
        expected = tuple(
            isa_models.ParameterValue(
                name=k,
                value=[self.sheet_io._export_val(v['value'])]
                if not isinstance(v['value'], list)
                else self.sheet_io._export_val(v['value']),
                unit=self.sheet_io._export_val(v['unit']),
            )
            for k, v in in_data.items()
        )
        self.assertEqual(out_data, expected)
