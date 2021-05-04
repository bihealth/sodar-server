"""Plugins for the ontologyaccess app"""

# Projectroles dependency
from projectroles.plugins import SiteAppPluginPoint, BackendPluginPoint

from ontologyaccess.api import OntologyAccessAPI
from ontologyaccess.models import OBOFormatOntology, OBOFormatOntologyTerm
from ontologyaccess.urls import urlpatterns


class SiteAppPlugin(SiteAppPluginPoint):
    """Projectroles plugin for registering the app"""

    #: Name (slug-safe, used in URLs)
    name = 'ontologyaccess'

    #: Title (used in templates)
    title = 'Ontology Access'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    #: Iconify icon
    icon = 'mdi:tag-multiple'

    #: Description string
    description = 'Bio-ontology access and management'

    #: Entry point URL ID
    entry_point_url_id = 'ontologyaccess:list'

    #: Required permission for displaying the app
    app_permission = 'ontologyaccess.view_list'


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'ontologyaccess_backend'

    #: Title (used in templates)
    title = 'Ontology Access Backend'

    #: FontAwesome icon ID string
    icon = 'mdi:tags'

    #: Description string
    description = 'Backend for imported ontology access'

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = ['ONTOLOGYACCESS_BULK_CREATE', 'ONTOLOGYACCESS_QUERY_LIMIT']

    def get_api(self, **kwargs):
        """Return API entry point object."""
        return OntologyAccessAPI()

    def get_statistics(self):
        return {
            'obo_ontology_count': {
                'label': 'OBO ontologies',
                'value': OBOFormatOntology.objects.count(),
            },
            'obo_term_count': {
                'label': 'OBO ontology terms',
                'value': OBOFormatOntologyTerm.objects.count(),
            },
        }
