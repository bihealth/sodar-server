"""Tests for Ajax API views in the samplesheets app with Taskflow enabled"""

import json
import os

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Taskflowbackend dependency
from taskflowbackend.tests.base import TaskflowViewTestBase

from samplesheets.models import GenericMaterial, IrodsDataRequest
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR
from samplesheets.tests.test_views_taskflow import (
    TestIrodsRequestViewsBase,
    SampleSheetTaskflowMixin,
    TEST_FILE_NAME2,
)
from samplesheets.views import IRODS_REQ_CREATE_ALERT as CREATE_ALERT
from samplesheets.views_ajax import ALERT_LIB_FILES_EXIST


table_builder = SampleSheetTableBuilder()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
# Local constants
APP_NAME = 'samplesheets'
GERMLINE_SHEET_PATH = os.path.join(SHEET_DIR, 'bih_germline.zip')
LIBRARY_NAME = 'p1-N1-DNA1-WES1'
LIBRARY_NAME_EDIT = 'p1-N1-DNA1-WES1-EDITED'
LIBRARY_FIELD = 'p1'
LIBRARY_FIELD_EDIT = 'p1-EDITED'
DATA_OBJ_NAME = 'p1-N1.bam'
IRODS_NON_PROJECT_PATH = (
    '/' + settings.IRODS_ZONE + '/home/' + settings.IRODS_USER
)
IRODS_FAIL_COLL = 'xeiJ1Vie'


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
            assay=self.assay, name=LIBRARY_NAME
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
                'value': LIBRARY_NAME_EDIT,
                'colType': 'NAME',
                'header_name': 'Name',
                'header_type': 'name',
                'header_field': 'col51',
                'obj_cls': 'GenericMaterial',
                'item_type': 'MATERIAL',
                'og_value': LIBRARY_NAME,
            }
        )

    def test_update_library_name(self):
        """Test updating library name with no collection or files in iRODS"""
        self.assertEqual(self.library.name, LIBRARY_NAME)
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
        self.assertEqual(self.library.name, LIBRARY_NAME_EDIT)

    def test_update_library_name_coll(self):
        """Test updating library name with empty collection"""
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertIsNotNone(irods.collections.get(self.library_path))
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
        self.assertEqual(self.library.name, LIBRARY_NAME_EDIT)

    def test_update_library_name_file(self):
        """Test updating library name with file in iRODS (should fail)"""
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertIsNotNone(irods.collections.get(self.library_path))
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
        self.assertEqual(self.library.name, LIBRARY_NAME)

    def test_update_library_name_file_no_verify(self):
        """Test updating library name with file in iRODS and no verify"""
        self.values['verify'] = False
        with self.irods_backend.get_session() as irods:
            irods.collections.create(self.library_path)
            self.assertIsNotNone(irods.collections.get(self.library_path))
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
        self.assertEqual(self.library.name, LIBRARY_NAME_EDIT)

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
            self.assertIsNotNone(irods.collections.get(self.library_path))
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


class TestIrodsRequestCreateAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestCreateAjaxView"""

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
        with self.login(self.user_contrib):
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

        with self.login(self.user_contrib):
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
        with self.login(self.user_contrib):
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
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib2):
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
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
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


class TestIrodsRequestDeleteAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsRequestDeleteAjaxView"""

    def test_delete_request(self):
        """Test GET request for deleting an existing delete request"""
        # Create request
        with self.login(self.user_contrib):
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
        with self.login(self.user_contrib):
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
        with self.login(self.user_contrib):
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
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )

        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        # Delete request
        with self.login(self.user_contrib2):
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
        path2 = os.path.join(self.assay_path, TEST_FILE_NAME2)
        path2_md5 = os.path.join(self.assay_path, TEST_FILE_NAME2 + '.md5')
        self.irods.data_objects.create(path2)
        self.irods.data_objects.create(path2_md5)

        self.assertEqual(IrodsDataRequest.objects.count(), 0)
        self._assert_alert_count(CREATE_ALERT, self.user, 0)
        self._assert_alert_count(CREATE_ALERT, self.user_delegate, 0)

        with self.login(self.user_contrib):
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


class TestIrodsObjectListAjaxView(TestIrodsRequestViewsBase):
    """Tests for IrodsObjectListAjaxView"""

    def test_get_empty_coll(self):
        """Test GET request for listing an empty collection in iRODS"""
        self.irods.data_objects.unlink(self.obj_path, force=True)
        self.irods.data_objects.unlink(self.obj_path_md5, force=True)
        self.irods.data_objects.unlink(self.obj_path2, force=True)
        self.irods.data_objects.unlink(self.obj_path2_md5, force=True)
        self.assertEqual(self.irods.data_objects.exists(self.obj_path), False)
        self.assertEqual(
            self.irods.data_objects.exists(self.obj_path_md5), False
        )
        self.assertEqual(self.irods.data_objects.exists(self.obj_path2), False)
        self.assertEqual(
            self.irods.data_objects.exists(self.obj_path2_md5), False
        )
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
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['irods_data']), 2)
        list_obj = response.data['irods_data'][0]
        self.assertNotIn('md5_file', list_obj)
        self.assertEqual(self.file_obj.name, list_obj['name'])
        self.assertEqual(self.file_obj.path, list_obj['path'])
        self.assertEqual(self.file_obj.size, 0)

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
        new_user = self.make_user('new_user')
        self.make_assignment(
            self.project, new_user, self.role_contributor
        )  # No taskflow
        with self.login(new_user):
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
        # Create request
        with self.login(self.user_contrib):
            self.client.post(
                reverse(
                    'samplesheets:ajax_irods_request_create',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.obj_path},
            )
        self.assertEqual(IrodsDataRequest.objects.count(), 1)

        with self.login(self.user_contrib):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_irods_objects',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                data={'path': self.assay_path},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['irods_data'][0]['name'], 'test1')
        self.assertEqual(
            response.json()['irods_data'][0]['path'], self.obj_path
        )
        self.assertEqual(
            response.json()['irods_data'][0]['irods_request_status'],
            'ACTIVE',
        )
