"""Base classes and helpers for assay plugin tests"""

from django.conf import settings

from samplesheets.models import Investigation
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.plugins import SampleSheetAssayPluginPoint, get_backend_api
from samplesheets.tests.test_views import (
    SheetTemplateCreateMixin,
    SamplesheetsViewTestBase,
)
from samplesheets.views import CUBI_TPL_DICT


table_builder = SampleSheetTableBuilder()


class AssayPluginTestBase(SheetTemplateCreateMixin, SamplesheetsViewTestBase):
    """Base test class for assay plugins"""

    plugin_name = None
    template_name = None

    def setUp(self):
        super().setUp()
        self.make_sheets_from_cubi_tpl(CUBI_TPL_DICT[self.template_name])
        self.investigation = Investigation.objects.get(project=self.project)
        # NOTE: This assumes one study and assay, extend setup() to add more
        self.study = self.investigation.studies.order_by('pk').first()
        self.assay = self.study.assays.order_by('pk').first()
        self.study_tables = table_builder.build_study_tables(self.study)
        self.assay_table = self.study_tables['assays'][
            str(self.assay.sodar_uuid)
        ]
        self.irods_backend = get_backend_api('omics_irods')
        self.assay_path = self.irods_backend.get_path(self.assay)
        self.base_url = settings.IRODS_WEBDAV_URL + self.assay_path
        self.plugin = SampleSheetAssayPluginPoint.get_plugin(self.plugin_name)
