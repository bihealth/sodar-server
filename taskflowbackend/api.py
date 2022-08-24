"""SODAR Taskflow API for Django apps"""

import json
import logging

from irods.models import TicketQuery, UserGroup

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import get_backend_api

from taskflowbackend import flows
from taskflowbackend.lock_api import ProjectLockAPI
from taskflowbackend.tasks_celery import submit_flow_task


lock_api = ProjectLockAPI()
logger = logging.getLogger(__name__)


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
DEFAULT_PERMANENT_USERS = ['client_user', 'rods', 'rodsadmin', 'public']
UNKNOWN_RUN_ERROR = 'Running flow failed: unknown error, see server log'


class TaskflowAPI:
    """SODAR Taskflow API to be used by Django apps"""

    class FlowSubmitException(Exception):
        """SODAR Taskflow submission exception"""

    def __init__(self):
        self.taskflow_url = '{}:{}'.format(
            getattr(settings, 'TASKFLOW_BACKEND_HOST', ''),
            getattr(settings, 'TASKFLOW_BACKEND_PORT', ''),
        )

    @classmethod
    def get_flow(
        cls,
        irods_backend,
        project,
        flow_name,
        flow_data,
        async_mode,
        tl_event,
    ):
        """
        Get and create a taskflow.

        :param irods_backend: IrodsbackendAPI instance
        :param project: Project object
        :param flow_name: Name of flow (string)
        :param flow_data: Flow parameters (dict)
        :param async_mode: Set up flow asynchronously if True (boolean)
        :param tl_event: ProjectEvent object for timeline updating
        """
        flow_cls = flows.get_flow(flow_name)
        if not flow_cls:
            raise ValueError('Flow "{}" not supported'.format(flow_name))
        flow = flow_cls(
            irods_backend=irods_backend,
            project=project,
            flow_name=flow_name,
            flow_data=flow_data,
            async_mode=async_mode,
            tl_event=tl_event,
        )
        try:
            flow.validate()
        except TypeError as ex:
            msg = 'Error validating flow: {}'.format(ex)
            logger.error(msg)
            raise ex
        return flow

    @classmethod
    def run_flow(
        cls,
        flow,
        project,
        force_fail,
        async_mode=False,
        tl_event=None,
    ):
        """
        Run a flow, either synchronously or asynchronously.

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
            if async_mode and tl_event:
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

    def submit(
        self,
        project,
        flow_name,
        flow_data,
        async_mode=False,
        tl_event=None,
        force_fail=False,
    ):
        """
        Submit taskflow for SODAR project data modification.

        :param project: Project object
        :param flow_name: Name of flow to be executed (string)
        :param flow_data: Input data for flow execution (dict, must be JSON
                          serializable)
        :param async_mode: Run flow asynchronously (boolean, default False)
        :param tl_event: Corresponding timeline ProjectEvent (optional)
        :param force_fail: Make flow fail on purpose (boolean, default False)
        :return: Boolean
        :raise: FlowSubmitException if submission fails
        """
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            raise Exception('Irodsbackend not enabled')
        try:
            json.dumps(flow_data)
        except (TypeError, OverflowError) as ex:
            logger.error(
                'Argument flow_data is not JSON serializable: {}'.format(ex)
            )
            raise ex

        # Launch async submit task if async mode is set
        if async_mode:
            project_uuid = project.sodar_uuid
            tl_uuid = tl_event.sodar_uuid if tl_event else None
            submit_flow_task.delay(
                project_uuid,
                flow_name,
                flow_data,
                tl_uuid,
            )
            return None  # TBD: What to return

        # Else run flow synchronously
        flow = self.get_flow(
            irods_backend,
            project,
            flow_name,
            flow_data,
            async_mode,
            tl_event,
        )
        return self.run_flow(
            flow=flow,
            project=project,
            force_fail=force_fail,
            async_mode=False,
            tl_event=tl_event,
        )

    @classmethod
    def cleanup(cls):
        """
        Send a cleanup command to SODAR Taskflow. Only allowed in test mode.

        :return: Boolean
        :raise: ImproperlyConfigured if TASKFLOW_TEST_MODE is not set True
        :raise: Exception if iRODS cleanup fails
        """
        if not settings.TASKFLOW_TEST_MODE:
            raise ImproperlyConfigured(
                'TASKFLOW_TEST_MODE not True, cleanup command not allowed'
            )
        irods_backend = get_backend_api('omics_irods')
        irods = irods_backend.get_session()
        projects_root = irods_backend.get_projects_path()
        permanent_users = getattr(
            settings, 'TASKFLOW_TEST_PERMANENT_USERS', DEFAULT_PERMANENT_USERS
        )
        # TODO: Remove stuff from user folders
        # TODO: Remove stuff from trash

        # Remove project folders
        try:
            irods.collections.remove(projects_root, recurse=True, force=True)
            logger.debug('Removed projects root: {}'.format(projects_root))
        except Exception:
            pass  # This is OK, the root just wasn't there

        # Remove created user groups and users
        # NOTE: user_groups.remove does both
        for g in irods.query(UserGroup).all():
            if g[UserGroup.name] not in permanent_users:
                irods.user_groups.remove(user_name=g[UserGroup.name])
                logger.debug('Removed user: {}'.format(g[UserGroup.name]))

        # Remove all tickets
        ticket_query = irods.query(TicketQuery.Ticket).all()
        for ticket in ticket_query:
            ticket_str = ticket[TicketQuery.Ticket.string]
            irods_backend.delete_ticket(ticket_str)
            logger.debug('Deleted ticket: {}'.format(ticket_str))

    @classmethod
    def get_error_msg(cls, flow_name, submit_info):
        """
        Return a printable version of a SODAR Taskflow error message.

        :param flow_name: Name of submitted flow
        :param submit_info: Returned information from SODAR Taskflow
        :return: String
        """
        return 'Taskflow "{}" failed! Reason: "{}"'.format(
            flow_name, submit_info[:256]
        )
