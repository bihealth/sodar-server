# Projectroles dependency
from projectroles.plugins import SiteAppPluginPoint


from irodsinfo.urls import urlpatterns


class SiteAppPlugin(SiteAppPluginPoint):
    """Projectroles plugin for registering the app"""

    #: Name (slug-safe, used in URLs)
    name = 'irodsinfo'

    #: Title (used in templates)
    title = 'iRODS Info'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    #: Iconify icon
    icon = 'mdi:lifebuoy'

    #: Description string
    description = 'iRODS Information and Configuration'

    #: Entry point URL ID
    entry_point_url_id = 'irodsinfo:info'

    #: Required permission for displaying the app
    app_permission = 'irodsinfo.view_info'

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = ['IRODS_ENV_CLIENT']
