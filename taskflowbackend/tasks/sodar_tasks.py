"""SODAR Django site tasks for Taskflow"""

import logging

# Projectroles dependency
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.models import Investigation

from taskflowbackend.tasks.base_task import BaseTask


logger = logging.getLogger('sodar_taskflow')


class SODARBaseTask(BaseTask):
    """Base taskflow SODAR task"""

    def __init__(
        self, name, project, force_fail=False, inject=None, *args, **kwargs
    ):
        super().__init__(
            name, force_fail=force_fail, inject=inject, *args, **kwargs
        )
        self.target = 'sodar'
        self.name = '<SODAR> {} ({})'.format(name, self.__class__.__name__)
        self.project = project

    def execute(self, *args, **kwargs):
        # Raise Exception for testing revert()
        # NOTE: This doesn't work if done in pre_execute() or post_execute()
        if self.force_fail:
            raise Exception('force_fail=True')

    def post_execute(self, *args, **kwargs):
        logger.info(
            '{}: {}'.format(
                'force_fail' if self.force_fail else 'Executed', self.name
            )
        )

    def post_revert(self, *args, **kwargs):
        logger.error('Reverted: {}'.format(self.name))


# TODO: Move into samplesheets?
class SetIrodsCollStatusTask(SODARBaseTask):
    """Set iRODS collection creation status (True/False) for a sample sheet"""

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


# TODO: Move into samplesheets?
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


# TODO: Move into landingzones?
class SetLandingZoneStatusTask(SODARBaseTask):
    """Set LandingZone status"""

    def execute(
        self,
        landing_zone,
        flow_name,
        status,
        status_info,
        extra_data=None,
        *args,
        **kwargs
    ):
        # TODO: Implement TaskflowZoneStatusSetAPIView code here
        '''
        set_data = {
            'status': status,
            'status_info': status_info,
            'zone_uuid': zone_uuid,
            'flow_name': flow_name,
        }
        if extra_data:
            set_data.update(extra_data)
        self.sodar_api.send_request(
            'landingzones/taskflow/status/set', set_data
        )
        '''
        self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(
        self,
        landing_zone,
        flow_name,
        status,
        status_info,
        extra_data=None,
        *args,
        **kwargs
    ):
        pass  # Disabled, call RevertLandingZoneStatusTask to revert


# TODO: Move into landingzones
# TODO: Replace with site internal functionality
class RevertLandingZoneFailTask(SODARBaseTask):
    """Set LandingZone status in case of failure"""

    def execute(
        self,
        zone_uuid,
        flow_name,
        info_prefix,
        status='FAILED',
        extra_data=None,
        *args,
        **kwargs
    ):
        super().execute(*args, **kwargs)

    def revert(
        self,
        zone_uuid,
        flow_name,
        info_prefix,
        status='FAILED',
        extra_data=None,
        *args,
        **kwargs
    ):
        status_info = info_prefix

        for k, v in kwargs['flow_failures'].items():
            status_info += ': '
            status_info += str(v.exception) if v.exception else 'unknown error'

        set_data = {
            'zone_uuid': zone_uuid,
            'status': status,
            'status_info': status_info,
            'flow_name': flow_name,
        }
        if extra_data:
            set_data.update(extra_data)
        '''
        self.sodar_api.send_request(
            'landingzones/taskflow/status/set', set_data
        )
        '''
