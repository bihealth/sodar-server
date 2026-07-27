"""SODAR Taskflow API for Django apps"""

import json
import logging
import redis

from typing import Any, Optional

from django.conf import settings

from rest_framework.exceptions import APIException

# Landingzones dependency
from landingzones.constants import (
    ZONE_STATUS_NOT_CREATED,
    ZONE_STATUS_CREATING,
    ZONE_STATUS_FAILED,
    STATUS_FINISHED,
)
from landingzones.models import LandingZone

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import Project, SODARUser, SODAR_CONSTANTS
from projectroles.plugins import PluginAPI
from projectroles.views_api import ServiceUnavailable

from taskflowbackend import flows
from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.irods_utils import get_flow_role as _get_flow_role
from taskflowbackend.lock_api import ProjectLockAPI, PROJECT_LOCKED_MSG
from taskflowbackend.tasks_celery import submit_flow_task


app_settings = AppSettingAPI()
lock_api = ProjectLockAPI()
logger = logging.getLogger(__name__)
plugin_api = PluginAPI()


# SODAR constants
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']

# Local constants
UNKNOWN_RUN_ERROR = 'Running flow failed: unknown error, see server log'
LOCK_FAIL_MSG = 'Unable to acquire project lock'
READ_ONLY_MSG = 'Site in read-only mode, taskflow operations not allowed'
COORDINATOR_EX_MSG = 'Failed to retrieve lock coordinator'


class TaskflowAPI:
    """SODAR Taskflow API to be used by Django apps"""

    class FlowSubmitException(Exception):
        """SODAR Taskflow submission exception"""

    #: Exception message for locked project
    project_locked_msg = PROJECT_LOCKED_MSG

    @classmethod
    def _raise_flow_exception(
        cls,
        ex_msg: str,
        tl_event: Any = None,
        zone: Optional[LandingZone] = None,
    ):
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
            zone.refresh_from_db()
            if zone.status not in STATUS_FINISHED:  # Skip if already finished
                status = (
                    ZONE_STATUS_NOT_CREATED
                    if zone.status == ZONE_STATUS_CREATING
                    else ZONE_STATUS_FAILED
                )
                zone.set_status(status, ex_msg)
        # TODO: Create app alert for failure if async (see #1499)
        raise cls.FlowSubmitException(ex_msg)

    @classmethod
    def _raise_run_flow_exception(
        cls,
        ex_msg: str,
        tl_event: Any = None,
        zone: Optional[LandingZone] = None,
    ):
        """
        Wrapper for _raise_flow_exception() to be called from run_flow().

        :param ex_msg: Exception message (string)
        :param tl_event: Timeline event or None
        :param zone: LandingZone object or None
        :raise: FlowSubmitException
        """
        logger.error(ex_msg)
        # Provide landing zone if error occurs but status has not been set
        # (This means a failure has not been properly handled in the flow)
        ex_zone = None
        if zone:
            zone.refresh_from_db()
            if zone.status not in STATUS_FINISHED:
                ex_zone = zone
        cls._raise_flow_exception(ex_msg, tl_event, ex_zone)

    @classmethod
    def _raise_lock_exception(
        cls,
        ex_msg: str,
        tl_event: Any = None,
        zone: Optional[LandingZone] = None,
    ):
        """
        Raise exception specifically for project lock errors. Updates the status
        of the landing zone only if zone has not yet been finished by a
        concurrent taskflow.

        :param ex_msg: Exception message (string)
        :param tl_event: Timeline event or None
        :param zone: LandingZone object or None
        :raise: FlowSubmitException
        """
        lock_zone = None
        if zone:
            zone.refresh_from_db()
            if zone.status not in STATUS_FINISHED:
                lock_zone = zone  # Exclude zone if already finished (see #1909)
        cls._raise_flow_exception(
            LOCK_FAIL_MSG + ': ' + str(ex_msg),
            tl_event,
            lock_zone,
        )

    # HACK for returning 503 if project is locked (see #1505, #1847)
    @classmethod
    def raise_submit_api_exception(
        cls, msg_prefix: str, ex: Exception, default_class: Any = APIException
    ):
        """
        Raise zone submit API exception. Selects appropriate API response based
        on exception type.

        :param msg_prefix: API response prefix
        :param ex: Exception object
        :param default_class: Default API exception class to be returned
        :raises: Exception of varying type
        """
        msg = f'{msg_prefix}{ex}'
        if PROJECT_LOCKED_MSG in msg:
            raise ServiceUnavailable(msg)
        raise default_class(msg)

    @classmethod
    def get_flow_role(
        cls, project: Project, user: SODARUser, role_rank: Optional[int] = None
    ) -> dict:
        """
        Return role dict for taskflows performing role modification.

        :param project: Project object
        :param user: SODARUser object or username string
        :param role_rank: String or None
        :return: Dict
        """
        return _get_flow_role(project, user, role_rank)

    @classmethod
    def get_flow(
        cls,
        irods_backend: Any,
        project: Project,
        user: Optional[SODARUser],
        flow_name: str,
        flow_data: dict,
        async_mode: bool = False,
        tl_event: Any = None,
    ) -> BaseLinearFlow:
        """
        Get and create a taskflow.

        :param irods_backend: IrodsbackendAPI instance
        :param project: Project object
        :param user: User submitting the flow (SODARUser or None)
        :param flow_name: Name of flow (string)
        :param flow_data: Flow parameters (dict)
        :param async_mode: Set up flow asynchronously if True (boolean)
        :param tl_event: TimelineEvent object for timeline updating or None
        :return: Flow object inheriting BaseLinearFlow
        """
        flow_cls = flows.get_flow(flow_name)
        if not flow_cls:
            raise ValueError(f'Flow "{flow_name}" not supported')
        flow = flow_cls(
            irods_backend=irods_backend,
            project=project,
            user=user,
            flow_name=flow_name,
            flow_data=flow_data,
            async_mode=async_mode,
            tl_event=tl_event,
        )
        try:
            flow.validate()
        except TypeError as ex:
            msg = f'Error validating flow: {ex}'
            logger.error(msg)
            raise ex
        return flow

    @classmethod
    def run_flow(
        cls,
        flow: BaseLinearFlow,
        project: Project,
        force_fail: bool = False,
        async_mode: bool = False,
        tl_event: Any = None,
    ) -> dict:
        """
        Run a flow, either synchronously or asynchronously.

        NOTE: Does NOT check for site read-only mode, that must be done in the
        calling views.

        :param flow: Flow object
        :param project: Project object
        :param force_fail: Force failure (boolean, for testing)
        :param async_mode: Submit in async mode (boolean, default=False)
        :param tl_event: TimelineEvent object or None. Event status will be
                         updated if the flow is run in async mode
        :return: Dict
        """
        flow_result = None
        ex_msg = None
        coordinator = None
        lock = None
        # Get landing zone if present in flow
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
                cls._raise_lock_exception(COORDINATOR_EX_MSG, tl_event, zone)
            else:
                lock_id = str(project.sodar_uuid)
                lock = coordinator.get_lock(lock_id)
                try:
                    lock_api.acquire(lock)
                except Exception as ex:
                    # In case of regular locked project API, delete tl_event and
                    # do not provide it to the raise method
                    # TODO: Check for project lock before running flow and
                    #       creating timeline event (see #2136)
                    raise_event = tl_event
                    if PROJECT_LOCKED_MSG in str(ex):
                        if tl_event:
                            tl_event.delete()
                        raise_event = None
                    cls._raise_lock_exception(str(ex), raise_event, zone)
        else:
            logger.info('Lock not required (flow.require_lock=False)')

        # Build flow
        logger.info(f'Building flow "{flow.flow_name}"..')
        try:
            flow.build(force_fail)
        except Exception as ex:
            ex_msg = f'Error building flow: {ex}'

        # Run flow
        if not ex_msg:
            logger.info('Building flow OK')
            try:
                flow_result = flow.run()
            except Exception as ex:
                ex_msg = f'Error running flow: {ex}'

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
            cls._raise_run_flow_exception(ex_msg, tl_event, zone)
        return flow_result

    def submit(
        self,
        project: Project,
        user: Optional[SODARUser],
        flow_name: str,
        flow_data: dict,
        async_mode: bool = False,
        tl_event: Any = None,
        force_fail: bool = False,
    ) -> Optional[dict]:
        """
        Submit taskflow for SODAR project data modification.

        :param project: Project object
        :param user: User submitting the flow (SODARUser or None)
        :param flow_name: Name of flow to be executed (string)
        :param flow_data: Input data for flow execution (dict, must be JSON
                          serializable)
        :param async_mode: Run flow asynchronously (boolean, default False)
        :param tl_event: Corresponding TimelineEvent (optional)
        :param force_fail: Make flow fail on purpose (boolean, default False)
        :return: Dict or None
        :raise: FlowSubmitException if submission fails
        """
        irods_backend = plugin_api.get_backend_api('omics_irods')
        if not irods_backend:
            raise Exception('Irodsbackend not enabled')
        try:
            json.dumps(flow_data)
        except (TypeError, OverflowError) as ex:
            logger.error(f'Argument flow_data is not JSON serializable: {ex}')
            raise ex

        # Launch async submit task if async mode is set
        if async_mode:
            tl_uuid = tl_event.sodar_uuid if tl_event else None
            submit_flow_task.delay(
                project.sodar_uuid,
                user.sodar_uuid if user else None,
                flow_name,
                flow_data,
                tl_uuid,
            )
            return None

        # Else run flow synchronously
        flow = self.get_flow(
            irods_backend,
            project,
            user,
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
    def get_error_msg(cls, flow_name: str, submit_info: str) -> str:
        """
        Return a printable version of a SODAR Taskflow error message.

        :param flow_name: Name of submitted flow
        :param submit_info: Returned information from SODAR Taskflow
        :return: String
        """
        return f'Taskflow "{flow_name}" failed! Reason: "{submit_info[:256]}"'

    @classmethod
    def is_locked(cls, project: Project) -> bool:
        """
        Return lock status for project, True meaning locked.

        :param project: Project object
        :return: Boolean
        """
        # NOTE: We query redis directly to allow having to call acquire()
        # NOTE: Yes, this is how tooz encodes the lock IDs (see #2144)
        lock_db_id = f"b'_tooz'_{project.sodar_uuid}_lock".encode()
        redis_conn = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return redis_conn.get(lock_db_id) is not None
