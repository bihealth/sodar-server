"""View tests for the cancer study app"""

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
SHEET_PATH = os.path.join(SHEET_DIR, 'bih_cancer.zip')
SOURCE_ID = 'normal1'


class TestIGVSessionFileRenderView(
    SODARAPIViewTestMixin,
    SampleSheetModelMixin,
    SamplesheetsViewTestBase,
):
    """Tests for cancer plugin IGVSessionFileRenderView"""

    @staticmethod
    def _get_auth_header(username: str, password: str) -> dict:
        """Return basic auth header"""
        credentials = base64.b64encode(
            f'{username}:{password}'.encode('utf-8')
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
            'samplesheets.studyapps.cancer:igv',
            kwargs={'genericmaterial': self.source.sodar_uuid},
        )

    def test_get(self):
        """Test IGVSessionFileRenderView GET"""
        with self.login(self.user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            f'attachment; filename="{SOURCE_ID}.case.igv.xml"',
        )
        # NOTE: XML forming tested in TestGetIGVXML

    def test_get_xml_suffix(self):
        """Test GET with XML URL suffix"""
        with self.login(self.user_contributor):
            response = self.client.get(self.url + '.xml')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            f'attachment; filename="{SOURCE_ID}.case.igv.xml"',
        )

    def test_get_basic_auth(self):
        """Test GET with basic auth"""
        response = self.client.get(
            self.url,
            **self._get_auth_header(self.user_contributor.username, 'password'),
        )
        self.assertEqual(response.status_code, 200)

    def test_get_token(self):
        """Test GET with Knox token"""
        knox_token = self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self._get_auth_header(self.user_contributor.username, knox_token),
        )
        self.assertEqual(response.status_code, 200)

    def test_get_token_invalid(self):
        """Test GET with invalid Knox token"""
        self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self._get_auth_header(
                self.user_contributor.username, EMPTY_KNOX_TOKEN
            ),
        )
        self.assertEqual(response.status_code, 401)

    def test_get_token_wrong_user(self):
        """Test GET with Knox token and wrong user"""
        knox_token = self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self._get_auth_header(self.user_delegate.username, knox_token),
        )
        self.assertEqual(response.status_code, 401)
