"""Omics Taskflow API for Django apps"""
import requests

from django.conf import settings

# Projectroles dependency
from projectroles.models import OMICS_CONSTANTS


# Omics constants
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


# Local constants
TASKFLOW_URL = '{}:{}'.format(
    settings.TASKFLOW_BACKEND_HOST,
    settings.TASKFLOW_BACKEND_PORT)
HEADERS = {'Content-Type': 'application/json'}
TARGETS = ['irods', 'omics']


class TaskflowAPI:
    """Taskflow API to be used by Django apps"""

    class FlowSubmitException(Exception):
        """Omics Taskflow submission exception"""
        pass

    class CleanupException(Exception):
        """Omics Taskflow cleanup exception"""
        pass

    def __init__(self):
        pass

    def submit(
            self, project_uuid, flow_name, flow_data, request=None,
            targets=TARGETS, request_mode='sync', timeline_uuid=None,
            force_fail=False):
        """
        Submit taskflow for project data modification.
        :param project_uuid: UUID of the project
        :param flow_name: Name of flow to be executed (string)
        :param flow_data: Input data for flow execution (dict)
        :param request: Request object (optional)
        :param targets: Names of backends to sync with (list)
        :param request_mode: "sync" or "async"
        :param timeline_uuid: UUID of corresponding timeline event (optional)
        :param force_fail: Make flow fail on purpose (boolean, default False)
        :return: Boolean, status info if failure (string)
        """
        url = TASKFLOW_URL + '/submit'

        data = {
            'project_uuid': project_uuid,
            'flow_name': flow_name,
            'flow_data': flow_data,
            'request_mode': request_mode,
            'targets': targets,
            'force_fail': force_fail,
            'timeline_uuid': timeline_uuid}

        # HACK: Add overriding URL for test server
        if request:
            if request.POST and 'omics_url' in request.POST:
                data['omics_url'] = request.POST['omics_url']

            elif request.GET and 'omics_url' in request.GET:
                data['omics_url'] = request.GET['omics_url']

        # print('DATA: {}'.format(data))  # DEBUG
        response = requests.post(url, json=data, headers=HEADERS)

        if response.status_code == 200 and bool(response.text) is True:
            return True

        else:
            print('Submit Response (url={}): {}'.format(
                url, response.text))    # DEBUG
            raise self.FlowSubmitException(
                self.get_error_msg(flow_name, response.text))

    def use_taskflow(self, project):
        """
        Return True/False regarding if taskflow should be used with a project
        :param project: Project object
        :return: bool
        """
        return True if project.type == PROJECT_TYPE_PROJECT else False

    def cleanup(self):
        """Clean up everything from the iRODS iCAT server database. NOTE: only
        to be used with a test db!"""
        # TODO: Some security measures preventing using this on a prod icat..
        url = TASKFLOW_URL + '/cleanup'
        response = requests.get(url)

        if response.status_code == 200:
            return True

        else:
            print('Cleanup Response: {}'.format(response.text))  # DEBUG
            raise self.FlowSubmitException(response.text)

    def get_error_msg(self, flow_name, submit_info):
        return 'iRODS taskflow "{}" failed! Reason: "{}"'.format(
            flow_name, submit_info[:256])
