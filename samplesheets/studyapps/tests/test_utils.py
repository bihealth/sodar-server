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
from samplesheets.studyapps.utils import (
    get_igv_omit_list,
    check_igv_file_suffix,
    check_igv_file_path,
    get_igv_xml,
)
from samplesheets.tests.test_io import SampleSheetIOMixin


app_settings = AppSettingAPI()


# Local constants
INVALID_FILE_TYPE = 'INVALID_TYPE'


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


class TestGetIGVOmitList(TestStudyAppUtilsBase):
    """Tests for get_igv_omit_list()"""

    def test_get(self):
        """Test get_igv_omit_list()"""
        self.assertEqual(
            get_igv_omit_list(self.project, 'bam'), ['*dragen_evidence.bam']
        )
        self.assertEqual(
            get_igv_omit_list(self.project, 'vcf'),
            ['*cnv.vcf.gz', '*ploidy.vcf.gz', '*sv.vcf.gz'],
        )

    def test_get_invalid_file_type(self):
        """Test get_igv_omit_list() with invalid file type"""
        with self.assertRaises(ValueError):
            get_igv_omit_list(self.project, INVALID_FILE_TYPE)

    def test_get_no_preceeding_asterisk(self):
        """Test get_igv_omit_list() without preceeding asterisk"""
        # NOTE: We can't use override_settings here
        app_settings.set(
            'samplesheets',
            'igv_omit_bam',
            'dragen_evidence.bam',
            project=self.project,
        )
        app_settings.set(
            'samplesheets', 'igv_omit_vcf', 'cnv.vcf.gz', project=self.project
        )
        self.assertEqual(
            get_igv_omit_list(self.project, 'bam'), ['*dragen_evidence.bam']
        )
        self.assertEqual(
            get_igv_omit_list(self.project, 'vcf'), ['*cnv.vcf.gz']
        )

    def test_get_mixed_preceeding_asterisks(self):
        """Test get_igv_omit_list() with mixed preceeding asterisk"""
        app_settings.set(
            'samplesheets',
            'igv_omit_bam',
            '*xxx.bam,yyy.bam',
            project=self.project,
        )
        app_settings.set(
            'samplesheets',
            'igv_omit_vcf',
            '*xxx.vcf.gz,yyy.vcf.gz',
            project=self.project,
        )
        self.assertEqual(
            get_igv_omit_list(self.project, 'bam'), ['*xxx.bam', '*yyy.bam']
        )
        self.assertEqual(
            get_igv_omit_list(self.project, 'vcf'),
            ['*xxx.vcf.gz', '*yyy.vcf.gz'],
        )

    def test_get_empty_setting(self):
        """Test get_igv_omit_list() with empty setting values"""
        app_settings.set(
            'samplesheets', 'igv_omit_bam', '', project=self.project
        )
        app_settings.set(
            'samplesheets', 'igv_omit_vcf', '', project=self.project
        )
        self.assertEqual(get_igv_omit_list(self.project, 'bam'), [])
        self.assertEqual(get_igv_omit_list(self.project, 'vcf'), [])


class TestCheckIGVFileSuffix(TestCase):  # TestStudyAppUtilsBase not needed
    """Tests for check_igv_file_suffix()"""

    def test_check_bam(self):
        """Test checking with BAM type and valid name"""
        self.assertTrue(check_igv_file_suffix('test.bam', 'bam'))

    def test_check_bam_invalid_name(self):
        """Test checking with BAM type and invalid name"""
        self.assertFalse(check_igv_file_suffix('test.vcf', 'bam'))

    def test_check_bam_cram(self):
        """Test checking with BAM type and CRAM name"""
        self.assertTrue(check_igv_file_suffix('test.cram', 'bam'))

    def test_check_bam_uppercase(self):
        """Test checking with BAM type and uppercase name"""
        self.assertTrue(check_igv_file_suffix('TEST.BAM', 'bam'))

    def test_check_vcf(self):
        """Test checking with VCF type and valid name"""
        self.assertTrue(check_igv_file_suffix('test.vcf.gz', 'vcf'))

    def test_check_vcf_no_gz(self):
        """Test checking with VCF type and name without .gz suffix"""
        self.assertFalse(check_igv_file_suffix('test.vcf', 'vcf'))

    def test_check_invalid_type(self):
        """Test checking with invalid_type"""
        with self.assertRaises(ValueError):
            check_igv_file_suffix('test.bam', 'INVALID')


class TestCheckIGVFilePath(TestCase):
    """Tests for check_igv_file_path()"""

    def test_path(self):
        """Test check_igv_file_path()"""
        path = 'xxx/yyy.bam'
        omit_list = ['*zzz.bam']
        self.assertTrue(check_igv_file_path(path, omit_list))

    def test_path_omit_file(self):
        """Test check_igv_file_path() with file name in omit list"""
        path = 'xxx/yyy.bam'
        omit_list = ['*yyy.bam']
        self.assertFalse(check_igv_file_path(path, omit_list))

    def test_path_empty_list(self):
        """Test check_igv_file_path() with empty omit list"""
        path = 'xxx/yyy.bam'
        omit_list = []
        self.assertTrue(check_igv_file_path(path, omit_list))

    def test_path_omit_multiple(self):
        """Test check_igv_file_path() with multiple patterns"""
        path = 'xxx/yyy.bam'
        omit_list = ['*yyy.bam', '*zzz.bam']
        self.assertFalse(check_igv_file_path(path, omit_list))

    def test_path_omit_no_math(self):
        """Test check_igv_file_path() with multiple non-matching patterns"""
        path = 'xxx/yyy.bam'
        omit_list = ['*aaa.bam', '*bbb.bam']
        self.assertTrue(check_igv_file_path(path, omit_list))

    def test_path_omit_case(self):
        """Test check_igv_file_path() with file name in different case"""
        path = 'xxx/YYY.BAM'
        omit_list = ['*yyy.bam']
        self.assertFalse(check_igv_file_path(path, omit_list))

    def test_path_omit_collections(self):
        """Test check_igv_file_path() with matching collections"""
        path = '000/aaa/bbb/yyy.bam'
        omit_list = ['*/aaa/bbb/*']
        self.assertFalse(check_igv_file_path(path, omit_list))

    def test_path_omit_collections_middle(self):
        """Test check_igv_file_path() with partial collection match"""
        path = '000/aaa/bbb/yyy.bam'
        omit_list = ['*/aaa/*/yyy.bam']
        self.assertFalse(check_igv_file_path(path, omit_list))


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
