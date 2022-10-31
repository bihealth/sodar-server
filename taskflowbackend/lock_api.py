"""Project locking API"""

import logging
import time
import uuid

from tooz import coordination

from django.conf import settings


LOCK_ENABLED = settings.TASKFLOW_LOCK_ENABLED
LOCK_RETRY_COUNT = settings.TASKFLOW_LOCK_RETRY_COUNT
LOCK_RETRY_INTERVAL = settings.TASKFLOW_LOCK_RETRY_INTERVAL


logger = logging.getLogger('__name__')


class LockAcquireException(Exception):
    """Project lock acquiring exception"""


class ProjectLockAPI:
    """Project locking and unlocking API"""

    @classmethod
    def _log_status(cls, lock, unlock=False, failed=False):
        msg = '{} {} for project {}'.format(
            'Unlock' if unlock else 'Lock',
            'FAILED' if failed else 'OK',
            lock.name.split('_')[2],
        )
        logger.error(msg) if failed else logger.info(msg)

    @classmethod
    def get_coordinator(cls):
        """Return a Tooz coordinator object"""
        host_id = 'sodar_{}'.format(uuid.uuid4())
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
            logger.error('Tooz connection error: {}'.format(ex))
        return None

    @classmethod
    def acquire(
        cls,
        lock,
        retry_count=LOCK_RETRY_COUNT,
        retry_interval=LOCK_RETRY_INTERVAL,
    ):
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
        raise LockAcquireException('Project is locked by another operation')

    @classmethod
    def release(cls, lock):
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
