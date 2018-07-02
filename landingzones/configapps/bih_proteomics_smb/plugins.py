from landingzones.plugins import LandingZoneConfigPluginPoint

from landingzones.configapps.bih_proteomics_smb.urls import urlpatterns


class LandingZoneConfigPlugin(LandingZoneConfigPluginPoint):
    """Plugin for BIH Proteomics SMB landing zone configuration sub-app"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'landingzones_config_bih_proteomics_smb'

    #: Title (used in templates)
    title = 'Landing Zones BIH Proteomics SMB Config App'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    # Properties defined in LandingZoneConfigPluginPoint ------------------

    #: Configuration name (used to identify plugin by configuration string)
    config_name = 'bih_proteomics_smb'

    #: Configuration display name (to be visible in GUI)
    config_display_name = 'BIH Proteomics SMB Server'

    #: Description string
    description = 'BIH Proteomics SMB file server config plugin'

    #: Additional zone menu items
    menu_items = [
        {
        'label': 'Generate/Refresh Ticket',
        'icon': 'key',
        'url_name': 'landingzones.configapps.bih_proteomics_smb:ticket_get'}
     ]

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None
