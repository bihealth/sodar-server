"""Permission tests for the germline study app"""

# NOTE: Basic auth tested in test_views

import os

from django.urls import reverse

from samplesheets.models import GenericMaterial
from samplesheets.tests.test_io import SHEET_DIR
from samplesheets.tests.test_permissions import SamplesheetsPermissionTestBase


# Local constants
SHEET_PATH = os.path.join(SHEET_DIR, 'bih_germline.zip')
SOURCE_ID = 'p1'


class TestIGVSessionFileRenderView(SamplesheetsPermissionTestBase):
    """Tests for IGVSessionFileRenderView permissions"""

    def setUp(self):
        super().setUp()
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.source = GenericMaterial.objects.get(
            study=self.study, name=SOURCE_ID
        )
        self.url = reverse(
            'samplesheets.studyapps.germline:igv',
            kwargs={'genericmaterial': self.source.sodar_uuid},
        )

    def test_get(self):
        """Test IGVSessionFileRenderView GET"""
        good_users = [
            self.superuser,
            self.user_owner_cat,  # Inherited
            self.user_delegate_cat,  # Inherited
            self.user_contributor_cat,  # Inherited
            self.user_guest_cat,  # Inherited
            self.user_owner,
            self.user_delegate,
            self.user_contributor,
            self.user_guest,
        ]
        bad_users = [
            self.user_viewer_cat,  # Inherited
            self.user_finder_cat,  # Inherited
            self.user_viewer,
            self.user_no_roles,
        ]
        self.assert_response(self.url, good_users, 200)
        self.assert_response(self.url, bad_users, 302)
        self.assert_response(self.url, self.anonymous, 401)
        # Test public project
        self.project.set_public_access(self.role_guest)
        self.assert_response(self.url, bad_users, 200)
        self.assert_response(self.url, self.anonymous, 401)
        self.project.set_public_access(self.role_viewer)
        self.assert_response(self.url, bad_users, 302)
        self.assert_response(self.url, self.anonymous, 401)
