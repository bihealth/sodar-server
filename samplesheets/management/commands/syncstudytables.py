"""Syncstudytables management command"""

import sys

from django.core.management.base import BaseCommand

# Projectroles dependency
from projectroles.management.logging import ManagementCommandLogger
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from samplesheets.models import Investigation
from samplesheets.rendering import (
    SampleSheetTableBuilder,
    STUDY_TABLE_CACHE_ITEM,
)


logger = ManagementCommandLogger(__name__)
table_builder = SampleSheetTableBuilder()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
# Local constants
APP_NAME = 'samplesheets'


class Command(BaseCommand):
    help = 'Syncs study render tables in sodarcache for optimized rendering'

    @classmethod
    def _get_log_project(cls, project):
        """Return logging-friendly project title"""
        return '"{}" ({})'.format(project.title, project.sodar_uuid)

    @classmethod
    def _get_log_study(cls, study):
        """Return logging-friendly project title"""
        return '"{}" ({})'.format(study.get_title(), study.sodar_uuid)

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--project',
            metavar='UUID',
            type=str,
            help='Limit sync to a project',
        )

    def handle(self, *args, **options):
        cache_backend = get_backend_api('sodar_cache')
        if not cache_backend:
            logger.error('Sodarcache not enabled, exiting')
            sys.exit(1)

        q_kwargs = {'type': PROJECT_TYPE_PROJECT}
        if options.get('project'):
            q_kwargs['sodar_uuid'] = options['project']
        projects = Project.objects.filter(**q_kwargs).order_by('full_title')
        if not projects:
            logger.info(
                'No project{} found'.format(
                    's' if not options.get('project') else ''
                )
            )
            return
        if options.get('project'):
            project = projects.first()
            logger.info(
                'Limiting sync to project {}'.format(
                    self._get_log_project(project)
                )
            )

        for project in projects:
            study_count = 0
            try:
                investigation = Investigation.objects.get(
                    project=project, active=True
                )
            except Investigation.DoesNotExist:
                logger.debug(
                    'No investigation found, skipping for project {}'.format(
                        self._get_log_project(project)
                    )
                )
                continue
            logger.debug(
                'Building study render tables for project {}..'.format(
                    self._get_log_project(project)
                )
            )
            for study in investigation.studies.all():
                try:
                    study_tables = table_builder.build_study_tables(
                        study, use_config=True
                    )
                except Exception as ex:
                    logger.error(
                        'Error building tables for study {}: {}'.format(
                            self._get_log_study(study), ex
                        )
                    )
                    continue
                item_name = STUDY_TABLE_CACHE_ITEM.format(
                    study=study.sodar_uuid
                )
                try:
                    cache_backend.set_cache_item(
                        app_name=APP_NAME,
                        name=item_name,
                        data=study_tables,
                        project=project,
                    )
                    logger.info('Set cache item "{}"'.format(item_name))
                    study_count += 1
                except Exception as ex:
                    logger.error(
                        'Failed to set cache item "{}": {}'.format(
                            item_name, ex
                        )
                    )
            logger.info(
                'Built {} study table{} for project {}'.format(
                    study_count,
                    's' if study_count != 1 else '',
                    self._get_log_project(project),
                )
            )
        logger.info('Study table cache sync done')
