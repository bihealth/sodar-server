"""Tests for IO in the ontologyaccess app"""

import fastobo
import os
from urllib.request import urlopen

from test_plus.test import TestCase

from ontologyaccess.io import OBOFormatOntologyIO
from ontologyaccess.models import OBOFormatOntology, OBOFormatOntologyTerm


# Local constants
OBO_DIR = os.path.dirname(__file__) + '/obo/'
OBO_PATH = OBO_DIR + 'ex.obo'
EX_OBO_TERM_IDS = {
    'synonyms': 'EX:0000002',
    'alt_ids': 'EX:0000003',
    'comment': 'EX:0000004',
    'namespace': 'EX:0000005',
    'is_obsolete': 'EX:0000006',
    'no_def': 'EX:0000007',
}
OBO_BATCH_URLS = [
    'http://purl.obolibrary.org/obo/hp.obo',
    'http://purl.obolibrary.org/obo/cl.obo',
    'https://github.com/obophenotype/ncbitaxon/releases/download/current/taxslim.obo',
    # 'http://purl.obolibrary.org/obo/go.obo',  # Large and slow to parse
    # TODO: Add more imports to test in batch here
    # TODO: Also see issue #944
]


class TestOBOFormatOntologyIO(TestCase):
    """Tests for the OBOFormatOntologyIO class"""

    def setUp(self):
        self.obo_io = OBOFormatOntologyIO()

    def test_import(self):
        """Test importing an example ontology"""

        # Assert preconditions
        self.assertEqual(OBOFormatOntology.objects.count(), 0)
        self.assertEqual(OBOFormatOntologyTerm.objects.count(), 0)

        obo_doc = fastobo.load(OBO_PATH)
        ontology = self.obo_io.import_obo(obo_doc=obo_doc, file_name='ex.obo')

        # Assert postconditions
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

    def test_import_batch(self):
        """Test importing ontologies in a batch (this may take a while)"""

        for url in OBO_BATCH_URLS:
            # Assert preconditions
            self.assertEqual(OBOFormatOntology.objects.count(), 0)
            self.assertEqual(OBOFormatOntologyTerm.objects.count(), 0)

            file_name = url.split('/')[-1]
            obo_doc = fastobo.load(urlopen(url))
            ontology = self.obo_io.import_obo(
                obo_doc=obo_doc, file_name=file_name
            )

            # Assert postconditions
            self.assertIsNotNone(ontology, msg=file_name)
            self.assertEqual(
                OBOFormatOntology.objects.count(), 1, msg=file_name
            )
            self.assertNotEqual(
                OBOFormatOntologyTerm.objects.count(), 0, msg=file_name
            )

            ontology.delete()
