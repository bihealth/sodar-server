"""Taskflow tasks for the samplesheets app"""


# Projectroles dependency
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.models import Investigation

# Taskflowbackend dependency
from taskflowbackend.tasks.sodar_tasks import SODARBaseTask


class SetIrodsCollStatusTask(SODARBaseTask):
    """Set iRODS collection creation status (True/False) for sample sheets"""

    #: Investigation object for the project
    investigation = None

    def execute(self, irods_status, *args, **kwargs):
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

    def revert(self, irods_status, *args, **kwargs):
        if self.data_modified is True:
            self.investigation.irods_status = self.execute_data['irods_status']
            self.investigation.save()


class RemoveSampleSheetsTask(SODARBaseTask):
    """Remove sample sheets from a project"""

    def execute(self, *args, **kwargs):
        cache_backend = get_backend_api('sodar_cache')
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
