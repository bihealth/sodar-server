"""Tests for models in the samplesheets app"""

# NOTE: Retraction and sharing data not yet tested, to be implemented
# TODO: Test validation rules and uniqueness constraints

import altamisa
import os
import re

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils import timezone

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import (
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
)
from projectroles.utils import build_secret

from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    Protocol,
    Process,
    GenericMaterial,
    ISATab,
    IrodsAccessTicket,
    IrodsDataRequest,
    NOT_AVAILABLE_STR,
    CONFIG_LABEL_CREATE,
    ISA_META_ASSAY_PLUGIN,
    IRODS_REQUEST_ACTION_DELETE,
    IRODS_REQUEST_STATUS_ACTIVE,
)
from samplesheets.utils import get_alt_names


# Local constants
DEFAULT_PARSER_VERSION = altamisa.__version__

INV_IDENTIFIER = 'Investigation identifier'
INV_FILE_NAME = 'i_Investigation.txt'
INV_TITLE = 'Investigation'
INV_ARCHIVE_NAME = 'investigation.zip'

STUDY_IDENTIFIER = 'Study identifier'
STUDY_FILE_NAME = 's_study.txt'
STUDY_TITLE = 'study'

PROTOCOL_NAME = 'sample collection'
PROTOCOL_TYPE = 'sample collection'
PROTOCOL_PARAMS = [
    'library kit',
    'library selection',
    'mid',
    'library source',
    'library layout',
    'library strategy',
]
PROTOCOL_URI = 'pmid:11314272'
PROTOCOL_VERSION = '1'
PROTOCOL_COMPONENTS = '454 GS FLX Titanium'

ASSAY_IDENTIFIER = 'Study identifier'
ASSAY_FILE_NAME = 'a_assay.txt'
ASSAY_MEASURE_TYPE = 'environmental gene survey'
ASSAY_TECH_PLATFORM = '454 GS FLX'
ASSAY_TECH_TYPE = 'nucleotide sequencing'
ASSAY2_FILE_NAME = 'a_assay2.txt'
ASSAY2_MEASURE_TYPE = 'environmental gene survey'
ASSAY2_TECH_PLATFORM = '454 GS FLX'
ASSAY2_TECH_TYPE = 'nucleotide sequencing'

SOURCE_NAME = 'patient0'
SOURCE_UNIQUE_NAME = 'p1-s1-a1-patient0-1-1'
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

SAMPLE_NAME = 'patient0-s1'
SAMPLE_UNIQUE_NAME = 'p1-s1-a1-patient0-s1'
SAMPLE_CHARACTERISTICS = {'Tissue': {'unit': None, 'value': 'N'}}

MATERIAL_NAME = 'extract'
MATERIAL_UNIQUE_NAME = 'p1-s1-a1-extract-1-1'
MATERIAL_TYPE = 'Extract Name'

DATA_NAME = 'file.gz'
DATA_UNIQUE_NAME = 'p1-s1-a1-file.gz-COL1'
DATA_TYPE = 'Raw Data File'

PROCESS_NAME = 'Process'
PROCESS_UNIQUE_NAME = 'p1-s1-a1-process-1-1'
PROCESS_NAME_TYPE = 'Data Transformation Name'
PROCESS_PARAM_VALUES = {'INSERT_SIZE': {'unit': None, 'value': '481'}}
PROCESS_PERFORMER = 'Alice Example'
PROCESS_PERFORM_DATE = timezone.now()

DEFAULT_DESCRIPTION = 'Description'
DEFAULT_COMMENTS = {'comment': 'value'}

ISATAB_DATA = {'i_investigation.txt': '', 's_study.txt': '', 'a_assay.txt': ''}
ISATAB_DESC = 'description'

PLUGIN_NAME_DNA_SEQ = 'samplesheets_assay_dna_sequencing'
PLUGIN_NAME_GENERIC_RAW = 'samplesheets_assay_generic_raw'

IRODS_TICKET_LABEL = 'Ticket'
IRODS_TICKET_PATH = '/sodarZone/path/to/irods/collection'
IRODS_TICKET_STR = 'taihic7Ieengu1Ch'
IRODS_REQUEST_DESC = 'Request description'


# Helper mixins ----------------------------------------------------------------


class SampleSheetModelMixin:
    """Helpers for samplesheets models creation"""

    @classmethod
    def make_investigation(
        cls,
        identifier,
        file_name,
        project,
        title,
        description,
        submission_date=None,
        public_release_date=None,
        ontology_source_refs={},
        publications={},
        contacts={},
        comments=None,
        headers=[],
        parser_version=DEFAULT_PARSER_VERSION,
        parser_warnings={},
        archive_name=None,
        retraction_data=None,
        sharing_data=None,
    ):
        """Create Investigation in database"""
        values = {
            'identifier': identifier,
            'file_name': file_name,
            'project': project,
            'title': title,
            'description': description,
            'submission_date': submission_date,
            'public_release_date': public_release_date,
            'ontology_source_refs': ontology_source_refs,
            'publications': publications,
            'contacts': contacts,
            'parser_version': parser_version,
            'parser_warnings': parser_warnings,
            'archive_name': archive_name,
            'comments': comments,
            'headers': headers,
            'active': True,
        }  # NOTE: Must explicitly set active to True
        return Investigation.objects.create(**values)

    @classmethod
    def make_study(
        cls,
        identifier,
        file_name,
        investigation,
        title,
        description,
        submission_date=None,
        public_release_date=None,
        factors={},
        contacts={},
        comments=None,
        headers=[],
        retraction_data=None,
        sharing_data=None,
    ):
        """Create Study in database"""
        values = {
            'identifier': identifier,
            'file_name': file_name,
            'investigation': investigation,
            'title': title,
            'description': description,
            'submission_date': submission_date,
            'public_release_date': public_release_date,
            'factors': factors,
            'contacts': contacts,
            'comments': comments,
            'headers': headers,
        }
        return Study.objects.create(**values)

    @classmethod
    def make_protocol(
        cls,
        name,
        study,
        protocol_type,
        description,
        uri,
        version,
        parameters,
        components,
        comments=None,
        headers=[],
        retraction_data=None,
        sharing_data=None,
    ):
        """Create Protocol in database"""
        values = {
            'name': name,
            'study': study,
            'protocol_type': protocol_type,
            'description': description,
            'uri': uri,
            'version': version,
            'parameters': parameters,
            'components': components,
            'comments': comments,
            'headers': headers,
        }
        return Protocol.objects.create(**values)

    @classmethod
    def make_assay(
        cls,
        file_name,
        study,
        tech_platform,
        tech_type,
        measurement_type,
        arcs,
        comments=None,
        headers=[],
        retraction_data=None,
        sharing_data=None,
    ):
        """Create Assay in database"""
        values = {
            'file_name': file_name,
            'study': study,
            'technology_platform': tech_platform,
            'technology_type': tech_type,
            'measurement_type': measurement_type,
            'arcs': arcs,
            'comments': comments,
            'headers': headers,
        }
        return Assay.objects.create(**values)

    @classmethod
    def make_material(
        cls,
        item_type,
        name,
        unique_name,
        characteristics,
        study,
        assay,
        material_type,
        extra_material_type,
        factor_values,
        extract_label={},
        comments=None,
        headers=[],
        retraction_data=None,
        sharing_data=None,
    ):
        """Create Material in database"""
        values = {
            'item_type': item_type,
            'name': name,
            'unique_name': unique_name,
            'characteristics': characteristics,
            'study': study,
            'assay': assay,
            'material_type': material_type,
            'extra_material_type': extra_material_type,
            'factor_values': factor_values,
            'extract_label': extract_label,
            'headers': headers,
            'comments': comments,
        }
        return GenericMaterial.objects.create(**values)

    @classmethod
    def make_process(
        cls,
        name,
        unique_name,
        name_type,
        protocol,
        study,
        assay,
        parameter_values,
        performer,
        perform_date,
        first_dimension={},
        second_dimension={},
        comments=None,
        headers=[],
        retraction_data=None,
        sharing_data=None,
    ):
        """Create Material in database"""
        values = {
            'name': name,
            'unique_name': unique_name,
            'name_type': name_type,
            'protocol': protocol,
            'study': study,
            'assay': assay,
            'parameter_values': parameter_values,
            'performer': performer,
            'perform_date': perform_date,
            'first_dimension': first_dimension,
            'second_dimension': second_dimension,
            'comments': comments,
            'headers': headers,
        }
        return Process.objects.create(**values)

    @classmethod
    def set_configuration(cls, investigation, config_name):
        """Set the configuration for an investigation"""
        investigation.comments[CONFIG_LABEL_CREATE] = {
            'unit': None,
            'value': config_name,
        }
        investigation.save()
        return investigation

    @classmethod
    def make_isatab(
        cls,
        project,
        data,
        investigation_uuid=None,
        archive_name=None,
        tags=[],
        parser_version=None,
        user=None,
        extra_data={},
        description=None,
    ):
        """Create an ISATab object in the database"""
        values = {
            'project': project,
            'data': data,
            'investigation_uuid': investigation_uuid,
            'archive_name': archive_name,
            'tags': tags,
            'parser_version': parser_version,
            'user': user,
            'extra_data': extra_data,
            'description': description,
        }
        return ISATab.objects.create(**values)


class IrodsAccessTicketMixin:
    """Helpers for IrodsAccessTicket model creation"""

    @classmethod
    def make_irods_ticket(
        cls,
        study,
        assay,
        path,
        user=None,
        label=None,
        ticket=None,
        date_expires=None,  # never expires
    ):
        """Create an IrodsAccessTicket object in the database"""
        if not ticket:
            ticket = build_secret(16)
        values = {
            'study': study,
            'assay': assay,
            'ticket': ticket,
            'path': path,
            'label': label,
            'user': user,
            'date_expires': date_expires,
        }
        return IrodsAccessTicket.objects.create(**values)


class IrodsDataRequestMixin:
    """Helpers for IrodsDataRequest model creation"""

    @classmethod
    def make_irods_request(
        cls,
        project,
        action,
        path,
        status,
        target_path='',
        status_info='',
        description='',
        user=None,
    ):
        """Create an IrodsDataRequest object in the database"""
        values = {
            'project': project,
            'action': action,
            'path': path,
            'status': status,
            'target_path': target_path,
            'status_info': status_info,
            'description': description,
            'user': user,
        }
        return IrodsDataRequest.objects.create(**values)


# Test classes -----------------------------------------------------------------


class SamplesheetsModelTestBase(
    ProjectMixin,
    RoleMixin,
    RoleAssignmentMixin,
    SampleSheetModelMixin,
    TestCase,
):
    """Base class for samplesheets model tests"""

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


class TestInvestigation(SamplesheetsModelTestBase):
    """Tests for the Investigation model"""

    def test_initialization(self):
        """Test Investigation initialization"""
        expected = {
            'id': self.investigation.pk,
            'identifier': INV_IDENTIFIER,
            'file_name': INV_FILE_NAME,
            'project': self.project.pk,
            'title': INV_TITLE,
            'description': DEFAULT_DESCRIPTION,
            'submission_date': None,
            'public_release_date': None,
            'ontology_source_refs': {},
            'publications': {},
            'contacts': {},
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'irods_status': False,
            'active': True,
            'parser_version': DEFAULT_PARSER_VERSION,
            'parser_warnings': {},
            'archive_name': INV_ARCHIVE_NAME,
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.investigation.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.investigation), expected)

    def test__str__(self):
        """Test Investigation __str__() function"""
        expected = '{}: {}'.format(self.project.title, INV_TITLE)
        self.assertEqual(str(self.investigation), expected)

    def test__repr__(self):
        """Test Investigation __repr__() function"""
        expected = "Investigation('{}', '{}')".format(
            self.project.title, INV_TITLE
        )
        self.assertEqual(repr(self.investigation), expected)

    def test_get_study(self):
        """Test Investigation get_study() function"""
        self.assertEqual(self.investigation.get_study(), None)

    def test_get_project(self):
        """Test Investigation get_project() function"""
        self.assertEqual(self.investigation.get_project(), self.project)

    def test_get_url(self):
        """Test get_url()"""
        expected = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        )
        self.assertEqual(self.investigation.get_url(), expected)


class TestStudy(SamplesheetsModelTestBase):
    """Tests for the Study model"""

    def test_initialization(self):
        """Test Study initialization"""
        expected = {
            'id': self.study.pk,
            'identifier': STUDY_IDENTIFIER,
            'file_name': STUDY_FILE_NAME,
            'investigation': self.investigation.pk,
            'title': STUDY_TITLE,
            'description': DEFAULT_DESCRIPTION,
            'submission_date': None,
            'public_release_date': None,
            'study_design': {},
            'publications': {},
            'factors': {},
            'contacts': {},
            'arcs': [],
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.study.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.study), expected)

    def test__str__(self):
        """Test Study __str__() function"""
        expected = '{}: {}'.format(self.project.title, STUDY_TITLE)
        self.assertEqual(str(self.study), expected)

    def test__repr__(self):
        """Test Study __repr__() function"""
        expected = "Study('{}', '{}')".format(self.project.title, STUDY_TITLE)
        self.assertEqual(repr(self.study), expected)

    def test_get_study(self):
        """Test Study get_study() function"""
        self.assertEqual(self.study.get_study(), self.study)

    def test_get_project(self):
        """Test Study get_project() function"""
        self.assertEqual(self.study.get_project(), self.project)

    def test_get_name(self):
        """Test get_name() when title is set"""
        self.assertEqual(self.study.get_name(), self.study.title)

    def test_get_name_no_title(self):
        """Test get_name() when no title is set"""
        self.study.title = ''
        self.study.save()
        self.assertEqual(self.study.get_name(), self.study.identifier)

    def test_get_url(self):
        """Test get_url()"""
        expected = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        ) + '#/study/{}'.format(self.study.sodar_uuid)
        self.assertEqual(self.study.get_url(), expected)


class TestProtocol(SamplesheetsModelTestBase):
    """Tests for the Protocol model"""

    def setUp(self):
        super().setUp()
        # Set up Protocol
        self.protocol = self.make_protocol(
            name=PROTOCOL_NAME,
            study=self.study,
            protocol_type=PROTOCOL_TYPE,
            description=DEFAULT_DESCRIPTION,
            uri=PROTOCOL_URI,
            version=PROTOCOL_VERSION,
            parameters=PROTOCOL_PARAMS,
            components=PROTOCOL_COMPONENTS,
            comments=DEFAULT_COMMENTS,
        )

    def test_initialization(self):
        """Test Protocol initialization"""
        expected = {
            'id': self.protocol.pk,
            'name': PROTOCOL_NAME,
            'study': self.study.pk,
            'protocol_type': PROTOCOL_TYPE,
            'description': DEFAULT_DESCRIPTION,
            'uri': PROTOCOL_URI,
            'version': PROTOCOL_VERSION,
            'parameters': PROTOCOL_PARAMS,
            'components': PROTOCOL_COMPONENTS,
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.protocol.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.protocol), expected)

    def test__str__(self):
        """Test Protocol __str__() function"""
        expected = '{}: {}/{}'.format(
            self.project.title, STUDY_TITLE, PROTOCOL_NAME
        )
        self.assertEqual(str(self.protocol), expected)

    def test__repr__(self):
        """Test Protocol __repr__() function"""
        expected = "Protocol('{}', '{}', '{}')".format(
            self.project.title, STUDY_TITLE, PROTOCOL_NAME
        )
        self.assertEqual(repr(self.protocol), expected)

    def test_get_study(self):
        """Test Protocol get_study() function"""
        self.assertEqual(self.protocol.get_study(), self.study)

    def test_get_project(self):
        """Test Protocol get_project() function"""
        self.assertEqual(self.protocol.get_project(), self.project)


class TestAssay(SamplesheetsModelTestBase):
    """Tests for the Assay model"""

    def test_initialization(self):
        """Test Study initialization"""
        expected = {
            'id': self.assay.pk,
            'file_name': ASSAY_FILE_NAME,
            'study': self.study.pk,
            'technology_platform': ASSAY_TECH_PLATFORM,
            'technology_type': ASSAY_TECH_TYPE,
            'measurement_type': ASSAY_MEASURE_TYPE,
            'arcs': [],
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.assay.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.assay), expected)

    def test__str__(self):
        """Test Assay __str__() function"""
        expected = '{}: {}/{}'.format(
            self.project.title, STUDY_TITLE, self.assay.get_name()
        )
        self.assertEqual(str(self.assay), expected)

    def test__repr__(self):
        """Test Assay __repr__() function"""
        expected = "Assay('{}', '{}', '{}')".format(
            self.project.title, STUDY_TITLE, self.assay.get_name()
        )
        self.assertEqual(repr(self.assay), expected)

    def test_get_study(self):
        """Test Assay get_study() function"""
        self.assertEqual(self.assay.get_study(), self.study)

    def test_get_project(self):
        """Test Assay get_project() function"""
        self.assertEqual(self.assay.get_project(), self.project)

    def test_get_name(self):
        """Test Assay get_name() function"""
        self.assertEqual(self.assay.get_name(), 'assay')

    def test_get_plugin(self):
        """Test get_plugin() with measurement/technology type"""
        self.assay.measurement_type = {
            'name': 'genome sequencing',
            'accession': None,
            'ontology_name': None,
        }
        self.assay.technology_type = {
            'name': 'nucleotide sequencing',
            'accession': None,
            'ontology_name': None,
        }
        plugin = self.assay.get_plugin()
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.name, PLUGIN_NAME_DNA_SEQ)

    def test_get_plugin_unknown(self):
        """Test get_plugin() without measurement/technology type"""
        self.assertEqual(self.assay.get_plugin(), None)

    def test_get_plugin_force(self):
        """Test get_plugin() with forced plugin in assay comments"""
        self.assay.comments = {ISA_META_ASSAY_PLUGIN: PLUGIN_NAME_GENERIC_RAW}
        plugin = self.assay.get_plugin()
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.name, PLUGIN_NAME_GENERIC_RAW)

    def test_get_plugin_override(self):
        """Test get_plugin() override with measurement and technology type"""
        self.assay.measurement_type = {
            'name': 'genome sequencing',
            'accession': None,
            'ontology_name': None,
        }
        self.assay.technology_type = {
            'name': 'nucleotide sequencing',
            'accession': None,
            'ontology_name': None,
        }
        self.assay.comments = {ISA_META_ASSAY_PLUGIN: PLUGIN_NAME_GENERIC_RAW}
        plugin = self.assay.get_plugin()
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.name, PLUGIN_NAME_GENERIC_RAW)

    def test_get_url(self):
        """Test get_url()"""
        expected = reverse(
            'samplesheets:project_sheets',
            kwargs={'project': self.project.sodar_uuid},
        ) + '#/assay/{}'.format(self.assay.sodar_uuid)
        self.assertEqual(self.assay.get_url(), expected)


class TestSource(SamplesheetsModelTestBase):
    """Tests for the GenericMaterial model with type SOURCE"""

    def setUp(self):
        super().setUp()
        # Set up SOURCE GenericMaterial
        self.material = self.make_material(
            item_type='SOURCE',
            name=SOURCE_NAME,
            unique_name=SOURCE_UNIQUE_NAME,
            characteristics=SOURCE_CHARACTERISTICS,
            study=self.study,
            assay=None,
            material_type=None,
            extra_material_type=None,
            factor_values=None,
            extract_label={},
            comments=DEFAULT_COMMENTS,
        )

    def test_initialization(self):
        """Test SOURCE GenericMaterial initialization"""
        expected = {
            'id': self.material.pk,
            'item_type': 'SOURCE',
            'name': SOURCE_NAME,
            'unique_name': SOURCE_UNIQUE_NAME,
            'alt_names': get_alt_names(SOURCE_NAME),
            'characteristics': SOURCE_CHARACTERISTICS,
            'study': self.study.pk,
            'assay': None,
            'material_type': None,
            'extra_material_type': None,
            'factor_values': None,
            'extract_label': {},
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.material.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.material), expected)

    def test__str__(self):
        """Test SOURCE GenericMaterial __str__() function"""
        expected = '{}: {}/{}/{}/{}'.format(
            self.project.title,
            STUDY_TITLE,
            NOT_AVAILABLE_STR,
            'SOURCE',
            SOURCE_UNIQUE_NAME,
        )
        self.assertEqual(str(self.material), expected)

    def test__repr__(self):
        """Test SOURCE GenericMaterial __repr__() function"""
        expected = "GenericMaterial('{}', '{}', '{}', '{}', '{}')".format(
            self.project.title,
            STUDY_TITLE,
            NOT_AVAILABLE_STR,
            'SOURCE',
            SOURCE_UNIQUE_NAME,
        )
        self.assertEqual(repr(self.material), expected)

    def test_get_study(self):
        """Test SOURCE GenericMaterial get_study() function"""
        self.assertEqual(self.material.get_study(), self.study)

    def test_get_project(self):
        """Test SOURCE GenericMaterial get_project() function"""
        self.assertEqual(self.material.get_project(), self.project)

    def test_get_parent(self):
        """Test SOURCE GenericMaterial get_parent() function"""
        self.assertEqual(self.material.get_parent(), self.study)

    # TODO: Test header helpers


class TestSample(SamplesheetsModelTestBase):
    """Tests for the GenericMaterial model with type SAMPLE"""

    def setUp(self):
        super().setUp()
        # Set up SAMPLE GenericMaterial
        self.material = self.make_material(
            item_type='SAMPLE',
            name=SAMPLE_NAME,
            unique_name=SAMPLE_UNIQUE_NAME,
            characteristics=SAMPLE_CHARACTERISTICS,
            study=self.study,
            assay=None,
            material_type=None,
            extra_material_type=None,
            factor_values=None,  # TODO: Test this
            extract_label={},  # TODO: Test this
            comments=DEFAULT_COMMENTS,
        )

    def test_initialization(self):
        """Test SAMPLE GenericMaterial initialization"""
        expected = {
            'id': self.material.pk,
            'item_type': 'SAMPLE',
            'name': SAMPLE_NAME,
            'unique_name': SAMPLE_UNIQUE_NAME,
            'alt_names': get_alt_names(SAMPLE_NAME),
            'characteristics': SAMPLE_CHARACTERISTICS,
            'study': self.study.pk,
            'assay': None,
            'material_type': None,
            'extra_material_type': None,
            'factor_values': None,
            'extract_label': {},
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.material.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.material), expected)

    def test__str__(self):
        """Test SAMPLE GenericMaterial __str__() function"""
        expected = '{}: {}/{}/{}/{}'.format(
            self.project.title,
            STUDY_TITLE,
            NOT_AVAILABLE_STR,
            'SAMPLE',
            SAMPLE_UNIQUE_NAME,
        )
        self.assertEqual(str(self.material), expected)

    def test__repr__(self):
        """Test SAMPLE GenericMaterial __repr__() function"""
        expected = "GenericMaterial('{}', '{}', '{}', '{}', '{}')".format(
            self.project.title,
            STUDY_TITLE,
            NOT_AVAILABLE_STR,
            'SAMPLE',
            SAMPLE_UNIQUE_NAME,
        )
        self.assertEqual(repr(self.material), expected)

    def test_get_study(self):
        """Test SAMPLE GenericMaterial get_study() function"""
        self.assertEqual(self.material.get_study(), self.study)

    def test_get_project(self):
        """Test SAMPLE GenericMaterial get_project() function"""
        self.assertEqual(self.material.get_project(), self.project)

    def test_get_parent(self):
        """Test SAMPLE GenericMaterial get_parent() function"""
        self.assertEqual(self.material.get_parent(), self.study)


class TestMaterial(SamplesheetsModelTestBase):
    """Tests for the GenericMaterial model with type MATERIAL"""

    def setUp(self):
        super().setUp()
        # Set up MATERIAL GenericMaterial
        self.material = self.make_material(
            item_type='MATERIAL',
            name=MATERIAL_NAME,
            unique_name=MATERIAL_UNIQUE_NAME,
            characteristics={},
            study=self.study,
            assay=self.assay,
            material_type=MATERIAL_TYPE,
            extra_material_type=None,
            factor_values=None,
            extract_label={},
            comments=DEFAULT_COMMENTS,
        )

    def test_initialization(self):
        """Test MATERIAL GenericMaterial initialization"""
        expected = {
            'id': self.material.pk,
            'item_type': 'MATERIAL',
            'name': MATERIAL_NAME,
            'unique_name': MATERIAL_UNIQUE_NAME,
            'alt_names': get_alt_names(MATERIAL_NAME),
            'characteristics': {},
            'study': self.study.pk,
            'assay': self.assay.pk,
            'material_type': MATERIAL_TYPE,
            'extra_material_type': None,
            'factor_values': None,
            'extract_label': {},
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.material.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.material), expected)

    def test__str__(self):
        """Test MATERIAL GenericMaterial __str__() function"""
        expected = '{}: {}/{}/{}/{}'.format(
            self.project.title,
            STUDY_TITLE,
            self.assay.get_name(),
            'MATERIAL',
            MATERIAL_UNIQUE_NAME,
        )
        self.assertEqual(str(self.material), expected)

    def test__repr__(self):
        """Test MATERIAL GenericMaterial __repr__() function"""
        expected = "GenericMaterial('{}', '{}', '{}', '{}', '{}')".format(
            self.project.title,
            STUDY_TITLE,
            self.assay.get_name(),
            'MATERIAL',
            MATERIAL_UNIQUE_NAME,
        )
        self.assertEqual(repr(self.material), expected)

    def test_get_study(self):
        """Test MATERIAL GenericMaterial get_study() function"""
        self.assertEqual(self.material.get_study(), self.study)

    def test_get_project(self):
        """Test MATERIAL GenericMaterial get_project() function"""
        self.assertEqual(self.material.get_project(), self.project)

    def test_get_parent(self):
        """Test MATERIAL GenericMaterial get_parent() function"""
        self.assertEqual(self.material.get_parent(), self.assay)


class TestDataFile(SamplesheetsModelTestBase):
    """Tests for the GenericMaterial model with type DATA"""

    def setUp(self):
        super().setUp()
        # Set up DATA GenericMaterial
        self.material = self.make_material(
            item_type='DATA',
            name=DATA_NAME,
            unique_name=DATA_UNIQUE_NAME,
            characteristics={},
            study=self.study,
            assay=self.assay,
            material_type=DATA_TYPE,
            extra_material_type=None,
            factor_values=None,
            extract_label={},
            comments=DEFAULT_COMMENTS,
        )

    def test_initialization(self):
        """Test MATERIAL GenericMaterial initialization"""
        expected = {
            'id': self.material.pk,
            'item_type': 'DATA',
            'name': DATA_NAME,
            'unique_name': DATA_UNIQUE_NAME,
            'alt_names': get_alt_names(DATA_NAME),
            'characteristics': {},
            'study': self.study.pk,
            'assay': self.assay.pk,
            'material_type': DATA_TYPE,
            'extra_material_type': None,
            'factor_values': None,
            'extract_label': {},
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.material.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.material), expected)

    def test__str__(self):
        """Test DATA GenericMaterial __str__() function"""
        expected = '{}: {}/{}/{}/{}'.format(
            self.project.title,
            STUDY_TITLE,
            self.assay.get_name(),
            'DATA',
            DATA_UNIQUE_NAME,
        )
        self.assertEqual(str(self.material), expected)

    def test__repr__(self):
        """Test DATA GenericMaterial __repr__() function"""
        expected = "GenericMaterial('{}', '{}', '{}', '{}', '{}')".format(
            self.project.title,
            STUDY_TITLE,
            self.assay.get_name(),
            'DATA',
            DATA_UNIQUE_NAME,
        )
        self.assertEqual(repr(self.material), expected)

    def test_get_study(self):
        """Test DATA GenericMaterial get_study() function"""
        self.assertEqual(self.material.get_study(), self.study)

    def test_get_project(self):
        """Test DATA GenericMaterial get_project() function"""
        self.assertEqual(self.material.get_project(), self.project)

    def test_get_parent(self):
        """Test DATA GenericMaterial get_parent() function"""
        self.assertEqual(self.material.get_parent(), self.assay)


class TestGenericMaterialManager(SamplesheetsModelTestBase):
    """Tests for GenericMaterialManager"""

    def setUp(self):
        super().setUp()
        # Set up SOURCE GenericMaterial
        self.source = self.make_material(
            item_type='SOURCE',
            name=SOURCE_NAME,
            unique_name=SOURCE_UNIQUE_NAME,
            characteristics=SOURCE_CHARACTERISTICS,
            study=self.study,
            assay=None,
            material_type=None,
            extra_material_type=None,
            factor_values=None,
            extract_label={},
            comments=DEFAULT_COMMENTS,
        )
        # Set up SAMPLE GenericMaterial
        self.sample = self.make_material(
            item_type='SAMPLE',
            name=SAMPLE_NAME,
            unique_name=SAMPLE_UNIQUE_NAME,
            characteristics=SAMPLE_CHARACTERISTICS,
            study=self.study,
            assay=None,
            material_type=None,
            extra_material_type=None,
            factor_values=None,
            extract_label={},
            comments=DEFAULT_COMMENTS,
        )

    def test_find_source(self):
        """Test find() by source name"""
        result = GenericMaterial.objects.find([SOURCE_NAME])
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.source)

    def test_find_source_type_source(self):
        """Test find() by source name with item_type=SOURCE"""
        result = GenericMaterial.objects.find(
            [SOURCE_NAME], item_types=['SOURCE']
        )
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.source)

    def test_find_source_type_sample(self):
        """Test find() by source name with item_type=SAMPLE (should fail)"""
        result = GenericMaterial.objects.find(
            [SOURCE_NAME], item_types=['SAMPLE']
        )
        self.assertEqual(result.count(), 0)

    def test_find_source_partial(self):
        """Test find() by partial source name (should fail)"""
        result = GenericMaterial.objects.find([SOURCE_NAME[:-2]])
        self.assertEqual(result.count(), 0)

    def test_find_source_alt(self):
        """Test find() by alt source name"""
        result = GenericMaterial.objects.find([get_alt_names(SOURCE_NAME)[0]])
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.source)

    def test_find_sample(self):
        """Test find() by sample name"""
        result = GenericMaterial.objects.find([SAMPLE_NAME])
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.sample)

    def test_find_sample_type_sample(self):
        """Test find() by sample name with item_type=SAMPLE"""
        result = GenericMaterial.objects.find(
            [SAMPLE_NAME], item_types=['SAMPLE']
        )
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.sample)

    def test_find_sample_type_source(self):
        """Test find() by sample name with item_type=SOURCE (should fail)"""
        result = GenericMaterial.objects.find(
            [SAMPLE_NAME], item_types=['SOURCE']
        )
        self.assertEqual(result.count(), 0)

    def test_find_sample_partial(self):
        """Test find() by partial sample name (should fail)"""
        result = GenericMaterial.objects.find([SAMPLE_NAME[:-2]])
        self.assertEqual(result.count(), 0)

    def test_find_sample_alt(self):
        """Test find() by alt sample name"""
        result = GenericMaterial.objects.find([get_alt_names(SAMPLE_NAME)[0]])
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.sample)

    def test_find_multi(self):
        """Test find() with multiple terms"""
        result = GenericMaterial.objects.find([SOURCE_NAME, SAMPLE_NAME])
        self.assertEqual(result.count(), 2)

    def test_find_multi_type_source(self):
        """Test find() with multiple terms and item_type=SOURCE"""
        result = GenericMaterial.objects.find(
            [SOURCE_NAME, SAMPLE_NAME], item_types=['SOURCE']
        )
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.source)

    def test_find_multi_type_sample(self):
        """Test find() with multiple terms and item_type=SAMPLE"""
        result = GenericMaterial.objects.find(
            [SOURCE_NAME, SAMPLE_NAME], item_types=['SAMPLE']
        )
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.sample)


class TestProcess(SamplesheetsModelTestBase):
    """Tests for the Process model"""

    def setUp(self):
        super().setUp()
        # Set up Protocol
        self.protocol = self.make_protocol(
            name=PROTOCOL_NAME,
            study=self.study,
            protocol_type=PROTOCOL_TYPE,
            description=DEFAULT_DESCRIPTION,
            uri=PROTOCOL_URI,
            version=PROTOCOL_VERSION,
            parameters=PROTOCOL_PARAMS,
            components=PROTOCOL_COMPONENTS,
            comments=DEFAULT_COMMENTS,
        )
        # Set up Process
        self.process = self.make_process(
            name=PROCESS_NAME,
            unique_name=PROCESS_UNIQUE_NAME,
            name_type=PROCESS_NAME_TYPE,
            protocol=self.protocol,
            study=self.study,
            assay=self.assay,
            parameter_values=PROCESS_PARAM_VALUES,
            performer=PROCESS_PERFORMER,
            perform_date=PROCESS_PERFORM_DATE,
            comments=DEFAULT_COMMENTS,
        )

    def test_initialization(self):
        """Test Process initialization"""
        expected = {
            'id': self.process.pk,
            'name': PROCESS_NAME,
            'unique_name': PROCESS_UNIQUE_NAME,
            'name_type': PROCESS_NAME_TYPE,
            'protocol': self.protocol.pk,
            'study': self.study.pk,
            'assay': self.assay.pk,
            'parameter_values': PROCESS_PARAM_VALUES,
            'performer': PROCESS_PERFORMER,
            'perform_date': PROCESS_PERFORM_DATE,
            'array_design_ref': None,
            'first_dimension': {},
            'second_dimension': {},
            'comments': DEFAULT_COMMENTS,
            'headers': [],
            'sharing_data': {},
            'retraction_data': {},
            'sodar_uuid': self.process.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.process), expected)

    def test__str__(self):
        """Test Process __str__() function"""
        expected = '{}: {}/{}/{}'.format(
            self.project.title,
            STUDY_TITLE,
            self.assay.get_name(),
            PROCESS_UNIQUE_NAME,
        )
        self.assertEqual(str(self.process), expected)

    def test__repr__(self):
        """Test Process __repr__() function"""
        expected = "Process('{}', '{}', '{}', '{}')".format(
            self.project.title,
            STUDY_TITLE,
            self.assay.get_name(),
            PROCESS_UNIQUE_NAME,
        )
        self.assertEqual(repr(self.process), expected)

    def test_get_study(self):
        """Test Process get_study() function"""
        self.assertEqual(self.process.get_study(), self.study)

    def test_get_project(self):
        """Test Process get_project() function"""
        self.assertEqual(self.process.get_project(), self.project)

    def test_get_parent(self):
        """Test Process get_parent() function"""
        self.assertEqual(self.process.get_parent(), self.assay)

    # TODO: Test header helpers


class TestISATab(SamplesheetsModelTestBase):
    """Tests for the ISATab model"""

    def setUp(self):
        super().setUp()
        self.isatab = self.make_isatab(
            project=self.project,
            data=ISATAB_DATA,
            investigation_uuid=self.investigation.sodar_uuid,
            archive_name=self.investigation.archive_name,
            tags=[],
            parser_version=DEFAULT_PARSER_VERSION,
            user=self.user_owner,
            description=ISATAB_DESC,
        )

    def test_initialization(self):
        """Test ISATab initialization"""
        expected = {
            'id': self.isatab.pk,
            'project': self.project.pk,
            'data': ISATAB_DATA,
            'investigation_uuid': self.investigation.sodar_uuid,
            'archive_name': self.investigation.archive_name,
            'tags': [],
            'parser_version': DEFAULT_PARSER_VERSION,
            'user': self.user_owner.pk,
            'extra_data': {},
            'description': ISATAB_DESC,
            'sodar_uuid': self.isatab.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.isatab), expected)

    def test__str__(self):
        """Test ISATab __str__()"""
        expected = '{}: {} ({})'.format(
            self.isatab.project.title,
            self.isatab.archive_name,
            self.isatab.date_created,
        )
        self.assertEqual(str(self.isatab), expected)

    def test__repr__(self):
        """Test ISATab __repr__()"""
        expected = 'ISATab({})'.format(
            ', '.join(
                repr(v)
                for v in [
                    self.isatab.project.title,
                    self.isatab.archive_name,
                    self.isatab.date_created,
                ]
            )
        )
        self.assertEqual(repr(self.isatab), expected)

    def test_get_name(self):
        """Test get_name()"""
        expected = '{} ({})'.format(
            self.investigation.title,
            timezone.localtime(self.isatab.date_created).strftime(
                '%Y-%m-%d %H:%M:%S'
            ),
        )
        self.assertEqual(self.isatab.get_full_name(), expected)

    def test_get_name_no_title(self):
        """Test get_name() with no title"""
        self.investigation.title = ''
        self.investigation.save()
        expected = '{} ({})'.format(
            self.investigation.archive_name.split('.')[0],
            timezone.localtime(self.isatab.date_created).strftime(
                '%Y-%m-%d %H:%M:%S'
            ),
        )
        self.assertEqual(self.isatab.get_full_name(), expected)

    def test_get_name_no_archive(self):
        """Test get_name() with no title or archive name"""
        self.investigation.title = ''
        self.investigation.save()
        self.isatab.archive_name = ''
        expected = '{} ({})'.format(
            self.project.title,
            timezone.localtime(self.isatab.date_created).strftime(
                '%Y-%m-%d %H:%M:%S'
            ),
        )
        self.assertEqual(self.isatab.get_full_name(), expected)


class TestIrodsAccessTicket(IrodsAccessTicketMixin, SamplesheetsModelTestBase):
    """Tests for the IrodsAccessTicket model"""

    def setUp(self):
        super().setUp()
        self.ticket = self.make_irods_ticket(
            study=self.study,
            assay=self.assay,
            ticket=IRODS_TICKET_STR,
            path=IRODS_TICKET_PATH,
            label=IRODS_TICKET_LABEL,
            user=self.user_owner,
        )

    def test_initialization(self):
        """Test IrodsAccessTicket initialization"""
        expected = {
            'id': self.ticket.pk,
            'study': self.study.pk,
            'assay': self.assay.pk,
            'label': IRODS_TICKET_LABEL,
            'ticket': IRODS_TICKET_STR,
            'path': IRODS_TICKET_PATH,
            'user': self.user_owner.pk,
            'sodar_uuid': self.ticket.sodar_uuid,
            'date_expires': None,
        }
        self.assertEqual(model_to_dict(self.ticket), expected)

    def test__str__(self):
        """Test IrodsAccessTicket __str__()"""
        expected = '{} / {} / {} / {}'.format(
            self.ticket.get_project().title,
            self.ticket.assay.get_display_name(),
            self.ticket.get_coll_name(),
            self.ticket.get_label(),
        )
        self.assertEqual(str(self.ticket), expected)

    def test__repr__(self):
        """Test IrodsAccessTicket __repr__()"""
        expected = 'IrodsAccessTicket({})'.format(
            ', '.join(
                repr(v)
                for v in [
                    self.ticket.get_project().title,
                    self.ticket.assay.get_display_name(),
                    self.ticket.get_coll_name(),
                    self.ticket.get_label(),
                ]
            )
        )
        self.assertEqual(repr(self.ticket), expected)

    def test_get_display_name(self):
        """Test get_display_name() with single assay"""
        expected = '{} / {}'.format(
            self.ticket.get_coll_name(),
            self.ticket.get_label(),
        )
        self.assertEqual(self.ticket.get_display_name(), expected)

    def test_get_display_name_multiple_assays(self):
        """Test get_display_name() with multiple assays"""
        self.make_assay(
            file_name=ASSAY2_FILE_NAME,
            study=self.study,
            tech_platform=ASSAY2_TECH_PLATFORM,
            tech_type=ASSAY2_TECH_TYPE,
            measurement_type=ASSAY2_MEASURE_TYPE,
            arcs=[],
            comments=DEFAULT_COMMENTS,
        )
        expected = '{} / {} / {}'.format(
            self.ticket.assay.get_display_name(),
            self.ticket.get_coll_name(),
            self.ticket.get_label(),
        )
        self.assertEqual(self.ticket.get_display_name(), expected)

    def test_get_webdav_link(self):
        """Test get_webdav_link()"""
        m = re.search(r'^(https?://)', settings.IRODS_WEBDAV_URL_ANON)
        self.assertTrue(m)
        url = re.sub(m.group(1), '', settings.IRODS_WEBDAV_URL_ANON)
        expected = (
            m.group(1)
            + settings.IRODS_WEBDAV_USER_ANON
            + ':'
            + IRODS_TICKET_STR
            + '@'
            + url
            + IRODS_TICKET_PATH
        )
        self.assertEqual(self.ticket.get_webdav_link(), expected)

    def test_is_active_no_expiry_date(self):
        """Test is_active() with no expiry date"""
        # Expiry date is None by default
        self.assertTrue(self.ticket.is_active())

    def test_is_active_expired(self):
        """Test is_active() with expired ticket"""
        self.ticket.date_expires = timezone.now() - timedelta(days=1)
        self.ticket.save()
        self.assertFalse(self.ticket.is_active())

    def test_is_active_not_expired(self):
        """Test is_active() with active ticket"""
        self.ticket.date_expires = timezone.now() + timedelta(days=1)
        self.ticket.save()
        self.assertTrue(self.ticket.is_active())

    def test_get_coll_name(self):
        """Test get_coll_name()"""
        self.assertEqual(
            self.ticket.get_coll_name(),
            IRODS_TICKET_PATH.split('/')[-1],
        )

    def test_get_label(self):
        """Test get_label()"""
        self.assertEqual(self.ticket.get_label(), IRODS_TICKET_LABEL)

    def test_get_label_none(self):
        """Test get_label() with no label set"""
        self.ticket.label = None
        self.ticket.save()
        self.assertEqual(
            self.ticket.get_label(),
            self.ticket.get_date_created(),
        )

    def test_get_date_created(self):
        """Test get_date_created()"""
        self.assertEqual(
            self.ticket.get_date_created(),
            timezone.localtime(self.ticket.date_created).strftime(
                '%Y-%m-%d %H:%M'
            ),
        )

    def test_get_date_expires(self):
        """Test get_date_expires()"""
        self.ticket.date_expires = timezone.now()
        self.ticket.save()
        self.assertEqual(
            self.ticket.get_date_expires(),
            timezone.localtime(self.ticket.date_expires).strftime('%Y-%m-%d'),
        )


class TestIrodsDataRequest(IrodsDataRequestMixin, SamplesheetsModelTestBase):
    """Tests for the IrodsDataRequest model"""

    def setUp(self):
        super().setUp()
        self.irods_backend = get_backend_api('omics_irods')
        self.request_path = os.path.join(
            self.irods_backend.get_path(self.assay), 'file.txt'
        )
        self.request = self.make_irods_request(
            project=self.project,
            action=IRODS_REQUEST_ACTION_DELETE,
            path=self.request_path,
            status=IRODS_REQUEST_STATUS_ACTIVE,
            description=IRODS_REQUEST_DESC,
            user=self.user_owner,
        )

    def test_initialization(self):
        """Test IrodsDataRequest initialization"""
        expected = {
            'id': self.request.pk,
            'project': self.project.pk,
            'action': IRODS_REQUEST_ACTION_DELETE,
            'path': self.request_path,
            'status': IRODS_REQUEST_STATUS_ACTIVE,
            'target_path': '',
            'status_info': '',
            'description': IRODS_REQUEST_DESC,
            'user': self.user_owner.pk,
            'sodar_uuid': self.request.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.request), expected)

    def test__str__(self):
        """Test IrodsDataRequest __str__()"""
        expected = '{}: {} {}'.format(
            self.request.project.title,
            self.request.action,
            self.request.get_short_path(),
        )
        self.assertEqual(str(self.request), expected)

    def test__repr__(self):
        """Test IrodsDataRequest __repr__()"""
        expected = 'IrodsDataRequest({})'.format(
            ', '.join(
                repr(v)
                for v in [
                    self.request.project.title,
                    self.assay.get_display_name(),
                    self.request.action,
                    self.request_path,
                    self.user_owner.username,
                ]
            )
        )
        self.assertEqual(repr(self.request), expected)

    def test_validate_action(self):
        """Test _validate_action()"""
        with self.assertRaises(ValidationError):
            self.request.action = 'MOVE'
            self.request.save()

    def test_validate_status(self):
        """Test _validate_status()"""
        with self.assertRaises(ValidationError):
            self.request.status = 'NOT A VALID STATUS'
            self.request.save()

    def test_get_display_name(self):
        """Test get_display_name()"""
        expected = '{} {}'.format(
            IRODS_REQUEST_ACTION_DELETE.capitalize(),
            self.request.get_short_path(),
        )
        self.assertEqual(self.request.get_display_name(), expected)

    def test_get_date_created(self):
        """Test get_date_created()"""
        self.assertEqual(
            self.request.get_date_created(),
            timezone.localtime(self.request.date_created).strftime(
                '%Y-%m-%d %H:%M'
            ),
        )

    def test_get_short_path(self):
        """Test get_short_path()"""
        expected = self.request_path.split('/')[-1]
        self.assertEqual(self.request.get_short_path(), expected)

    def test_get_assay(self):
        """Test get_assay()"""
        self.assertEqual(self.request.get_assay(), self.assay)

    def test_get_assay_no_assay(self):
        """Test get_assay() with no assay in path"""
        self.request.path = os.path.join(
            self.irods_backend.get_path(self.study), 'file.txt'
        )
        self.request.save()
        self.assertEqual(self.request.get_assay(), None)

    def test_get_assay_name(self):
        """Test get_assay_name()"""
        self.assertEqual(
            self.request.get_assay_name(), self.assay.get_display_name()
        )

    # NOTE: For is_data_object() and is_collection(), see test_models_taskflow
