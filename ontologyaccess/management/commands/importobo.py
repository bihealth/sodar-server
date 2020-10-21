"""Management command importobo for the ontologyaccess app"""

import fastobo
import logging
from urllib.request import urlopen

from django.core.management.base import BaseCommand

from ontologyaccess.io import OBOFormatOntologyIO
from ontologyaccess.models import OBOFormatOntology


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Imports an OBO format ontology file into the SODAR database'

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
            help='Path to a local .obo file',
        )
        parser.add_argument(
            '-u',
            '--url',
            dest='url',
            type=str,
            required=False,
            help='URL of an .obo file',
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

    def handle(self, *args, **options):
        name = options['name'].upper()
        logger.info('Importing OBO Format ontology "{}"..'.format(name))
        logger.debug('Using options: {}'.format(options))
        obo_io = OBOFormatOntologyIO()

        # Ensure path or url (but not both) is set
        if (options['path'] and options['url']) or (
            not options['path'] and not options['url']
        ):
            logger.error('Please provide either a path or a URL')
            return

        # Load .obo
        if options['url']:
            path = urlopen(options['url'])

        else:
            path = options['path']

        try:
            obo_doc = fastobo.load(path)

        except Exception as ex:
            logger.error('Fastobo exception: {}'.format(ex))
            return

        # ontology_id = obo_io.get_header(obo_doc, 'ontology')
        data_version = obo_io.get_header(obo_doc, 'data-version')
        obo_obj = OBOFormatOntology.objects.filter(name=name).first()

        if obo_obj:
            if obo_obj.data_version == data_version:
                logger.info(
                    'Identical version of ontology "{}" already exists'.format(
                        name
                    )
                )

            else:
                logger.info(
                    'Version "{}" of ontology "{}" already exists, please'
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
