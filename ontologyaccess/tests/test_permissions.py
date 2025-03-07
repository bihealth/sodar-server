"""Tests for UI view permissions in the ontologyaccess app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.tests.test_permissions import SiteAppPermissionTestBase

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


class OntologyAccessPermissionTestBase(
    OBOFormatOntologyModelMixin, SiteAppPermissionTestBase
):
    """Base class for ontologyaccess UI view permission tests"""

    def setUp(self):
        super().setUp()
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
        self.bad_users = [self.anonymous, self.regular_user]


class TestOntologyAccessPermissions(OntologyAccessPermissionTestBase):
    """Tests for ontologyaccess UI view permissions"""

    def test_get_ontology_list(self):
        """Test OBOFormatOntologyListView GET"""
        url = reverse('ontologyaccess:list')
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_ontology_detail(self):
        """Test OBOFormatOntologyDetailView GET"""
        url = reverse(
            'ontologyaccess:obo_detail',
            kwargs={'oboformatontology': self.ontology.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_ontology_detail_read_only(self):
        """Test OBOFormatOntologyDetailView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse(
            'ontologyaccess:obo_detail',
            kwargs={'oboformatontology': self.ontology.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_ontology_import(self):
        """Test OBOFormatOntologyImportView GET"""
        url = reverse('ontologyaccess:obo_import')
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_ontology_import_read_only(self):
        """Test OBOFormatOntologyImportView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse('ontologyaccess:obo_import')
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_ontology_update(self):
        """Test OBOFormatOntologyUpdateView GET"""
        url = reverse(
            'ontologyaccess:obo_update',
            kwargs={'oboformatontology': self.ontology.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_get_ontology_update_read_only(self):
        """Test OBOFormatOntologyUpdateView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse(
            'ontologyaccess:obo_update',
            kwargs={'oboformatontology': self.ontology.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_ontology_delete(self):
        """Test OBOFormatOntologyDeleteView GET"""
        url = reverse(
            'ontologyaccess:obo_delete',
            kwargs={'oboformatontology': self.ontology.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)

    def test_ontology_delete_read_only(self):
        """Test OBOFormatOntologyDeleteView GET with site read-only mode"""
        self.set_site_read_only()
        url = reverse(
            'ontologyaccess:obo_delete',
            kwargs={'oboformatontology': self.ontology.sodar_uuid},
        )
        self.assert_response(url, self.superuser, 200)
        self.assert_response(url, self.bad_users, 302)
