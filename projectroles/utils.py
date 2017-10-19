import datetime as dt
import random
import string

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from .models import Project, ProjectSetting
from .plugins import ProjectAppPluginPoint, BackendPluginPoint


# Settings
SECRET_LENGTH = settings.PROJECTROLES_SECRET_LENGTH
INVITE_EXPIRY_DAYS = settings.PROJECTROLES_INVITE_EXPIRY_DAYS


def get_user_display_name(user, inc_user=False):
    """
    Return full name of user for displaying
    :param user: User object
    :param inc_user: Include user name if true (boolean)
    :return: String
    """
    if user.name != '':
        return user.name + (' (' + user.username + ')' if inc_user else '')

    # If full name can't be found, return username
    return user.username


def save_default_project_settings(project):
    """
    Save default project settings for project.
    :param project: Project in which settings will be saved
    """
    plugins = [p for p in ProjectAppPluginPoint.get_plugins() if p.is_active()]
    project = Project.objects.get(pk=project.pk)

    for plugin in [p for p in plugins if hasattr(p, 'project_settings')]:
        for set_key in plugin.project_settings.keys():
            try:
                ProjectSetting.objects.get(
                    project=project,
                    app_plugin=plugin.get_model(),
                    name=set_key)

            except ProjectSetting.DoesNotExist:
                set_def = plugin.project_settings[set_key]
                setting = ProjectSetting(
                    project=project,
                    app_plugin=plugin.get_model(),
                    name=set_key,
                    type=set_def['type'],
                    value=set_def['default'])
                setting.save()


def build_secret(length=SECRET_LENGTH):
    """
    Return secret string for e.g. public URLs.
    :param length: Length of string if specified, default value from settings
    :return: Randomized secret (string)
    """
    length = int(length) if int(length) <= 255 else 255

    return ''.join(random.SystemRandom().choice(
        string.ascii_lowercase + string.digits) for x in range(length))


def build_invite_url(invite, request):
    """
    Return invite URL for a project invitation.
    :param invite: ProjectInvite object
    :param request: HTTP request
    :return: URL (string)
    """
    return request.build_absolute_uri(reverse(
        'role_invite_accept',
        kwargs={'secret': invite.secret}))


def get_expiry_date():
    """
    Return expiry date based on current date + INVITE_EXPIRY_DAYS
    :return: DateTime object
    """
    return timezone.now() + dt.timedelta(
        days=INVITE_EXPIRY_DAYS)


def get_app_names():
    """Return list of names for local apps"""

    return sorted([
        a.split('.')[0] for a in settings.LOCAL_APPS if
        a.split('.')[0] != 'omics_data_access'])


def get_project_setting(project, app_name, setting_name):
    """
    Return setting value for a project and an app.
    :param project: Project object
    :param app_name: App name (string, must correspond to "name" in app plugin)
    :param setting_name: Setting name (string)
    :return: String or None
    """
    return ProjectSetting.objects.get_setting_value(
        project, app_name, setting_name)
