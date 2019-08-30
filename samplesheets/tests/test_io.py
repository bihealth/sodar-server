"""Tests for samplesheets.io"""

import csv
import io
import os
from zipfile import ZipFile

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import Investigation
from ..io import SampleSheetIO


# Local constants
SHEET_DIR = os.path.dirname(__file__) + '/isatab/'


class SampleSheetIOMixin:
    """Helper functions for sample sheet i/o"""

    @classmethod
    def _import_isa_from_file(cls, path, project):
        """
        Import ISA from a zip file.

        :param path: Path to zip file in the file system
        :param project: Project object
        :return: Investigation object
        """
        zf = ZipFile(os.fsdecode(path))
        sheet_io = SampleSheetIO(warn=False, allow_critical=True)
        investigation = sheet_io.import_isa(zf, project)
        investigation.active = True  # Must set this explicitly
        investigation.save()
        return investigation


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

    def _fail_isa(self, zip_name, ex):
        """Fail with exception message and ISAtab zip file name"""
        self.fail('Exception in {}: {}'.format(zip_name, ex))

    @classmethod
    def _get_isatab_files(cls):
        """
        Return all test ISAtab files.

        :return: Dict
        """
        return {
            os.fsdecode(file.name): file
            for file in sorted(
                [x for x in os.scandir(SHEET_DIR) if x.is_file()],
                key=lambda x: x.name,
            )
        }

    @classmethod
    def _get_flat_export_data(cls, export_data):
        """Return export ISA data as a flat list"""
        ret = {
            export_data['investigation']['path'].split('/')[-1]: export_data[
                'investigation'
            ]['data']
        }

        for k, v in export_data['studies'].items():
            ret[k] = v['data']

        for k, v in export_data['assays'].items():
            ret[k] = v['data']

        return ret


class TestSampleSheetImport(TestSampleSheetIOBase):
    def test_isa_import_batch(self):
        """Test ISAtab import in batch"""
        self.assertEqual(Investigation.objects.count(), 0)

        for zip_name, zip_file in self._get_isatab_files().items():
            msg = 'file={}'.format(zip_name)

            try:
                investigation = self._import_isa_from_file(
                    zip_file.path, self.project
                )

            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            self.assertEqual(Investigation.objects.count(), 1, msg=msg)

            # TODO: Compare content

            investigation.delete()
            self.assertEqual(Investigation.objects.count(), 0, msg=msg)


class TestSampleSheetExport(TestSampleSheetIOBase):
    def test_isa_export_batch(self):
        """Test ISAtab export in batch"""
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
