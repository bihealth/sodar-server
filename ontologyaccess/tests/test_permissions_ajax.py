"""Tests for Ajax API view permissions in the ontologyaccess app"""

from django.urls import reverse

from ontologyaccess.tests.test_models import OBO_TERM_NAME
from ontologyaccess.tests.test_permissions import (
    OntologyAccessPermissionTestBase,
)


class TestOntologyAccessAjaxPermissions(OntologyAccessPermissionTestBase):
    """Tests for ontologyaccess Ajax API view permissions"""

    def setUp(self):
        super().setUp()
        self.good_users = [self.superuser, self.regular_user]
        self.bad_users = [self.anonymous]

    def test_get_ontology_list(self):
        """Test OBOOntologyListAjaxView GET"""
        url = reverse('ontologyaccess:ajax_obo_list')
        self.assert_response(url, self.good_users, 200)
        self.assert_response(url, self.bad_users, 403)

    def test_get_ontology_list_read_only(self):
        """Test OBOOntologyListAjaxView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse('ontologyaccess:ajax_obo_list')
        self.assert_response(url, self.good_users, 200)
        self.assert_response(url, self.bad_users, 403)

    def test_get_term_query(self):
        """Test OBOTermQueryAjaxView GET"""
        url = reverse('ontologyaccess:ajax_obo_term_query')
        request_data = {'s': OBO_TERM_NAME}
        self.assert_response(url, self.good_users, 200, data=request_data)
        self.assert_response(url, self.bad_users, 403, data=request_data)

    def test_get_term_query_read_only(self):
        """Test OBOTermQueryAjaxView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse('ontologyaccess:ajax_obo_term_query')
        request_data = {'s': OBO_TERM_NAME}
        self.assert_response(url, self.good_users, 200, data=request_data)
        self.assert_response(url, self.bad_users, 403, data=request_data)

    def test_get_term_list(self):
        """Test OBOTermQueryAjaxView GET"""
        url = reverse('ontologyaccess:ajax_obo_term_list')
        request_data = {'t': OBO_TERM_NAME}
        self.assert_response(url, self.good_users, 200, data=request_data)
        self.assert_response(url, self.bad_users, 403, data=request_data)

    def test_get_term_list_read_only(self):
        """Test OBOTermQueryAjaxView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse('ontologyaccess:ajax_obo_term_list')
        request_data = {'t': OBO_TERM_NAME}
        self.assert_response(url, self.good_users, 200, data=request_data)
        self.assert_response(url, self.bad_users, 403, data=request_data)
