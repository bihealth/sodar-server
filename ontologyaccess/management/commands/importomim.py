"""Management command importomim for the ontologyaccess app"""

import sys

from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger

from ontologyaccess.io import OBOFormatOntologyIO, OMIM_NAME
from ontologyaccess.models import OBOFormatOntology


logger = ManagementCommandLogger(__name__)


class Command(BaseCommand):
    help = (
        'Imports OMIM disease data into the SODAR database as a fake OBO '
        'ontology'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--path',
            dest='path',
            type=str,
            required=False,
            help='Path to a local .obo or .owl file',
        )

    def handle(self, *args, **options):
        logger.info(
            'Importing OMIM disease data from "{}"..'.format(options['path'])
        )
        obo_io = OBOFormatOntologyIO()
        # Ensure path or url (but not both) is set
        if not options['path'] and options['url']:
            logger.error('Path to OMIM CSV file required')
            sys.exit(1)
        if OBOFormatOntology.objects.filter(name=OMIM_NAME).first():
            logger.info('OMIM data already on server')
            logger.info('Import cancelled')
            return
        with open(options['path']) as f:
            obo_io.import_omim(csv_data=f, file=options['path'])
            logger.info('Import OK')
