"""SODAR Taskflow API for Django apps"""

import json
import logging

# Landingzones dependency
from landingzones.constants import (
    ZONE_STATUS_NOT_CREATED,
    ZONE_STATUS_CREATING,
    ZONE_STATUS_FAILED,
)
from landingzones.models import LandingZone

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
UNKNOWN_RUN_ERROR = 'Running flow failed: unknown error, see server log'
LOCK_FAIL_MSG = 'Unable to acquire project lock'


class TaskflowAPI:
    """SODAR Taskflow API to be used by Django apps"""

    class FlowSubmitException(Exception):
        """SODAR Taskflow submission exception"""

    @classmethod
    def _raise_flow_exception(cls, ex_msg, tl_event=None, zone=None):
        """
        Handle and raise exception with flow building or execution. Updates the
        status of timeline event and/or landing zone if provided.

        :param ex_msg: Exception message (string)
        :param tl_event: Timeline event or None
        :param zone: LandingZone object or None
        :raise: FlowSubmitException
        """
        if tl_event:
            tl_event.set_status(ZONE_STATUS_FAILED, ex_msg)
        # Update landing zone
        if zone:
            status = (
                ZONE_STATUS_NOT_CREATED
                if zone.status == ZONE_STATUS_CREATING
                else ZONE_STATUS_FAILED
            )
            zone.set_status(status, ex_msg)
        # TODO: Create app alert for failure if async (see #1499)
        raise cls.FlowSubmitException(ex_msg)

    @classmethod
    def get_flow(
        cls,
        irods_backend,
        project,
        flow_name,
        flow_data,
        async_mode=False,
        tl_event=None,
    ):
        """
        Get and create a taskflow.

        :param irods_backend: IrodsbackendAPI instance
        :param project: Project object
        :param flow_name: Name of flow (string)
        :param flow_data: Flow parameters (dict)
        :param async_mode: Set up flow asynchronously if True (boolean)
        :param tl_event: ProjectEvent object for timeline updating or None
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
        force_fail=False,
        async_mode=False,
        tl_event=None,
    ):
        """
        Run a flow, either synchronously or asynchronously.

        :param flow: Flow object
        :param project: Project object
        :param force_fail: Force failure (boolean, for testing)
        :param async_mode: Submit in async mode (boolean, default=False)
        :param tl_event: Timeline ProjectEvent object or None. Event status will
                         be updated if the flow is run in async mode
        :return: Dict
        """
        flow_result = None
        ex_msg = None
        coordinator = None
        lock = None
        # Get zone if present in flow
        zone = None
        if flow.flow_data.get('zone_uuid'):
            zone = LandingZone.objects.filter(
                sodar_uuid=flow.flow_data['zone_uuid']
            ).first()

        # Acquire lock if needed
        if flow.require_lock:
            # Acquire lock
            coordinator = lock_api.get_coordinator()
            if not coordinator:
                cls._raise_flow_exception(
                    LOCK_FAIL_MSG + ': Failed to retrieve lock coordinator',
                    tl_event,
                    zone,
                )
            else:
                lock_id = str(project.sodar_uuid)
                lock = coordinator.get_lock(lock_id)
                try:
                    lock_api.acquire(lock)
                except Exception as ex:
                    cls._raise_flow_exception(
                        LOCK_FAIL_MSG + ': {}'.format(ex),
                        tl_event,
                        zone,
                    )
        else:
            logger.info('Lock not required (flow.require_lock=False)')

        # Build flow
        logger.info('Building flow "{}"..'.format(flow.flow_name))
        try:
            flow.build(force_fail)
        except Exception as ex:
            ex_msg = 'Error building flow: {}'.format(ex)

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
        elif not flow_result and not ex_msg:
            ex_msg = UNKNOWN_RUN_ERROR

        # Release lock if acquired
        if flow.require_lock and lock:
            lock_api.release(lock)
            coordinator.stop()

        # Raise exception if failed, otherwise return result
        if ex_msg:
            logger.error(ex_msg)  # TODO: Isn't this redundant?
            # NOTE: Not providing zone here since it's handled by flow
            cls._raise_flow_exception(ex_msg, tl_event, None)
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
            return None

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
