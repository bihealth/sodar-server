"""Tests for models in the samplesheets app"""

# NOTE: Retraction and sharing data not yet tested, to be implemented
# TODO: Test validation rules and uniqueness constraints
import altamisa
from datetime import timedelta
import pytz
import re

from django.conf import settings
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.datetime_safe import datetime
from django.utils.timezone import localtime

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import Role, SODAR_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from samplesheets.models import (
    Investigation,
    Study,
    Assay,
    Protocol,
    Process,
    GenericMaterial,
    ISATab,
    NOT_AVAILABLE_STR,
    CONFIG_LABEL_CREATE,
    IrodsAccessTicket,
)
from samplesheets.utils import get_alt_names


# Local constants --------------------------------------------------------------


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


# Helper mixins ----------------------------------------------------------------


class SampleSheetModelMixin:
    """Helpers for samplesheets models creation"""

    @classmethod
    def _make_investigation(
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
        obj = Investigation(**values)
        obj.save()
        return obj

    @classmethod
    def _make_study(
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
        obj = Study(**values)
        obj.save()
        return obj

    @classmethod
    def _make_protocol(
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
        obj = Protocol(**values)
        obj.save()
        return obj

    @classmethod
    def _make_assay(
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
        obj = Assay(**values)
        obj.save()
        return obj

    @classmethod
    def _make_material(
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
        obj = GenericMaterial(**values)
        obj.save()
        return obj

    @classmethod
    def _make_process(
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
        obj = Process(**values)
        obj.save()
        return obj

    @classmethod
    def _set_configuration(cls, investigation, config_name):
        """Set the configuration for an investigation"""
        investigation.comments[CONFIG_LABEL_CREATE] = {
            'unit': None,
            'value': config_name,
        }
        investigation.save()
        return investigation

    @classmethod
    def _make_isatab(
        cls,
        project,
        data,
        investigation_uuid=None,
        archive_name=None,
        tags=[],
        parser_version=None,
        user=None,
        extra_data={},
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
        }
        obj = ISATab(**values)
        obj.save()
        return obj

    @classmethod
    def _make_irods_access_ticket(
        cls,
        project,
        study,
        assay,
        ticket,
        path,
        label=None,
        user=None,
        date_expires=None,  # never expires
    ):
        """Create an iRODS access ticket object in the database"""
        values = {
            'project': project,
            'study': study,
            'assay': assay,
            'ticket': ticket,
            'path': path,
            'label': label,
            'user': user,
            'date_expires': date_expires,
        }
        obj = IrodsAccessTicket(**values)
        obj.save()
        return obj


# Test classes -----------------------------------------------------------------


class TestSampleSheetBase(
    ProjectMixin, RoleAssignmentMixin, SampleSheetModelMixin, TestCase
):
    """Base class for Samplesheets tests"""

    def setUp(self):
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

        # Set up Investigation
        self.investigation = self._make_investigation(
            identifier=INV_IDENTIFIER,
            file_name=INV_FILE_NAME,
            project=self.project,
            title=INV_TITLE,
            description=DEFAULT_DESCRIPTION,
            comments=DEFAULT_COMMENTS,
            archive_name=INV_ARCHIVE_NAME,
        )

        # Set up Study
        self.study = self._make_study(
            identifier=STUDY_IDENTIFIER,
            file_name=STUDY_FILE_NAME,
            investigation=self.investigation,
            title=STUDY_TITLE,
            description=DEFAULT_DESCRIPTION,
            comments=DEFAULT_COMMENTS,
        )

        # Set up Assay
        self.assay = self._make_assay(
            file_name=ASSAY_FILE_NAME,
            study=self.study,
            tech_platform=ASSAY_TECH_PLATFORM,
            tech_type=ASSAY_TECH_TYPE,
            measurement_type=ASSAY_MEASURE_TYPE,
            arcs=[],
            comments=DEFAULT_COMMENTS,
        )


class TestInvestigation(TestSampleSheetBase):
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


class TestStudy(TestSampleSheetBase):
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


class TestProtocol(TestSampleSheetBase):
    """Tests for the Protocol model"""

    def setUp(self):
        super().setUp()

        # Set up Protocol
        self.protocol = self._make_protocol(
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


class TestAssay(TestSampleSheetBase):
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


class TestSource(TestSampleSheetBase):
    """Tests for the GenericMaterial model with type SOURCE"""

    def setUp(self):
        super().setUp()

        # Set up SOURCE GenericMaterial
        self.material = self._make_material(
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


class TestSample(TestSampleSheetBase):
    """Tests for the GenericMaterial model with type SAMPLE"""

    def setUp(self):
        super().setUp()

        # Set up SAMPLE GenericMaterial
        self.material = self._make_material(
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


class TestMaterial(TestSampleSheetBase):
    """Tests for the GenericMaterial model with type MATERIAL"""

    def setUp(self):
        super().setUp()

        # Set up MATERIAL GenericMaterial
        self.material = self._make_material(
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


class TestDataFile(TestSampleSheetBase):
    """Tests for the GenericMaterial model with type DATA"""

    def setUp(self):
        super().setUp()

        # Set up DATA GenericMaterial
        self.material = self._make_material(
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


class TestGenericMaterialManager(TestSampleSheetBase):
    """Tests for GenericMaterialManager"""

    def setUp(self):
        super().setUp()

        # Set up SOURCE GenericMaterial
        self.source = self._make_material(
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
        self.sample = self._make_material(
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


class TestProcess(TestSampleSheetBase):
    """Tests for the Process model"""

    def setUp(self):
        super().setUp()

        # Set up Protocol
        self.protocol = self._make_protocol(
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
        self.process = self._make_process(
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


class TestISATab(TestSampleSheetBase):
    """Tests for the ISATab model"""

    def setUp(self):
        super().setUp()
        self.isatab = self._make_isatab(
            project=self.project,
            data=ISATAB_DATA,
            investigation_uuid=self.investigation.sodar_uuid,
            archive_name=self.investigation.archive_name,
            tags=[],
            parser_version=DEFAULT_PARSER_VERSION,
            user=self.user_owner,
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
        self.assertEqual(self.isatab.get_name(), expected)

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
        self.assertEqual(self.isatab.get_name(), expected)

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
        self.assertEqual(self.isatab.get_name(), expected)


class TestIrodsAccessTicket(TestSampleSheetBase):
    """Tests for the IrodsAccessTicket model"""

    def setUp(self):
        super().setUp()
        self.path = '/path/to/some/trackhub'
        self.label = 'Some Ticket'
        self.ticket = 'abcdef'
        self.date_expires = None
        self.irods_access_ticket = self._make_irods_access_ticket(
            project=self.project,
            study=self.study,
            assay=self.assay,
            ticket=self.ticket,
            path=self.path,
            label=self.label,
            user=self.user_owner,
            date_expires=self.date_expires,
        )

    def _get_expiry_today(self):
        return (
            datetime.now()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(pytz.utc)
        )

    def test_initialization(self):
        """Test IrodsAccessTicket initialization"""
        expected = {
            'id': self.irods_access_ticket.pk,
            'project': self.project.pk,
            'study': self.study.pk,
            'assay': self.assay.pk,
            'label': self.label,
            'ticket': self.ticket,
            'path': self.path,
            'user': self.user_owner.pk,
            'sodar_uuid': self.irods_access_ticket.sodar_uuid,
            'date_expires': self.date_expires,
        }
        self.assertEqual(model_to_dict(self.irods_access_ticket), expected)

    def test__str__(self):
        """Test IrodsAccessTicket __str__()"""
        expected = '{} / {} / {} / {}'.format(
            self.irods_access_ticket.project.title,
            self.irods_access_ticket.assay.get_display_name(),
            self.irods_access_ticket.get_track_hub_name(),
            self.irods_access_ticket.get_label(),
        )
        self.assertEqual(str(self.irods_access_ticket), expected)

    def test__repr__(self):
        """Test IrodsAccessTicket __repr__()"""
        expected = 'IrodsAccessTicket({})'.format(
            ', '.join(
                repr(v)
                for v in [
                    self.irods_access_ticket.project.title,
                    self.irods_access_ticket.assay.get_display_name(),
                    self.irods_access_ticket.get_track_hub_name(),
                    self.irods_access_ticket.get_label(),
                ]
            )
        )
        self.assertEqual(repr(self.irods_access_ticket), expected)

    def test_get_display_name_one_assay(self):
        """Test get_display_name()"""
        expected = '{} / {}'.format(
            self.irods_access_ticket.get_track_hub_name(),
            self.irods_access_ticket.get_label(),
        )
        self.assertEqual(self.irods_access_ticket.get_display_name(), expected)

    def test_get_display_name_two_assays(self):
        """Test get_display_name()"""
        self._make_assay(
            file_name=ASSAY2_FILE_NAME,
            study=self.study,
            tech_platform=ASSAY2_TECH_PLATFORM,
            tech_type=ASSAY2_TECH_TYPE,
            measurement_type=ASSAY2_MEASURE_TYPE,
            arcs=[],
            comments=DEFAULT_COMMENTS,
        )
        expected = '{} / {} / {}'.format(
            self.irods_access_ticket.assay.get_display_name(),
            self.irods_access_ticket.get_track_hub_name(),
            self.irods_access_ticket.get_label(),
        )
        self.assertEqual(self.irods_access_ticket.get_display_name(), expected)

    def test_get_webdav_link(self):
        """Test get_webdav_link()"""
        m = re.search(r'^(https?://)', settings.IRODS_WEBDAV_URL_ANON)
        self.assertTrue(m)
        url = re.sub(m.group(1), '', settings.IRODS_WEBDAV_URL_ANON)
        expected = (
            m.group(1)
            + settings.IRODS_WEBDAV_USER_ANON
            + ':'
            + self.ticket
            + '@'
            + url
            + self.path
        )
        self.assertEqual(self.irods_access_ticket.get_webdav_link(), expected)

    def test_is_active_no_expiry_date(self):
        """Test is_active()"""
        self.irods_access_ticket.date_expires = None
        self.irods_access_ticket.save()
        self.assertTrue(self.irods_access_ticket.is_active())

    def test_is_active_expired(self):
        """Test is_active()"""
        self.irods_access_ticket.date_expires = (
            self._get_expiry_today() - timedelta(days=1)
        )
        self.irods_access_ticket.save()
        self.assertFalse(self.irods_access_ticket.is_active())

    def test_is_active_expires_today(self):
        """Test is_active()"""
        # Ugly timezone conversion
        self.irods_access_ticket.date_expires = self._get_expiry_today()
        self.irods_access_ticket.save()
        self.assertFalse(self.irods_access_ticket.is_active())

    def test_is_active_expires_tomorrow(self):
        """Test is_active()"""
        self.irods_access_ticket.date_expires = (
            self._get_expiry_today() + timedelta(days=1)
        )
        self.irods_access_ticket.save()
        self.assertTrue(self.irods_access_ticket.is_active())

    def test_get_track_hub_name(self):
        """Test get_track_hub_name()"""
        self.assertEqual(
            self.irods_access_ticket.get_track_hub_name(),
            self.path.split('/')[-1],
        )

    def test_get_label(self):
        """Test get_label()"""
        self.assertEqual(self.irods_access_ticket.get_label(), self.label)

    def test_get_label_none(self):
        """Test get_label()"""
        self.irods_access_ticket.label = None
        self.irods_access_ticket.save()
        self.assertEqual(
            self.irods_access_ticket.get_label(),
            self.irods_access_ticket.get_date_created(),
        )

    def test_get_date_created(self):
        """Test get_date_created()"""
        self.assertEqual(
            self.irods_access_ticket.get_date_created(),
            localtime(self.irods_access_ticket.date_created).strftime(
                '%Y-%m-%d %H:%M'
            ),
        )

    def test_get_date_expires(self):
        """Test get_date_expires()"""
        self.irods_access_ticket.date_expires = self._get_expiry_today()
        self.irods_access_ticket.save()
        self.assertEqual(
            self.irods_access_ticket.get_date_expires(),
            localtime(self.irods_access_ticket.date_expires).strftime(
                '%Y-%m-%d'
            ),
        )
