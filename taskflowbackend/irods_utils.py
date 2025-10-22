"""iRODS utilities for the taskflowbackend app"""

from typing import Optional, Union

from django.contrib.auth import get_user_model

# Projectroles dependency
from projectroles.models import Project


User = get_user_model()


def get_flow_role(
    project: Project, user: Union[str, User], role_rank: Optional[int] = None
) -> dict:
    """
    Return role dict for taskflows performing role modification.

    :param project: Project object
    :param user: User object or username string
    :param role_rank: String or None
    :return: Dict
    """
    return {
        'project_uuid': str(project.sodar_uuid),
        'user_name': user if isinstance(user, str) else user.username,
        'role_rank': role_rank,
    }
