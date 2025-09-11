"""Irodsorphans management command"""

import re
import sys

from itertools import chain
from typing import Optional, Union

from irods.collection import iRODSCollection
from irods.path import iRODSPath
from irods.session import iRODSSession

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.template.defaultfilters import filesizeformat

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.models import Project, PROJECT_TYPE_PROJECT
from projectroles.plugins import PluginAPI

# Landingzones dependency
from landingzones.constants import ZONE_STATUS_MOVED, ZONE_STATUS_DELETED
from landingzones.models import LandingZone

# Samplesheets dependency
from samplesheets.models import Assay, Study
from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.views import TRACK_HUBS_COLL, RESULTS_COLL, MISC_FILES_COLL


logger = ManagementCommandLogger(__name__)
plugin_api = PluginAPI()
table_builder = SampleSheetTableBuilder()


# Local constants
DELETED = '<DELETED>'
ERROR = '<ERROR>'


class Command(BaseCommand):
    """Command to find orphans in iRODS collections."""

    help = 'Find orphans in iRODS project collections.'

    def __init__(self):
        super().__init__()
        self.irods_backend = plugin_api.get_backend_api('omics_irods')

    def _get_assay_colls(self, assays: Union[QuerySet, list]) -> list[str]:
        """
        Return a list of all assay collection names.

        :param assays: QuerySet or list of Assay objects
        :return: List of strings
        """
        return [self.irods_backend.get_path(a) for a in assays]

    def _get_assay_subcolls(self, studies: Union[QuerySet, list]) -> list[str]:
        """
        Return a list of all assay row collection names.

        :param studies: QuerySet or list of Study objects
        :return: List of strings
        """
        ret = []
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
                        if row_path not in ret:
                            ret.append(row_path)
                    shortcuts = assay_plugin.get_shortcuts(assay)
                    if shortcuts:
                        for shortcut in shortcuts:
                            ret.append(shortcut['path'])

                    # Add default expected subcollections of assay collection
                    ret.append(iRODSPath(assay_path, TRACK_HUBS_COLL))
                    ret.append(iRODSPath(assay_path, RESULTS_COLL))
                    ret.append(iRODSPath(assay_path, MISC_FILES_COLL))
        return ret

    def _get_study_colls(self, studies: Union[QuerySet, list]) -> list[str]:
        """
        Return a list of all study collection names.

        :param studies: QuerySet or list of Study objects
        :return: List of strings
        """
        return [self.irods_backend.get_path(s) for s in studies]

    def _get_zone_colls(self) -> list[str]:
        """
        Return a list of all landing zone collection names that are not MOVED or
        DELETED.

        :return: List of strings
        """
        return [
            self.irods_backend.get_path(lz)
            for lz in LandingZone.objects.exclude(
                status__in=[ZONE_STATUS_MOVED, ZONE_STATUS_DELETED]
            )
        ]

    def _get_project_colls(self) -> list[str]:
        """
        Return a list of all study collection names.

        :return: List of strings
        """
        return [
            self.irods_backend.get_path(p)
            for p in Project.objects.filter(type=PROJECT_TYPE_PROJECT).order_by(
                'full_title'
            )
        ]

    def _is_zone(self, coll: iRODSCollection) -> Optional[re.Match[str]]:
        """
        Check if a given collection matches the format of path to a landing zone
        collection.

        :param coll: iRODSCollection object
        :return: Match or None
        """
        projects_path = self.irods_backend.get_projects_path()
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}/'
            r'landing_zones'
        )
        return re.search(r'{}'.format(pattern), coll.path) and re.search(
            r'^\d{8}_\d{6}', coll.name
        )

    def _is_assay_or_study(
        self, coll: iRODSCollection
    ) -> Optional[re.Match[str]]:
        """
        Check if a given collection matches the format of path to a study or
        assay collection.

        :param coll: iRODSCollection object
        :return: Match or None
        """
        projects_path = self.irods_backend.get_projects_path()
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}/.*/'
            r'(assay|study)_[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$'
        )
        return re.search(pattern, coll.path)

    def _is_assay_orphan(
        self, coll: iRODSCollection
    ) -> Optional[re.Match[str]]:
        """
        Check if a given collection matches the format of path to a study or
        assay orphan.

        :param coll: iRODSCollection object
        :return: Match or None
        """
        projects_path = self.irods_backend.get_projects_path()
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}/.*/'
            r'(assay|study)_[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}'
        )
        return re.search(pattern, coll.path)

    @classmethod
    def _is_project(
        cls, projects_path: str, coll: iRODSCollection
    ) -> Optional[re.Match[str]]:
        """
        Check if a given collection matches the format of path to a project
        collection under the projects path.

        :param projects_path: String
        :param coll: iRODSCollection object
        :return: Match or None
        """
        pattern = (
            r'^'
            + projects_path
            + r'/([a-f0-9]{2})/\1[a-f0-9]{6}-([a-f0-9]{4}-){3}[a-f0-9]{12}$'
        )
        return re.search(r'{}'.format(pattern), coll.path)

    def _sort_colls_on_projects(
        self, colls: list[iRODSCollection]
    ) -> list[iRODSCollection]:
        """
        Return list of sorted collections based on project list.

        :param colls: List of Collection objects
        :return: List of Collection objects
        """
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
        for coll in colls:
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

    def _get_orphans(
        self,
        irods: iRODSSession,
        expected: list[str],
        assays: Union[QuerySet, list],
    ):
        """
        Return a list of orphans in a given irods session that are not in given
        list of expected collections.

        :param irods: iRODSSession object
        :param expected: List of strings
        :param assays: QuerySet or list of Assay objects
        """
        # Get a sorted list of all project collections
        project_colls = sorted(
            self.irods_backend.get_colls_recursively(
                irods.collections.get(f'/{irods.zone}/projects')
            ),
            key=lambda coll: coll.path,
        )
        assay_colls = list(
            chain.from_iterable(
                self.irods_backend.get_child_colls(
                    irods, self.irods_backend.get_path(a)
                )
                for a in assays
                if a.get_plugin()
            )
        )
        assay_coll_paths = [coll.path for coll in assay_colls]

        # Sort collections by project full_title
        sorted_colls = self._sort_colls_on_projects(project_colls + assay_colls)

        projects_path = self.irods_backend.get_projects_path()
        for collection in sorted_colls:
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
        studies = Study.objects.all()
        assays = Assay.objects.all()
        expected = [
            *self._get_assay_colls(assays),
            *self._get_study_colls(studies),
            *self._get_zone_colls(),
            *self._get_project_colls(),
            *self._get_assay_subcolls(studies),
        ]
        with self.irods_backend.get_session() as irods:
            self._get_orphans(irods, expected, assays)
