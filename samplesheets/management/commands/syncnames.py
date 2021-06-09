from django.core.management.base import BaseCommand
from django.db import transaction

from samplesheets.models import GenericMaterial
from samplesheets.utils import get_alt_names


class Command(BaseCommand):
    help = 'Refreshes all alternative names for sample sheet materials'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        print('Refreshing alternative names for materials...')
        with transaction.atomic():
            for m in GenericMaterial.objects.all():
                m.alt_names = get_alt_names(m.name)
                m.save()
        print(
            '{} materials updated.'.format(
                GenericMaterial.objects.all().count()
            )
        )
