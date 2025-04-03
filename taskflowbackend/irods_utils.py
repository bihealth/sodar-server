"""iRODS utilities for the taskflowbackend app"""


def get_flow_role(project, user, role_rank=None):
    """
    Return role dict for taskflows performing role modification.

    :param project: Project object
    :param user: SODARUser object or username string
    :param role_rank: String or None
    :return: Dict
    """
    return {
        'project_uuid': str(project.sodar_uuid),
        'user_name': user if isinstance(user, str) else user.username,
        'role_rank': role_rank,
    }
