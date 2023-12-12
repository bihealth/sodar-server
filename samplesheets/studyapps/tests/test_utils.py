"""Tests for general samplesheets study app utils"""

import os

from django.test import RequestFactory
from django.urls import reverse

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.plugins import IGV_DEFAULT_GENOME
from samplesheets.studyapps.utils import get_igv_xml
from samplesheets.tests.test_io import SampleSheetIOMixin


app_settings = AppSettingAPI()


class TestStudyAppUtilsBase(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase
):
    """Base class for samplesheets study app utils tests"""

    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')
        # Init project, role and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )


class TestGetIGVXML(TestStudyAppUtilsBase):
    """Tests for get_igv_xml()"""

    def _get_all_paths(self):
        return list(self.bam_urls.values()) + list(self.vcf_urls.values())

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods')
        self.project_path = self.irods_backend.get_path(self.project)
        self.bam_urls = {
            'P1001-N1-DNA1-WGS1': os.path.join(
                self.project_path, 'P1001-N1.bam'
            ),
            'P1002-N1-DNA1-WGS1': os.path.join(
                self.project_path, 'P1002-N1.bam'
            ),
        }
        self.vcf_urls = {
            'P1001-N1-DNA1-WGS1': os.path.join(
                self.project_path, 'P1001-N1.vcf.gz'
            ),
        }
        self.paths = list(self.bam_urls.values()) + list(self.vcf_urls.values())
        self.req_factory = RequestFactory()
        self.request = self.req_factory.get(reverse('home'))

    def test_get_igv_xml(self):
        """Test get_igv_xml()"""
        # NOTE: Receiving as lxml object structure to ease testing
        xml = get_igv_xml(
            self.project,
            self.bam_urls,
            self.vcf_urls,
            'Library',
            self.request,
            False,
        )
        self.assertEqual(xml.get('genome'), IGV_DEFAULT_GENOME)
        resources = xml.find('Resources')
        for r in resources.findall('Resource'):
            self.assertIn(r.get('path'), self.paths)

    def test_get_igv_xml_override_genome(self):
        """Test get_igv_xml() with genome override in project"""
        app_settings.set(
            'samplesheets', 'igv_genome', 'GRCh37', project=self.project
        )
        xml = get_igv_xml(
            self.project,
            self.bam_urls,
            self.vcf_urls,
            'Library',
            self.request,
            False,
        )
        self.assertEqual(xml.get('genome'), 'GRCh37')
