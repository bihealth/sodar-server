"""Management command importobo for the ontologyaccess app"""

import fastobo
import logging
import sys
from urllib.request import urlopen

from django.core.management.base import BaseCommand

from ontologyaccess.io import OBOFormatOntologyIO
from ontologyaccess.models import OBOFormatOntology


logger = logging.getLogger(__name__)


VALID_FORMATS = ['obo', 'owl']


class Command(BaseCommand):
    help = 'Imports an OBO or OWL format ontology file into the SODAR database'

    def add_arguments(self, parser):
        parser.add_argument(
            '-n',
            '--name',
            dest='name',
            type=str,
            required=True,
            help='Ontology name as it appears in sample sheets',
        )
        parser.add_argument(
            '-p',
            '--path',
            dest='path',
            type=str,
            required=False,
            help='Path to a local .obo or .owl file',
        )
        parser.add_argument(
            '-u',
            '--url',
            dest='url',
            type=str,
            required=False,
            help='URL of an .obo or .owl file',
        )
        parser.add_argument(
            '-t',
            '--title',
            dest='title',
            type=str,
            required=False,
            help='Ontology title (optional)',
        )
        parser.add_argument(
            '--term-url',
            dest='term_url',
            type=str,
            required=False,
            help='Term accession URL (optional)',
        )
        parser.add_argument(
            '-f',
            '--format',
            dest='format',
            required=False,
            help='Format of source file (optional, default=obo)',
        )

    def handle(self, *args, **options):
        name = options['name'].upper()
        logger.info('Importing ontology "{}"..'.format(name))
        logger.debug('Using options: {}'.format(options))
        obo_io = OBOFormatOntologyIO()

        # Ensure path or url (but not both) is set
        if (options['path'] and options['url']) or (
            not options['path'] and not options['url']
        ):
            logger.error('Please provide either a path or a URL')
            sys.exit(1)

        # Validate format
        if options['format'] and options['format'] not in VALID_FORMATS:
            logger.error(
                'Invalid format "{}". Supported formats: {}'.format(
                    options['format'], ', '.join(VALID_FORMATS)
                )
            )
            sys.exit(1)

        if options['url']:
            path = options['url']
        else:
            path = options['path']
        if not options['format'] and path.split('.')[-1].lower() == 'owl':
            options['format'] = 'owl'

        # Load ontology
        if options['url']:
            target = urlopen(options['url'])
        else:
            target = options['path']

        # Set up OWL
        if options['format'] == 'owl':
            logger.info('Converting ontology from OWL..')
            try:
                target = obo_io.owl_to_obo(target)
            except Exception as ex:
                logger.error('OWL convert exception: {}'.format(ex))
                sys.exit(1)

        try:
            obo_doc = fastobo.load(target)
        except Exception as ex:
            logger.error('Fastobo exception: {}'.format(ex))
            sys.exit(1)

        # ontology_id = obo_io.get_obo_header(obo_doc, 'ontology')
        obo_obj = OBOFormatOntology.objects.filter(name=name).first()

        if obo_obj:
            data_version = obo_io.get_obo_header(obo_doc, 'data-version')
            if obo_obj.data_version == data_version:
                logger.info(
                    'Identical version of ontology "{}" already exists'.format(
                        name
                    )
                )
            else:
                logger.info(
                    'Version "{}" of ontology "{}" already exists, please '
                    'delete the existing version before importing'.format(
                        obo_obj.data_version, name
                    )
                )
                # TODO: Implement replacing if needed
            logger.info('Import cancelled')
            return

        obo_io.import_obo(
            obo_doc=obo_doc,
            name=name,
            file=path,
            title=options['title'],
            term_url=options['term_url'],
        )
        logger.info('Import OK')
