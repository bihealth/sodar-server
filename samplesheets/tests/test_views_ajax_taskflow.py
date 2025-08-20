"""Tests for Ajax API views in the samplesheets app with Taskflow enabled"""

import json
import os

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.tests.base import (
    TaskflowViewTestBase,
    HASH_SCHEME_MD5,
    HASH_SCHEME_SHA256,
)

from samplesheets.models import (
    GenericMaterial,
    IrodsDataRequest,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_models import IrodsDataRequestMixin
from samplesheets.tests.test_views_taskflow import (
    IrodsDataRequestViewTestBase,
    SampleSheetTaskflowMixin,
    IRODS_FILE_NAME,
    IRODS_FILE_NAME2,
    SHEET_PATH,
)
from samplesheets.views import IRODS_REQUEST_EVENT_CREATE as CREATE_ALERT
from samplesheets.views_ajax import ALERT_LIB_FILES_EXIST


app_settings = AppSettingAPI()
table_builder = SampleSheetTableBuilder()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
# Local constants
APP_NAME = 'samplesheets'
GERMLINE_SHEET_PATH = os.path.join(SHEET_DIR, 'bih_germline.zip')
SAMPLE_ID = 'p1-N1'
FAMILY_ID = 'FAM_p1'
LIBRARY_ID = 'p1-N1-DNA1-WES1'
LIBRARY_ID_EDIT = 'p1-N1-DNA1-WES1-EDITED'
LIBRARY_FIELD = 'p1'
LIBRARY_FIELD_EDIT = 'p1-EDITED'
DATA_OBJ_NAME = 'p1-N1.bam'
IRODS_NON_PROJECT_PATH = (
    '/' + settings.IRODS_ZONE + '/home/' + settings.IRODS_USER
)
IRODS_FAIL_COLL = 'xeiJ1Vie'


class TestStudyLinksAjaxView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowViewTestBase
):
    """Tests for StudyLinksAjaxView with iRODS and taskflow"""

    def setUp(self):
        super().setUp()
        # Make project with owner
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(
            GERMLINE_SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Set up other variables
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.source_path = os.path.join(self.assay_path, LIBRARY_ID)
        self.url = reverse(
            'samplesheets:ajax_study_links',
            kwargs={'study': self.study.sodar_uuid},
        ) + '?family={}'.format(FAMILY_ID)

    def test_get(self):
        """Test StudyLinksAjaxView GET with no files in iRODS"""
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rd = response.data
        self.assertEqual(rd['data']['session']['files'], [])
        self.assertEqual(rd['data']['bam']['files'], [])
        self.assertEqual(rd['data']['vcf']['files'], [])
        omit_bam = app_settings.get(
            APP_NAME, 'igv_omit_bam', project=self.project
        )
        omit_vcf = app_settings.get(
            APP_NAME, 'igv_omit_vcf', project=self.project
        )
        self.assertEqual(rd['data']['bam']['omit_info'], omit_bam)
        self.assertEqual(rd['data']['vcf']['omit_info'], omit_vcf)
        self.assertNotIn('error', rd)

    def test_get_files(self):
        """Test GET with files in iRODS"""
        self.irods.collections.create(self.source_path)
        bam_path = os.path.join(
            self.source_path, '{}_test.bam'.format(SAMPLE_ID)
        )
        vcf_path = os.path.join(
            self.source_path, '{}_test.vcf.gz'.format(FAMILY_ID)
        )
        self.irods.data_objects.create(bam_path)
        self.irods.data_objects.create(vcf_path)
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rd = response.data
        # NOTE: Link content tested in TestGermlinePlugin
        self.assertEqual(len(rd['data']['session']['files']), 1)
        self.assertEqual(len(rd['data']['bam']['files']), 1)
        self.assertEqual(len(rd['data']['vcf']['files']), 1)
        self.assertIsNotNone(rd['data']['bam']['omit_info'])
        self.assertIsNotNone(rd['data']['vcf']['omit_info'])
        self.assertNotIn('error', rd)

    def test_get_no_empty_omit_values(self):
        """Test GET with empty BAM/VCF omit values"""
        app_settings.set(APP_NAME, 'igv_omit_bam', '', project=self.project)
        app_settings.set(APP_NAME, 'igv_omit_vcf', '', project=self.project)
        with self.login(self.user):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        rd = response.data
        self.assertEqual(rd['data']['bam']['omit_info'], '')
        self.assertEqual(rd['data']['vcf']['omit_info'], '')


class TestSheetCellEditAjaxView(
    SampleSheetIOMixin, SampleSheetTaskflowMixin, TaskflowViewTestBase
):
    """Tests for SheetCellEditAjaxView with iRODS and taskflow"""

    def setUp(self):
        super().setUp()
        # Make project with owner
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(
            GERMLINE_SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.assay_plugin = self.assay.get_plugin()
        # Set up library
        self.library = GenericMaterial.objects.get(
            assay=self.assay, name=LIBRARY_ID
        )
        self.library_path = os.path.join(
            self.irods_backend.get_path(self.assay), self.library.name
        )
        # Create iRODS collections
        self.make_irods_colls(self.investigation)
        # Set up URL and data
        self.url = reverse(
            'samplesheets:ajax_edit_cell',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.post_data = {'updated_cells': [], 'verify': True}
        self.post_data['updated_cells'].append(
            {
                'uuid': str(self.library.sodar_uuid),
                'value': LIBRARY_ID_EDIT,
                'colType': 'NAME',
                'header_name': 'Name',
                'header_type': 'name',
                'header_field': 'col51',
                'obj_cls': 'GenericMaterial',
                'item_type': 'MATERIAL',
                'og_value': LIBRARY_ID,
            }
        )

    def test_post_library_name(self):
        """Test SheetCellEditAjaxView POST for library name with no collection or files in iRODS"""
        self.assertEqual(self.library.name, LIBRARY_ID)
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                self.url,
                json.dumps(self.post_data),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, LIBRARY_ID_EDIT)

    def test_post_library_name_coll(self):
        """Test POST for library name with empty collection"""
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertEqual(irods.collections.exists(self.library_path), True)
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                self.url,
                json.dumps(self.post_data),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, LIBRARY_ID_EDIT)

    def test_post_library_name_file(self):
        """Test POST for library name with file in iRODS (should fail)"""
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertEqual(irods.collections.exists(self.library_path), True)
            irods.data_objects.create(
                os.path.join(self.library_path, DATA_OBJ_NAME)
            )
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                self.url,
                json.dumps(self.post_data),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'alert')
        self.assertEqual(
            response.data['alert_msg'],
            ALERT_LIB_FILES_EXIST.format(name=self.library.name),
        )
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, LIBRARY_ID)

    def test_post_library_name_file_no_verify(self):
        """Test POST for library name with file in iRODS and no verify"""
        self.post_data['verify'] = False
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertEqual(irods.collections.exists(self.library_path), True)
            irods.data_objects.create(
                os.path.join(self.library_path, DATA_OBJ_NAME)
            )
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                self.url,
                json.dumps(self.post_data),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, LIBRARY_ID_EDIT)

    def test_post_library_field(self):
        """Test POST for library characteristics field with file in iRODS"""
        self.post_data['updated_cells'][0] = {
            'uuid': str(self.library.sodar_uuid),
            'value': LIBRARY_FIELD_EDIT,
            'colType': 'NAME',
            'header_name': 'Folder name',
            'header_type': 'characteristics',
            'header_field': 'col52',
            'obj_cls': 'GenericMaterial',
            'item_type': 'MATERIAL',
            'og_value': LIBRARY_FIELD,
        }
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertEqual(irods.collections.exists(self.library_path), True)
            irods.data_objects.create(
                os.path.join(self.library_path, DATA_OBJ_NAME)
            )
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                self.url,
                json.dumps(self.post_data),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        # Not updating name = this is OK
        self.assertEqual(response.data['detail'], 'ok')
        self.library.refresh_from_db()
        self.assertEqual(
            self.library.characteristics['Folder name']['value'],
            LIBRARY_FIELD_EDIT,
        )


class TestIrodsDataRequestCreateAjaxView(IrodsDataRequestViewTestBase):
    """Tests for IrodsDataRequestCreateAjaxView"""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            'samplesheets:ajax_irods_request_create',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.get_data = {'path': self.obj_path}

    def test_post(self):
        """Test IrodsDataRequestCreateAjaxView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        with self.login(self.user):
            response = self.client.post(self.url, self.get_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], 'ACTIVE')
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    def test_post_exists_same_user(self):
        """Test POST with existing request for same user"""
        with self.login(self.user_contributor):
            self.client.post(self.url, self.get_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        with self.login(self.user_contributor):
            response = self.client.post(self.url, self.get_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    def test_post_exists_as_admin_by_contributor(self):
        """Test POST as admin with request from contributor"""
        with self.login(self.user_contributor):
            self.client.post(self.url, self.get_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        with self.login(self.user):
            response = self.client.post(self.url, self.get_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_post_exists_as_contributor_by_contributor2(self):
        """Test POST as contributor with request from contributor2"""
        user_contributor2 = self.make_user('user_contributor2')
        self.make_assignment_taskflow(
            self.project, user_contributor2, self.role_contributor
        )
        with self.login(self.user_contributor):
            self.client.post(self.url, self.get_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        with self.login(user_contributor2):
            response = self.client.post(self.url, self.get_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_post_multiple(self):
        """Test POST to create multiple delete requests"""
        obj_path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.irods.data_objects.create(obj_path2)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)
        with self.login(self.user):
            self.client.post(self.url, self.get_data)
        with self.login(self.user):
            self.client.post(self.url, {'path': obj_path2})
        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


class TestIrodsDataRequestDeleteAjaxView(IrodsDataRequestViewTestBase):
    """Tests for IrodsDataRequestDeleteAjaxView"""

    def setUp(self):
        super().setUp()
        self.post_data = {'path': self.obj_path}
        # Create request
        # TODO: Why use POST for request creation?
        # TODO: Couldn't this be in test_views_ajax without Taskflow needed?
        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                self.post_data,
            )
        self.url = reverse(
            'samplesheets:ajax_irods_request_delete',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_post(self):
        """Test IrodsDataRequestDeleteAjaxView POST"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)
        with self.login(self.user_contributor):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

    def test_post_as_admin_by_contributor(self):
        """Test POST as admin with request by contributor"""
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        # Delete request
        with self.login(self.user):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)

    def test_post_as_contributor_by_contributor2(self):
        """Test POST as contributor with request by contributor"""
        user_contributor2 = self.make_user('user_contributor2')
        self.make_assignment_taskflow(
            self.project, user_contributor2, self.role_contributor
        )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        with self.login(user_contributor2):
            response = self.client.post(self.url, self.post_data)
        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data['detail'], 'User not allowed to delete request'
        )

    def test_post_non_existent(self):
        """Test POST on non-existent request"""
        obj_path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        self.irods.data_objects.create(obj_path2)
        with self.login(self.user):
            response = self.client.post(self.url, {'path': obj_path2})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['detail'], 'Request not found')


class TestIrodsObjectListAjaxView(
    SampleSheetIOMixin,
    SampleSheetTaskflowMixin,
    IrodsDataRequestMixin,
    TaskflowViewTestBase,
):
    """Tests for IrodsObjectListAjaxView"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.make_irods_colls(self.investigation)
        self.url = reverse(
            'samplesheets:ajax_irods_objects',
            kwargs={'project': self.project.sodar_uuid},
        )

    def test_get_empty_coll(self):
        """Test IrodsObjectListAjaxView GET with empty collection"""
        data = {'path': self.assay_path}
        with self.login(self.user):
            response = self.client.get(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 0)

    def test_get_coll_obj(self):
        """Test GET with data objects in collection"""
        obj_path = os.path.join(self.assay_path, IRODS_FILE_NAME)
        file_obj = self.irods.data_objects.create(obj_path)
        self.make_checksum_object(file_obj, HASH_SCHEME_MD5)
        self.make_checksum_object(file_obj, HASH_SCHEME_SHA256)
        self.assertTrue(self.irods.data_objects.exists(obj_path))
        self.assertTrue(self.irods.data_objects.exists(obj_path + '.md5'))
        self.assertTrue(self.irods.data_objects.exists(obj_path + '.sha256'))
        data = {'path': self.assay_path}
        with self.login(self.user):
            response = self.client.get(self.url, data)
        self.assertEqual(response.status_code, 200)
        # Checksum objects should not be returned
        self.assertEqual(len(response.data['irods_data']), 1)
        list_obj = response.data['irods_data'][0]
        self.assertEqual(file_obj.name, list_obj['name'])
        self.assertEqual(file_obj.path, list_obj['path'])
        self.assertEqual(file_obj.size, 0)

    def test_get_invalid_path(self):
        """Test GET with invalid path"""
        data = {'path': self.assay_path + '/..'}
        with self.login(self.user):
            response = self.client.get(self.url, data)
        self.assertEqual(response.status_code, 400)

    def test_get_coll_not_found(self):
        """Test GET with non-existent collection"""
        fail_path = self.assay_path + '/' + IRODS_FAIL_COLL
        self.assertEqual(self.irods.collections.exists(fail_path), False)
        data = {'path': fail_path}
        with self.login(self.user):
            response = self.client.get(self.url, data)
        self.assertEqual(response.status_code, 404)

    def test_get_coll_not_in_project(self):
        """Test GET for collection not in project"""
        self.assertEqual(
            self.irods.collections.exists(IRODS_NON_PROJECT_PATH), True
        )
        data = {'path': IRODS_NON_PROJECT_PATH}
        with self.login(self.user):
            response = self.client.get(self.url, data)
        self.assertEqual(response.status_code, 400)

    def test_get_no_access(self):
        """Test GET with no access to collection"""
        user_new = self.make_user('user_new')
        self.make_assignment(
            self.project, user_new, self.role_contributor
        )  # No taskflow
        data = {'path': self.assay_path}
        with self.login(user_new):
            response = self.client.get(self.url, data)
        self.assertEqual(response.status_code, 403)

    def test_get_coll_obj_delete_request(self):
        """Test GET with delete request for data object"""
        user_contributor = self.make_user('user_contributor')
        self.make_assignment_taskflow(
            self.project, user_contributor, self.role_contributor
        )
        obj_path = os.path.join(self.assay_path, IRODS_FILE_NAME)
        self.irods.data_objects.create(obj_path)
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=obj_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            user=user_contributor,
            description='',
        )

        data = {'path': self.assay_path}
        with self.login(user_contributor):
            response = self.client.get(self.url, data)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()['irods_data']
        self.assertEqual(response_data[0]['name'], IRODS_FILE_NAME)
        self.assertEqual(response_data[0]['path'], obj_path)
        self.assertEqual(
            response_data[0]['irods_request_status'],
            IRODS_REQUEST_STATUS_ACTIVE,
        )
