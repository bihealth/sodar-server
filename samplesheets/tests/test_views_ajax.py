"""Tests for Ajax API views in the samplesheets app"""

from altamisa.constants import table_headers as th
import json
import os
from unittest.case import skipIf

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import get_backend_api

# Timeline dependency
from timeline.models import ProjectEvent

from samplesheets.models import (
    Study,
    Assay,
    Protocol,
    Process,
    GenericMaterial,
    ISATab,
)
from samplesheets.sheet_config import SheetConfigAPI
from samplesheets.tests.test_sheet_config import (
    SheetConfigMixin,
    CONFIG_STUDY_UUID,
)
from samplesheets.tests.test_views import (
    IRODS_BACKEND_ENABLED,
    IRODS_BACKEND_SKIP_MSG,
    TestViewsBase,
    SHEET_DIR_SPECIAL,
    SHEET_PATH,
    app_settings,
    EDIT_NEW_VALUE_STR,
    CONFIG_DATA_DEFAULT,
)
from samplesheets.utils import get_node_obj


conf_api = SheetConfigAPI()


APP_NAME = 'samplesheets'

# Local constants
EDIT_DIR = os.path.dirname(__file__) + '/edit/'
STUDY_INSERT_PATH = EDIT_DIR + 'i_small_study_insert.json'
ASSAY_INSERT_PATH = EDIT_DIR + 'i_small_assay_insert.json'
STUDY_DELETE_PATH = EDIT_DIR + 'i_small_study_delete.json'
ASSAY_DELETE_PATH = EDIT_DIR + 'i_small_assay_delete.json'
EDIT_SOURCE_NAME = '0818'
EDIT_SOURCE_UUID = '11111111-1111-1111-1111-000000000000'
EDIT_STUDY_PROC_UUID = '11111111-1111-1111-1111-000000000001'
EDIT_SAMPLE_NAME = '0818-N1'
EDIT_SAMPLE_UUID = '11111111-1111-1111-5555-000000000000'
SHEET_PATH_INSERTED = SHEET_DIR_SPECIAL + 'i_small_insert.zip'


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestContextAjaxView(TestViewsBase):
    """Tests for SampleSheetContextAjaxView"""

    # TODO: Test with realistic ISAtab examples using BIH configs (see #434)

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods')

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test context retrieval with example sheet"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_context',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        response_data.pop('csrf_token')  # HACK

        expected = {
            'configuration': self.investigation.get_configuration(),
            'inv_file_name': self.investigation.file_name.split('/')[-1],
            'irods_status': False,
            'parser_version': self.investigation.parser_version,
            'irods_backend_enabled': True if self.irods_backend else False,
            'parser_warnings': True
            if self.investigation.parser_warnings
            else False,
            'irods_webdav_enabled': settings.IRODS_WEBDAV_ENABLED,
            'irods_webdav_url': settings.IRODS_WEBDAV_URL,
            'external_link_labels': settings.SHEETS_EXTERNAL_LINK_LABELS,
            'table_height': settings.SHEETS_TABLE_HEIGHT,
            'min_col_width': settings.SHEETS_MIN_COLUMN_WIDTH,
            'max_col_width': settings.SHEETS_MAX_COLUMN_WIDTH,
            'allow_editing': app_settings.get_default_setting(
                APP_NAME, 'allow_editing'
            ),
            'alerts': [],
            'investigation': {
                'identifier': self.investigation.identifier,
                'title': self.investigation.title,
                'description': None,
                'comments': None,
            },
            'studies': {
                str(self.study.sodar_uuid): {
                    'display_name': self.study.get_display_name(),
                    'identifier': self.study.identifier,
                    'description': self.study.description,
                    'comments': self.study.comments,
                    'irods_path': self.irods_backend.get_path(self.study),
                    'table_url': response.wsgi_request.build_absolute_uri(
                        reverse(
                            'samplesheets:ajax_study_tables',
                            kwargs={'study': str(self.study.sodar_uuid)},
                        )
                    ),
                    'plugin': None,
                    'assays': {
                        str(self.assay.sodar_uuid): {
                            'name': self.assay.get_name(),
                            'display_name': self.assay.get_display_name(),
                            'irods_path': self.irods_backend.get_path(
                                self.assay
                            ),
                            'display_row_links': True,
                            'plugin': None,
                        }
                    },
                }
            },
            'perms': {
                'edit_sheet': True,
                'manage_sheet': True,
                'create_colls': True,
                'export_sheet': True,
                'delete_sheet': True,
                'is_superuser': True,
            },
            'sheet_stats': {
                'study_count': Study.objects.filter(
                    investigation=self.investigation
                ).count(),
                'assay_count': Assay.objects.filter(
                    study__investigation=self.investigation
                ).count(),
                'protocol_count': Protocol.objects.filter(
                    study__investigation=self.investigation
                ).count(),
                'process_count': Process.objects.filter(
                    protocol__study__investigation=self.investigation
                ).count(),
                'source_count': self.investigation.get_material_count('SOURCE'),
                'material_count': self.investigation.get_material_count(
                    'MATERIAL'
                ),
                'sample_count': self.investigation.get_material_count('SAMPLE'),
                'data_count': self.investigation.get_material_count('DATA'),
            },
        }
        self.assertEqual(response_data, expected)


class TestStudyTablesAjaxView(TestViewsBase):
    """Tests for SampleSheetStudyTablesAjaxView"""

    # TODO: Test with realistic ISAtab examples using BIH configs (see #434)

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Allow sample sheet editing in project
        app_settings.set_app_setting(
            APP_NAME, 'allow_editing', True, project=self.project
        )

    def test_get(self):
        """Test study tables retrieval"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_study_tables',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)

        # Assert return data correctness
        ret_data = response.data
        self.assertIn('study', ret_data)
        self.assertIn('tables', ret_data)
        self.assertNotIn('render_error', ret_data)
        self.assertNotIn('shortcuts', ret_data['tables']['study'])
        self.assertEqual(len(ret_data['tables']['assays']), 1)
        self.assertNotIn(
            'uuid', ret_data['tables']['study']['table_data'][0][0]
        )
        self.assertIn('display_config', ret_data)
        self.assertNotIn('edit_context', ret_data)

    def test_get_edit(self):
        """Test study tables retrieval with edit mode enabled"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_study_tables',
                    kwargs={'study': self.study.sodar_uuid},
                ),
                {'edit': 1},
            )

        self.assertEqual(response.status_code, 200)

        # Assert return data correctness
        ret_data = response.data
        self.assertIn('study', ret_data)
        self.assertIn('tables', ret_data)
        self.assertNotIn('render_error', ret_data)
        self.assertNotIn('shortcuts', ret_data['tables']['study'])
        self.assertEqual(len(ret_data['tables']['assays']), 1)
        self.assertIn('uuid', ret_data['tables']['study']['table_data'][0][0])
        self.assertIn('display_config', ret_data)
        self.assertIn('study_config', ret_data)
        self.assertIn('edit_context', ret_data)
        self.assertIsNotNone(ret_data['edit_context']['samples'])
        self.assertIsNotNone(ret_data['edit_context']['protocols'])


class TestStudyLinksAjaxView(TestViewsBase):
    """Tests for SampleSheetStudyLinksAjaxView"""

    # TODO: Test with realistic ISAtab examples using BIH configs (see #434)

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_get(self):
        """Test study links retrieval without plugin"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_study_links',
                    kwargs={'study': self.study.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 404)  # No plugin for test ISAtab


class TestSampleSheetWarningsAjaxView(TestViewsBase):
    """Tests for SampleSheetWarningsAjaxView"""

    # TODO: Test with realistic ISAtab examples using BIH configs (see #434)

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )

    def test_get(self):
        """Test study tables retrieval"""
        with self.login(self.user):
            response = self.client.get(
                reverse(
                    'samplesheets:ajax_warnings',
                    kwargs={'project': self.project.sodar_uuid},
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['warnings'], self.investigation.parser_warnings
        )


class TestSampleSheetEditAjaxView(TestViewsBase):
    """Tests for SampleSheetEditAjaxView"""

    # TODO: Test with multiple cells
    # TODO: Test with realistic ISAtab examples using BIH configs (see #434)
    # TODO: Add helper to create update data
    # TODO: Test all value types
    # TODO: Unify tests once saving a list of values is implemented

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

        # Set up POST data
        self.values = {'updated_cells': []}

    def test_edit_name(self):
        """Test editing the name of a material"""
        obj = GenericMaterial.objects.get(study=self.study, name='0816')
        new_name = '0816aaa'

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': 'name',
                'header_type': 'name',
                'obj_cls': 'GenericMaterial',
                'value': new_name,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.name, new_name)

    def test_edit_name_empty(self):
        """Test setting an empty material name (should fail)"""
        obj = GenericMaterial.objects.get(study=self.study, name='0816')

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': 'name',
                'header_type': 'name',
                'obj_cls': 'GenericMaterial',
                'value': '',
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 500)
        obj.refresh_from_db()
        self.assertEqual(obj.name, '0816')

    def test_edit_performer(self):
        """Test editing the performer of a process"""
        obj = Process.objects.filter(study=self.study, assay=None).first()
        value = 'Alice Example <alice@example.com>'

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': 'Performer',
                'header_type': 'performer',
                'obj_cls': 'Process',
                'value': value,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.performer, value)

    def test_edit_perform_date(self):
        """Test editing the perform date of a process"""
        obj = Process.objects.filter(study=self.study, assay=None).first()
        value = '2020-07-07'

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': 'Perform date',
                'header_type': 'perform_date',
                'obj_cls': 'Process',
                'value': value,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.perform_date.strftime('%Y-%m-%d'), value)

    def test_edit_perform_date_empty(self):
        """Test editing the perform date of a process with an empty date"""
        obj = Process.objects.filter(study=self.study, assay=None).first()
        value = ''

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': 'Perform date',
                'header_type': 'perform_date',
                'obj_cls': 'Process',
                'value': value,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertIsNone(obj.perform_date)

    def test_edit_perform_date_invalid(self):
        """Test editing the perform date of a process with an invalid date"""
        obj = Process.objects.filter(study=self.study, assay=None).first()
        og_date = obj.perform_date
        value = '2020-11-31'

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': 'Perform date',
                'header_type': 'perform_date',
                'obj_cls': 'Process',
                'value': value,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 500)  # TODO: Should be 400?
        obj.refresh_from_db()
        self.assertEqual(obj.perform_date, og_date)

    def test_edit_characteristics_str(self):
        """Test editing a characteristics string value in a material"""
        obj = GenericMaterial.objects.get(study=self.study, name='0816')
        header_name = 'organism'

        # Assert preconditions
        self.assertNotEqual(
            obj.characteristics[header_name], EDIT_NEW_VALUE_STR
        )

        # TODO: Add complete set of params once they have been refactored
        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': header_name,
                'header_type': 'characteristics',
                'obj_cls': 'GenericMaterial',
                'value': EDIT_NEW_VALUE_STR,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(
            obj.characteristics[header_name],
            {'unit': None, 'value': EDIT_NEW_VALUE_STR},
        )

    def test_edit_param_values_str(self):
        """Test editing a parameter values string value in a process"""
        obj = Process.objects.filter(study=self.study, assay=None).first()
        header_name = 'instrument'

        # Assert preconditions
        self.assertNotEqual(
            obj.parameter_values[header_name], EDIT_NEW_VALUE_STR
        )

        # TODO: Add complete set of params once they have been refactored
        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': header_name,
                'header_type': 'parameter_values',
                'obj_cls': 'Process',
                'value': EDIT_NEW_VALUE_STR,
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(
            obj.parameter_values[header_name],
            {'unit': None, 'value': EDIT_NEW_VALUE_STR},
        )

    def test_edit_protocol(self):
        """Test editing the protocol reference of a process"""

        obj = Process.objects.filter(
            study=self.study, unique_name__icontains='sample collection'
        ).first()
        new_protocol = Protocol.objects.exclude(
            sodar_uuid=obj.protocol.sodar_uuid
        ).first()

        # Assert preconditions
        self.assertIsNotNone(new_protocol)
        self.assertNotEqual(obj.protocol, new_protocol)

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': 'protocol',
                'header_type': 'protocol',
                'obj_cls': 'Process',
                'value': new_protocol.name,
                'uuid_ref': str(new_protocol.sodar_uuid),
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.protocol, new_protocol)

    def test_edit_process_name(self):
        """Test editing the name of a process"""

        obj = Process.objects.filter(
            study=self.study, unique_name__icontains='sample collection'
        ).first()
        name_type = th.DATA_TRANSFORMATION_NAME
        name = 'New Process'

        # Assert preconditions
        self.assertNotEqual(obj.name, name)
        self.assertNotEqual(obj.name_type, name_type)

        self.values['updated_cells'].append(
            {
                'uuid': str(obj.sodar_uuid),
                'header_name': name_type,
                'header_type': 'process_name',
                'obj_cls': 'Process',
                'value': name,
                'uuid_ref': str(obj.sodar_uuid),
            }
        )

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_cell',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.name, name)
        self.assertEqual(obj.name_type, name_type)


class TestSheetRowInsertAjaxView(SheetConfigMixin, TestViewsBase):
    """Tests for SheetRowInsertAjaxView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        # Set up UUIDs and default config
        self._update_uuids(self.investigation, CONFIG_DATA_DEFAULT)
        app_settings.set_app_setting(
            APP_NAME,
            'sheet_config',
            conf_api.build_sheet_config(self.investigation),
            project=self.project,
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Set up POST data
        self.values = {'new_row': {}}

    def test_insert_study_row(self):
        """Test inserting a new row into a study"""

        # Assert preconditions
        self.assertIsNone(
            GenericMaterial.objects.filter(
                study=self.study, name='0818'
            ).first()
        )

        process_pks = [
            p.pk for p in Process.objects.filter(study=self.study, assay=None)
        ]
        protocol = Protocol.objects.get(
            study=self.study, name='sample collection'
        )

        with open(STUDY_INSERT_PATH) as fp:
            self.values['new_row'] = json.load(fp)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_row_insert',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)

        source = GenericMaterial.objects.get(
            study=self.study, name='0818', item_type='SOURCE'
        )
        self.assertEqual(source.characteristics['age']['value'], '170')
        self.assertEqual(source.characteristics['age']['unit']['name'], 'day')

        process = (
            Process.objects.filter(study=self.study, assay=None)
            .exclude(pk__in=process_pks)
            .first()
        )
        self.assertIsNotNone(process)
        self.assertEqual(process.protocol, protocol)
        self.assertEqual(
            process.parameter_values['instrument']['value'], 'scalpel'
        )
        self.assertEqual(process.performer, 'John Doe')
        self.assertEqual(
            process.perform_date.strftime('%Y-%m-%d'), '2020-09-03'
        )

        sample = GenericMaterial.objects.get(
            study=self.study, name=EDIT_SAMPLE_NAME, item_type='SAMPLE'
        )
        self.assertEqual(sample.characteristics['status']['value'], '0')
        self.assertEqual(sample.factor_values['treatment']['value'], 'yes')

    def test_insert_assay_row(self):
        """Test inserting a new row into an assay"""

        # Insert study row
        with open(STUDY_INSERT_PATH) as fp:
            self.values['new_row'] = json.load(fp)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_row_insert',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)

        # Update sample UUID
        sample = GenericMaterial.objects.get(
            study=self.study, name=EDIT_SAMPLE_NAME
        )
        sample.sodar_uuid = EDIT_SAMPLE_UUID
        sample.save()

        # Insert assay row
        with open(ASSAY_INSERT_PATH) as fp:
            self.values['new_row'] = json.load(fp)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_row_insert',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        self.assay.refresh_from_db()
        node_names = []

        for uuid in response.data['node_uuids']:
            obj = GenericMaterial.objects.filter(sodar_uuid=uuid).first()

            if not obj:
                obj = Process.objects.filter(sodar_uuid=uuid).first()

            self.assertIsNotNone(obj)
            node_names.append(obj.unique_name)

        for i in range(len(node_names) - 1):
            self.assertIn([node_names[i], node_names[i + 1]], self.assay.arcs)


class TestSheetRowDeleteAjaxView(SheetConfigMixin, TestViewsBase):
    """Tests for SheetRowDeleteAjaxView"""

    def setUp(self):
        super().setUp()

        # Import investigation where extra rows have been inserted
        self.investigation = self._import_isa_from_file(
            SHEET_PATH_INSERTED, self.project
        )
        # Set up UUIDs and default config
        self._update_uuids(self.investigation, CONFIG_DATA_DEFAULT)
        app_settings.set_app_setting(
            APP_NAME,
            'sheet_config',
            conf_api.build_sheet_config(self.investigation),
            project=self.project,
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

        # Update UUIDs in study
        source = GenericMaterial.objects.get(
            study=self.study, name=EDIT_SOURCE_NAME
        )
        source.sodar_uuid = EDIT_SOURCE_UUID
        source.save()

        proc = (
            Process.objects.filter(
                study=self.study, assay=None, protocol__name='sample collection'
            )
            .order_by('-pk')
            .first()
        )
        proc.sodar_uuid = EDIT_STUDY_PROC_UUID
        proc.save()

        # Update UUIDs in assay
        self.row_uuids = [
            '22222222-2222-2222-2222-00000000000' + str(i) for i in range(1, 8)
        ]
        self.row_names = []

        n_uuid = EDIT_SAMPLE_UUID
        u_name = GenericMaterial.objects.get(
            study=self.study, name=EDIT_SAMPLE_NAME
        ).unique_name

        for i in range(len(self.row_uuids) + 1):
            obj = get_node_obj(study=self.study, unique_name=u_name)
            obj.sodar_uuid = n_uuid
            obj.save()

            if i < len(self.row_uuids):
                for a in self.assay.arcs:
                    if a[0] == u_name:
                        u_name = a[1]
                        self.row_names.append(a[1])
                        break
                n_uuid = self.row_uuids[i]

        # Set up POST data
        self.values = {'del_row': {}}

    def test_delete_assay_row(self):
        """Test row deletion from assay"""

        with open(ASSAY_DELETE_PATH) as fp:
            self.values['del_row'] = json.load(fp)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_row_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        self.assay.refresh_from_db()
        self.assertIsNotNone(
            GenericMaterial.objects.filter(
                study=self.study, name=EDIT_SAMPLE_NAME
            ).first()
        )

        for u in self.row_uuids:
            self.assertIsNone(get_node_obj(study=self.study, sodar_uuid=u))

        target_nodes = [a[1] for a in self.assay.arcs]

        for n in self.row_names:
            self.assertNotIn(n, target_nodes)

    def test_delete_study_row(self):
        """Test row deletion from study"""

        # First delete the assay row
        with open(ASSAY_DELETE_PATH) as fp:
            self.values['del_row'] = json.load(fp)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_row_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)

        # Delete the study row
        with open(STUDY_DELETE_PATH) as fp:
            self.values['del_row'] = json.load(fp)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_row_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            GenericMaterial.objects.filter(
                study=self.study, name=EDIT_SAMPLE_NAME
            ).first()
        )
        self.assertIsNone(
            Process.objects.filter(
                study=self.study, sodar_uuid=EDIT_STUDY_PROC_UUID
            ).first()
        )
        self.assertIsNone(
            GenericMaterial.objects.filter(
                study=self.study, name=EDIT_SOURCE_NAME
            ).first()
        )

    def test_delete_study_row_in_use(self):
        """Test study row deletion with sample used in asssay (should fail)"""

        # Delete the study row
        with open(STUDY_DELETE_PATH) as fp:
            self.values['del_row'] = json.load(fp)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_row_delete',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 500)
        self.assertIsNotNone(
            GenericMaterial.objects.filter(
                study=self.study, name=EDIT_SAMPLE_NAME
            ).first()
        )
        self.assertIsNotNone(
            Process.objects.filter(
                study=self.study, sodar_uuid=EDIT_STUDY_PROC_UUID
            ).first()
        )
        self.assertIsNotNone(
            GenericMaterial.objects.filter(
                study=self.study, name=EDIT_SOURCE_NAME
            ).first()
        )

    # TODO: Test deletion with splitting/pooling after fixing #923 and #924


class TestSampleSheetEditFinishAjaxView(TestViewsBase):
    """Tests for SampleSheetEditFinishAjaxView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()

    def test_post(self):
        """Test POST with updates=True"""
        # Assert preconditions
        self.assertEqual(ISATab.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_finish',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps({'updated': True}),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ISATab.objects.all().count(), 2)

    def test_post_no_updates(self):
        """Test POST with updates=False"""
        # Assert preconditions
        self.assertEqual(ISATab.objects.all().count(), 1)

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_edit_finish',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps({'updated': False}),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ISATab.objects.all().count(), 1)


class TestSampleSheetManageAjaxView(SheetConfigMixin, TestViewsBase):
    """Tests for SampleSheetManageAjaxView"""

    # TODO: Test with assay updates (needs a better test ISAtab)

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        # Set up UUIDs and default config
        self._update_uuids(self.investigation, CONFIG_DATA_DEFAULT)
        app_settings.set_app_setting(
            APP_NAME,
            'sheet_config',
            conf_api.build_sheet_config(self.investigation),
            project=self.project,
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_post_update_study_column(self):
        """Test posting a study column update"""

        # Assert preconditions
        sheet_config = app_settings.get_app_setting(
            APP_NAME, 'sheet_config', project=self.project
        )
        self.assertEqual(sheet_config, CONFIG_DATA_DEFAULT)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project, app=APP_NAME, event_name='field_update',
            ).count(),
            0,
        )

        values = {
            'fields': [
                {
                    'action': 'update',
                    'study': CONFIG_STUDY_UUID,
                    'assay': None,
                    'node_idx': 0,
                    'field_idx': 2,
                    'config': {
                        'name': 'age',
                        'type': 'characteristics',
                        'editable': True,
                        'format': 'integer',
                        'range': [None, None],
                        'regex': '',
                        'default': '',
                        'unit': ['day'],
                        'unit_default': 'day',
                    },
                }
            ]
        }

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_manage',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(values),
                content_type='application/json',
            )

        # Assert postconditions
        self.assertEqual(response.status_code, 200)

        sheet_config = app_settings.get_app_setting(
            APP_NAME, 'sheet_config', project=self.project
        )
        expected = {
            'name': 'age',
            'type': 'characteristics',
            'editable': True,
            'format': 'integer',
            'regex': '',
            'default': '',
            'unit': ['day'],
            'unit_default': 'day',
        }
        self.assertEqual(
            sheet_config['studies'][CONFIG_STUDY_UUID]['nodes'][0]['fields'][2],
            expected,
        )
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project, app=APP_NAME, event_name='field_update',
            ).count(),
            1,
        )


class TestStudyDisplayConfigAjaxView(TestViewsBase):
    """Tests for StudyDisplayConfigAjaxView"""

    def setUp(self):
        super().setUp()

        # Import investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        self.study = self.investigation.studies.first()
        self.s_uuid = str(self.investigation.studies.first().sodar_uuid)
        self.a_uuid = str(
            self.investigation.studies.first().assays.first().sodar_uuid
        )
        # Build sheet config and default display config
        self.sheet_config = conf_api.build_sheet_config(self.investigation)
        self.display_config = conf_api.build_display_config(
            self.investigation, self.sheet_config
        )
        app_settings.set_app_setting(
            APP_NAME,
            'display_config_default',
            project=self.project,
            value=self.display_config,
        )
        app_settings.set_app_setting(
            APP_NAME,
            'display_config',
            project=self.project,
            user=self.user,
            value=self.display_config,
        )
        self.study_config = self.display_config['studies'][self.s_uuid]

    def test_post(self):
        """Test updating the sheet configuration"""

        # Assert precondition
        self.assertEqual(
            self.study_config['nodes'][0]['fields'][2]['visible'], True
        )

        self.study_config['nodes'][0]['fields'][2]['visible'] = False

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_display_update',
                    kwargs={'study': self.study.sodar_uuid},
                ),
                json.dumps(
                    {'study_config': self.study_config, 'set_default': False}
                ),
                content_type='application/json',
            )

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')

        # Assert config status
        updated_config = app_settings.get_app_setting(
            APP_NAME, 'display_config', project=self.project, user=self.user
        )
        self.assertEqual(
            updated_config['studies'][self.s_uuid]['nodes'][0]['fields'][2][
                'visible'
            ],
            False,
        )

    def test_post_default(self):
        """Test updating along with the default configuration"""

        # Assert precondition
        self.assertEqual(
            self.study_config['nodes'][0]['fields'][2]['visible'], True
        )

        self.study_config['nodes'][0]['fields'][2]['visible'] = False

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_display_update',
                    kwargs={'study': self.study.sodar_uuid},
                ),
                json.dumps(
                    {'study_config': self.study_config, 'set_default': True}
                ),
                content_type='application/json',
            )

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'ok')

        # Assert config status
        updated_config = app_settings.get_app_setting(
            APP_NAME, 'display_config', project=self.project, user=self.user
        )
        default_config = app_settings.get_app_setting(
            APP_NAME, 'display_config_default', project=self.project
        )
        self.assertEqual(
            updated_config['studies'][self.s_uuid]['nodes'][0]['fields'][2][
                'visible'
            ],
            False,
        )
        self.assertEqual(updated_config, default_config)

    def test_post_no_change(self):
        """Test posting with no updates"""

        with self.login(self.user):
            response = self.client.post(
                reverse(
                    'samplesheets:ajax_display_update',
                    kwargs={'study': self.study.sodar_uuid},
                ),
                json.dumps(
                    {'study_config': self.study_config, 'set_default': False}
                ),
                content_type='application/json',
            )

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['detail'], 'ok')

        # Assert config status
        updated_config = app_settings.get_app_setting(
            APP_NAME, 'display_config', project=self.project, user=self.user
        )
        self.assertEqual(
            updated_config, self.display_config,
        )
