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
OBO_NAME = 'EX'
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
    'http://purl.obolibrary.org/obo/ms.obo',
    'http://purl.obolibrary.org/obo/pato.obo',
    # 'http://purl.obolibrary.org/obo/cl.obo',  # TODO: Fix (see #1064)
    # TODO: Also see issue #944
]

OWL_BATCH_URLS = [
    'http://purl.obolibrary.org/obo/duo.owl',
    'http://data.bioontology.org/ontologies/ROLEO/submissions/3/download?apikey=8b5b7825-538d-40e0-9e9e-5ab9274a9aeb',
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
        ontology = self.obo_io.import_obo(
            obo_doc=obo_doc, name=OBO_NAME, file=OBO_PATH
        )

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
                obo_doc=obo_doc, name=file_name.split('.')[0].upper(), file=url
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

    def test_import_batch_owl(self):
        """Test converting and importing OWL ontologies in a batch (this may take a while)"""

        for url in OWL_BATCH_URLS:
            # Assert preconditions
            self.assertEqual(OBOFormatOntology.objects.count(), 0)
            self.assertEqual(OBOFormatOntologyTerm.objects.count(), 0)

            file_name = url.split('/')[-1]
            file = self.obo_io.owl_to_obo(url)
            obo_doc = fastobo.load(file)
            ontology = self.obo_io.import_obo(
                obo_doc=obo_doc, name=file_name.split('.')[0].upper(), file=url
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

    # TODO: Test import_omim()
