"""Irodsorphans management command"""

import sys

from typing import Optional

from irods.path import iRODSPath
from irods.session import iRODSSession

from django.conf import settings
from django.core.management.base import BaseCommand
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
OUT_PROJECT_DELETED = '<DELETED>'
OUT_NONE = '<N/A>'


class Command(BaseCommand):
    """Command to find orphans in iRODS collections."""

    help = 'Find orphans in iRODS project collections.'

    def __init__(self):
        super().__init__()
        self.irods_backend = plugin_api.get_backend_api('omics_irods')

    # Helpers ------------------------------------------------------------------

    def _get_expected_sample_paths(self, project: Project) -> list[str]:
        """
        Return expexted sample data collection paths for a project.

        :param project: Project object
        :return: List of strings
        """
        ret = []
        studies = Study.objects.filter(investigation__project=project)
        for study in studies:
            try:
                study_tables = table_builder.get_study_tables(
                    study, save_cache=False
                )
            except Exception as ex:
                raise Exception(
                    'Study table building exception for "{}" '
                    'in project "{}" ({}): {}'.format(
                        study.get_name(),
                        study.investigation.project.title,
                        study.investigation.project.sodar_uuid,
                        ex,
                    )
                )

            study_path = self.irods_backend.get_path(study)
            ret.append(study_path)
            for assay in Assay.objects.filter(study=study):
                assay_path = self.irods_backend.get_path(assay)
                ret.append(assay_path)
                assay_plugin = assay.get_plugin()
                if not assay_plugin:
                    continue
                assay_table = study_tables['assays'][str(assay.sodar_uuid)]
                for row in assay_table['table_data']:
                    row_path = assay_plugin.get_row_path(
                        row, assay_table, assay, assay_path
                    )
                    if row_path not in ret:
                        ret.append(row_path)
                shortcuts = assay_plugin.get_shortcuts(assay) or []
                for shortcut in shortcuts:
                    if shortcut['path'] not in ret:
                        ret.append(shortcut['path'])
                # Add default expected subcollections of assay collection
                assay_path = self.irods_backend.get_path(assay)
                ret.append(iRODSPath(assay_path, TRACK_HUBS_COLL))
                ret.append(iRODSPath(assay_path, RESULTS_COLL))
                ret.append(iRODSPath(assay_path, MISC_FILES_COLL))
        return sorted(ret)

    def _write_output(
        self, irods: iRODSSession, path: str, project: Optional[Project]
    ):
        """
        Write output for orphaned iRODS collection.

        :param irods: iRODSSession object
        :param path: Full iRODS path (string)
        :param project: Project object or None
        """
        stats = self.irods_backend.get_stats(irods, path)
        ret = [
            str(project.sodar_uuid) if project else OUT_NONE,
            project.full_title if project else OUT_PROJECT_DELETED,
            path,
            str(stats['file_count']),
            filesizeformat(stats['total_size']).replace(u'\xa0', ' '),
        ]
        sys.stdout.write(';'.join(ret) + '\n')

    # Checking Methods ---------------------------------------------------------

    def _check_orphan_projects(self, irods: iRODSSession):
        """
        Check for collections for orphaned projects, write output if found.

        :param irods: iRODSSession object
        """
        project_uuids = [
            str(u)
            for u in Project.objects.filter(
                type=PROJECT_TYPE_PROJECT
            ).values_list('sodar_uuid', flat=True)
        ]
        projects_root = irods.collections.get(
            self.irods_backend.get_projects_path()
        )
        for rc in projects_root.subcollections:
            for pc in rc.subcollections:
                if pc.path.split('/')[-1] not in project_uuids:
                    self._write_output(irods, pc.path, None)

    def _check_sample_data(self, irods: iRODSSession, project: Project):
        """
        Check for orphaned sample data in given project, write output if found.

        :param irods: iRODSSession object
        :param project: Project object
        """
        sample_path = self.irods_backend.get_sample_path(project)
        if not irods.collections.exists(sample_path):
            return  # Nothing to check
        sample_coll = irods.collections.get(sample_path)
        # Get expected study and assay colls
        expected = self._get_expected_sample_paths(project)
        # Precalculate path depths
        ex_max_depth = (
            max([len(e.split('/')) for e in expected])
            if expected
            else len(sample_path.split('/'))
        )
        # Get actual paths
        colls = self.irods_backend.get_colls_recursively(sample_coll)
        paths = [c.path for c in colls]
        assay_depth = len(sample_path.split('/')) + 2

        for p in paths:
            # print(f'DEBUG: path={p}')
            if p in expected:  # Exact path found = ok
                continue
            path_depth = len(p.split('/'))
            ex_parent = '/'.join(p.split('/')[:ex_max_depth])
            # Single-level max depth under assay and expected parent at max = ok
            # (This catches most cases of self-declared colls under assays)
            if (
                ex_max_depth == assay_depth + 1
                and path_depth > ex_max_depth
                and ex_parent in expected
            ):
                continue
            # Any child collections for this path are expected = ok
            if any([e.startswith(p + '/') for e in expected]):
                continue
            # No expected neighbouring paths = ok
            if path_depth > assay_depth + 1 and any(
                [p.startswith(e + '/') for e in expected]
            ):
                parent = '/'.join(p.split('/')[:-1])
                if not [
                    e for e in expected if e.startswith(parent + '/') and e != p
                ]:
                    continue
            # If we get this far, path is orphaned
            self._write_output(irods, p, project)

    def _check_landing_zones(self, irods: iRODSSession, project: Project):
        """
        Check for orphaned landing zone collections in given project, write
        output if found.

        :param irods: iRODSSession object
        :param project: Project object
        """
        root_path = self.irods_backend.get_zone_path(project)
        if not irods.collections.exists(root_path):
            return  # Nothing to check
        root_coll = irods.collections.get(root_path)
        # Get expected paths
        # NOTE: We don't exclude NOT_CREATED status here, as it's possible
        #       creation failed after the zone collection was created
        expected = [
            self.irods_backend.get_path(z)
            for z in LandingZone.objects.filter(project=project).exclude(
                status__in=[ZONE_STATUS_MOVED, ZONE_STATUS_DELETED]
            )
        ]
        # Get actual paths
        # NOTE: We only care about the top level collections of zones here
        zone_depth = len(root_path.split('/')) + 4
        colls = self.irods_backend.get_colls_recursively(root_coll)
        paths = [c.path for c in colls if len(c.path.split('/')) == zone_depth]
        for p in paths:
            if p not in expected:
                self._write_output(irods, p, project)

    # Command Handling ---------------------------------------------------------

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--project',
            metavar='UUID',
            type=str,
            help='Limit check to a project',
        )

    def handle(self, *args, **options):
        with self.irods_backend.get_session() as irods:
            project_uuid = options.get('project')
            if project_uuid:
                projects = Project.objects.filter(
                    type=PROJECT_TYPE_PROJECT, sodar_uuid=project_uuid
                )
                if not projects:
                    logger.error(f'Project not found with UUID: {project_uuid}')
                    sys.exit(1)
            else:
                # Check for orphaned projects
                self._check_orphan_projects(irods)
                projects = Project.objects.filter(
                    type=PROJECT_TYPE_PROJECT
                ).order_by('full_title')

            for project in projects:
                # Check for orphaned sample data collections
                try:
                    self._check_sample_data(irods, project)
                except Exception as ex:
                    logger.error(
                        f'Exception in checking sample data for '
                        f'{project.get_log_title()}: {ex}'
                    )
                    if settings.DEBUG:
                        raise ex
                # Check for orphaned landing zone collections
                try:
                    self._check_landing_zones(irods, project)
                except Exception as ex:
                    logger.error(
                        f'Exception in checking landing zones for '
                        f'{project.get_log_title()}: {ex}'
                    )
                    if settings.DEBUG:
                        raise ex
