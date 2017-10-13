

# Projectroles dependency
from projectroles.plugins import ProjectAppPluginPoint, BackendPluginPoint

from .api import TimelineAPI
from .urls import urlpatterns
from .models import ProjectEvent


class ProjectAppPlugin(ProjectAppPluginPoint):
    """Plugin for registering app with Projectroles"""

    # Properties required by django-plugins ------------------------------

    #: Name (slug-safe, used in URLs)
    name = 'timeline'

    #: Title (used in templates)
    title = 'Timeline'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    # Properties defined in ProjectAppPluginPoint -----------------------

    #: Project settings definition
    project_settings = {}

    #: FontAwesome icon ID string
    icon = 'clock-o'

    #: Entry point URL ID (must take project pk as "project" argument)
    entry_point_url_id = 'project_timeline'

    #: Description string
    description = 'Timeline of project events'

    #: Required permission for accessing the app
    app_permission = 'timeline.view_timeline'

    #: App card template for the project details page
    details_template = 'timeline/_details_card.html'

    #: App card title for the project details page
    details_title = 'Project Timeline Overview'

    #: App card position
    details_position = 40

    def get_info(self, pk):
        """
        Return app information to be displayed on the project details page
        :param pk: Project ID
        :returns: List of tuples
        """
        return [(
            'Event Count', ProjectEvent.objects.filter(project=pk).count())]

    def get_taskflow_sync_data(self):
        """
        Return data for syncing taskflow operations
        :return: List of dicts or None.
        """
        return None


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'timeline_backend'

    #: Title (used in templates)
    title = 'Timeline Backend'

    #: FontAwesome icon ID string
    icon = 'clock-o'

    #: Description string
    description = 'Timeline backend for modifying events'

    def get_api(self):
        """Return API entry point object."""
        return TimelineAPI()
