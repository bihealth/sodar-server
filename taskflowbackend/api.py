"""SODAR Taskflow API for Django apps"""

import logging
import requests

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Projectroles dependency
from projectroles.models import RoleAssignment, SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from taskflowbackend import flows
from taskflowbackend.apis import lock_api, sodar_api


logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
HEADERS = {'Content-Type': 'application/json'}
UNKNOWN_RUN_ERROR = 'Running flow failed: unknown error, see server log'


class TaskflowAPI:
    """SODAR Taskflow API to be used by Django apps"""

    class FlowSubmitException(Exception):
        """SODAR Taskflow submission exception"""

    class CleanupException(Exception):
        """SODAR Taskflow cleanup exception"""

    def __init__(self):
        self.taskflow_url = '{}:{}'.format(
            getattr(settings, 'TASKFLOW_BACKEND_HOST', ''),
            getattr(settings, 'TASKFLOW_BACKEND_PORT', ''),
        )

    # TODO: Update to work here
    @classmethod
    def _run_flow(
        cls,
        flow,
        project,
        force_fail,
        async_mode=False,
        tl_event=None,
    ):
        """
        Run a task flow, either synchronously or asynchronously.

        :param flow: Flow object
        :param project: Project object
        :param force_fail: Force failure (boolean, for testing)
        :param async_mode: Submit in async mode (boolean, default=False)
        :param tl_event: Timeline ProjectEvent object or None
        :return: Response object
        """
        flow_result = None
        ex_msg = None
        coordinator = None
        lock = None

        # Acquire lock if needed
        if flow.require_lock:
            # Acquire lock
            coordinator = lock_api.get_coordinator()
            if not coordinator:
                raise Exception('Unable to retrieve lock coordinator')
            else:
                lock_id = str(project.sodar_uuid)
                lock = coordinator.get_lock(lock_id)
                try:
                    lock_api.acquire(lock)
                except Exception as ex:
                    raise Exception(
                        'Unable to acquire project lock: {}'.format(ex)
                    )
        else:
            logger.info('Lock not required (flow.require_lock=False)')

        # Build flow
        logger.info('Building flow "{}"..'.format(flow.flow_name))
        try:
            flow.build(force_fail)
        except Exception as ex:
            ex_msg = 'Error building flow: {}'.format(ex)
            # HACK: Fix for building issues with landing zone flows
            # TODO: Generalize to report all building problems
            if async_mode and flow.flow_data.get('landing_zone'):
                # Set zone status
                zone_status = (
                    'NOT CREATED'
                    if flow.flow_name == 'landing_zone_create'
                    else 'FAILED'
                )
                flow.flow_data['landing_zone'].set_status(zone_status, ex_msg)
                # Set timeline status
                if tl_event:
                    tl_event.set_status('FAILED', ex_msg)

        # Run flow
        if not ex_msg:
            logger.info('Building flow OK')
            try:
                flow_result = flow.run()
            except Exception as ex:
                ex_msg = 'Error running flow: {}'.format(ex)

        # Flow completion
        if flow_result and tl_event and async_mode:
            tl_event.set_status('OK', 'Async submit OK')
        # Exception/failure
        elif not flow_result:
            if not ex_msg:
                ex_msg = UNKNOWN_RUN_ERROR
            if async_mode and tl_event:  # TODO: Why not for sync events?
                tl_event.set_status('FAILED', ex_msg)

        # Release lock if acquired
        if flow.require_lock and lock:
            lock_api.release(lock)
            coordinator.stop()

        # Raise exception if failed, otherwise return result
        if ex_msg:
            logger.error(ex_msg)
            raise cls.FlowSubmitException(ex_msg)
        return flow_result

    # TODO: Update to work here, remove unnecessary complexity, update params
    def submit(
        self,
        project,
        flow_name,
        flow_data,
        request=None,
        targets=settings.TASKFLOW_TARGETS,
        async_mode=False,
        tl_event=None,
        force_fail=False,
        sodar_url=None,  # TODO: Remove
    ):
        """
        Submit taskflow for SODAR project data modification.

        :param project: Project object
        :param flow_name: Name of flow to be executed (string)
        :param flow_data: Input data for flow execution (dict)
        :param request: Request object (optional)
        :param targets: Names of backends to sync with (list)
        :param async_mode: Run flow asynchronously (boolean, default False)
        :param tl_event: Corresponding timeline ProjectEvent (optional)
        :param force_fail: Make flow fail on purpose (boolean, default False)
        :param sodar_url: URL of SODAR server (optional, for testing)
        :return: Boolean
        :raise: FlowSubmitException if submission fails
        """
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            raise Exception('Irodsbackend not enabled')

        # Get flow class
        flow_cls = flows.get_flow(flow_name)
        if not flow_cls:
            raise ValueError('Flow "{}" not supported'.format(flow_name))

        # Init SODAR API
        # TODO: Remove this entirely?
        sodar_tf = sodar_api.SODARAPI(sodar_url)

        # Create flow
        flow = flow_cls(
            irods_backend=irods_backend,
            sodar_api=sodar_tf,
            project=project,
            flow_name=flow_name,
            flow_data=flow_data,
            targets=targets,
            async_mode=async_mode,
            tl_event=tl_event,
        )
        try:
            flow.validate()
        except TypeError as ex:
            msg = 'Error validating flow: {}'.format(ex)
            logger.error(msg)
            raise ex

        # Build and run flow
        # TODO: Run async using celery instead
        '''
        if async_mode:
            p = Process(
                target=self._run_flow,
                args=(
                    flow,
                    project,
                    force_fail,
                    True,
                    tl_event,
                ),
            )
            p.start()
            return None  # TBD: What to return
        '''
        # Run synchronously
        return self._run_flow(
            flow=flow,
            project=project,
            force_fail=force_fail,
            async_mode=False,
            tl_event=tl_event,
        )

    def use_taskflow(self, project):
        """
        Check whether taskflow use is allowed with a project.

        :param project: Project object
        :return: Boolean
        """
        return True if project.type == PROJECT_TYPE_PROJECT else False

    def cleanup(self):
        """
        Send a cleanup command to SODAR Taskflow. Only allowed in test mode.

        :return: Boolean
        :raise: ImproperlyConfigured if TASKFLOW_TEST_MODE is not set True
        :raise: CleanupException if SODAR Taskflow raises an error
        """
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, cleanup command not allowed'
            )
        # TODO: Simply call cleanup() instead or implement here
        url = self.taskflow_url + '/cleanup'
        data = {'test_mode': settings.TASKFLOW_TEST_MODE}

        response = requests.post(url, json=data, headers=HEADERS)
        if response.status_code == 200:
            logger.debug('Cleanup OK')
            return True
        else:
            logger.debug('Cleanup failed: {}'.format(response.text))
            raise self.CleanupException(response.text)

    def get_error_msg(self, flow_name, submit_info):
        """
        Return a printable version of a SODAR Taskflow error message.

        :param flow_name: Name of submitted flow
        :param submit_info: Returned information from SODAR Taskflow
        :return: String
        """
        return 'Taskflow "{}" failed! Reason: "{}"'.format(
            flow_name, submit_info[:256]
        )

    # TODO: Refactor
    @classmethod
    def get_inherited_roles(cls, project, user, roles=None):
        """
        Return list of inherited owner roles to be used in taskflow sync.

        :param project: Project object
        :param user: User object
        :pram roles: Previously collected roles (optional, list or None)
        :return: List of dicts
        """
        if roles is None:
            roles = []
        # TODO: Remove support for legacy roles in v0.9 (see #506)
        if (
            project.type == PROJECT_TYPE_PROJECT
            and not RoleAssignment.objects.filter(project=project, user=user)
        ):
            r = {
                'project_uuid': str(project.sodar_uuid),
                'username': user.username,
            }
            if r not in roles:  # Avoid unnecessary dupes
                roles.append(r)
        for child in project.get_children():
            roles = cls.get_inherited_roles(child, user, roles)
        return roles

    # TODO: Refactor
    @classmethod
    def get_inherited_users(cls, project, roles=None):
        """
        Return list of all inherited users within a project and its children, to
        be used in taskflow sync.

        :param project: Project object
        :pram roles: Previously collected roles (optional, list or None)
        :return: List of dicts
        """
        if roles is None:
            roles = []
        if project.type == PROJECT_TYPE_PROJECT:
            i_owners = [a.user for a in project.get_owners(inherited_only=True)]
            all_users = [a.user for a in project.get_all_roles(inherited=False)]
            for u in [u for u in i_owners if u not in all_users]:
                roles.append(
                    {
                        'project_uuid': str(project.sodar_uuid),
                        'username': u.username,
                    }
                )
        for child in project.get_children():
            roles = cls.get_inherited_users(child, roles)
        return roles
