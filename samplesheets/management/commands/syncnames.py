"""Syncnames management command"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from samplesheets.models import GenericMaterial
from samplesheets.utils import get_alt_names


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refreshes all alternative names for sample sheet materials'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        logger.info('Refreshing alternative names for materials..')
        with transaction.atomic():
            for m in GenericMaterial.objects.all():
                m.alt_names = get_alt_names(m.name)
                m.save()
        logger.info(
            '{} materials updated.'.format(
                GenericMaterial.objects.all().count()
            )
        )
