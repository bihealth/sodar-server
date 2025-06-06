"""Tests for Ajax API views in the ontologyaccess app"""

import json

from django.urls import reverse

from ontologyaccess.tests.test_views import (
    OntologyAccessViewTestBase,
    OBO_TERM_NAME,
)


# Local constants
OBO_ONTOLOGY_ID_ALT = 'alt.obo'
OBO_ONTOLOGY_NAME_ALT = 'ALT'
OBO_ONTOLOGY_FILE_ALT = 'alt.obo'
OBO_ONTOLOGY_TITLE_ALT = 'Alternative ontology'
OBO_TERM_ID_ALT = 'ALT:0000003'
OBO_TERM_NAME_ALT = 'Alt term'


class TestOBOOntologyListAjaxView(OntologyAccessViewTestBase):
    """Tests for OBOOntologyListAjaxView"""

    def test_get(self):
        """Test OBOOntologyListAjaxView GET"""
        with self.login(self.superuser):
            response = self.client.get(reverse('ontologyaccess:ajax_obo_list'))
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        expected = {
            'ontologies': {
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
        }
        self.assertEqual(response_data, expected)


class TestOBOTermQueryAjaxView(OntologyAccessViewTestBase):
    """Tests for OBOTermQueryAjaxView"""

    def setUp(self):
        super().setUp()
        # Create second ontology and term
        self.ontology2 = self.make_obo_ontology(
            name=OBO_ONTOLOGY_NAME_ALT,
            file=OBO_ONTOLOGY_FILE_ALT,
            ontology_id=OBO_ONTOLOGY_ID_ALT,
            title=OBO_ONTOLOGY_TITLE_ALT,
        )
        self.term2 = self.make_obo_term(
            ontology=self.ontology2,
            term_id=OBO_TERM_ID_ALT,
            name=OBO_TERM_NAME_ALT,
        )
        self.url = reverse('ontologyaccess:ajax_obo_term_query')

    def test_get(self):
        """Test OBOTermQueryAjaxView GET with single term"""
        query_data = {'s': self.term.name}
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 1)
        expected = {
            'ontology_name': self.ontology.name,
            'term_id': self.term.term_id,
            'name': self.term.name,
            # 'definition': self.term.definition,
            'is_obsolete': self.term.is_obsolete,
            'replaced_by': self.term.replaced_by,
            'accession': self.term.get_url(),
        }
        self.assertEqual(response_data['terms'][0], expected)

    def test_get_multiple(self):
        """Test GET with multiple terms"""
        query_data = {'s': 'term'}
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 2)

    def test_get_limit(self):
        """Test GET limited to specific ontology"""
        query_data = {'s': 'term', 'o': self.ontology2.name}
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 1)
        expected = {
            'ontology_name': self.ontology2.name,
            'term_id': self.term2.term_id,
            'name': self.term2.name,
            # 'definition': self.term2.definition,
            'is_obsolete': self.term2.is_obsolete,
            'replaced_by': self.term2.replaced_by,
            'accession': self.term2.get_url(),
        }
        self.assertEqual(response_data['terms'][0], expected)

    def test_get_limit_multiple(self):
        """Test GET limited to multiple ontologies"""
        query_data = {
            's': 'term',
            'o': [self.ontology.name, self.ontology2.name],
        }
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 2)

    def test_get_no_data(self):
        """Test GET without query string (should fail)"""
        query_data = {}
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 400)

    def test_get_order(self):
        """Test GET with ordering by ontology"""
        query_data = {
            's': 'term',
            'o': [self.ontology2.name, self.ontology.name],
            'order': '1',
        }
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 2)
        expected = {
            'ontology_name': self.ontology2.name,
            'term_id': self.term2.term_id,
            'name': self.term2.name,
            # 'definition': self.term2.definition,
            'is_obsolete': self.term2.is_obsolete,
            'replaced_by': self.term2.replaced_by,
            'accession': self.term2.get_url(),
        }
        self.assertEqual(response_data['terms'][0], expected)

    def test_get_id(self):
        """Test GET for single term with term ID"""
        query_data = {'s': self.term.term_id}
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 1)
        expected = {
            'ontology_name': self.ontology.name,
            'term_id': self.term.term_id,
            'name': self.term.name,
            # 'definition': self.term.definition,
            'is_obsolete': self.term.is_obsolete,
            'replaced_by': self.term.replaced_by,
            'accession': self.term.get_url(),
        }
        self.assertEqual(response_data['terms'][0], expected)


class TestOBOTermListAjaxView(OntologyAccessViewTestBase):
    """Tests for OBOTermListAjaxView"""

    def setUp(self):
        super().setUp()
        # Create second ontology and term
        self.ontology2 = self.make_obo_ontology(
            name=OBO_ONTOLOGY_NAME_ALT,
            file=OBO_ONTOLOGY_FILE_ALT,
            ontology_id=OBO_ONTOLOGY_ID_ALT,
            title=OBO_ONTOLOGY_TITLE_ALT,
        )
        self.term2 = self.make_obo_term(
            ontology=self.ontology2,
            term_id=OBO_TERM_ID_ALT,
            name=OBO_TERM_NAME_ALT,
        )
        self.url = reverse('ontologyaccess:ajax_obo_term_list')

    def test_get(self):
        """Test OBOTermListAjaxView GET"""
        query_data = {'t': [OBO_TERM_NAME, OBO_TERM_NAME_ALT]}
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 2)
        expected = [
            {
                'ontology_name': self.ontology.name,
                'term_id': self.term.term_id,
                'name': self.term.name,
                # 'definition': self.term.definition,
                'is_obsolete': self.term.is_obsolete,
                'replaced_by': self.term.replaced_by,
                'accession': self.term.get_url(),
            },
            {
                'ontology_name': self.ontology2.name,
                'term_id': self.term2.term_id,
                'name': self.term2.name,
                # 'definition': self.term2.definition,
                'is_obsolete': self.term2.is_obsolete,
                'replaced_by': self.term2.replaced_by,
                'accession': self.term2.get_url(),
            },
        ]
        self.assertEqual(response_data['terms'], expected)

    def test_get_inexact(self):
        """Test GET with inexact key (should fail)"""
        query_data = {'t': 'term'}
        with self.login(self.superuser):
            response = self.client.get(self.url, data=query_data)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 0)
