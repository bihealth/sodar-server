from django.conf import settings

# Projectroles dependency
from projectroles.plugins import BackendPluginPoint

from .api import TaskflowAPI


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'taskflow'

    #: Title (used in templates)
    title = 'Taskflow'

    #: FontAwesome icon ID string
    icon = 'database'

    #: Description string
    description = 'Taskflow backend for iRODS and Postgres transactions'

    def get_api(self):
        """Return API entry point object."""
        return TaskflowAPI()
