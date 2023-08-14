"""Irodsorphans management command"""

import re
import sys

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.template.defaultfilters import filesizeformat

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.models import Project, PROJECT_TYPE_PROJECT
from projectroles.plugins import get_backend_api

# Landingzones dependency
from landingzones.constants import ZONE_STATUS_MOVED, ZONE_STATUS_DELETED
from landingzones.models import LandingZone

# Samplesheets dependency
from samplesheets.models import Assay, Study
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.views import TRACK_HUBS_COLL, RESULTS_COLL, MISC_FILES_COLL


logger = ManagementCommandLogger(__name__)
table_builder = SampleSheetTableBuilder()


# Local constants
DELETED = '<DELETED>'
ERROR = '<ERROR>'


class Command(BaseCommand):
    """Command to find orphans in iRODS collections."""

    help = 'Find orphans in iRODS project collections.'

    def __init__(self):
        super().__init__()
        self.irods_backend = get_backend_api('omics_irods')

    def _sort_colls_on_projects(self, collections):
        """Helper function to sort collections based on project list"""
        colls_with_project = []
        colls_no_project = []

        # Create a set of valid project paths based on project UUIDs
        valid_project_paths = [
            self.irods_backend.get_path(p)
            for p in Project.objects.filter(type=PROJECT_TYPE_PROJECT).order_by(
                'full_title'
            )
        ]

        for coll in collections:
            uuid_prefix = (
                coll.path.split('/')[4] if len(coll.path.split('/')) > 4 else ''
            )
            if any(uuid_prefix in path for path in valid_project_paths):
                colls_with_project.append(coll)
            else:
                colls_no_project.append(coll)
        # Sort collections with project path based on project list
        sorted_colls = sorted(
            colls_with_project,
            key=lambda coll: next(
                (
                    i
                    for i, path in enumerate(valid_project_paths)
                    if (
                        coll.path.split('/')[4]
                        if len(coll.path.split('/')) > 4
                        else ''
                    )
                    in path
                ),
                float('inf'),
            ),
        )
        return sorted_colls + colls_no_project

    def _get_assay_collections(self, assays):
        """Return a list of all assay collection names."""
        return [self.irods_backend.get_path(a) for a in assays]

    def _get_assay_subcollections(self, studies):
        """Return a list of all assay row collection names."""
        collections = []
        for study in studies:
            try:
                study_tables = table_builder.get_study_tables(study)
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
                assay_plugin = assay.get_plugin()
                assay_path = self.irods_backend.get_path(assay)

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

    def _get_study_collections(self, studies):
        """Return a list of all study collection names."""
        return [self.irods_backend.get_path(s) for s in studies]

    def _get_zone_collections(self):
        """
        Return a list of all landing zone collection names that are not MOVED or
        DELETED.
        """
        return [
            self.irods_backend.get_path(lz)
            for lz in LandingZone.objects.filter(
                ~(Q(status=ZONE_STATUS_MOVED) & Q(status=ZONE_STATUS_DELETED))
            )
        ]

    def _get_project_collections(self):
        """Return a list of all study collection names."""
        return [
            self.irods_backend.get_path(p)
            for p in Project.objects.all().order_by('full_title')
        ]

    def _is_zone(self, collection):
        """
        Check if a given collection matches the format of path to a landing zone
        collection.
        """
        return '/landing_zones/' in collection.path and re.search(
            r'^\d{8}_\d{6}', collection.name
        )

    def _is_assay_or_study(self, collection):
        """
        Check if a given collection matches the format of path to a study or assay
        collection.
        """
        return re.match(
            r'(assay|study)_[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}',
            collection.name,
        )

    def _is_project(self, collection):
        """
        Check if a given collection matches the format of path to a project
        collection.
        """
        return re.search(
            r'projects/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}$',
            collection.path,
        )

    def _get_orphans(self, irods, expected, assays):
        """
        Return a list of orphans in a given irods session that are not in a given
        list of expected collections.
        """
        # Get a sorted list of all project collections
        project_collections = sorted(
            self.irods_backend.get_colls_recursively(
                irods.collections.get('/{}/projects'.format(irods.zone))
            ),
            key=lambda coll: coll.path,
        )
        # Sort collections by project full_title
        sorted_collections = self._sort_colls_on_projects(project_collections)

        for collection in sorted_collections:
            if (
                self._is_zone(collection)
                or self._is_assay_or_study(collection)
                or self._is_project(collection)
            ):
                if collection.path not in expected:
                    self._write_orphan(collection.path, irods)

        for assay in assays:
            if not assay.get_plugin():
                continue
            with self.irods_backend.get_session() as irods:
                for collection in self.irods_backend.get_child_colls(
                    irods, self.irods_backend.get_path(assay)
                ):
                    if collection.path not in expected:
                        self._write_orphan(collection.path, irods)

    def _write_orphan(self, path, irods):
        stats = self.irods_backend.get_object_stats(irods, path)
        m = re.search(r'/projects/([^/]{2})/(\1[^/]+)', path)
        if m:
            uuid = m.group(2)
            try:
                project = Project.objects.get(sodar_uuid=uuid)
                title = project.full_title
            except Project.DoesNotExist:
                title = DELETED
        else:
            uuid = ERROR
            title = ERROR
        sys.stdout.write(
            ';'.join(
                [
                    uuid,
                    title,
                    path,
                    str(stats['file_count']),
                    filesizeformat(stats['total_size']).replace(u'\xa0', ' '),
                ]
            )
            + '\n'
        )

    def handle(self, *args, **options):
        studies = list(Study.objects.all())
        assays = list(Assay.objects.all())
        expected = (
            *self._get_assay_collections(assays),
            *self._get_study_collections(studies),
            *self._get_zone_collections(),
            *self._get_project_collections(),
            *self._get_assay_subcollections(studies),
        )
        with self.irods_backend.get_session() as irods:
            self._get_orphans(irods, expected, assays)
