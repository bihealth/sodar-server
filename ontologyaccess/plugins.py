"""Plugins for the ontologyaccess app"""

# Projectroles dependency
from projectroles.plugins import SiteAppPluginPoint

# from ontologyaccess.models import BioOntology
from ontologyaccess.urls import urlpatterns


class SiteAppPlugin(SiteAppPluginPoint):
    """Projectroles plugin for registering the app"""

    #: Name (slug-safe, used in URLs)
    name = 'ontologyaccess'

    #: Title (used in templates)
    title = 'Ontology Access'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    #: FontAwesome icon ID string
    icon = 'tags'

    #: Description string
    description = 'Bio-ontology access and management'

    #: Entry point URL ID
    entry_point_url_id = 'ontologyaccess:list'

    #: Required permission for displaying the app
    app_permission = 'ontologyaccess.view_list'
