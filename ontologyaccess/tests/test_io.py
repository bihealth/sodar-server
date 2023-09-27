"""Tests for IO in the ontologyaccess app"""

import fastobo
import os

from test_plus.test import TestCase

from ontologyaccess.io import OBOFormatOntologyIO
from ontologyaccess.models import OBOFormatOntology, OBOFormatOntologyTerm


# Local constants
OBO_DIR = os.path.dirname(__file__) + '/obo/'
OBO_PATH = OBO_DIR + 'ex.obo'
OBO_NAME = 'EX'
EX_OBO_TERM_IDS = {
    'synonyms': 'EX:0000002',
    'alt_ids': 'EX:0000003',
    'comment': 'EX:0000004',
    'namespace': 'EX:0000005',
    'is_obsolete': 'EX:0000006',
    'no_def': 'EX:0000007',
}


class TestOBOFormatOntologyIO(TestCase):
    """Tests for the OBOFormatOntologyIO class"""

    def setUp(self):
        self.obo_io = OBOFormatOntologyIO()
        self.req_headers = {'User-Agent': 'Mozilla'}

    def test_import(self):
        """Test importing an example ontology"""
        self.assertEqual(OBOFormatOntology.objects.count(), 0)
        self.assertEqual(OBOFormatOntologyTerm.objects.count(), 0)

        obo_doc = fastobo.load(OBO_PATH)
        ontology = self.obo_io.import_obo(
            obo_doc=obo_doc, name=OBO_NAME, file=OBO_PATH
        )

        self.assertEqual(OBOFormatOntology.objects.count(), 1)
        self.assertEqual(OBOFormatOntologyTerm.objects.count(), 7)

        term = ontology.get_term_by_id(EX_OBO_TERM_IDS['synonyms'])
        self.assertEqual(len(term.synonyms), 2)
        self.assertEqual(
            term.synonyms[0], 'First synonym for example term 0000002'
        )
        term = ontology.get_term_by_id(EX_OBO_TERM_IDS['alt_ids'])
        self.assertEqual(len(term.alt_ids), 2)
        self.assertEqual(term.alt_ids[0], 'EX:8888883')
        term = ontology.get_term_by_id(EX_OBO_TERM_IDS['comment'])
        self.assertIsNotNone(term.comment)
        term = ontology.get_term_by_id(EX_OBO_TERM_IDS['namespace'])
        self.assertIsNotNone(term.namespace)
        term = ontology.get_term_by_id(EX_OBO_TERM_IDS['is_obsolete'])
        self.assertTrue(term.is_obsolete)
        self.assertEqual(term.replaced_by, 'EX:0000005')
        term = ontology.get_term_by_id(EX_OBO_TERM_IDS['no_def'])
        self.assertIsNone(term.definition)

    '''
    def test_import_batch_owl(self):
        """Test importing OWL ontologies in batch (this may take a while)"""
        for url in OWL_BATCH_URLS:
            self.assertEqual(OBOFormatOntology.objects.count(), 0)
            self.assertEqual(OBOFormatOntologyTerm.objects.count(), 0)

            file_name = url.split('/')[-1]
            file = self.obo_io.owl_to_obo(url)
            obo_doc = fastobo.load(file)
            ontology = self.obo_io.import_obo(
                obo_doc=obo_doc, name=file_name.split('.')[0].upper(), file=url
            )

            self.assertIsNotNone(ontology, msg=file_name)
            self.assertEqual(
                OBOFormatOntology.objects.count(), 1, msg=file_name
            )
            self.assertNotEqual(
                OBOFormatOntologyTerm.objects.count(), 0, msg=file_name
            )
            ontology.delete()
    '''

    # TODO: Test importing OWL with a local file
    # TODO: Test import_omim() with a local file
