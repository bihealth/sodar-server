"""Tests for the API in the ontologyaccess app"""

from test_plus.test import TestCase

from projectroles.plugins import get_backend_api

from ontologyaccess.models import DEFAULT_TERM_URL
from ontologyaccess.tests.test_models import OBOFormatOntologyModelMixin


# Local constants
OBO_ONTOLOGY_ID = 'tst.obo'
OBO_NAME = 'TST'
OBO_FILE = 'tst.obo'
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

OBO_TITLE_UPDATED = 'Updated Ontology Title'
OBO_TERM_URL_ALT = 'http://example.com/ontology/TST/{local_id}'


class TestOntologyAccessAPI(OBOFormatOntologyModelMixin, TestCase):
    """OntologyAccessAPI tests"""

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()

        self.regular_user = self.make_user('regular_user')

        # No user
        self.anonymous = None

        # Create Ontology and term
        self.ontology = self._make_obo_ontology(
            name=OBO_NAME,
            file=OBO_FILE,
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

        # Get API
        self.ontology_api = get_backend_api('ontologyaccess_backend')

    def test_get_obo_dict_name(self):
        """Test get_obo_dict() with name as key"""
        expected = {
            self.ontology.name: {
                'sodar_uuid': str(self.ontology.sodar_uuid),
                'file': self.ontology.file,
                'title': self.ontology.title,
                'ontology_id': self.ontology.ontology_id,
                'description': self.ontology.description,
                'data_version': self.ontology.data_version,
                'term_url': self.ontology.term_url,
            }
        }
        ret_data = self.ontology_api.get_obo_dict(key='name')
        self.assertEqual(ret_data, expected)

    def test_get_obo_dict_uuid(self):
        """Test get_obo_dict() with sodar_uuid as key"""
        expected = {
            str(self.ontology.sodar_uuid): {
                'name': self.ontology.name,
                'file': self.ontology.file,
                'title': self.ontology.title,
                'ontology_id': self.ontology.ontology_id,
                'description': self.ontology.description,
                'data_version': self.ontology.data_version,
                'term_url': self.ontology.term_url,
            }
        }
        ret_data = self.ontology_api.get_obo_dict(key='sodar_uuid')
        self.assertEqual(ret_data, expected)

    def test_get_obo_dict_invalid(self):
        """Test get_obo_dict() with an invalid key (should fail)"""
        with self.assertRaises(ValueError):
            self.ontology_api.get_obo_dict(key=None)
