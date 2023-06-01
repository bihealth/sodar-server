"""Tests for samplesheets REST API View permissions with taskflow"""

from irods.keywords import REG_CHKSUM_KW

from django.urls import reverse

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowAPIPermissionTestBase

from samplesheets.tests.test_io import SampleSheetIOMixin
from samplesheets.tests.test_permissions import SHEET_PATH
from samplesheets.tests.test_views_api_taskflow import (
    IRODS_FILE_PATH,
    IRODS_FILE_MD5,
)
from samplesheets.tests.test_views_taskflow import SampleSheetTaskflowMixin


class TestSampleDataFileExistsAPIView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowAPIPermissionTestBase
):
    """Tests for SampleDataFileExistsAPIView permissions"""

    def setUp(self):
        super().setUp()
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Make iRODS collections
        self.make_irods_colls(self.investigation)
        # Upload file
        coll_path = self.irods_backend.get_sample_path(self.project) + '/'
        self.irods.data_objects.put(
            IRODS_FILE_PATH, coll_path, **{REG_CHKSUM_KW: ''}
        )
        self.post_data = {'checksum': IRODS_FILE_MD5}

    def test_get(self):
        """Test get() in SampleDataFileExistsAPIView"""
        url = reverse('samplesheets:api_file_exists')
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(url, good_users, 200, data=self.post_data)
        self.assert_response_api(url, self.anonymous, 401, data=self.post_data)

    def test_get_archive(self):
        """Test get() with archived project"""
        self.project.set_archive()
        url = reverse('samplesheets:api_file_exists')
        good_users = [
            self.superuser,
            self.user_owner_cat,
            self.user_delegate_cat,
            self.user_contributor_cat,
            self.user_guest_cat,
            self.user_finder_cat,
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
            self.user_no_roles,
        ]
        self.assert_response_api(url, good_users, 200, data=self.post_data)
        self.assert_response_api(url, self.anonymous, 401, data=self.post_data)
