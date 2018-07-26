from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static

# Projectroles dependency
from projectroles.plugins import BackendPluginPoint

from .api import IrodsAPI


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'omics_irods'

    #: Title (used in templates)
    title = 'Omics iRODS Service'

    #: FontAwesome icon ID string
    icon = 'cloud-download'

    #: Description string
    description = 'iRODS backend for queries via the Omics iRODS REST Service'

    #: URL of optional javascript file to be included
    javascript_url = static('irodsbackend/js/irodsbackend.js')

    def get_api(self):
        """Return API entry point object."""
        try:
            return IrodsAPI()

        except Exception as ex:
            print(str(ex))
            return None     # TODO: log exception
