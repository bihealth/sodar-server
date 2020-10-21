"""Tests for Ajax API view permissions in the ontologyaccess app"""

from django.urls import reverse

from ontologyaccess.tests.test_models import OBO_TERM_NAME
from ontologyaccess.tests.test_permissions import (
    TestOntologyAccessPermissionBase,
)


class TestOntologyAccessAjaxPermissions(TestOntologyAccessPermissionBase):
    """Tests for ontologyaccess Ajax API view permissions"""

    def test_ontology_list(self):
        """Test permissions for OBOOntologyListAjaxView"""
        url = reverse('ontologyaccess:ajax_obo_list')
        good_users = [self.superuser, self.regular_user]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200)
        self.assert_response(url, bad_users, 403)

    def test_term_query(self):
        """Test permissions for OBOTermQueryAjaxView"""
        url = reverse('ontologyaccess:ajax_obo_term_query')
        request_data = {'name': OBO_TERM_NAME}
        good_users = [self.superuser, self.regular_user]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200, data=request_data)
        self.assert_response(url, bad_users, 403, data=request_data)

    def test_term_list(self):
        """Test permissions for OBOTermQueryAjaxView"""
        url = reverse('ontologyaccess:ajax_obo_term_list')
        request_data = {'t': OBO_TERM_NAME}
        good_users = [self.superuser, self.regular_user]
        bad_users = [self.anonymous]
        self.assert_response(url, good_users, 200, data=request_data)
        self.assert_response(url, bad_users, 403, data=request_data)
