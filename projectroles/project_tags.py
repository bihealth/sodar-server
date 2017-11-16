"""Functions for project tagging/starring in the projectroles app"""
# NOTE: This can be expanded to include other types of tags later on

from .models import ProjectUserTag, PROJECT_TAG_STARRED


def get_tag_state(project, user, name=PROJECT_TAG_STARRED):
    """
    Get current starring status of a project/user
    :param project: Project object
    :param user: User object
    :param name: Tag name (string)
    :return: Boolean
    """
    try:
        ProjectUserTag.objects.get(
            project=project, user=user, name=name)
        return True

    except ProjectUserTag.DoesNotExist:
        return False


def set_tag_state(project, user, name=PROJECT_TAG_STARRED):
    """
    Set starring status of a project/user to true/false depending on the current
    status
    :param project: Project object
    :param user: User object
    :param name: Tag name (string)
    """
    try:
        tag = ProjectUserTag.objects.get(
            project=project, user=user, name=name)
        tag.delete()

    except ProjectUserTag.DoesNotExist:
        tag = ProjectUserTag(
            project=project,
            user=user,
            name=name)
        tag.save()


def remove_tag(project, user, name=PROJECT_TAG_STARRED):
    """
    Remove ProjectUserTag object from project and user if it exists
    :param project: Project object
    :param user: User object
    :param name: Tag name (string)
    """
    try:
        ProjectUserTag.objects.get(
            project=project, user=user, name=name).delete()

    except ProjectUserTag.DoesNotExist:
        pass
