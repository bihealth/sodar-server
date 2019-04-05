"""Plugin tests for the samplesheets studyapps"""
import os

from django.conf import settings
from django.forms.models import model_to_dict

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

from samplesheets.tests.test_models import (
    TestSampleSheetBase,
    SampleSheetModelMixin,
)
from samplesheets.tests.test_rendering import TestRenderingBase
from samplesheets.plugins import SampleSheetStudyPluginPoint

from sodarcache.models import JSONCacheItem

from unittest import skipIf

# SODAR constants
PROJECT_ROLE_OWNER = SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = SODAR_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
PLUGIN_NAME_CANCER = 'samplesheets_study_cancer'
PLUGIN_TITLE_CANCER = 'Sample Sheets Cancer Study Plugin'

PLUGIN_NAME_GERMLINE = 'samplesheets_study_germline'
PLUGIN_TITLE_GERMLINE = 'Sample Sheets Germline Study Plugin'

DATA_NAME = 'file.vcf'
DATA_UNIQUE_NAME = 'p1-s1-a1-file.vcf-COL1'
DATA_TYPE = 'Raw Data File'

SOURCE_NAME = 'patient1'
SOURCE_UNIQUE_NAME = 'p1-s1-a1-patient1-1-1'
SOURCE_CHARACTERISTICS = {
    'Age': {
        'unit': {
            'name': 'day',
            'accession': 'http://purl.obolibrary.org/obo/UO_0000033',
            'ontology_name': 'UO',
        },
        'value': '2423',
    }
}

DEFAULT_COMMENTS = {'comment': 'value'}
DEFAULT_DESCRIPTION = 'Description'

SHEET_DIR = os.path.dirname(__file__) + '/../../tests/isatab/'
SHEET_PATH = SHEET_DIR + 'i_small2.zip'


IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestCancerPlugins(TestSampleSheetBase):
    """Class for testing the cancer studyapp plugins"""

    def setUp(self):
        super().setUp()

        # Init admin user
        self.admin_user = self.make_user(settings.PROJECTROLES_DEFAULT_ADMIN)
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True

        # Set up DATA GenericMaterial with vcf
        self.material = self._make_material(
            item_type='DATA',
            name=DATA_NAME,
            unique_name=DATA_UNIQUE_NAME,
            characteristics={},
            study=self.study,
            assay=self.assay,
            material_type=DATA_TYPE,
            factor_values=None,
            extract_label=None,
            comments=DEFAULT_COMMENTS,
        )

    def test_plugin_retrieval(self):
        """Test retrieving SampleSheetStudyPlugin from the database"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_CANCER)
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.get_model().name, PLUGIN_NAME_CANCER)
        self.assertEqual(plugin.name, PLUGIN_NAME_CANCER)
        self.assertEqual(plugin.get_model().title, PLUGIN_TITLE_CANCER)
        self.assertEqual(plugin.title, PLUGIN_TITLE_CANCER)

    def test_create_cache(self):
        """Test creating cache items with the cancer studyapp plugin"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_CANCER)

        # Assert precondition
        self.assertEqual(JSONCacheItem.objects.all().count(), 0)

        plugin.update_cache(project=self.project)

        self.assertEqual(JSONCacheItem.objects.all().count(), 1)

        item = JSONCacheItem.objects.filter(project=self.project).first()

        expected = {
            'id': item.pk,
            'project': self.project.pk,
            'app_name': 'samplesheets',
            'name': str(self.study.sodar_uuid)
            + '/'
            + 'samplesheets_study_cancer',
            'user': self.admin_user.pk,
            'sodar_uuid': item.sodar_uuid,
            'data': {
                'bam_urls': {'file.vcf': None},
                'vcf_urls': {'file.vcf': None},
            },
        }

        self.assertEqual(model_to_dict(item), expected)

    def test_update_cache(self):
        """Test updating cache items with the cancer studyapp plugin"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_CANCER)

        # Assert precondition
        self.assertEqual(JSONCacheItem.objects.all().count(), 0)

        plugin.update_cache(project=self.project)

        self.assertEqual(JSONCacheItem.objects.all().count(), 1)

        self._make_material(
            item_type='DATA',
            name='file2.bam',
            unique_name='p1-s1-a1-file2.bam-COL1',
            characteristics={},
            study=self.study,
            assay=self.assay,
            material_type=DATA_TYPE,
            factor_values=None,
            extract_label=None,
            comments=DEFAULT_COMMENTS,
        )

        plugin.update_cache(project=self.project)

        self.assertEqual(JSONCacheItem.objects.all().count(), 1)

        item = JSONCacheItem.objects.filter(project=self.project).first()

        expected = {
            'id': item.pk,
            'project': self.project.pk,
            'app_name': 'samplesheets',
            'name': str(self.study.sodar_uuid)
            + '/'
            + 'samplesheets_study_cancer',
            'user': self.admin_user.pk,
            'sodar_uuid': item.sodar_uuid,
            'data': {
                'bam_urls': {'file.vcf': None, 'file2.bam': None},
                'vcf_urls': {'file.vcf': None, 'file2.bam': None},
            },
        }

        self.assertEqual(model_to_dict(item), expected)

    def test_update_one_cache_item(self):
        """Test updating only one cache item with the cancer studyapp plugin"""

        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_CANCER)

        # Assert precondition
        self.assertEqual(JSONCacheItem.objects.all().count(), 0)

        second_study = self._make_study(
            identifier='Second Study Identifier',
            file_name='second_study.txt',
            investigation=self.investigation,
            title='second_study',
            description=DEFAULT_DESCRIPTION,
            comments=DEFAULT_COMMENTS,
        )

        self._make_material(
            item_type='DATA',
            name='file2.bam',
            unique_name='p1-s1-a1-file2.bam-COL1',
            characteristics={},
            study=second_study,
            assay=self.assay,
            material_type=DATA_TYPE,
            factor_values=None,
            extract_label=None,
            comments=DEFAULT_COMMENTS,
        )

        plugin.update_cache(project=self.project)

        # there are two different cache items now
        self.assertEqual(JSONCacheItem.objects.all().count(), 2)

        items = JSONCacheItem.objects.filter(project=self.project).order_by(
            '-date_modified'
        )

        self.assertEqual(
            items[0].data,
            {'bam_urls': {'file.vcf': None}, 'vcf_urls': {'file.vcf': None}},
        )
        self.assertEqual(
            items[1].data,
            {'bam_urls': {'file2.bam': None}, 'vcf_urls': {'file2.bam': None}},
        )

        # add another item to the second study
        self._make_material(
            item_type='DATA',
            name='another_item',
            unique_name='p3-s3-a3-another_item-COL1',
            characteristics={},
            study=self.study,
            assay=self.assay,
            material_type=DATA_TYPE,
            factor_values=None,
            extract_label=None,
            comments=DEFAULT_COMMENTS,
        )

        # add another item to the second study
        self._make_material(
            item_type='DATA',
            name='another_item',
            unique_name='p3-s3-a3-another_item-COL2',
            characteristics={},
            study=second_study,
            assay=self.assay,
            material_type=DATA_TYPE,
            factor_values=None,
            extract_label=None,
            comments=DEFAULT_COMMENTS,
        )

        # update only the samplesheets_cancer cache item of the second study
        plugin.update_cache(
            name=str(second_study.sodar_uuid)
            + '/'
            + 'samplesheets_study_cancer',
            project=self.project,
        )

        # still two items
        self.assertEqual(JSONCacheItem.objects.all().count(), 2)

        items = JSONCacheItem.objects.filter(project=self.project).order_by(
            '-date_modified'
        )

        self.assertEqual(
            items[0].data,
            {'bam_urls': {'file.vcf': None}, 'vcf_urls': {'file.vcf': None}},
        )
        self.assertEqual(
            items[1].data,
            {
                'bam_urls': {'another_item': None, 'file2.bam': None},
                'vcf_urls': {'another_item': None, 'file2.bam': None},
            },
        )


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestGermlinePlugins(SampleSheetModelMixin, TestRenderingBase):
    """Class for testing the germline studyapp plugins"""

    def setUp(self):
        super().setUp()

        # Init admin user
        self.admin_user = self.make_user(settings.PROJECTROLES_DEFAULT_ADMIN)
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True

    def test_plugin_retrieval(self):
        """Test retrieving SampleSheetStudyPlugin from the database"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_GERMLINE)
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.get_model().name, PLUGIN_NAME_GERMLINE)
        self.assertEqual(plugin.name, PLUGIN_NAME_GERMLINE)
        self.assertEqual(plugin.get_model().title, PLUGIN_TITLE_GERMLINE)
        self.assertEqual(plugin.title, PLUGIN_TITLE_GERMLINE)

    def test_create_cache(self):
        """Test creating cache items with the germline studyapp plugin"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_GERMLINE)
        # Assert precondition
        self.assertEqual(JSONCacheItem.objects.all().count(), 0)

        print(str(self.admin_user.sodar_uuid))

        plugin.update_cache(project=self.project)

        self.assertEqual(JSONCacheItem.objects.all().count(), 1)

        item = JSONCacheItem.objects.filter(project=self.project).first()

        expected = {
            'id': item.pk,
            'project': self.project.pk,
            'app_name': 'samplesheets',
            'name': str(self.study.sodar_uuid)
            + '/'
            + 'samplesheets_study_germline',
            'user': self.admin_user.pk,
            'sodar_uuid': item.sodar_uuid,
            'data': {'bam_urls': {'0815': None}, 'vcf_urls': {'0815': None}},
        }

        self.assertEqual(model_to_dict(item), expected)

    def test_update_cache(self):
        """Test updating cache items with the germline studyapp plugin"""
        plugin = SampleSheetStudyPluginPoint.get_plugin(PLUGIN_NAME_GERMLINE)
        # Assert precondition
        self.assertEqual(JSONCacheItem.objects.all().count(), 0)

        plugin.update_cache(project=self.project)

        self.assertEqual(JSONCacheItem.objects.all().count(), 1)

        # Set up new SOURCE GenericMaterial
        self.material = self._make_material(
            item_type='SOURCE',
            name=SOURCE_NAME,
            unique_name=SOURCE_UNIQUE_NAME,
            characteristics=SOURCE_CHARACTERISTICS,
            study=self.study,
            assay=None,
            material_type=None,
            factor_values=None,
            extract_label=None,
            comments=DEFAULT_COMMENTS,
        )

        plugin.update_cache(project=self.project)

        self.assertEqual(JSONCacheItem.objects.all().count(), 1)

        item = JSONCacheItem.objects.filter(project=self.project).first()

        expected = {
            'id': item.pk,
            'project': self.project.pk,
            'app_name': 'samplesheets',
            'name': str(self.study.sodar_uuid)
            + '/'
            + 'samplesheets_study_germline',
            'user': self.admin_user.pk,
            'sodar_uuid': item.sodar_uuid,
            'data': {
                'bam_urls': {'0815': None, 'patient1': None},
                'vcf_urls': {'0815': None, 'patient1': None},
            },
        }

        self.assertEqual(model_to_dict(item), expected)
