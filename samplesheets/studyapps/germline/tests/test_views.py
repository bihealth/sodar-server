"""View tests for the germline study app"""

# NOTE: We don't need to add files in iRODS to test this view

import os

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

# Projectroles dependency
from projectroles.tests.base import (
    SODARAPIViewTestMixin,
    AUTHENTICATION_BACKENDS_AXES,
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
USER_PW = 'password'
INVALID_PW = 'INVALID_PASSWORD'


class IGVSessionFileRenderViewTestBase(
    SODARAPIViewTestMixin,
    SampleSheetModelMixin,
    SamplesheetsViewTestBase,
):
    """Base class germline plugin IGVSessionFileRenderView tests"""

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


class TestIGVSessionFileRenderView(IGVSessionFileRenderViewTestBase):
    """Tests for germline plugin IGVSessionFileRenderView"""

    def test_get(self):
        """Test IGVSessionFileRenderView GET"""
        with self.login(self.user_contributor):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            f'attachment; filename="{FAMILY_ID}.pedigree.igv.xml"',
        )
        # NOTE: XML forming tested in TestGetIGVXML

    def test_get_xml_suffix(self):
        """Test GET with XML URL suffix"""
        with self.login(self.user_contributor):
            response = self.client.get(self.url + '.xml')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('Content-Disposition'),
            f'attachment; filename="{FAMILY_ID}.pedigree.igv.xml"',
        )

    def test_get_basic_auth(self):
        """Test GET with basic auth"""
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(
                self.user_contributor.username, USER_PW
            ),
        )
        self.assertEqual(response.status_code, 200)

    def test_get_token(self):
        """Test GET with Knox token"""
        knox_token = self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(
                self.user_contributor.username, knox_token
            ),
        )
        self.assertEqual(response.status_code, 200)

    def test_get_token_invalid(self):
        """Test GET with invalid Knox token"""
        self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(
                self.user_contributor.username, EMPTY_KNOX_TOKEN
            ),
        )
        self.assertEqual(response.status_code, 401)

    def test_get_token_wrong_user(self):
        """Test GET with Knox token and wrong user"""
        knox_token = self.get_token(self.user_contributor)
        response = self.client.get(
            self.url,
            **self.get_basic_auth_header(
                self.user_delegate.username, knox_token
            ),
        )
        self.assertEqual(response.status_code, 401)


@override_settings(
    AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS_AXES, AXES_ENABLED=True
)
class TestIGVSessionFileRenderViewAxes(IGVSessionFileRenderViewTestBase):
    """Tests for IGVSessionFileRenderView with basic auth and django-axes"""

    def setUp(self):
        super().setUp()
        self.user_name = self.user_contributor.username

    def test_get(self):
        """Test IGVSessionFileRenderView GET with valid credentials"""
        response = self.client.get(
            self.url, **self.get_basic_auth_header(self.user_name, USER_PW)
        )
        self.assertEqual(response.status_code, 200)

    def test_get_invalid(self):
        """Test GET with invalid credentials"""
        response = self.client.get(
            self.url, **self.get_basic_auth_header(self.user_name, INVALID_PW)
        )
        self.assertEqual(response.status_code, 401)

    def test_get_lock(self):
        """Test GET with account locking"""
        header = self.get_basic_auth_header(self.user_name, INVALID_PW)
        for i in range(0, settings.AXES_FAILURE_LIMIT - 1):
            response = self.client.get(self.url, **header)
            self.assertEqual(response.status_code, 401)
        # User should now be locked, attempt login one more time
        response = self.client.get(self.url, **header)
        self.assertEqual(response.status_code, 429)
