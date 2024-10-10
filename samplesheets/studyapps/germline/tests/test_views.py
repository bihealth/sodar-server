"""View tests for the germline study app"""

# NOTE: We don't need to add files in iRODS to test this view

import base64
import os

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_views_api import (
    SODARAPIViewTestMixin,
    EMPTY_KNOX_TOKEN,
)

from samplesheets.models import GenericMaterial
from samplesheets.tests.test_io import SHEET_DIR
from samplesheets.tests.test_models import SampleSheetModelMixin
from samplesheets.tests.test_views import SamplesheetsViewTestBase


# Local constants
SHEET_PATH = os.path.join(SHEET_DIR, 'bih_germline.zip')
SOURCE_ID = 'p1'
FAMILY_ID = 'FAM_p1'


class TestIGVSessionFileRenderView(
    SODARAPIViewTestMixin,
    SampleSheetModelMixin,
    SamplesheetsViewTestBase,
):
    """Tests for germline plugin IGVSessionFileRenderView"""

    @staticmethod
    def _get_auth_header(username, password):
        """Return basic auth header"""
        credentials = base64.b64encode(
            '{}:{}'.format(username, password).encode('utf-8')
        ).strip()
        return {
            'HTTP_AUTHORIZATION': 'Basic {}'.format(credentials.decode('utf-8'))
        }

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
        with self.login(self.user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename="{}.pedigree.igv.xml"'.format(FAMILY_ID),
        )
        # NOTE: XML forming tested in TestGetIGVXML

    def test_get_basic_auth(self):
        """Test GET with basic auth"""
        response = self.client.get(
            self.url,
            **self._get_auth_header(self.user_contributor.username, 'password')
        )
        self.assertEqual(response.status_code, 200)

    def test_get_token(self):
        """Test GET with Knox token"""
        knox_token = self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self._get_auth_header(self.user_contributor.username, knox_token)
        )
        self.assertEqual(response.status_code, 200)

    def test_get_token_invalid(self):
        """Test GET with invalid Knox token"""
        self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self._get_auth_header(
                self.user_contributor.username, EMPTY_KNOX_TOKEN
            )
        )
        self.assertEqual(response.status_code, 401)

    def test_get_token_wrong_user(self):
        """Test GET with Knox token and wrong user"""
        knox_token = self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self._get_auth_header(self.user_delegate.username, knox_token)
        )
        self.assertEqual(response.status_code, 401)
