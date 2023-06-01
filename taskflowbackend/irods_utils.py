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


def get_batch_role(project, user_name):
    """
    Return role dict for use with e.g. the role_update_irods_batch flow.

    :param project: Project object
    :param user_name: String
    :return: Dict
    """
    return {'project_uuid': str(project.sodar_uuid), 'user_name': user_name}
