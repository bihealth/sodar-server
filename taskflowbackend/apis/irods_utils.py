import logging
import random
import string

from irods.models import UserGroup

from django.conf import settings


logger = logging.getLogger('sodar_taskflow')


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT
PERMANENT_USERS = settings.TASKFLOW_TEST_PERMANENT_USERS


def cleanup_irods_data(irods, verbose=True):
    """Cleanup data from iRODS. Used in debugging/testing."""
    # TODO: Remove stuff from user folders
    # TODO: Remove stuff from trash
    # Remove project folders
    try:
        irods.collections.remove(PROJECT_ROOT, recurse=True, force=True)
        if verbose:
            logger.info('Removed project root: {}'.format(PROJECT_ROOT))
    except Exception:
        pass  # This is OK, the root just wasn't there
    # Remove created user groups and users
    # NOTE: user_groups.remove does both
    for g in irods.query(UserGroup).all():
        if g[UserGroup.name] not in PERMANENT_USERS:
            irods.user_groups.remove(user_name=g[UserGroup.name])
            if verbose:
                logger.info('Removed user: {}'.format(g[UserGroup.name]))


def get_trash_path(path, add_rand=False):
    """
    Return base trash path for an object without a versioning suffix. Adds
    random characters if add_rand is set True (for revert operations).
    """
    trash_path = (
        '/'
        + path.split('/')[1]
        + '/trash/'
        + '/'.join([x for x in path.split('/')[2:]])
    )
    if add_rand:
        trash_path += '_' + ''.join(
            random.SystemRandom().choice(string.ascii_lowercase + string.digits)
            for _ in range(16)
        )
    return trash_path


def get_subcoll_obj_paths(coll):
    """
    Return paths to all files within collection and its subcollections
    recursively.
    """
    ret = []
    for sub_coll in coll.subcollections:
        ret += get_subcoll_obj_paths(sub_coll)
    for data_obj in coll.data_objects:
        ret.append(data_obj.path)
    return ret


def get_subcoll_paths(coll):
    """Return paths to all subcollections within collection recursively"""
    ret = []
    for sub_coll in coll.subcollections:
        ret.append(sub_coll.path)
        ret += get_subcoll_paths(sub_coll)
    return ret
