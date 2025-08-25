"""Tests for template tags in the samplesheets app"""

import os

from django.conf import settings
from django.urls import reverse

from test_plus.test import TestCase

from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import PluginAPI
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)

from samplesheets.models import GENERIC_MATERIAL_TYPES
from samplesheets.templatetags import samplesheets_tags as s_tags
from samplesheets.tests.test_models import (
    SampleSheetModelMixin,
    IrodsDataRequestMixin,
    INV_IDENTIFIER,
    INV_FILE_NAME,
    INV_TITLE,
    DEFAULT_DESCRIPTION,
    DEFAULT_COMMENTS,
    INV_ARCHIVE_NAME,
    STUDY_IDENTIFIER,
    STUDY_FILE_NAME,
    STUDY_TITLE,
    ASSAY_FILE_NAME,
    ASSAY_TECH_PLATFORM,
    ASSAY_TECH_TYPE,
    ASSAY_MEASURE_TYPE,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)


plugin_api = PluginAPI()


# Local constants
IRODS_SAMPLE_COLL = settings.IRODS_SAMPLE_COLL
DEFAULT_TAG_COLOR = s_tags.DEFAULT_TAG_COLOR
TAG_COLORS = s_tags.TAG_COLORS
REQUEST_STATUS_CLASSES = s_tags.REQUEST_STATUS_CLASSES
MISC_FILES_COLL = 'MiscFiles'
SUB_COLL = 'SubCollection'


class TestSamplesheetsTemplateTags(
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    SampleSheetModelMixin,
    IrodsDataRequestMixin,
    TestCase,
):
    """Tests for template tags in the samplesheets app"""

    def setUp(self):
        # Init roles
        self.init_roles()
        # Make owner user
        self.user_owner = self.make_user('owner')
        # Init project and assignment
        self.project = self.make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.owner_as = self.make_assignment(
            self.project, self.user_owner, self.role_owner
        )
        # Set up Investigation
        self.investigation = self.make_investigation(
            identifier=INV_IDENTIFIER,
            file_name=INV_FILE_NAME,
            project=self.project,
            title=INV_TITLE,
            description=DEFAULT_DESCRIPTION,
            comments=DEFAULT_COMMENTS,
            archive_name=INV_ARCHIVE_NAME,
        )
        # Set up Study
        self.study = self.make_study(
            identifier=STUDY_IDENTIFIER,
            file_name=STUDY_FILE_NAME,
            investigation=self.investigation,
            title=STUDY_TITLE,
            description=DEFAULT_DESCRIPTION,
            comments=DEFAULT_COMMENTS,
        )
        # Set up Assay
        self.assay = self.make_assay(
            file_name=ASSAY_FILE_NAME,
            study=self.study,
            tech_platform=ASSAY_TECH_PLATFORM,
            tech_type=ASSAY_TECH_TYPE,
            measurement_type=ASSAY_MEASURE_TYPE,
            arcs=[],
            comments=DEFAULT_COMMENTS,
        )
        # Setup iRODS backend for the test
        self.irods_backend = plugin_api.get_backend_api('omics_irods')

    def test_get_investigation(self):
        """Test get_investigation()"""
        self.assertEqual(
            s_tags.get_investigation(self.project), self.investigation
        )

    def test_get_investigation_no_investigation(self):
        """Test get_investigation() without investigation"""
        self.investigation.delete()
        self.assertEqual(s_tags.get_investigation(self.project), None)

    def test_get_search_item_type_material_types(self):
        """Test get_search_item_type() with material types"""
        for material_type in GENERIC_MATERIAL_TYPES:
            item = {'type': material_type}
            expected = GENERIC_MATERIAL_TYPES[material_type]
            self.assertEqual(s_tags.get_search_item_type(item), expected)

    def test_get_search_item_type_file(self):
        """Test get_search_item_type() with special case 'file'"""
        item = {'type': 'file'}
        self.assertEqual(s_tags.get_search_item_type(item), 'Data File')

    def test_get_irods_tree(self):
        """Test get_irods_tree()"""
        ret = s_tags.get_irods_tree(self.investigation)
        # Assert that IRODS_SAMPLE_COLL exists in the returned string
        self.assertIn(IRODS_SAMPLE_COLL, ret)
        # Assert that study path exists in the returned string
        self.assertIn(self.irods_backend.get_sub_path(self.study), ret)
        # Assert that assay path exists in the returned string
        study_path, assay_path = self.irods_backend.get_sub_path(
            self.assay
        ).split('/')
        self.assertIn(study_path, ret)
        self.assertIn(assay_path, ret)

    def test_get_material_search_url(self):
        """Test get_material_search_url()"""
        item = {'study': self.study, 'name': 'Sample1'}
        url = s_tags.get_material_search_url(item)
        expected = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )
        expected += f'#/study/{self.study.sodar_uuid}/filter/Sample1'
        self.assertEqual(url, expected)

    def test_get_irods_path_with_project(self):
        """Test get_irods_path() with project"""
        expected = self.irods_backend.get_path(self.project)
        self.assertEqual(s_tags.get_irods_path(self.project), expected)

    def test_get_irods_path_with_assay(self):
        """Test get_irods_path() with assay"""
        expected = self.irods_backend.get_path(self.assay)
        self.assertEqual(s_tags.get_irods_path(self.assay), expected)

    def test_get_irods_path_with_project_and_sub_path(self):
        """Test get_irods_path() with project and sub_path"""
        project_path = self.irods_backend.get_path(self.project)
        sub_path = 'subfolder1/subfolder2'
        expected = project_path + '/' + sub_path
        self.assertEqual(
            s_tags.get_irods_path(self.project, sub_path), expected
        )

    def test_get_irods_path_with_assay_and_sub_path(self):
        """Test get_irods_path() with assay and sub_path"""
        assay_path = self.irods_backend.get_path(self.assay)
        sub_path = 'subfolder1/subfolder2'
        expected = assay_path + '/' + sub_path
        self.assertEqual(s_tags.get_irods_path(self.assay, sub_path), expected)

    def test_get_icon_study(self):
        """Test get_icon() with Study"""
        icon_html = s_tags.get_icon(self.study)
        self.assertIn('text-info', icon_html)
        self.assertIn('mdi:folder-table', icon_html)

    def test_get_icon_assay(self):
        """Test get_icon() with Assay"""
        icon_html = s_tags.get_icon(self.assay)
        self.assertIn('text-danger', icon_html)
        self.assertIn('mdi:table-large', icon_html)

    def test_get_isatab_tag_html_tags_in_tag_colors(self):
        """Test get_isatab_tag_html() with tags in TAG_COLORS"""
        isatab = type('MockISATab', (object,), {'tags': TAG_COLORS.keys()})
        tag_html = s_tags.get_isatab_tag_html(isatab)
        for tag, color in TAG_COLORS.items():
            self.assertIn(color, tag_html)

    def test_get_isatab_tag_html_unknown_tag(self):
        """Test get_isatab_tag_html() with an unknown tag"""
        isatab = type('MockISATab', (object,), {'tags': ['UNKNOWN_TAG']})
        tag_html = s_tags.get_isatab_tag_html(isatab)
        self.assertIn(DEFAULT_TAG_COLOR, tag_html)

    def test_get_request_path_html(self):
        """Test get_request_path_html()"""
        req_path = os.path.join(
            self.irods_backend.get_path(self.assay), MISC_FILES_COLL
        )
        request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            path=req_path,
            user=self.user_owner,
        )
        expected = f'<span class="text-muted">/</span>{MISC_FILES_COLL}'
        self.assertEqual(s_tags.get_request_path_html(request), expected)

    def test_get_request_path_html_nested(self):
        """Test get_request_path_html() with nested collections"""
        req_path = os.path.join(
            self.irods_backend.get_path(self.assay), MISC_FILES_COLL, SUB_COLL
        )
        request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            path=req_path,
            user=self.user_owner,
        )
        expected = (
            f'<span class="text-muted">{MISC_FILES_COLL}/</span>{SUB_COLL}'
        )
        self.assertEqual(s_tags.get_request_path_html(request), expected)

    def test_get_request_status_class_valid(self):
        """Test get_request_status_class() with values in REQUEST_STATUS_CLASSES"""
        for status, css_class in REQUEST_STATUS_CLASSES.items():
            irods_request = type(
                'MockIrodsRequest', (object,), {'status': status}
            )
            self.assertEqual(
                s_tags.get_request_status_class(irods_request), css_class
            )

    def test_get_request_status_class_unknown(self):
        """Test get_request_status_class() with unknown status"""
        irods_request = type(
            'MockIrodsRequest', (object,), {'status': 'UNKNOWN'}
        )
        self.assertEqual(s_tags.get_request_status_class(irods_request), '')

    def test_trim_base_path(self):
        """Test trim_base_path() with a realistic iRODS path"""
        prefix = '/base_path'
        path = prefix + '/project/subfolder1/subfolder2'
        expected = '/project/subfolder1/subfolder2'
        self.assertEqual(s_tags.trim_base_path(path, prefix), expected)
