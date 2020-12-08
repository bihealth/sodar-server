import logging
import re

from django.core.management.base import BaseCommand
from django.db.models import Q
from projectroles.models import Project

from projectroles.plugins import get_backend_api

# Landingzones dependency
from landingzones.models import LandingZone

# Samplesheets dependency
from samplesheets.models import Assay, Study
from samplesheets.plugins import find_assay_plugin
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.views import TRACK_HUBS_COLL, RESULTS_COLL, MISC_FILES_COLL


logger = logging.getLogger(__name__)


def get_assay_collections(assays, irods_backend):
    """Return a list of all assay collection names."""
    return [irods_backend.get_path(a) for a in assays]


def get_assay_subcollections(studies, irods_backend):
    """Return a list of all assay row colletion names."""
    tb = SampleSheetTableBuilder()

    collections = []

    for study in studies:
        try:
            study_tables = tb.build_study_tables(study)
        except Exception as ex:
            logger.error(
                'Study table building exception for "{}" '
                'in project "{}" ({}): {}'.format(
                    study.get_display_name(),
                    study.investigation.project.title,
                    study.investigation.project.sodar_uuid,
                    ex,
                )
            )
            continue

        for assay in study.assays.all():
            assay_table = study_tables['assays'][str(assay.sodar_uuid)]
            assay_plugin = find_assay_plugin(
                assay.measurement_type, assay.technology_type
            )
            assay_path = irods_backend.get_path(assay)

            if assay_plugin:
                for row in assay_table['table_data']:
                    row_path = assay_plugin.get_row_path(
                        row, assay_table, assay, assay_path
                    )
                    if row_path not in collections:
                        collections.append(row_path)

                shortcuts = assay_plugin.get_shortcuts(assay)

                if shortcuts:
                    for shortcut in shortcuts:
                        collections.append(shortcut['path'])

                # Add default expected subcollections of assay collection
                collections.append(assay_path + '/' + TRACK_HUBS_COLL)
                collections.append(assay_path + '/' + RESULTS_COLL)
                collections.append(assay_path + '/' + MISC_FILES_COLL)

    return collections


def get_study_collections(studies, irods_backend):
    """Return a list of all study collection names."""
    return [irods_backend.get_path(s) for s in studies]


def get_zone_collections(irods_backend):
    """
    Return a list of all landing zone collection names that are not MOVED or
    DELETED.
    """
    return [
        irods_backend.get_path(lz)
        for lz in LandingZone.objects.filter(
            ~(Q(status='MOVED') & Q(status='DELETED'))
        )
    ]


def get_project_collections(irods_backend):
    """Return a list of all study collection names."""
    return [irods_backend.get_path(p) for p in Project.objects.all()]


def is_zone(collection):
    """
    Check if a given collection matches the format of path to a landing zone
    collection.
    """
    return '/landing_zones/' in collection.path and re.search(
        r'^\d{8}_\d{6}', collection.name
    )


def is_assay_or_study(collection):
    """
    Check if a given collection matches the format of path to a study or assay
    collection.
    """
    return re.match(
        r'(assay|study)_[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}',
        collection.name,
    )


def is_project(collection):
    """
    Check if a given collection matches the format of path to a project
    collection.
    """
    return re.search(
        r'projects/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}$',
        collection.path,
    )


def get_orphans(session, irods_backend, expected, assays):
    """
    Return a list of orphans in a given irods session that are not in a given
    list of expected collections.
    """
    orphans = []
    collections = session.collections.get('/{}/projects'.format(session.zone))

    for collection in irods_backend.get_colls_recursively(collections):
        if (
            is_zone(collection)
            or is_assay_or_study(collection)
            or is_project(collection)
        ):
            if collection.path not in expected:
                orphans.append(collection.path)

    for assay in assays:
        if not find_assay_plugin(assay.measurement_type, assay.technology_type):
            continue

        for collection in irods_backend.get_child_colls_by_path(
            irods_backend.get_path(assay)
        ):
            if collection.path not in expected:
                orphans.append(collection.path)

    return orphans


class Command(BaseCommand):
    """Command to find orphans in iRODS collections."""

    help = 'Find orphans in iRODS project collections.'

    def handle(self, *args, **options):
        irods_backend = get_backend_api('omics_irods')
        session = irods_backend.get_session()
        studies = list(Study.objects.all())
        assays = list(Assay.objects.all())
        expected = (
            *get_assay_collections(assays, irods_backend),
            *get_study_collections(studies, irods_backend),
            *get_zone_collections(irods_backend),
            *get_project_collections(irods_backend),
            *get_assay_subcollections(studies, irods_backend),
        )

        orphans = get_orphans(session, irods_backend, expected, assays)
        if orphans:
            self.stdout.write('\n'.join(orphans))
