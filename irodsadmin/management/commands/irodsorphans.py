"""Irodsorphans management command"""

import re
import sys

from itertools import chain

from django.core.management.base import BaseCommand
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

    def _get_assay_collections(self, assays):
        """Return a list of all assay collection names."""
        return [self.irods_backend.get_path(a) for a in assays]

    def _get_assay_subcollections(self, studies):
        """Return a list of all assay row collection names."""
        collections = []
        for study in studies:
            try:
                study_tables = table_builder.get_study_tables(
                    study, save_cache=False
                )
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
            for lz in LandingZone.objects.exclude(
                status__in=[ZONE_STATUS_MOVED, ZONE_STATUS_DELETED]
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
        projects_path = self.irods_backend.get_projects_path()
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}/'
            r'landing_zones'
        )
        return re.search(r'{}'.format(pattern), collection.path) and re.search(
            r'^\d{8}_\d{6}', collection.name
        )

    def _is_assay_or_study(self, collection):
        """
        Check if a given collection matches the format of path to a study or
        assay collection.
        """
        projects_path = self.irods_backend.get_projects_path()
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}/.*/'
            r'(assay|study)_[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$'
        )
        return re.search(pattern, collection.path)

    def _is_assay_orphan(self, collection):
        """
        Check if a given collection matches the format of path to a study or
        assay orphan.
        """
        projects_path = self.irods_backend.get_projects_path()
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}/.*/'
            r'(assay|study)_[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}'
        )
        return re.search(pattern, collection.path)

    def _is_project(self, projects_path, collection):
        """
        Check if a given collection matches the format of path to a project
        collection under the projects path.
        """
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}$'
        )
        return re.search(r'{}'.format(pattern), collection.path)

    def _sort_colls_on_projects(self, collections):
        """Helper function to sort collections based on project list"""
        colls_with_project = []
        colls_no_project = []
        temp_paths = []

        # Create a set of valid project paths based on project UUIDs
        valid_project_paths = [
            self.irods_backend.get_path(p)
            for p in Project.objects.filter(type=PROJECT_TYPE_PROJECT).order_by(
                'full_title'
            )
        ]

        # Get the actual path to the projects collection
        project_path = self.irods_backend.get_projects_path()
        depth = len(project_path.split('/')) + 1
        for coll in collections:
            pattern = (
                r'^'
                + project_path
                + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}'
            )
            match = re.search(r'{}'.format(pattern), coll.path)
            uuid = match.string.split('/')[depth] if match else ''
            if (
                uuid
                and any(uuid in path for path in valid_project_paths)
                and coll.path not in temp_paths
            ):
                colls_with_project.append(coll)
                temp_paths.append(coll.path)
            elif coll.path not in temp_paths:
                colls_no_project.append(coll)
                temp_paths.append(coll.path)

        # Sort collections with project path based on project list
        sorted_colls = sorted(
            colls_with_project,
            key=lambda coll: next(
                (
                    i
                    for i, path in enumerate(valid_project_paths)
                    if (
                        coll.path.split('/')[depth]
                        if len(coll.path.split('/')) > depth
                        else ''
                    )
                    in path
                ),
                float('inf'),
            ),
        )
        return sorted_colls + colls_no_project

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
        assay_collections = list(
            chain.from_iterable(
                self.irods_backend.get_child_colls(
                    irods, self.irods_backend.get_path(a)
                )
                for a in assays
                if a.get_plugin()
            )
        )
        assay_coll_paths = [coll.path for coll in assay_collections]

        # Sort collections by project full_title
        sorted_collections = self._sort_colls_on_projects(
            project_collections + assay_collections
        )

        projects_path = self.irods_backend.get_projects_path()
        for collection in sorted_collections:
            if (
                self._is_zone(collection)
                or self._is_assay_or_study(collection)
                or self._is_project(projects_path, collection)
                or collection.path in assay_coll_paths
            ) and collection.path not in expected:
                self._write_orphan(collection.path, irods)

    def _write_orphan(self, path, irods):
        stats = self.irods_backend.get_stats(irods, path)
        projects_path = self.irods_backend.get_projects_path()
        pattern = projects_path + r'/([^/]{2})/(\1[^/]+)'
        m = re.search(pattern, path)
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
        assays = list(Assay.objects.all().order_by())
        expected = (
            *self._get_assay_collections(assays),
            *self._get_study_collections(studies),
            *self._get_zone_collections(),
            *self._get_project_collections(),
            *self._get_assay_subcollections(studies),
        )
        with self.irods_backend.get_session() as irods:
            self._get_orphans(irods, expected, assays)
