from django import template
from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import get_backend_api

from ..models import LandingZone, STATUS_STYLES
from ..plugins import get_zone_config_plugin


irods_backend = get_backend_api('omics_irods')
register = template.Library()


DISABLED_STATES = ['NOT CREATED', 'MOVED', 'DELETED']


@register.simple_tag
def get_status_style(zone):
    return STATUS_STYLES[zone.status] \
        if zone.status in STATUS_STYLES else 'bg_faded'


@register.simple_tag
def get_zone_row_class(zone):
    return 'sodar-lz-zone-tr-moved text-muted' if \
        zone.status in DISABLED_STATES else 'sodar-lz-zone-tr-existing'


@register.simple_tag
def get_details_zones(project, user):
    """Return active user zones for the project details page"""
    return LandingZone.objects.filter(
        project=project, user=user).exclude(
            status__in=['MOVED', 'DELETED']).order_by('-pk')


@register.simple_tag
def get_zone_desc_html(zone):
    """Return zone description as HTML"""
    return '<div><strong>Description</strong><br />{}</div>'.format(
        zone.description)


@register.simple_tag
def get_zone_samples_url(zone):
    """Return URL for samples related to zone"""
    # TODO: TBD: Inherit this from samplesheets instead?
    return reverse(
        'samplesheets:project_sheets',
        kwargs={'study': zone.assay.study.sodar_uuid}) + \
        '#' + str(zone.assay.sodar_uuid)


@register.simple_tag
def is_zone_enabled(zone):
    """Return True/False if the zone can be enabled in the UI"""
    return True if zone.status not in DISABLED_STATES else False


@register.simple_tag
def is_zone_disabled(zone):
    """Return True/False if the zone can be enabled in the UI"""
    # NOTE: Have to do this silly hack because limitations of Django templates
    return False if zone.status not in DISABLED_STATES else True


@register.simple_tag
def get_zone_list_url(zone):
    """Return iRODS file list querying URL for landing zone"""
    if not irods_backend:
        return None

    path = irods_backend.get_path(zone)

    return reverse(
        'irodsbackend:list',
        kwargs={
            'project': zone.project.sodar_uuid,
            'path': path,
            'md5': 1})


@register.simple_tag
def get_config_legend(zone):
    """Return printable legend for zone configuration"""
    if not zone.configuration:
        return None

    zone_plugin = get_zone_config_plugin(zone)

    if zone_plugin:
        return zone_plugin.config_display_name


@register.simple_tag
def get_config_plugin(zone):
    """Retrieve landing zone configuration sub-app plugin"""
    return get_zone_config_plugin(zone)


@register.simple_tag
def get_config_link_url(zone, url_name):
    """Return URL for a config plugin link"""
    return reverse(url_name, kwargs={'landingzone': zone.sodar_uuid})