"""iRODS utilities for the taskflowbackend app"""


def get_batch_role(project, user_name):
    """
    Return role dict for use with e.g. the role_update_irods_batch flow.

    :param project: Project object
    :param user_name: String
    :return: Dict
    """
    return {'project_uuid': str(project.sodar_uuid), 'user_name': user_name}
