"""Import and export utilities for the ontologyaccess app"""

import fastobo.header as fh
from fastobo.term import TermFrame
from importlib import import_module
import logging

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
    @transaction.atomic
    def import_obo(cls, obo_doc, file_name, title=None, term_url=None):
        """
        Import data from an OBO format ontology into the SODAR database.

        :param obo_doc: OboDoc object
        :param file_name: Name of the original .obo file (string)
        :param title: Title for the obo file (string, optional)
        :param term_url: Term URL for the object (string)
        :return: OBOFormatOntology object
        """
        logger.info(
            'Importing OBO format ontology from file: {}'.format(file_name)
        )
        o_kwargs = {
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
            logger.debug('Ontology ID missing, using file name')
            o_kwargs['ontology_id'] = file_name

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
        term_count = 0
        term_vals = []

        for term in obo_doc:
            if not isinstance(term, TermFrame):
                continue  # Skip typedefs

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

        logger.debug('Parsing terms OK')
        logger.info(
            'Imported OBOFormatOntology "{}" with {} term{} (UUID={})'.format(
                obo_obj.title,
                term_count,
                's' if term_count != 1 else '',
                obo_obj.sodar_uuid,
            )
        )
        return obo_obj

    @classmethod
    def get_header(cls, obo_doc, raw_tag, raw_value=True):
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
