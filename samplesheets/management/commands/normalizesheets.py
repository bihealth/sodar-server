"""Normalizesheets management command"""

import sys

from altamisa.constants import table_headers as th

from django.core.management.base import BaseCommand
from django.db import transaction

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.management.logging import ManagementCommandLogger
from projectroles.models import Project, SODAR_CONSTANTS
from projectroles.plugins import PluginAPI

from samplesheets.models import Investigation
from samplesheets.rendering import STUDY_TABLE_CACHE_ITEM

# from samplesheets.rendering import SampleSheetTableBuilder
from samplesheets.views_ajax import SheetVersionMixin


app_settings = AppSettingAPI()
logger = ManagementCommandLogger(__name__)
plugin_api = PluginAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
APP_NAME = 'samplesheets'
LIB_NAME = 'library name'
LIB_NAME_REPLACE = th.EXTRACT_NAME
COMMAND_DESC = 'Normalize sheets with management command'


class Command(SheetVersionMixin, BaseCommand):
    help = (
        'Clean up and normalize previously imported sample sheets for '
        'non-standard data or other issues. Also updates render tables and '
        'creates a backup ISA-Tab version of the normalized sheets.'
    )

    def _update_database(self, investigation, check):
        """Update the sample sheets database model"""

        def _update_materials(materials, check):
            """Update materials and return update count"""
            for m in materials:
                if not check:
                    m.material_type = LIB_NAME_REPLACE
                    m.headers[0] = LIB_NAME_REPLACE
                    m.save()
            return materials.count()

        m_count = 0
        for study in investigation.studies.all():
            for assay in study.assays.all():
                m_count += _update_materials(
                    assay.materials.filter(material_type__iexact=LIB_NAME),
                    check,
                )
        logger.info(
            '{} {} affected material{} in database'.format(
                'Found' if check else 'Renamed',
                m_count,
                's' if m_count != 1 else '',
            )
        )
        return m_count

    def _update_study_tables(self, project, check):
        """Update cached study render tables"""
        inv = Investigation.objects.filter(project=project, active=True).first()
        if not inv:
            return
        th_count = 0
        cache_backend = plugin_api.get_backend_api('sodar_cache')
        for study in inv.studies.all():
            item_name = STUDY_TABLE_CACHE_ITEM.format(study=study.sodar_uuid)
            item = cache_backend.get_cache_item(
                app_name=APP_NAME,
                name=item_name,
                project=project,
            )
            if not item or not item.data:
                continue
            for k, v in item.data['assays'].items():
                # Rename top header
                top_header = item.data['assays'][k]['top_header']
                for i in range(0, len(top_header)):
                    if top_header[i]['value'].lower() == LIB_NAME:
                        if not check:
                            top_header[i]['value'] = LIB_NAME_REPLACE
                            top_header[i]['headers'][0] = LIB_NAME_REPLACE
                        th_count += 1
            if not check:
                item.save()
        logger.info(
            '{} {} affected top header{} in render tables'.format(
                'Found' if check else 'Renamed',
                th_count,
                's' if th_count != 1 else '',
            )
        )
        return th_count

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--project',
            metavar='UUID',
            type=str,
            help='Limit normalization to a project',
        )
        parser.add_argument(
            '-c',
            '--check',
            action='store_true',
            help='Check sample sheets and log changes without modifications',
        )

    def handle(self, *args, **options):
        timeline = plugin_api.get_backend_api('timeline_backend')
        cache_backend = plugin_api.get_backend_api('sodar_cache')
        if not cache_backend:
            logger.error('Sodarcache not enabled, exiting')
            sys.exit(1)
        project_uuid = options.get('project')
        if project_uuid:
            project = Project.objects.filter(sodar_uuid=project_uuid).first()
            if not project:
                logger.error(f'Project not found with UUID "{project_uuid}"')
                sys.exit(1)
            projects = [project]
        else:
            projects = Project.objects.all().order_by('full_title')

        check = options.get('check')
        ok_count = 0
        err_count = 0
        skip_count = 0
        for project in projects:
            investigation = Investigation.objects.filter(
                project=project, active=True
            ).first()
            if not investigation:
                logger.info(
                    f'No investigation found, skipping project '
                    f'{project.get_log_title()}'
                )
                skip_count += 1
                continue
            logger.info(
                '{} sheets in project {}..'.format(
                    'Checking' if check else 'Normalizing',
                    project.get_log_title(),
                )
            )
            edit_count = 0
            try:
                with transaction.atomic():  # Atomic transaction per project
                    edit_count += self._update_database(investigation, check)
                    edit_count += self._update_study_tables(project, check)
                    if not check and edit_count > 0:
                        logger.info('Saving ISA-Tab version..')
                        self.save_version(
                            investigation, description=COMMAND_DESC
                        )
                ok_count += 1
                if timeline:
                    tl_status = timeline.TL_STATUS_OK
                    tl_desc = None
            except Exception as ex:
                logger.error(
                    f'Error normalizing sheets in project '
                    f'{project.get_log_title()}: {ex}'
                )
                err_count += 1
                if timeline:
                    tl_status = timeline.TL_STATUS_FAILED
                    tl_desc = str(ex)
            if timeline and not check and edit_count > 0:
                tl_event = timeline.add_event(
                    project=project,
                    app_name=APP_NAME,
                    user=None,
                    event_name='sheet_normalize',
                    description='normalize investigation {investigation}',
                    status_type=tl_status,
                    status_desc=tl_desc,
                )
                tl_event.add_object(
                    investigation, 'investigation', investigation.title
                )

        logger.info(
            'Sheet normalization {} for {} project{} ({} OK, {} '
            'error{}, {} skipped)'.format(
                'checked' if check else 'done',
                len(projects),
                's' if len(projects) != 1 else '',
                ok_count,
                err_count,
                's' if err_count != 1 else '',
                skip_count,
            )
        )
