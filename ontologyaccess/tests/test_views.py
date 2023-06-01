"""Tests for UI views in the ontologyaccess app"""

from django.urls import reverse

from test_plus.test import TestCase

from ontologyaccess.models import (
    OBOFormatOntology,
    OBOFormatOntologyTerm,
    DEFAULT_TERM_URL,
)
from ontologyaccess.tests.test_io import OBO_PATH
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


class TestOntologyAccessViewBase(OBOFormatOntologyModelMixin, TestCase):
    """Base class for ontologyaccess view tests"""

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()
        self.regular_user = self.make_user('regular_user')
        self.anonymous = None
        # Create Ontology and term
        self.ontology = self.make_obo_ontology(
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
        self.term = self.make_obo_term(
            ontology=self.ontology,
            term_id=OBO_TERM_ID,
            name=OBO_TERM_NAME,
            definition=OBO_TERM_DEFINITION,
            alt_ids=OBO_TERM_ALT_IDS,
            synonyms=OBO_TERM_SYNONYMS,
            namespace=OBO_TERM_NAMESPACE,
            comment=OBO_TERM_COMMENT,
        )


class TestOBOFormatOntologyListView(TestOntologyAccessViewBase):
    """Tests for OBOFormatOntologyListView"""

    def test_render(self):
        """Test rendering the ontology list view"""
        with self.login(self.superuser):
            response = self.client.get(reverse('ontologyaccess:list'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['object_list'])
        self.assertEqual(
            response.context['object_list'][0].pk, self.ontology.pk
        )


class TestOBOFormatOntologyDetailView(TestOntologyAccessViewBase):
    """Tests for OBOFormatOntologyDetailView"""

    def test_render(self):
        """Test rendering the ontology detail view"""
        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'ontologyaccess:obo_detail',
                    kwargs={'oboformatontology': self.ontology.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], self.ontology)
        self.assertIsNotNone(response.context['ex_term'])
        self.assertIsNotNone(response.context['ex_term_acc'])

    def test_render_no_terms(self):
        """Test rendering the ontology detail view with no terms"""
        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'ontologyaccess:obo_detail',
                    kwargs={'oboformatontology': self.ontology.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 200)


class TestOBOFormatOntologyImportView(TestOntologyAccessViewBase):
    """Tests for OBOFormatOntologyImportView"""

    def test_render(self):
        """Test rendering the ontology import view"""
        with self.login(self.superuser):
            response = self.client.get(reverse('ontologyaccess:obo_import'))
            self.assertEqual(response.status_code, 200)

    def test_import(self):
        """Test importing an ontology"""
        self.assertEqual(OBOFormatOntology.objects.count(), 1)
        with open(OBO_PATH) as file:
            post_data = {
                'file_upload': file,
                'name': 'EX',
                'title': 'Example Ontology',
                'term_url': DEFAULT_TERM_URL,
            }
            with self.login(self.superuser):
                response = self.client.post(
                    reverse('ontologyaccess:obo_import'), post_data
                )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('ontologyaccess:list'))
        self.assertEqual(OBOFormatOntology.objects.count(), 2)

    # TODO: Add test for OWL import


class TestOBOFormatOntologyUpdateView(TestOntologyAccessViewBase):
    """Tests for OBOFormatOntologyUpdateView"""

    def test_render(self):
        """Test rendering the ontology update view"""
        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'ontologyaccess:obo_update',
                    kwargs={'oboformatontology': self.ontology.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_update(self):
        """Test updating an ontology"""
        self.assertEqual(OBOFormatOntology.objects.count(), 1)
        post_data = {
            'name': OBO_NAME,
            'title': OBO_TITLE_UPDATED,
            'term_url': OBO_TERM_URL_ALT,
        }
        with self.login(self.superuser):
            response = self.client.post(
                reverse(
                    'ontologyaccess:obo_update',
                    kwargs={'oboformatontology': self.ontology.sodar_uuid},
                ),
                post_data,
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('ontologyaccess:list'))
        self.assertEqual(OBOFormatOntology.objects.count(), 1)
        self.ontology.refresh_from_db()
        self.assertEqual(self.ontology.title, OBO_TITLE_UPDATED)
        self.assertEqual(self.ontology.term_url, OBO_TERM_URL_ALT)


class TestOBOFormatOntologyDeleteView(TestOntologyAccessViewBase):
    """Tests for OBOFormatOntologyDeleteView"""

    def test_render(self):
        """Test rendering the ontology delete view"""
        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'ontologyaccess:obo_delete',
                    kwargs={'oboformatontology': self.ontology.sodar_uuid},
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_delete(self):
        """Test deleting an ontology"""
        self.assertEqual(OBOFormatOntology.objects.count(), 1)
        with self.login(self.superuser):
            response = self.client.post(
                reverse(
                    'ontologyaccess:obo_delete',
                    kwargs={'oboformatontology': self.ontology.sodar_uuid},
                )
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('ontologyaccess:list'))
        self.assertEqual(OBOFormatOntology.objects.count(), 0)
        self.assertEqual(OBOFormatOntologyTerm.objects.count(), 0)
