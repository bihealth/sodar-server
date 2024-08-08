"""Tests for Ajax API views in the samplesheets app with Taskflow enabled"""

import json
import os

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

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
            description='description',
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
            description='description',
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
        # Set up POST data
        self.values = {'updated_cells': [], 'verify': True}
        self.values['updated_cells'].append(
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

    def test_update_library_name(self):
        """Test updating library name with no collection or files in iRODS"""
        self.assertEqual(self.library.name, LIBRARY_ID)
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, LIBRARY_ID_EDIT)

    def test_update_library_name_coll(self):
        """Test updating library name with empty collection"""
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertEqual(irods.collections.exists(self.library_path), True)
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, LIBRARY_ID_EDIT)

    def test_update_library_name_file(self):
        """Test updating library name with file in iRODS (should fail)"""
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertEqual(irods.collections.exists(self.library_path), True)
            irods.data_objects.create(
                os.path.join(self.library_path, DATA_OBJ_NAME)
            )
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
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

    def test_update_library_name_file_no_verify(self):
        """Test updating library name with file in iRODS and no verify"""
        self.values['verify'] = False
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertEqual(irods.collections.exists(self.library_path), True)
            irods.data_objects.create(
                os.path.join(self.library_path, DATA_OBJ_NAME)
            )
        self.assay_plugin.update_cache(project=self.project, user=self.user)
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.library.refresh_from_db()
        self.assertEqual(self.library.name, LIBRARY_ID_EDIT)

    def test_update_library_field(self):
        """Test updating library characteristics field with file in iRODS"""
        self.values['updated_cells'][0] = {
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
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
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

    def test_create_request(self):
        """Test creating a delete request on a data object"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], 'ACTIVE')
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    def test_create_exists_same_user(self):
        """Test creating delete request if request for same user exists"""
        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

        with self.login(self.user_contributor):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

    def test_create_exists_as_admin_by_contributor(self):
        """Test creating request as admin if request from contributor exists"""
        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_create_exists_as_contributor_by_contributor2(self):
        """Test creating as contributor if request by contributor2 exists"""
        user_contributor2 = self.make_user('user_contributor2')
        self.make_assignment_taskflow(
            self.project, user_contributor2, self.role_contributor
        )
        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(user_contributor2):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['detail'], 'active request for path already exists'
        )

    def test_create_multiple(self):
        """Test creating multiple delete requests"""
        path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, IRODS_FILE_NAME2 + '.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        with self.login(self.user):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': path2},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 2)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


class TestIrodsDataRequestDeleteAjaxView(IrodsDataRequestViewTestBase):
    """Tests for IrodsDataRequestDeleteAjaxView"""

    def test_delete_request(self):
        """Test GET request for deleting an existing delete request"""
        # Create request
        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self._assert_alert_count(CREATE_ALERT, self.user, 1)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

        # Delete request
        with self.login(self.user_contributor):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

    def test_delete_request_as_admin_by_contributor(self):
        """Test deleting an existing delete request"""
        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')
        self.assertEqual(response.data['status'], None)

    def test_delete_request_as_contributor_by_contributor2(self):
        """Test GET request for deleting an existing delete request"""
        user_contributor2 = self.make_user('user_contributor2')
        self.make_assignment_taskflow(
            self.project, user_contributor2, self.role_contributor
        )
        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(user_contributor2):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data['detail'], 'User not allowed to delete request'
        )

    def test_delete_no_request(self):
        """Test deleting a delete request that doesn't exist"""
        self.assertEqual(IrodsDataRequest.objects.count(), 0)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['detail'], 'Request not found')

    def test_delete_one_of_multiple(self):
        """Test deleting one of multiple requests"""
        path2 = os.path.join(self.assay_path, IRODS_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, IRODS_FILE_NAME2 + '.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

        with self.login(self.user_contributor):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': path2},
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 2)
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)

            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

            self.assertEqual(IrodsDataRequest.objects.count(), 1)
            self._assert_alert_count(CREATE_ALERT, self.user, 1)
            self._assert_alert_count(CREATE_ALERT, self.user_delegate, 1)


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
            description='description',
        )
        # Import investigation
        self.investigation = self.import_isa_from_file(SHEET_PATH, self.project)
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.make_irods_colls(self.investigation)

    def test_get_empty_coll(self):
        """Test GET request for listing an empty collection in iRODS"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 0)

    def test_get_coll_obj(self):
        """Test GET request for listing a collection with a data object"""
        obj_path = os.path.join(self.assay_path, IRODS_FILE_NAME)
        file_obj = self.irods.data_objects.create(obj_path)
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 1)
        list_obj = response.data['irods_data'][0]
        self.assertNotIn('md5_file', list_obj)
        self.assertEqual(file_obj.name, list_obj['name'])
        self.assertEqual(file_obj.path, list_obj['path'])
        self.assertEqual(file_obj.size, 0)

    def test_get_invalid_path(self):
        """Test GET request with invalid path"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path + '/..'},
            )
        self.assertEqual(response.status_code, 400)

    def test_get_coll_not_found(self):
        """Test GET request for listing a collection which doesn't exist"""
        fail_path = self.assay_path + '/' + IRODS_FAIL_COLL
        self.assertEqual(self.irods.collections.exists(fail_path), False)
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': fail_path},
            )
        self.assertEqual(response.status_code, 404)

    def test_get_coll_not_in_project(self):
        """Test GET request for listing a collection not belonging to project"""
        self.assertEqual(
            self.irods.collections.exists(IRODS_NON_PROJECT_PATH), True
        )
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': IRODS_NON_PROJECT_PATH},
            )
        self.assertEqual(response.status_code, 400)

    def test_get_no_access(self):
        """Test GET request for listing with no acces for the iRODS folder"""
        user_new = self.make_user('user_new')
        self.make_assignment(
            self.project, user_new, self.role_contributor
        )  # No taskflow
        with self.login(user_new):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )
        self.assertEqual(response.status_code, 403)

    def test_get_coll_obj_delete_request(self):
        """Test listing collection with data object and delete request"""
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

        with self.login(user_contributor):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()['irods_data']
        self.assertEqual(response_data[0]['name'], IRODS_FILE_NAME)
        self.assertEqual(response_data[0]['path'], obj_path)
        self.assertEqual(
            response_data[0]['irods_request_status'],
            IRODS_REQUEST_STATUS_ACTIVE,
        )
