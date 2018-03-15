"""Buildsheets management command for samplesheets"""

from django.core.management import BaseCommand

from samplesheets.models import Investigation
from samplesheets.rendering import SampleSheetTableBuilder


class Command(BaseCommand):
    help = 'Builds pre-rendered sample sheet tables for display, replacing ' \
           'existing tables.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--project',
            action='store',
            dest='project',
            default=None,
            help='Limit to tables of a specified project by project.pk')

    def handle(self, *args, **options):
        tb = SampleSheetTableBuilder()

        if options['project']:
            try:
                investigation = Investigation.objects.get(
                    project__pk=options['project'])
                tb.build_investigation(investigation)

            except Investigation.DoesNotExist:
                print('ERROR: No investigation found for project')

        else:
            print('Building all render tables in database..')

            for investigation in Investigation.objects.all():
                tb.build_investigation(investigation)

            print('All OK')
