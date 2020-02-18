"""Tests for Ajax API views in the samplesheets app"""

import json
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
from samplesheets.tests.test_utils import SheetConfigMixin, CONFIG_STUDY_UUID
from samplesheets.tests.test_views import (
    IRODS_BACKEND_ENABLED,
    IRODS_BACKEND_SKIP_MSG,
    TestViewsBase,
    SHEET_PATH,
    app_settings,
    EDIT_NEW_VALUE_STR,
    CONFIG_DATA_DEFAULT,
)
from samplesheets.utils import build_sheet_config


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
                'samplesheets', 'allow_editing'
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
                'create_dirs': True,
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
            'samplesheets', 'allow_editing', True, project=self.project
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
        self.assertIn('study_config', ret_data)


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
                    'samplesheets:ajax_edit',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Asert postconditions
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
                    'samplesheets:ajax_edit',
                    kwargs={'project': self.project.sodar_uuid},
                ),
                json.dumps(self.values),
                content_type='application/json',
            )

        # Asert postconditions
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(
            obj.parameter_values[header_name],
            {'unit': None, 'value': EDIT_NEW_VALUE_STR},
        )


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

        # Asert postconditions
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

        # Asert postconditions
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
            'samplesheets',
            'sheet_config',
            build_sheet_config(self.investigation),
            project=self.project,
        )
        self.study = self.investigation.studies.first()
        self.assay = self.study.assays.first()

    def test_post_update_study_column(self):
        """Test posting a study column update"""

        # Assert preconditions
        sheet_config = app_settings.get_app_setting(
            'samplesheets', 'sheet_config', project=self.project
        )
        self.assertEqual(sheet_config, CONFIG_DATA_DEFAULT)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project,
                app='samplesheets',
                event_name='field_update',
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
            'samplesheets', 'sheet_config', project=self.project
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
                project=self.project,
                app='samplesheets',
                event_name='field_update',
            ).count(),
            1,
        )
