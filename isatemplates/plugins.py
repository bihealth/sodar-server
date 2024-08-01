"""Plugins for the isatemplates app"""

from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import SiteAppPluginPoint, BackendPluginPoint

from isatemplates.api import ISATemplateAPI
from isatemplates.models import CookiecutterISATemplate
from isatemplates.urls import urlpatterns


# Local constants
ISATEMPLATES_INFO_SETTINGS = ['ISATEMPLATES_ENABLE_CUBI_TEMPLATES']


class SiteAppPlugin(SiteAppPluginPoint):
    """Projectroles plugin for registering the app"""

    #: Name (slug-safe, used in URLs)
    name = 'isatemplates'

    #: Title (used in templates)
    title = 'ISA-Tab Templates'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    #: Iconify icon
    icon = 'mdi:file-table'

    #: Description string
    description = 'Sample sheet ISA-Tab template management'

    #: Entry point URL ID
    entry_point_url_id = 'isatemplates:list'

    #: Required permission for displaying the app
    app_permission = 'isatemplates.view_list'

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = ISATEMPLATES_INFO_SETTINGS

    def get_object_link(self, model_str, uuid):
        """
        Return URL for referring to a object used by the app, along with a
        label to be shown to the user for linking.

        :param model_str: Object class (string)
        :param uuid: sodar_uuid of the referred object
        :return: Dict or None if not found
        """
        obj = self.get_object(eval(model_str), uuid)
        if not obj:
            return None
        if obj.__class__ == CookiecutterISATemplate:
            return {
                'url': reverse(
                    'isatemplates:detail',
                    kwargs={'cookiecutterisatemplate': obj.sodar_uuid},
                ),
                'label': obj.description,
            }

    def get_statistics(self):
        """
        Return app statistics as a dict. Should take the form of
        {id: {label, value, url (optional), description (optional)}}.

        :return: Dict
        """
        return {
            'custom_templates': {
                'label': 'Total Custom Templates',
                'value': CookiecutterISATemplate.objects.count(),
            },
            'active_templates': {
                'label': 'Active Custom Templates',
                'value': CookiecutterISATemplate.objects.filter(
                    active=True
                ).count(),
            },
        }


class BackendPlugin(BackendPluginPoint):
    """Plugin for registering backend app with Projectroles"""

    #: Name (slug-safe, used in URLs)
    name = 'isatemplates_backend'

    #: Title (used in templates)
    title = 'ISA-Tab Templates Backend'

    #: Iconify icon
    icon = 'mdi:file-table-outline'

    #: Description string
    description = 'Backend for ISA-Tab template retrieval'

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = None

    def get_api(self, **kwargs):
        """Return API entry point object"""
        return ISATemplateAPI()
