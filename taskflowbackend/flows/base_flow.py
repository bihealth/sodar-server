import logging

from typing import Any, Optional

from taskflow import engines
from taskflow.patterns import linear_flow as lf

from django.conf import settings

# Projectroles dependency
from projectroles.models import Project, SODARUser

from taskflowbackend.tasks.base_task import BaseTask, ForceFailException


logger = logging.getLogger('taskflowbackend.flows')


class BaseLinearFlow:
    """Base class for linear flows used for task queues"""

    def __init__(
        self,
        irods_backend: Any,
        project: Project,
        user: Optional[SODARUser],
        flow_name: str,
        flow_data: Optional[dict],
        async_mode: bool = False,
        tl_event: Any = None,
    ):
        self.irods_backend = irods_backend
        self.irods = irods_backend.get_session_obj()
        self.irods.connection_timeout = settings.TASKFLOW_IRODS_CONN_TIMEOUT
        self.project = project
        self.user = user
        self.flow_name = flow_name
        self.flow_data = flow_data
        self.required_fields = []  # For validation
        self.tl_event = tl_event
        self.request_mode = 'async' if async_mode else 'sync'
        self.supported_modes = ['sync']  # "sync" and/or "async", default=sync
        self.require_lock = True  # Require project lock by default
        self.flow = lf.Flow(flow_name)

    def validate(self) -> bool:
        """
        Method for validating flow parameters. Returns True/False based on
        validation success. Add required kwargs in the flow implementation and
        call this. Can be extended with further validation.
        """
        if self.request_mode not in self.supported_modes:
            raise TypeError(f'Request mode "{self.request_mode}" not supported')
        for k in self.required_fields:
            if k not in self.flow_data or self.flow_data[k] == '':
                raise TypeError(f'Missing or invalid argument: "{k}"')
        return True

    def add_task(self, task: BaseTask):
        """Add task into the flow"""
        self.flow.add(task)

    def build(self, force_fail: bool = False):
        """
        Build linear flow to be executed for one project. Override this in
        the flow implementation.

        :param force_fail: Force failure of flow for testing if True (bool)
        """
        # Add tasks to self.flow here with self.flow.add()
        # Add force_fail=force_fail to last add() for testing rollback
        msg = 'Function build() not implemented!'
        logger.error(msg)
        raise NotImplementedError(msg)

    def run(self, verbose: bool = True) -> bool:
        """
        Run the flow. Returns True or False depending on success. If False,
        the flow was rolled back. Also handle project locking and unlocking.

        :param verbose: Enable verbose logging (bool)
        :return: Bool
        """
        if verbose:
            logger.info(f'Running flow "{self.flow.name}"')
        engine = engines.load(self.flow, engine='serial')
        try:
            engine.run()
            # TODO: Better reporting of failed jobs?
            result = (
                True
                if (
                    engine.statistics['incomplete'] == 0
                    and engine.statistics['discarded_failures'] == 0
                )
                else False
            )
            if verbose:
                logger.info(
                    'Flow "{}" finished: {} ({} completed, {} incomplete, '
                    '{} discarded)'.format(
                        self.flow.name,
                        'OK' if result is True else 'ROLLBACK',
                        engine.statistics['completed'],
                        engine.statistics['incomplete'],
                        engine.statistics['discarded_failures'],
                    )
                )
            return result
        except ForceFailException:
            return False
        except Exception as ex:
            logger.error(f'Exception in run_flow(): {ex}')
            raise ex
        finally:
            self.irods.cleanup()
