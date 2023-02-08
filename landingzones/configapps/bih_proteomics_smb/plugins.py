import logging

from datetime import datetime as dt

# Projectroles dependency
from projectroles.plugins import get_backend_api

from landingzones.configapps.bih_proteomics_smb.urls import urlpatterns
from landingzones.plugins import LandingZoneConfigPluginPoint


logger = logging.getLogger(__name__)


# Local constants
TICKET_DATE_FORMAT = '%Y-%m-%d.%H:%M:%S'


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
            'icon': 'mdi:key-variant',
            'url_name': 'landingzones.configapps.bih_proteomics_smb:ticket_get',
        }
    ]

    #: Fields from LandingZone.config_data to be displayed in zone list API
    api_config_data = ['ticket', 'ticket_expire_date']

    #: Required permission for accessing the plugin
    # TODO: TBD: Do we need this?
    permission = None

    def get_extra_flow_data(self, zone, flow_name):
        """
        Return extra zone data parameters.

        :param zone: LandingZone object
        :param flow_name: Name of flow (string)
        :return: dict or None
        """
        return {'script_user': 'bih_proteomics_smb'}  # Workaround for #297

    def cleanup_zone(self, zone):
        """
        Perform actions before landing zone deletion.

        :param zone: LandingZone object
        """
        irods_backend = get_backend_api('omics_irods')
        if not irods_backend:
            return
        if (
            'ticket' in zone.config_data
            and dt.strptime(
                zone.config_data['ticket_expire_date'], TICKET_DATE_FORMAT
            )
            > dt.now()
        ):
            try:
                with irods_backend.get_session() as irods:
                    irods_backend.delete_ticket(
                        irods, zone.config_data['ticket']
                    )
            except Exception as ex:
                logger.error(
                    'Error deleting ticket "{}": {}'.format(
                        zone.config_data['ticket'], ex
                    )
                )
