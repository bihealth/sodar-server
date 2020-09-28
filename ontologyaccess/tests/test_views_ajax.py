"""Tests for Ajax API views in the ontologyaccess app"""

import json

from django.urls import reverse

from ontologyaccess.tests.test_views import TestOntologyAccessViewBase


OBO_ONTOLOGY_ID_ALT = 'alt.obo'
OBO_ONTOLOGY_TITLE_ALT = 'Alternative ontology'
OBO_TERM_ID_ALT = 'ALT:0000003'
OBO_TERM_NAME_ALT = 'Alt term'


class TestOBOOntologyListAjaxView(TestOntologyAccessViewBase):
    """Tests for OBOOntologyListAjaxView"""

    def test_list(self):
        """Test listing ontologies"""

        with self.login(self.superuser):
            response = self.client.get(reverse('ontologyaccess:ajax_obo_list'))

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        expected = {
            'ontologies': {
                str(self.ontology.sodar_uuid): {
                    'title': self.ontology.title,
                    'ontology_id': self.ontology.ontology_id,
                    'description': self.ontology.description,
                    'data_version': self.ontology.data_version,
                    'term_url': self.ontology.term_url,
                }
            }
        }
        self.assertEqual(response_data, expected)


class TestOBOTermQueryAjaxView(TestOntologyAccessViewBase):
    """Tests for OBOTermQueryAjaxView"""

    def setUp(self):
        super().setUp()

        # Create second ontology and term
        self.ontology2 = self._make_obo_ontology(
            ontology_id=OBO_ONTOLOGY_ID_ALT, title=OBO_ONTOLOGY_TITLE_ALT,
        )
        self.term2 = self._make_obo_term(
            ontology=self.ontology2,
            term_id=OBO_TERM_ID_ALT,
            name=OBO_TERM_NAME_ALT,
        )

    def test_query(self):
        """Test querying for a single term"""
        query_data = {'name': self.term.name}

        with self.login(self.superuser):
            response = self.client.get(
                reverse('ontologyaccess:ajax_obo_term_query'), data=query_data
            )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 1)
        expected = {
            'ontology': str(self.ontology.sodar_uuid),
            'term_id': self.term.term_id,
            'name': self.term.name,
            'definition': self.term.definition,
            'is_obsolete': self.term.is_obsolete,
            'replaced_by': self.term.replaced_by,
        }
        self.assertEqual(response_data['terms'][0], expected)

    def test_query_multiple(self):
        """Test querying for multiple terms"""
        query_data = {'name': 'term'}

        with self.login(self.superuser):
            response = self.client.get(
                reverse('ontologyaccess:ajax_obo_term_query'), data=query_data
            )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 2)

    def test_query_limit(self):
        """Test querying limited to a specific ontology"""
        query_data = {'name': 'term'}

        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'ontologyaccess:ajax_obo_term_query',
                    kwargs={'oboformatontology': self.ontology2.sodar_uuid},
                ),
                data=query_data,
            )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['terms']), 1)
        expected = {
            'ontology': str(self.ontology2.sodar_uuid),
            'term_id': self.term2.term_id,
            'name': self.term2.name,
            'definition': self.term2.definition,
            'is_obsolete': self.term2.is_obsolete,
            'replaced_by': self.term2.replaced_by,
        }
        self.assertEqual(response_data['terms'][0], expected)

    def test_query_no_data(self):
        """Test querying without a query string (should fail)"""
        query_data = {}

        with self.login(self.superuser):
            response = self.client.get(
                reverse(
                    'ontologyaccess:ajax_obo_term_query',
                    kwargs={'oboformatontology': self.ontology2.sodar_uuid},
                ),
                data=query_data,
            )

        self.assertEqual(response.status_code, 400)
