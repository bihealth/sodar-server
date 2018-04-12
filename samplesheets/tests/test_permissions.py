"""Tests for permissions in the samplesheets app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import TestProjectPermissionBase

from .test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'


class TestSampleSheetsPermissions(
        TestProjectPermissionBase, SampleSheetIOMixin):
    """Tests for samplesheets view permissions"""

    def setUp(self):
        super(TestSampleSheetsPermissions, self).setUp()
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_project_sheets(self):
        """Test the project sheets view"""
        url = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user]
        bad_users = [
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_overview(self):
        """Test the project sheets overview"""
        url = reverse(
            'samplesheets:overview',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user,
            self.as_guest.user]
        bad_users = [
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_import(self):
        """Test the project sheets import view"""
        url = reverse(
            'samplesheets:import',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.as_contributor.user,
            self.as_guest.user,
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_export_tsv_study(self):
        """Test the project sheets TSV export view for study table"""
        url = reverse(
            'samplesheets:export_tsv',
            kwargs={'study': self.study.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user]
        bad_users = [
            self.as_guest.user,
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_export_tsv_assay(self):
        """Test the project sheets TSV export view for assay table"""
        url = reverse(
            'samplesheets:export_tsv',
            kwargs={'assay': self.assay.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user,
            self.as_contributor.user]
        bad_users = [
            self.as_guest.user,
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)

    def test_sheet_delete(self):
        """Test the project sheets delete view"""
        url = reverse(
            'samplesheets:delete',
            kwargs={'project': self.project.omics_uuid})
        good_users = [
            self.superuser,
            self.as_owner.user,
            self.as_delegate.user]
        bad_users = [
            self.as_contributor.user,
            self.as_guest.user,
            self.anonymous,
            self.user_no_roles]
        self.assert_render200_ok(url, good_users)
        self.assert_redirect(url, bad_users)
