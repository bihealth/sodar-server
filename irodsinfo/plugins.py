from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.plugins import SiteAppPluginPoint


from .urls import urlpatterns


class SiteAppPlugin(SiteAppPluginPoint):
    """Projectroles plugin for registering the app"""

    #: Name (slug-safe, used in URLs)
    name = 'irodsinfo'

    #: Title (used in templates)
    title = 'iRODS Info'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    #: FontAwesome icon ID string
    icon = 'support'

    #: Description string
    description = 'iRODS Information and Configuration'

    #: Entry point URL ID
    entry_point_url_id = 'irodsinfo:info'

    #: Required permission for displaying the app
    app_permission = 'irodsinfo.view_info'
