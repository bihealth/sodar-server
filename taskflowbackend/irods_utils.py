"""iRODS utilities for the taskflowbackend app"""


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
