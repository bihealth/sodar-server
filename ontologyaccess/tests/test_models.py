"""Tests for models in the ontologyaccess app"""

from importlib import import_module
from test_plus.test import TestCase

from django.conf import settings
from django.forms.models import model_to_dict

from ontologyaccess.models import (
    OBOFormatOntology,
    OBOFormatOntologyTerm,
    DEFAULT_TERM_URL,
)


site = import_module(settings.SITE_PACKAGE)


# Local constants
OBO_ONTOLOGY_ID = 'tst.obo'
OBO_TITLE = 'Test Ontology'
OBO_DESCRIPTION = 'Ontology for testing.'
OBO_FORMAT_VERSION = '1.2'
OBO_DATA_VERSION = 'tst/releases/2020-09-23'
OBO_DEFAULT_NAMESPACE = 'test_ontology'

OBO_TERM_ID = 'TST:9990000'
OBO_TERM_ALT_IDS = ['TST:9990001', 'TST:9990002', 'TST:9990003']
OBO_TERM_NAME = 'Test term'
OBO_TERM_DEFINITION = 'Term used for testing.'
OBO_TERM_SYNONYMS = ['Imaginary term', 'Dummy term']
OBO_TERM_NAMESPACE = 'specific_namespace'
OBO_TERM_COMMENT = 'This is not a real term.'

SITE_VERSION = site.__version__


class OBOFormatOntologyModelMixin:
    """Helpers for OBOFormatOntology models creation"""

    @classmethod
    def _make_obo_ontology(
        cls,
        ontology_id,
        title,
        format_version=OBO_FORMAT_VERSION,
        description=None,
        data_version=None,
        default_namespace=None,
        term_url=DEFAULT_TERM_URL,
        sodar_version=SITE_VERSION,
    ):
        """Create OBOFormatOntology in database"""
        values = {
            'ontology_id': ontology_id,
            'title': title,
            'format_version': format_version,
            'description': description,
            'data_version': data_version,
            'default_namespace': default_namespace,
            'term_url': term_url,
            'sodar_version': sodar_version,
        }
        return OBOFormatOntology.objects.create(**values)

    @classmethod
    def _make_obo_term(
        cls,
        ontology,
        term_id,
        name,
        definition=None,
        alt_ids=None,
        synonyms=None,
        namespace=None,
        comment=None,
        is_obsolete=False,
        replaced_by=None,
    ):
        """Create OBOFormatOntologyTerm in database"""
        values = {
            'ontology': ontology,
            'term_id': term_id,
            'name': name,
            'definition': definition,
            'alt_ids': alt_ids or list(),
            'synonyms': synonyms or list(),
            'namespace': namespace,
            'comment': comment,
            'is_obsolete': is_obsolete,
            'replaced_by': replaced_by,
        }
        return OBOFormatOntologyTerm.objects.create(**values)


class TestOBOFormatOntologyBase(OBOFormatOntologyModelMixin, TestCase):
    """Base class for OBOFormatOntology model tests"""

    def setUp(self):
        self.ontology = self._make_obo_ontology(
            ontology_id=OBO_ONTOLOGY_ID,
            title=OBO_TITLE,
            description=OBO_DESCRIPTION,
            format_version=OBO_FORMAT_VERSION,
            data_version=OBO_DATA_VERSION,
            default_namespace=OBO_DEFAULT_NAMESPACE,
            term_url=DEFAULT_TERM_URL,
        )
        self.term = self._make_obo_term(
            ontology=self.ontology,
            term_id=OBO_TERM_ID,
            name=OBO_TERM_NAME,
            definition=OBO_TERM_DEFINITION,
            alt_ids=OBO_TERM_ALT_IDS,
            synonyms=OBO_TERM_SYNONYMS,
            namespace=OBO_TERM_NAMESPACE,
            comment=OBO_TERM_COMMENT,
        )


class TestOBOFormatOntology(TestOBOFormatOntologyBase):
    """Tests for the OBOFormatOntology model"""

    def test_initialization(self):
        """Test OBOFormatOntology initialization"""
        expected = {
            'id': self.ontology.pk,
            'ontology_id': OBO_ONTOLOGY_ID,
            'title': OBO_TITLE,
            'description': OBO_DESCRIPTION,
            'format_version': OBO_FORMAT_VERSION,
            'data_version': OBO_DATA_VERSION,
            'default_namespace': OBO_DEFAULT_NAMESPACE,
            'term_url': DEFAULT_TERM_URL,
            'sodar_version': SITE_VERSION,
            'sodar_uuid': self.ontology.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.ontology), expected)

    def test__str__(self):
        """Test OBOFormatOntology __str__() function"""
        expected = '{}: {}'.format(
            self.ontology.ontology_id, self.ontology.title,
        )
        self.assertEqual(str(self.ontology), expected)

    def test__repr__(self):
        """Test OBOFormatOntology __repr__() function"""
        expected = "OBOFormatOntology('{}', '{}')".format(
            self.ontology.ontology_id, self.ontology.title,
        )
        self.assertEqual(repr(self.ontology), expected)

    def test_get_term_by_id(self):
        """Test get_term_by_id()"""
        self.assertEqual(self.ontology.get_term_by_id(OBO_TERM_ID), self.term)
        self.assertEqual(self.ontology.get_term_by_id('Not an ID'), None)


class TestOBOFormatOntologyTerm(TestOBOFormatOntologyBase):
    """Tests for the OBOFormatOntologyTerm model"""

    def test_initialization(self):
        """Test OBOFormatOntologyTerm initialization"""
        expected = {
            'id': self.term.pk,
            'ontology': self.ontology.pk,
            'term_id': OBO_TERM_ID,
            'alt_ids': OBO_TERM_ALT_IDS,
            'name': OBO_TERM_NAME,
            'definition': OBO_TERM_DEFINITION,
            'synonyms': OBO_TERM_SYNONYMS,
            'namespace': OBO_TERM_NAMESPACE,
            'comment': OBO_TERM_COMMENT,
            'is_obsolete': False,
            'replaced_by': None,
            'sodar_uuid': self.term.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.term), expected)

    def test__str__(self):
        """Test OBOFormatOntologyTerm __str__() function"""
        expected = '{} ({})'.format(self.term.term_id, self.term.name,)
        self.assertEqual(str(self.term), expected)

    def test__repr__(self):
        """Test OBOFormatOntologyTerm __repr__() function"""
        expected = "OBOFormatOntologyTerm('{}', '{}', '{}')".format(
            self.term.ontology.ontology_id, self.term.term_id, self.term.name,
        )
        self.assertEqual(repr(self.term), expected)

    def test_get_id_space(self):
        """Test get_id_space()"""
        self.assertEqual(
            self.term.get_id_space(), self.term.term_id.split(':')[0]
        )

    def test_get_local_id(self):
        """Test get_local_id()"""
        self.assertEqual(
            self.term.get_local_id(), self.term.term_id.split(':')[1]
        )
