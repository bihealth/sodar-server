from django.conf import settings

# from django.contrib.staticfiles.templatetags.staticfiles import static
from django.template.defaultfilters import filesizeformat

# Projectroles dependency
from projectroles.plugins import BackendPluginPoint

from irodsbackend.api import IrodsAPI


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'omics_irods'

    #: Title (used in templates)
    title = 'iRODS Backend'

    #: FontAwesome icon ID string
    icon = 'cloud-download'

    #: Description string
    description = 'iRODS backend for interfacing with the SODAR iRODS server'

    #: URL of optional javascript file to be included
    javascript_url = 'irodsbackend/js/irodsbackend.js'

    #: URL of optional css file to be included
    css_url = 'irodsbackend/css/irodsbackend.css'

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
