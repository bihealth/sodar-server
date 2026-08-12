"""Project locking API"""

import logging
import time
import uuid

from typing import Optional

from tooz import coordination
from tooz.locking import Lock

from django.conf import settings


LOCK_ENABLED = settings.TASKFLOW_LOCK_ENABLED
LOCK_RETRY_COUNT = settings.TASKFLOW_LOCK_RETRY_COUNT
LOCK_RETRY_INTERVAL = settings.TASKFLOW_LOCK_RETRY_INTERVAL
PROJECT_LOCKED_MSG = 'Project is locked by another operation'


logger = logging.getLogger(__name__)


class LockAcquireException(Exception):
    """Project lock acquiring exception"""


class ProjectLockAPI:
    """Project locking and unlocking API"""

    @classmethod
    def _log_status(
        cls, lock: Lock, unlock: bool = False, failed: bool = False
    ):
        msg = '{} {} for project {}'.format(
            'Unlock' if unlock else 'Lock',
            'FAILED' if failed else 'OK',
            str(lock.name).split('_')[2],
        )
        logger.error(msg) if failed else logger.info(msg)

    @classmethod
    def get_coordinator(
        cls,
    ) -> Optional[coordination.CoordinationDriverWithExecutor]:
        """Return a Tooz coordinator object or None if failed"""
        host_id = f'sodar_{uuid.uuid4()}'
        try:
            coordinator = coordination.get_coordinator(
                backend_url=settings.REDIS_URL,
                member_id=host_id,
                socket_keepalive=True,
            )
            if coordinator:
                coordinator.start(start_heart=True)
                return coordinator
        except coordination.ToozConnectionError as ex:
            logger.error(f'Tooz connection error: {ex}')
        return None

    @classmethod
    def acquire(
        cls,
        lock: Lock,
        retry_count: int = LOCK_RETRY_COUNT,
        retry_interval: int = LOCK_RETRY_INTERVAL,
    ) -> bool:
        """
        Acquire project lock.

        :param lock: Tooz lock object
        :param retry_count: Times to retry if unsuccessful (int)
        :param retry_interval: Time in seconds to keep retrying (int)
        :return: Boolean
        """
        if not LOCK_ENABLED:
            return True
        acquired = lock.acquire(blocking=False)
        if acquired:
            cls._log_status(lock, unlock=False, failed=False)
            return True
        if retry_count > 0:
            for i in range(0, retry_count):
                acquired = lock.acquire(blocking=False)
                if acquired:
                    cls._log_status(lock, unlock=False, failed=False)
                    return True
                time.sleep(retry_interval)
        cls._log_status(lock, unlock=False, failed=True)
        raise LockAcquireException(PROJECT_LOCKED_MSG)

    @classmethod
    def release(cls, lock: Lock) -> bool:
        """
        Release project lock.

        :param lock: Tooz lock object
        """
        if not LOCK_ENABLED:
            return True
        released = lock.release()
        if released:
            cls._log_status(lock, unlock=True, failed=False)
            return True
        cls._log_status(lock, unlock=True, failed=True)
        return False
