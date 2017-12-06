"""Helper functions for Project settings"""

from projectroles.models import ProjectSetting, PROJECT_SETTING_TYPES, Project
from projectroles.plugins import ProjectAppPluginPoint, get_app_plugin


def get_project_setting(project, app_name, setting_name):
    """
    Return setting value for a project and an app. If not set, return default.
    :param project: Project object
    :param app_name: App name (string, must correspond to "name" in app plugin)
    :param setting_name: Setting name (string)
    :return: String or None
    """
    try:
        return ProjectSetting.objects.get_setting_value(
            project, app_name, setting_name)

    except ProjectSetting.DoesNotExist:
        # Get default
        app_plugin = get_app_plugin(app_name)

        if (app_plugin.project_settings and
                setting_name in app_plugin.project_settings):
            return app_plugin.project_settings[setting_name]['default']

        return None


def set_project_setting(project, app_name, setting_name, value, validate=True):
    """
    Set value of an existing project settings variable. Creates the object if
    not found.
    :param project: Project object
    :param app_name: App name (string, must correspond to "name" in app plugin)
    :param setting_name: Setting name (string)
    :param value: Value to be set
    :param validate: Validate value (bool, default=True)
    :return: True if changed, False if not changed
    :raise: ValueError if validating and value is not accepted for setting type
    """
    try:
        setting = ProjectSetting.objects.get(
            project=project, app_plugin__name=app_name, name=setting_name)

        if setting.value == value:
            return False

        if validate:
            validate_project_setting(setting.type, value)

        setting.value = value
        setting.save()
        return True

    except ProjectSetting.DoesNotExist:
        app_plugin = ProjectAppPluginPoint.get_plugin(name=app_name)
        s_type = app_plugin.project_settings[setting_name]['type']

        if validate:
            validate_project_setting(s_type, value)

        setting = ProjectSetting(
            app_plugin=app_plugin.get_model(),
            project=project,
            name=setting_name,
            type=s_type,
            value=value)
        setting.save()
        return True


def validate_project_setting(setting_type, setting_value):
    """
    Validate setting value according to its type
    :param setting_type: Setting type
    :param setting_value: Setting value
    :raise: ValueError if setting_type or setting_value is invalid
    """
    if setting_type not in PROJECT_SETTING_TYPES:
        raise ValueError('Invalid setting type')

    if setting_type == 'BOOLEAN' and not isinstance(setting_value, bool):
        raise ValueError('Please enter a valid boolean value')

    if setting_type == 'INTEGER' and (
            not isinstance(setting_value, int) or
            not str(setting_value).isdigit()):
        raise ValueError('Please enter a valid integer value')

    return True
