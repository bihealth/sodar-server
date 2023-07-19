"""Plugins for the landingzones app"""

import logging

from django.urls import reverse

from djangoplugins.point import PluginPoint

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import (
    ProjectAppPluginPoint,
    ProjectModifyPluginMixin,
    get_backend_api,
)

# Samplesheets dependency
from samplesheets.models import Investigation, Assay

from landingzones.constants import (
    STATUS_ALLOW_UPDATE,
    ZONE_STATUS_MOVED,
    ZONE_STATUS_DELETED,
)
from landingzones.models import LandingZone
from landingzones.urls import urlpatterns
from landingzones.views import ZoneModifyMixin


logger = logging.getLogger(__name__)


# Local constants
LANDINGZONES_INFO_SETTINGS = [
    'LANDINGZONES_DISABLE_FOR_USERS',
    'LANDINGZONES_STATUS_INTERVAL',
    'LANDINGZONES_TRIGGER_FILE',
    'LANDINGZONES_TRIGGER_MOVE_INTERVAL',
]


# Landingzones project app plugin ----------------------------------------------


class ProjectAppPlugin(
    ZoneModifyMixin, ProjectModifyPluginMixin, ProjectAppPluginPoint
):
    """Plugin for registering app with Projectroles"""

    # Properties required by django-plugins ------------------------------

    #: Name (slug-safe, used in URLs)
    name = 'landingzones'

    #: Title (used in templates)
    title = 'Landing Zones'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    # Properties defined in ProjectAppPluginPoint -----------------------

    #: App settings definition
    app_settings = {
        'member_notify_move': {
            'scope': SODAR_CONSTANTS['APP_SETTING_SCOPE_PROJECT'],
            'type': 'BOOLEAN',
            'label': 'Notify members of landing zone uploads',
            'description': 'Notify project members via alerts and email if '
            'new files are uploaded from landing zones',
            'user_modifiable': True,
            'default': True,
        }
    }

    #: Iconify icon
    icon = 'mdi:briefcase-upload'

    #: Entry point URL ID (must take project sodar_uuid as "project" argument)
    entry_point_url_id = 'landingzones:list'

    #: Description string
    description = 'Management of sample data landing zones in iRODS'

    #: Required permission for accessing the app
    app_permission = 'landingzones.view_zone_own'

    #: Enable or disable general search from project title bar
    search_enable = False  # TODO: Enable once implemented

    #: List of search object types for the app
    search_types = ['zone', 'file']

    #: Search results template
    search_template = 'landingzones/_search_results.html'

    #: App card template for the project details page
    details_template = 'landingzones/_details_card.html'

    #: App card title for the project details page
    details_title = 'Landing Zones Overview'

    #: Position in plugin ordering
    plugin_ordering = 20

    #: Project list columns
    project_list_columns = {
        'zones': {
            'title': 'Zones',
            'width': 70,
            'description': None,
            'active': True,
            'ordering': 10,
            'align': 'center',
        }
    }

    #: Names of plugin specific Django settings to display in siteinfo
    info_settings = LANDINGZONES_INFO_SETTINGS

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
        if obj.__class__ == LandingZone and obj.status != ZONE_STATUS_MOVED:
            return {
                'url': reverse(
                    'landingzones:list',
                    kwargs={'project': obj.project.sodar_uuid},
                )
                + '#'
                + str(obj.sodar_uuid),
                'label': obj.title,
            }
        elif obj.__class__ == Assay:
            return {
                'url': reverse(
                    'samplesheets:project_sheets',
                    kwargs={'project': obj.get_project().sodar_uuid},
                )
                + '#/assay/'
                + str(obj.sodar_uuid),
                'label': obj.get_display_name(),
            }

    def get_project_list_value(self, column_id, project, user):
        """
        Return a value for the optional additional project list column specific
        to a project.

        :param column_id: ID of the column (string)
        :param project: Project object
        :param user: User object (current user)
        :return: String (may contain HTML), integer or None
        """
        if not user or user.is_anonymous or column_id != 'zones':
            return ''

        investigation = Investigation.objects.filter(
            project=project, active=True
        ).first()
        if user.is_superuser:
            zones = LandingZone.objects.filter(project=project)
        else:
            zones = LandingZone.objects.filter(project=project, user=user)
        active_count = zones.exclude(
            status__in=[ZONE_STATUS_MOVED, ZONE_STATUS_DELETED]
        ).count()

        if investigation and investigation.irods_status and active_count > 0:
            return (
                '<a href="{}" title="{}">'
                # 'data-toggle="tooltip" data-placement="top">'
                '<i class="iconify text-success" data-icon="mdi:briefcase">'
                '</i></a>'.format(
                    reverse(
                        'landingzones:list',
                        kwargs={'project': project.sodar_uuid},
                    ),
                    '{} landing zone{} {}'.format(
                        active_count,
                        's' if active_count != 1 else '',
                        'in total' if user.is_superuser else 'owned by you',
                    ),
                )
            )
        elif (
            investigation
            and investigation.irods_status
            and user.has_perm('landingzones.create_zone', project)
        ):
            return (
                '<a href="{}" title="Create landing zone in project">'
                # 'data-toggle="tooltip" data-placement="top">'
                '<i class="iconify" data-icon="mdi:plus-thick"></i>'
                '</a>'.format(
                    reverse(
                        'landingzones:create',
                        kwargs={'project': project.sodar_uuid},
                    )
                )
            )
        else:
            return (
                '<i class="iconify text-muted" data-icon="mdi:briefcase" '
                'title="No available landing zones"></i>'
                # 'data-toggle="tooltip" data-placement="top"></i>'
            )

    def perform_project_sync(self, project):
        """
        Synchronize existing projects to ensure related data exists when the
        syncmodifyapi management comment is called. Should mostly be used in
        development when the development databases have been e.g. modified or
        recreated.

        :param project: Current project object (Project)
        """
        zones = LandingZone.objects.filter(
            project=project, status__in=STATUS_ALLOW_UPDATE
        )
        if zones.count() == 0:
            logger.debug('Skipping: No active zones found')
            return

        irods_backend = get_backend_api('omics_irods')
        taskflow = get_backend_api('taskflow')
        if not irods_backend or not taskflow:
            logger.debug('Skipping: Required backend plugins not active')
            return

        with irods_backend.get_session() as irods:
            for zone in zones:
                zone_path = irods_backend.get_path(zone)
                if irods.collections.exists(zone_path):
                    continue  # Skip if already there
                self.submit_create(zone, False)


# Landingzones configuration sub-app plugin ------------------------------------


class LandingZoneConfigPluginPoint(PluginPoint):
    """Plugin point for registering landingzones configuration sub-apps"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    # TODO: Implement this in your config plugin
    # TODO: Recommended in form of landingzones_config_name
    # name = 'landingzones_config_name'

    #: Title (used in templates)
    # TODO: Implement this in your config plugin
    # title = 'Landing Zones X Config App'

    # Properties defined in LandingZoneConfigPluginPoint ------------------

    #: Configuration name (used to identify plugin by configuration string)
    # TODO: Implement this in your config plugin
    config_name = ''

    #: Configuration display name (to be visible in GUI)
    # TODO: Implement this in your config plugin
    config_display_name = 'BIH Proteomics SMB Server'

    #: Description string
    # TODO: Implement this in your config plugin
    description = 'TODO: Write a description for your config plugin'

    #: Additional zone menu items
    # TODO: Implement this in your config plugin
    menu_items = [
        {
            'label': '',  # Label to be displayed in menu
            'icon': '',  # Iconify icon id
            'url_name': '',
        }  # URL name, will receive zone as "landingzone" kwarg
    ]

    #: Fields from LandingZone.config_data to be displayed in zone list API
    # TODO: Implement this in your config plugin
    api_config_data = []

    #: Required permission for accessing the plugin
    # TODO: Implement this in your config plugin (can be None)
    # TODO: TBD: Do we need this?
    permission = None

    # TODO: Implement this in your config plugin if needed
    def cleanup_zone(self, zone):
        """
        Perform actions before landing zone deletion.

        :param zone: LandingZone object
        """
        pass

    # TODO: Implement this in your config plugin if needed
    def get_extra_flow_data(self, zone, flow_name):
        """
        Return extra zone data parameters.

        :param zone: LandingZone object
        :param flow_name: Name of flow (string)
        :return: dict or None
        """
        pass


def get_zone_config_plugin(zone):
    """
    Return active landing zone configuration plugin.

    :param zone: LandingZone object
    :return: LandingZoneConfigPlugin object or None if not found
    """
    if not zone.configuration:
        return None
    try:
        return LandingZoneConfigPluginPoint.get_plugin(
            'landingzones_config_' + zone.configuration
        )
    except LandingZoneConfigPluginPoint.DoesNotExist:
        return None
