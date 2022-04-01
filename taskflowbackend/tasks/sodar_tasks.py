"""SODAR Django site tasks for Taskflow"""

# TODO: Replace with actual code instead of API calls

import json
import logging

from taskflowbackend.tasks.base_task import BaseTask
from taskflowbackend.apis.sodar_api import SODARRequestException


logger = logging.getLogger('sodar_taskflow')


class SODARBaseTask(BaseTask):
    """Base SODAR Django web UI task"""

    def __init__(
        self,
        name,
        project_uuid,
        sodar_api,
        force_fail=False,
        inject=None,
        *args,
        **kwargs
    ):
        super().__init__(
            name, force_fail=force_fail, inject=inject, *args, **kwargs
        )
        self.target = 'sodar'
        self.name = '<SODAR> {} ({})'.format(name, self.__class__.__name__)
        self.project_uuid = project_uuid
        self.sodar_api = sodar_api

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


# TODO: Remove, not used anymore
class UpdateProjectTask(SODARBaseTask):
    """Update project title and description"""

    def execute(
        self,
        title,
        description,
        readme,
        parent_uuid,
        public_guest_access,
        *args,
        **kwargs
    ):
        # Get initial data
        self.execute_data = self.sodar_api.send_request(
            'project/taskflow/get', {'project_uuid': self.project_uuid}
        ).json()

        update_data = {
            'project_uuid': self.project_uuid,
            'title': title,
            'parent_uuid': parent_uuid,
            'description': description,
            'readme': readme,
            'public_guest_access': public_guest_access,
        }

        self.sodar_api.send_request('project/taskflow/update', update_data)

        super().execute(*args, **kwargs)

    def revert(self, title, description, readme, parent_uuid, *args, **kwargs):
        if kwargs['result'] is True:
            self.sodar_api.send_request(
                'project/taskflow/update', self.execute_data
            )


# TODO: Remove, we won't be setting these from taskflow anymore
# TODO: Also remove all mentions in flows
class SetProjectSettingsTask(SODARBaseTask):
    """Set project settings"""

    def execute(self, settings, *args, **kwargs):
        # Get initial data
        self.execute_data = self.sodar_api.send_request(
            'project/taskflow/settings/get', {'project_uuid': self.project_uuid}
        ).json()

        update_data = {
            'project_uuid': self.project_uuid,
            'settings': json.dumps(settings),
        }

        self.sodar_api.send_request(
            'project/taskflow/settings/set', update_data
        )

        super().execute(*args, **kwargs)

    def revert(self, settings, *args, **kwargs):
        if kwargs['result'] is True:
            self.sodar_api.send_request(
                'project/taskflow/settings/set', self.execute_data
            )


# TODO: Remove, we won't be setting these from taskflow anymore
# TODO: Also remove all mentions in flows
class SetRoleTask(SODARBaseTask):
    """Update user role in a project"""

    def execute(self, user_uuid, role_pk, *args, **kwargs):
        # Get initial data
        query_data = {'project_uuid': self.project_uuid, 'user_uuid': user_uuid}

        try:
            self.execute_data = self.sodar_api.send_request(
                'project/taskflow/role/get', query_data
            ).json()

        except Exception:
            self.execute_data = None

        set_data = {
            'project_uuid': self.project_uuid,
            'user_uuid': user_uuid,
            'role_pk': role_pk,
        }
        self.sodar_api.send_request('project/taskflow/role/set', set_data)
        self.data_modified = True

        super().execute(*args, **kwargs)

    def revert(self, user_uuid, role_pk, *args, **kwargs):
        if self.data_modified:
            if self.execute_data:
                self.sodar_api.send_request(
                    'project/taskflow/role/set', self.execute_data
                )
            else:
                remove_data = {
                    'project_uuid': self.project_uuid,
                    'user_uuid': user_uuid,
                }
                self.sodar_api.send_request(
                    'project/taskflow/role/delete', remove_data
                )


# TODO: Remove, we won't be setting these from taskflow anymore
# TODO: Also remove all mentions in flows
class RemoveRoleTask(SODARBaseTask):
    """Remove user role in a project"""

    def execute(self, user_uuid, role_pk, *args, **kwargs):
        # Get initial data
        self.execute_data = {
            'project_uuid': self.project_uuid,
            'user_uuid': user_uuid,
            'role_pk': role_pk,
        }

        remove_data = {
            'project_uuid': self.project_uuid,
            'user_uuid': user_uuid,
        }

        try:
            self.sodar_api.send_request(
                'project/taskflow/role/delete', remove_data
            )
            self.data_modified = True

        except SODARRequestException:
            pass

        super().execute(*args, **kwargs)

    def revert(self, user_uuid, role_pk, *args, **kwargs):
        if self.data_modified:
            self.sodar_api.send_request(
                'project/taskflow/role/set', self.execute_data
            )


# TODO: Replace with code in the old API view
class SetIrodsCollStatusTask(SODARBaseTask):
    """Set iRODS collection creation status (True/False) for a sample sheet"""

    def execute(self, dir_status, *args, **kwargs):
        # Get initial data
        query_data = {'project_uuid': self.project_uuid}
        self.execute_data = self.sodar_api.send_request(
            'samplesheets/taskflow/dirs/get', query_data
        ).json()

        if self.execute_data['dir_status'] != dir_status:
            set_data = {
                'project_uuid': self.project_uuid,
                'dir_status': dir_status,
            }
            self.sodar_api.send_request(
                'samplesheets/taskflow/dirs/set', set_data
            )
            self.data_modified = True

        super().execute(*args, **kwargs)

    def revert(self, dir_status, *args, **kwargs):
        if self.data_modified is True:
            self.sodar_api.send_request(
                'samplesheets/taskflow/dirs/set', self.execute_data
            )


# TODO: Check how we even used this
# TODO: Handle revert (see above), before it this must be called last in flow
class RemoveSampleSheetTask(SODARBaseTask):
    """Remove sample sheet from a project"""

    def execute(self, *args, **kwargs):
        query_data = {'project_uuid': self.project_uuid}

        try:
            self.sodar_api.send_request(
                'samplesheets/taskflow/delete', query_data
            )
            self.data_modified = True

        except SODARRequestException:
            pass

        super().execute(*args, **kwargs)

    def revert(self, *args, **kwargs):
        pass  # TODO: How to handle this?


# TODO: Replace with site internal functionality
class CreateLandingZoneTask(SODARBaseTask):
    """Create LandingZone for a project and user in the SODAR database"""

    def execute(
        self, zone_title, user_uuid, assay_uuid, description, *args, **kwargs
    ):
        create_data = {
            'project_uuid': self.project_uuid,
            'assay_uuid': assay_uuid,
            'title': zone_title,
            'user_uuid': user_uuid,
            'description': description,
        }
        response = self.sodar_api.send_request(
            'landingzones/taskflow/create', create_data
        )
        self.execute_data = response.json()

        self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(
        self, zone_title, user_uuid, assay_uuid, description, *args, **kwargs
    ):
        if self.data_modified:
            remove_data = {'zone_uuid': self.execute_data['zone_uuid']}
            self.sodar_api.send_request(
                'landingzones/taskflow/create', remove_data
            )


# TODO: Replace with site internal functionality
class SetLandingZoneStatusTask(SODARBaseTask):
    """Set LandingZone status"""

    def execute(
        self,
        status,
        status_info,
        flow_name=None,
        zone_uuid=None,
        extra_data=None,
        *args,
        **kwargs
    ):
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
        self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(
        self,
        status,
        status_info,
        flow_name,
        zone_uuid=None,
        extra_data=None,
        *args,
        **kwargs
    ):
        pass  # Disabled, call RevertLandingZoneStatusTask to revert


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
        self.sodar_api.send_request(
            'landingzones/taskflow/status/set', set_data
        )
