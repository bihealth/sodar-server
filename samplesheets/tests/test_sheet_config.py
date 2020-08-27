"""Tests for SheetConfigAPI"""
import json
import os

from test_plus.test import TestCase

from django.conf import settings

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.models import Study, Assay, Protocol
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.sheet_config import SheetConfigAPI
from samplesheets.tests.test_io import SampleSheetIOMixin, SHEET_DIR


# Local constants
SHEET_PATH = SHEET_DIR + 'i_small.zip'

CONFIG_STUDY_UUID = '11111111-1111-1111-1111-111111111111'
CONFIG_ASSAY_UUID = '22222222-2222-2222-2222-222222222222'
CONFIG_PROTOCOL_UUIDS = [
    '11111111-1111-1111-bbbb-000000000000',
    '22222222-2222-2222-bbbb-111111111111',
    '22222222-2222-2222-bbbb-000000000000',
]
CONFIG_DIR = os.path.dirname(__file__) + '/config/'
CONFIG_PATH_DEFAULT = CONFIG_DIR + 'i_small_default.json'
CONFIG_PATH_UPDATED = CONFIG_DIR + 'i_small_updated.json'

with open(CONFIG_PATH_DEFAULT) as fp:
    CONFIG_DATA_DEFAULT = json.load(fp)

IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


app_settings = AppSettingAPI()
conf_api = SheetConfigAPI()


class SheetConfigMixin:
    """Mixin for sheet config testing helpers"""

    @classmethod
    def _update_uuids(cls, investigation, sheet_config):
        """
        Update study, assay and protocol UUIDs in the database to match a test
        sheet config file.

        :param investigation: Investigation object
        :param sheet_config: Dict
        """
        study_names = {}
        assay_names = {}

        for study in investigation.studies.all():
            study_names[study.get_display_name()] = str(study.sodar_uuid)

            for assay in study.assays.all():
                assay_names[assay.get_display_name()] = str(assay.sodar_uuid)

        for s_uuid, sc in sheet_config['studies'].items():
            study = Study.objects.get(
                sodar_uuid=study_names[sc['display_name']]
            )
            study.sodar_uuid = s_uuid
            study.save()

            for a_uuid, ac in sc['assays'].items():
                assay = Assay.objects.get(
                    sodar_uuid=assay_names[ac['display_name']]
                )
                assay.sodar_uuid = a_uuid
                assay.save()

            protocols = list(
                Protocol.objects.filter(study=study).order_by('pk')
            )

            for i in range(len(protocols)):
                protocols[i].sodar_uuid = CONFIG_PROTOCOL_UUIDS[i]
                protocols[i].save()


class TestSheetConfig(
    ProjectMixin,
    RoleAssignmentMixin,
    SampleSheetIOMixin,
    SheetConfigMixin,
    TestCase,
):
    """Tests for sheet configuration operations"""

    # NOTE: Not using TestUtilsBase

    def setUp(self):
        self.tb = SampleSheetTableBuilder()

        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner
        )

        # Build investigation
        self.investigation = self._import_isa_from_file(
            SHEET_PATH, self.project
        )
        # Update UUIDs to match JSON file
        self._update_uuids(self.investigation, CONFIG_DATA_DEFAULT)

    def test_build_sheet_config(self):
        """Test sheet building against the default i_small JSON config file"""
        sheet_config = conf_api.build_sheet_config(self.investigation)
        self.assertEqual(sheet_config, CONFIG_DATA_DEFAULT)

    # TODO: Test fields once we are finished with the notation
    def test_build_sheet_config_batch(self):
        """Test build_sheet_config() in batch"""
        for zip_name, zip_file in self._get_isatab_files().items():
            msg = 'file={}'.format(zip_name)

            try:
                investigation = self._import_isa_from_file(
                    zip_file.path, self.project
                )

            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            sc = conf_api.build_sheet_config(investigation)
            self.assertEqual(
                len(sc['studies']), investigation.studies.all().count(), msg=msg
            )

            for sk, sv in sc['studies'].items():
                study = investigation.studies.get(sodar_uuid=sk)
                study_tables = self.tb.build_study_tables(study)
                self.assertEqual(
                    len(sv['nodes']),
                    len(study_tables['study']['top_header']),
                    msg=msg,
                )
                self.assertEqual(
                    len(sv['assays']), study.assays.all().count(), msg=msg
                )

                for ak, av in sv['assays'].items():
                    # Get sample node index
                    s_idx = 0

                    for h in study_tables['study']['top_header']:
                        if h['value'] == 'Sample':
                            break
                        s_idx += 1

                    self.assertEqual(
                        len(av['nodes']),
                        len(study_tables['assays'][ak]['top_header'])
                        - s_idx
                        - 1,
                        msg=msg,
                    )

            investigation.delete()

    def test_validate_sheet_config(self):
        """Test validate_sheet_config() with a valid result"""
        sheet_config = conf_api.build_sheet_config(self.investigation)
        self.assertIsNone(conf_api.validate_sheet_config(sheet_config))

    def test_validate_sheet_config_newer(self):
        """Test validate_sheet_config() with a newer version"""
        sheet_config = conf_api.build_sheet_config(self.investigation)
        v = sheet_config['version'].split('.')
        v[1] = str(int(v[1]) + 1)
        sheet_config['version'] = '.'.join(v)
        self.assertIsNone(conf_api.validate_sheet_config(sheet_config))

    def test_validate_sheet_config_older(self):
        """Test validate_sheet_config() with an older version (should fail)"""
        sheet_config = conf_api.build_sheet_config(self.investigation)
        v = sheet_config['version'].split('.')
        v[1] = str(int(v[1]) - 1)
        sheet_config['version'] = '.'.join(v)

        with self.assertRaises(ValueError):
            conf_api.validate_sheet_config(sheet_config)

    def test_get_sheet_config(self):
        """Test get_sheet_config() once it's been added"""
        sheet_config = conf_api.build_sheet_config(self.investigation)
        self.assertEqual(
            sheet_config, conf_api.get_sheet_config(self.investigation)
        )

    def test_get_sheet_config_new(self):
        """Test get_sheet_config() with no previously created config"""
        self._update_uuids(self.investigation, CONFIG_DATA_DEFAULT)
        sheet_config = conf_api.get_sheet_config(self.investigation)
        self.assertEqual(sheet_config, CONFIG_DATA_DEFAULT)

    def test_get_sheet_config_old(self):
        """Test get_sheet_config() with an old version of the config"""
        sheet_config = conf_api.build_sheet_config(self.investigation)
        v = sheet_config['version'].split('.')
        v[1] = str(int(v[1]) - 1)
        sheet_config['version'] = '.'.join(v)
        app_settings.set_app_setting(
            'samplesheets', 'sheet_config', sheet_config, project=self.project
        )
        sheet_config = conf_api.get_sheet_config(self.investigation)
        self.assertEqual(
            sheet_config['version'], settings.SHEETS_CONFIG_VERSION
        )


class TestDisplayConfig(
    ProjectMixin, RoleAssignmentMixin, SampleSheetIOMixin, TestCase,
):
    """Tests for diplay config operations"""

    # NOTE: Not using TestUtilsBase

    def setUp(self):
        self.tb = SampleSheetTableBuilder()

        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', SODAR_CONSTANTS['PROJECT_TYPE_PROJECT'], None
        )
        self.role_owner = Role.objects.get_or_create(
            name=SODAR_CONSTANTS['PROJECT_ROLE_OWNER']
        )[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner
        )

    def test_build_config_batch(self):
        """Test building default display configs for example ISAtabs"""
        for zip_name, zip_file in self._get_isatab_files().items():
            msg = 'file={}'.format(zip_name)

            try:
                investigation = self._import_isa_from_file(
                    zip_file.path, self.project
                )

            except Exception as ex:
                return self._fail_isa(zip_name, ex)

            sc = conf_api.build_sheet_config(investigation)
            s_uuid = str(investigation.studies.first().sodar_uuid)
            a_uuid = str(
                investigation.studies.first().assays.first().sodar_uuid
            )
            dc = conf_api.build_display_config(investigation, sc)
            study_node_count = len(sc['studies'][s_uuid]['nodes'])

            self.assertEqual(
                len(dc['studies'][s_uuid]['nodes']), study_node_count, msg=msg,
            )
            self.assertEqual(
                len(dc['studies'][s_uuid]['assays'][a_uuid]['nodes']),
                len(sc['studies'][s_uuid]['assays'][a_uuid]['nodes'])
                + study_node_count,
                msg=msg,
            )
