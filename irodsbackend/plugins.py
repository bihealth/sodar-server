from django.conf import settings

from django.template.defaultfilters import filesizeformat

# Projectroles dependency
from projectroles.plugins import BackendPluginPoint

from irodsbackend.api import IrodsAPI


# Local constants
IRODS_INFO_SETTINGS = [
    'ENABLE_IRODS',
    'IRODS_CERT_PATH',
    'IRODS_ENV_BACKEND',
    'IRODS_ENV_DEFAULT',
    'IRODS_HOST',
    'IRODS_LANDING_ZONE_COLL',
    'IRODS_PORT',
    'IRODS_QUERY_BATCH_SIZE',
    'IRODS_ROOT_PATH',
    'IRODS_SAMPLE_COLL',
    'IRODS_SODAR_AUTH',
    'IRODS_USER',
    'IRODS_WEBDAV_ENABLED',
    'IRODS_WEBDAV_URL',
    'IRODS_WEBDAV_URL_ANON',
    'IRODS_WEBDAV_URL_ANON_TMPL',
    'IRODS_WEBDAV_USER_ANON',
    'IRODS_ZONE',
    'IRODSBACKEND_STATUS_INTERVAL',
]


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'omics_irods'

    #: Title (used in templates)
    title = 'iRODS Backend'

    #: FontAwesome icon ID string
    icon = 'mdi:database-search'

    #: Description string
    description = 'iRODS backend for interfacing with the SODAR iRODS server'

    #: URL of optional javascript file to be included
    javascript_url = 'irodsbackend/js/irodsbackend.js'

    #: URL of optional css file to be included
    css_url = 'irodsbackend/css/irodsbackend.css'

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = IRODS_INFO_SETTINGS

    def get_api(self, **kwargs):
        """Return API entry point object."""
        # Only init API if iRODS is enabled or in no connection mode
        if settings.ENABLE_IRODS or kwargs.get('conn') is False:
            try:
                return IrodsAPI(**kwargs)
            except Exception:
                pass  # Exception logged in constructor, return None

    def get_statistics(self):
        if (
            not settings.ENABLE_IRODS
            or 'omics_irods' not in settings.ENABLED_BACKEND_PLUGINS
        ):
            return {}

        irods_api = IrodsAPI()
        try:
            project_stats = irods_api.get_object_stats(
                irods_api.get_projects_path()
            )
        except Exception:
            return {}
        return {
            'irods_data_size': {
                'label': 'Project Data in iRODS',
                'value': filesizeformat(project_stats['total_size']),
                'description': 'Total file size including sample repositories '
                'and landing zones.',
            }
        }
