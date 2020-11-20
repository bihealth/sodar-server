import re

from django.core.management.base import BaseCommand
from django.db.models import Q
from projectroles.models import Project

from projectroles.plugins import get_backend_api

# Landingzone dependency
from landingzones.models import LandingZone

# Samplesheets dependency
from samplesheets.models import Assay, Study


def get_assay_collections():
    """Return a list of all assay collection names."""
    return ['assay_{}'.format(a.sodar_uuid) for a in Assay.objects.all()]


def get_study_collections():
    """Return a list of all study collection names."""
    return ['study_{}'.format(s.sodar_uuid) for s in Study.objects.all()]


def get_zone_collections():
    """
    Return a list of all landing zone collection names that are not MOVED or
    DELETED.
    """
    return [
        l.title
        for l in LandingZone.objects.filter(
            ~(Q(status='MOVED') & Q(status='DELETED'))
        )
    ]


def get_project_collections():
    """Return a list of all study collection names."""
    return [str(p.sodar_uuid) for p in Project.objects.all()]


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


def get_orphans(session, irods_backend, expected):
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
            if collection.name in expected:
                continue
            orphans.append(collection.path)

    return orphans


class Command(BaseCommand):
    """Command to find orphans in iRODS collections."""

    help = 'Find orphans in iRODS project collections.'

    def handle(self, *args, **options):
        irods_backend = get_backend_api('omics_irods')
        session = irods_backend.get_session()
        expected = (
            *get_assay_collections(),
            *get_study_collections(),
            *get_zone_collections(),
            *get_project_collections(),
        )
        orphans = get_orphans(session, irods_backend, expected)
        self.stdout.write('\n'.join(orphans))
