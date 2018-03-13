"""Rendersheets management command for samplesheets"""


from django.core.management import BaseCommand

from samplesheets.models import Investigation, Study, Assay
from samplesheets.rendering import render_investigation, render_study, \
    render_assay


class Command(BaseCommand):
    help = 'Renders imported sample sheet tables for display, replacing ' \
           'existing tables.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--project',
            action='store',
            dest='project',
            default=None,
            help='Limit to all tables of a specified project by project.pk')
        parser.add_argument(
            '-s',
            '--study',
            action='store',
            dest='study',
            default=None,
            help='Limit to a specific study by study__pk. Ignores -p.')
        parser.add_argument(
            '-a',
            '--assay',
            action='store',
            dest='assay',
            default=None,
            help='Limit to a specific assay by assay__pk. Ignores -s and -p.')

    def handle(self, *args, **options):
        if options['assay']:
            print('Rendering assay (pk={})'.format(options['assay']))

            try:
                assay = Assay.objects.get(pk=options['assay'])
                render_assay(assay)

            except Assay.DoesNotExist:
                print('ERROR: Assay not found')

        elif options['study']:
            print('Rendering study (pk={})'.format(options['study']))

            try:
                study = Study.objects.get(pk=options['study'])
                render_study(study)

            except Study.DoesNotExist:
                print('ERROR: Study not found')

        elif options['project']:
            print('Rendering all tables for project (pk={})'.format(
                options['project']))

            try:
                investigation = Investigation.objects.get(
                    project__pk=options['project'])
                render_investigation(investigation)

            except Investigation.DoesNotExist:
                print('ERROR: No investigation found for project')

        else:
            print('Rendering all tables in database..')

            for investigation in Investigation.objects.all():
                render_investigation(investigation)

            print('All OK')
