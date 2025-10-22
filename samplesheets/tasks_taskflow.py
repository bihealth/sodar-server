"""Taskflow tasks for the samplesheets app"""

import logging

from typing import Optional

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODARUser
from projectroles.plugins import PluginAPI

# Samplesheets dependency
from samplesheets.models import Investigation
from samplesheets.tasks_celery import update_project_cache_task

# Taskflowbackend dependency
from taskflowbackend.tasks.sodar_tasks import SODARBaseTask


logger = logging.getLogger(__name__)
plugin_api = PluginAPI()


class SetIrodsCollStatusTask(SODARBaseTask):
    """Set iRODS collection creation status (True/False) for sample sheets"""

    #: Investigation object for the project
    investigation = None

    def execute(self, irods_status: bool, *args, **kwargs):
        # Get initial data
        self.investigation = Investigation.objects.get(
            project=self.project, active=True
        )
        self.execute_data = {'irods_status': self.investigation.irods_status}
        # Update data
        if self.execute_data['irods_status'] != irods_status:
            self.investigation.irods_status = irods_status
            self.investigation.save()
            self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, irods_status: bool, *args, **kwargs):
        if self.data_modified is True:
            self.investigation.irods_status = self.execute_data['irods_status']
            self.investigation.save()


class RemoveSampleSheetsTask(SODARBaseTask):
    """Remove sample sheets from a project"""

    def execute(self, *args, **kwargs):
        cache_backend = plugin_api.get_backend_api('sodar_cache')
        investigation = Investigation.objects.get(
            project=self.project, active=True
        )
        investigation.delete()
        if cache_backend:
            cache_backend.delete_cache('samplesheets', self.project)
        self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, *args, **kwargs):
        pass  # TODO: How to handle this?


class UpdateProjectSheetCacheTask(SODARBaseTask):
    """Update project sample sheet cache"""

    def execute(
        self,
        user: Optional[SODARUser],
        add_alert: bool,
        alert_msg: Optional[str],
        *args,
        **kwargs,
    ):
        if settings.SHEETS_ENABLE_CACHE:
            try:
                update_project_cache_task.delay(
                    project_uuid=str(self.project.sodar_uuid),
                    user_uuid=str(user.sodar_uuid) if user else None,
                    add_alert=add_alert,
                    alert_msg=alert_msg,
                )
            except Exception as ex:
                logger.error(f'Unable to run project cache update task: {ex}')
        super().execute(*args, **kwargs)

    # NOTE: No revert needed
