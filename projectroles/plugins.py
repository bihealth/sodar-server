"""Plugin point definitions for other apps which depend on projectroles"""

from django.conf import settings

from djangoplugins.point import PluginPoint


# From djangoplugins
ENABLED = 0
DISABLED = 1
REMOVED = 2


class ProjectAppPluginPoint(PluginPoint):
    """Projectroles plugin points for registering apps"""

    #: App URLs (will be included in settings by djangoplugins)
    urls = []

    #: Project settings definition
    # TODO: Define project specific settings in your app plugin, example below
    project_settings = {
        'example_setting': {
            'type': 'STRING',   # 'STRING'/'INTEGER'/'BOOLEAN' (TBD: more?)
            'default': 'example',
            'description': 'Example setting'    # Optional
        }
    }

    #: FontAwesome icon ID string
    # TODO: Implement this in your app plugin
    icon = 'question-circle-o'

    #: Entry point URL ID (must take project pk as "project" argument)
    # TODO: Implement this in your app plugin
    entry_point_url_id = 'home'

    #: Description string
    # TODO: Implement this in your app plugin
    description = 'TODO: Write a description for your plugin'

    #: Required permission for accessing the app
    # TODO: Implement this in your app plugin (can be None)
    app_permission = None

    #: App card template for the project details page
    # TODO: Implement this in your app plugin (if None, get_info() is used)
    details_template = None

    #: App card title for the project details page
    # TODO: Implement this in your app plugin (can be None)
    details_title = None

    #: App card position
    # TODO: Implement this in your app plugin (should be an integer)
    details_position = 50

    def get_info(self, pk):
        """
        Return app information to be displayed on the project details page
        :param pk: Project ID
        :return: List of tuples
        """
        # TODO: Implement this in your app plugin
        return [('TODO', 'Implement get_info() in the app plugin!')]

    # NOTE: For projectroles, this is implemented directly in synctaskflow
    def get_taskflow_sync_data(self):
        """
        Return data for syncing taskflow operations
        :return: List of dicts or None.
        """

        '''
        Return data format:
        [
            {
                'flow_name': ''
                'project_pk: ''
                'flow_data': {}
            }
        ]
        '''
        # TODO: Implement this in your app plugin
        return None

    def get_object(self, model, pk):
        """
        Return object based on the model class string and the object's pk.
        :param model: Object model class
        :param pk: Pk of the referred object
        :return: Model object or None if not found
        :raise: NameError if model corresponding to class_str is not found
        """
        # NOTE: we raise NameError because it shouldn't happen (missing import)
        try:
            return model.objects.get(pk=pk)

        except model.DoesNotExist:
            return None

    def get_object_link(self, model_str, pk):
        """
        Return URL for referring to a object used by the app, along with a
        label to be shown to the user for linking.
        :param model_str: Object class (string)
        :param pk: Pk of the referred object
        :return: Dict or None if not found
        """
        obj = self.get_object(eval(model_str), pk)

        if not obj:
            return None

        # TODO: Implement this in your app plugin
        return None


class BackendPluginPoint(PluginPoint):
    """Projectroles plugin points for registering backend apps"""

    #: FontAwesome icon ID string
    # TODO: Implement this in your backend plugin
    icon = 'question-circle-o'

    #: Description string
    # TODO: Implement this in your backend plugin
    description = 'TODO: Write a description for your plugin'

    def get_api(self):
        """Return API entry point object."""
        # TODO: Implement this in your backend plugin
        raise NotImplementedError


def get_active_plugins(plugin_type='app'):
    """
    Return active plugins of a specific type
    :param plugin_type: 'app' or 'backend' (string)
    :return: List or None
    """
    # TODO: Replace code doing this same thing in views
    if plugin_type == 'app':
        plugins = ProjectAppPluginPoint.get_plugins()

    else:
        plugins = BackendPluginPoint.get_plugins()

    if plugins:
        return sorted([
            p for p in plugins if (p.is_active() and (
                plugin_type == 'app' or
                p.name in settings.ENABLED_BACKEND_PLUGINS))],
            key=lambda x: x.name)

    return None


def change_plugin_status(name, status, plugin_type='app'):
    """Disable selected plugin in the database"""
    # NOTE: Used to forge plugin to a specific status for e.g. testing
    if plugin_type == 'app':
        plugin = ProjectAppPluginPoint.get_plugin(name)

    else:
        plugin = BackendPluginPoint.get_plugin(name)

    if plugin:
        plugin = plugin.get_model()
        plugin.status = status
        plugin.save()


def get_backend_api(plugin_name, force=False):
    """
    Return backend API object
    :param plugin_name: Name of plugin
    :param force: Return plugin regardless of status in ENABLED_BACKEND_PLUGINS
    :return: Plugin object or None if not found
    """
    if plugin_name in settings.ENABLED_BACKEND_PLUGINS or force:
        try:
            plugin = BackendPluginPoint.get_plugin(plugin_name)
            return plugin.get_api() if plugin.is_active() else None

        except Exception as ex:
            pass

    return None
