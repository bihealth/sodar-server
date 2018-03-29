"""Plugin point definitions for other apps which depend on projectroles"""

from django.conf import settings

from djangoplugins.point import PluginPoint


# From djangoplugins
ENABLED = 0
DISABLED = 1
REMOVED = 2


class ProjectAppPluginPoint(PluginPoint):
    """Projectroles plugin point for registering project specific apps"""

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

    #: Entry point URL ID (must take project omics_uuid as "project" argument)
    # TODO: Implement this in your app plugin
    entry_point_url_id = 'home'

    #: Description string
    # TODO: Implement this in your app plugin
    description = 'TODO: Write a description for your plugin'

    #: Required permission for accessing the app
    # TODO: Implement this in your app plugin (can be None)
    app_permission = None

    #: Enable or disable general search from project title bar
    # TODO: Implement this in your app plugin
    search_enable = False

    #: List of search object types for the app
    # TODO: Implement this in your app plugin
    search_types = []

    #: Search results template
    # TODO: Implement this in your app plugin
    search_template = None

    #: App card title for the main search page
    # TODO: Implement this in your app plugin
    search_title = None

    #: App card template for the project details page
    # TODO: Implement this in your app plugin
    details_template = None

    #: App card title for the project details page
    # TODO: Implement this in your app plugin (can be None)
    details_title = None

    #: Position in plugin ordering
    # TODO: Implement this in your app plugin (must be an integer)
    plugin_ordering = 50

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

    def get_object(self, model, uuid):
        """
        Return object based on the model class string and the object's UUID.
        :param model: Object model class
        :param uuid: omics_uuid of the referred object
        :return: Model object or None if not found
        :raise: NameError if model corresponding to class_str is not found
        """
        # NOTE: we raise NameError because it shouldn't happen (missing import)
        try:
            return model.objects.get(omics_uuid=uuid)

        except model.DoesNotExist:
            return None

    def get_object_link(self, model_str, uuid):
        """
        Return URL for referring to a object used by the app, along with a
        label to be shown to the user for linking.
        :param model_str: Object class (string)
        :param uuid: omics_uuid of the referred object
        :return: Dict or None if not found
        """
        obj = self.get_object(eval(model_str), uuid)

        if not obj:
            return None

        # TODO: Implement this in your app plugin
        return None


class BackendPluginPoint(PluginPoint):
    """Projectroles plugin point for registering backend apps"""

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


class SiteAppPluginPoint(PluginPoint):
    """Projectroles plugin point for registering site-wide apps"""

    #: FontAwesome icon ID string
    # TODO: Implement this in your site app plugin
    icon = 'question-circle-o'

    #: Description string
    # TODO: Implement this in your site app plugin
    description = 'TODO: Write a description for your plugin'

    #: Entry point URL ID
    # TODO: Implement this in your app plugin
    entry_point_url_id = 'home'

    #: Required permission for displaying the app
    # TODO: Implement this in your site app plugin (can be None)
    app_permission = None

    def get_messages(self, user=None):
        """
        Return a list of messages to be shown to users.
        :param user: User object (optional)
        :return: List of dicts or and empty list if no messages
        """
        # TODO: Implement this in your site app plugin

        '''
        # Output example:
        return [{
            'content': 'Message content in here, can contain html',
            'color': 'info',        # Corresponds to bg-* in Bootstrap
            'dismissable': True     # False for non-dismissable
        }]
        '''
        return []


def get_active_plugins(plugin_type='project_app'):
    """
    Return active plugins of a specific type
    :param plugin_type: 'project_app', 'site_app' or 'backend' (string)
    :return: List or None
    :raise: ValueError if plugin_type is not recognized
    """
    # TODO: Replace code doing this same thing in views
    if plugin_type == 'project_app':
        plugins = ProjectAppPluginPoint.get_plugins()

    elif plugin_type == 'backend':
        plugins = BackendPluginPoint.get_plugins()

    elif plugin_type == 'site_app':
        plugins = SiteAppPluginPoint.get_plugins()

    else:
        raise ValueError('Invalid value for plugin_type')

    if plugins:
        return sorted([
            p for p in plugins if (p.is_active() and (
                plugin_type in ['project_app', 'site_app'] or
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


def get_app_plugin(plugin_name):
    """
    Return active app plugin
    :param plugin_name: Plugin name (string)
    :return: ProjectAppPlugin object or None if not found
    """
    try:
        return ProjectAppPluginPoint.get_plugin(plugin_name)

    except ProjectAppPluginPoint.DoesNotExist:
        return None


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
