"""Import and export utilities for the ontologyaccess app"""

import csv
import fastobo.header as fh
from fastobo.term import TermFrame
from importlib import import_module
import io
import logging
import pronto
import sys

from django.conf import settings
from django.db import transaction

from ontologyaccess.models import (
    OBOFormatOntology,
    OBOFormatOntologyTerm,
    DEFAULT_LENGTH,
    DEFAULT_TERM_URL,
)


logger = logging.getLogger(__name__)
site = import_module(settings.SITE_PACKAGE)


# Local constants
OBO_BASIC_HEADER_MAP = {
    fh.DataVersionClause: 'data_version',
    fh.DefaultNamespaceClause: 'default_namespace',
    fh.FormatVersionClause: 'format_version',
    fh.OntologyClause: 'ontology_id',
}
OBO_PROPERTY_MAP = {
    'http://purl.org/dc/elements/1.1/description': 'description',
    'dc-description': 'description',
    'http://purl.org/dc/elements/1.1/title': 'title',
    'dc-title': 'title',
}
OBO_RAW_TERMS = ['comment', 'name', 'namespace', 'replaced_by']
OMIM_NAME = 'OMIM'
OMIM_TITLE = 'Online Mendelian Inheritance in Man'
OMIM_URL = 'http://purl.bioontology.org/ontology/{id_space}/{local_id}'
MTHU_PREFIX = 'MTHU'


class OBOFormatOntologyIO:
    """Importing class for OBO format ontologies"""

    @classmethod
    def _create_terms(cls, term_vals):
        """Helper for bulk creating ontology terms"""
        logger.debug(
            'Bulk creating {} terms (start={})'.format(
                len(term_vals), term_vals[0]['term_id']
            )
        )
        OBOFormatOntologyTerm.objects.bulk_create(
            [OBOFormatOntologyTerm(**v) for v in term_vals]
        )

    @classmethod
    def owl_to_obo(cls, owl, verbose=False):
        """
        Convert an OWL format ontology into the OBO format.

        :param owl: Path, URL or file pointer to an OWL file
        :param verbose: Display pronto output if True (bool)
        :return: File pointer
        """
        logger.info('Converting OWL format ontology to OBO..')

        if not verbose:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()

        o = pronto.Ontology(owl)

        if not verbose:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

        logger.info('Parsed OWL ontology with {} terms'.format(len(o.terms())))
        f = io.BytesIO()
        o.dump(f, format='obo')
        logger.info('Converted OWL ontology into OBO')
        f.seek(0)
        return f

    @classmethod
    @transaction.atomic
    def import_obo(cls, obo_doc, name, file, title=None, term_url=None):
        """
        Import data from an OBO format ontology into the SODAR database.

        :param obo_doc: OboDoc object
        :param name: Ontology name as it appears in sample sheets (string)
        :param file: File name or URL (string)
        :param title: Title for the obo file (string, optional)
        :param term_url: Term URL for the object (string)
        :return: OBOFormatOntology object
        """
        logger.info(
            'Importing OBO format ontology "{}" from {}'.format(name, file)
        )
        o_kwargs = {
            'name': name,
            'file': file,
            'term_url': term_url or DEFAULT_TERM_URL,
            'sodar_version': site.__version__,
        }

        logger.debug('Parsing header..')

        for h in obo_doc.header:
            if type(h) in OBO_BASIC_HEADER_MAP:
                o_kwargs[OBO_BASIC_HEADER_MAP[type(h)]] = h.raw_value()

            elif (
                isinstance(h, fh.PropertyValueClause)
                and str(h.property_value.relation) in OBO_PROPERTY_MAP
            ):
                o_kwargs[
                    OBO_PROPERTY_MAP[str(h.property_value.relation)]
                ] = h.property_value.value

        if title:  # If manually enforcing a title, set here
            o_kwargs['title'] = title

        logger.debug('Parsing header OK')

        # If some optional values were missing, fill them
        if not o_kwargs.get('ontology_id'):
            logger.debug('Ontology ID missing, using name')
            o_kwargs['ontology_id'] = name

        if not o_kwargs.get('title'):
            logger.debug('Title missing, using ontology ID')
            o_kwargs['title'] = o_kwargs['ontology_id']

        logger.debug('Ontology kwargs: {}'.format(o_kwargs))
        obo_obj = OBOFormatOntology.objects.create(**o_kwargs)
        logger.debug(
            'OBOFormatOntology created: {} (UUID={})'.format(
                o_kwargs, obo_obj.sodar_uuid
            )
        )

        logger.debug('Parsing terms..')
        db_term_ids = OBOFormatOntologyTerm.objects.all().values_list(
            'term_id', flat=True
        )
        term_count = 0
        term_vals = []

        for term in obo_doc:
            if not isinstance(term, TermFrame):
                continue  # Skip typedefs

            if str(term.id) in db_term_ids:
                logger.warning(
                    'Skipping term already in database: {}'.format(term.id)
                )
                continue

            if ':' not in str(term.id):
                logger.warning(
                    'Skipping term without id space: {}'.format(term.id)
                )
                continue

            t_kwargs = {'ontology': obo_obj, 'term_id': str(term.id)}

            for c in term:
                c_tag = c.raw_tag()

                # Raw terms (name, replaced_by, namespace)
                if c_tag in OBO_RAW_TERMS:
                    t_kwargs[c_tag] = c.raw_value()

                # Definition
                elif c_tag == 'def':
                    val = c.raw_value()
                    if val[0] == '"' and val[-1] == '"':
                        val = val.strip('"')  # Cleanup excess quotes
                    t_kwargs['definition'] = val

                # Is obsolete
                elif c_tag == 'is_obsolete':
                    t_kwargs[c_tag] = c.obsolete

                # Synonym
                elif (
                    c_tag == 'synonym' and len(c.synonym.desc) <= DEFAULT_LENGTH
                ):
                    # NOTE: In some cases defs/comments seem to have been
                    #       erroneously placed in synonyms, hence the len check
                    if not t_kwargs.get('synonyms'):
                        t_kwargs['synonyms'] = []
                    t_kwargs['synonyms'].append(c.synonym.desc)

                # Alt id
                elif c_tag == 'alt_id':
                    if not t_kwargs.get('alt_ids'):
                        t_kwargs['alt_ids'] = []
                    t_kwargs['alt_ids'].append(c.raw_value())

            term_vals.append(t_kwargs)
            term_count += 1

            # Bulk create in batches
            if len(term_vals) == settings.ONTOLOGYACCESS_BULK_CREATE:
                cls._create_terms(term_vals)
                term_vals = []

        # Create remaining
        if len(term_vals) > 0:
            cls._create_terms(term_vals)

        if term_count == 0:
            logger.warning(
                '0 terms imported for OBOFormatOntology "{}", '
                'this is probably not what you wanted'.format(obo_obj.name)
            )
        logger.info(
            'Imported OBOFormatOntology "{}" ({}) with {} term{} '
            '(UUID={})'.format(
                obo_obj.name,
                obo_obj.title,
                term_count,
                's' if term_count != 1 else '',
                obo_obj.sodar_uuid,
            )
        )
        return obo_obj

    @classmethod
    def get_obo_header(cls, obo_doc, raw_tag, raw_value=True):
        """
        Get header from an OBO format ontology parsed by fastobo.

        :param obo_doc: OboDoc object
        :param raw_tag: Header name as returned by raw_tag()
        :param raw_value: Return raw_value() if True (bool)
        :return: String or None
        """
        for h in obo_doc.header:
            if h.raw_tag() == raw_tag:
                return h.raw_value() if raw_value else h

    @classmethod
    @transaction.atomic
    def import_omim(cls, csv_data, file):
        """
        Import OMIM data as a "fake" OBO ontology in the SODAR database.

        :param csv_data: File handle to CSV data
        :param file: File name (string)
        :return: OBOFormatOntology object
        """
        logger.info(
            'Importing CSV data into ontology "{}" from {}'.format(
                OMIM_NAME, file
            )
        )

        csv.field_size_limit(sys.maxsize)
        r = csv.reader(csv_data, delimiter=',')
        next(r, None)  # Skip header

        o_kwargs = {
            'name': OMIM_NAME,
            'file': file,
            'ontology_id': file.split('/')[-1],
            'title': OMIM_TITLE,
            'term_url': OMIM_URL,
            'sodar_version': site.__version__,
        }
        obo_obj = OBOFormatOntology.objects.create(**o_kwargs)
        logger.debug(
            'OBOFormatOntology created: {} (UUID={})'.format(
                o_kwargs, obo_obj.sodar_uuid
            )
        )

        logger.debug('Parsing terms..')
        db_term_ids = OBOFormatOntologyTerm.objects.all().values_list(
            'term_id', flat=True
        )
        term_count = 0
        current_ids = []
        term_vals = []

        for row in r:
            ts = str(row[0]).split('/')
            # Skip disease terms
            if ts[-1].startswith(MTHU_PREFIX):
                continue

            term_id = ts[-2] + ':' + ts[-1]

            if term_id in db_term_ids:
                logger.warning(
                    'Skipping term already in database: {}'.format(term_id)
                )
                continue
            elif term_id in current_ids:
                logger.warning(
                    'Skipping subject already inserted: {}'.format(term_id)
                )
                continue

            t_kwargs = {'ontology': obo_obj, 'term_id': term_id, 'name': row[1]}
            term_vals.append(t_kwargs)
            current_ids.append(term_id)
            term_count += 1

            # Bulk create in batches
            if len(term_vals) == settings.ONTOLOGYACCESS_BULK_CREATE:
                cls._create_terms(term_vals)
                term_vals = []

        # Create remaining
        if len(term_vals) > 0:
            cls._create_terms(term_vals)

        if term_count == 0:
            logger.warning(
                '0 OMIM disease terms imported, this is probably not what '
                'you wanted'
            )
        logger.info(
            'Imported OMIM diseases as OBOFormatOntology with {} term{} '
            '(UUID={})'.format(
                term_count,
                's' if term_count != 1 else '',
                obo_obj.sodar_uuid,
            )
        )
        return obo_obj
