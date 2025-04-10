"""Template tags for the landingzones app"""

from django import template
from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import get_backend_api

from landingzones.constants import (
    STATUS_STYLES,
    STATUS_FINISHED,
    STATUS_ALLOW_UPDATE,
)
from landingzones.models import LandingZone
from landingzones.plugins import get_zone_config_plugin


register = template.Library()


@register.simple_tag
def get_status_style(zone):
    return (
        STATUS_STYLES[zone.status]
        if zone.status in STATUS_STYLES
        else 'bg_faded'
    )


@register.simple_tag
def get_zone_row_class(zone):
    return (
        'sodar-lz-zone-tr-moved text-muted'
        if zone.status in STATUS_FINISHED
        else 'sodar-lz-zone-tr-existing'
    )


@register.simple_tag
def get_details_zones(project, user):
    """Return active user zones for the project details page"""
    return (
        LandingZone.objects.filter(project=project, user=user)
        .exclude(status__in=STATUS_FINISHED)
        .order_by('-pk')
    )


@register.simple_tag
def get_zone_desc_html(zone):
    """Return zone description as HTML"""
    return '<div><strong>Description</strong><br />{}</div>'.format(
        zone.description
    )


# TODO: Remove
@register.simple_tag
def is_zone_enabled(zone):
    """Return True/False if the zone can be enabled in the UI"""
    return True if zone.status not in STATUS_FINISHED else False


@register.simple_tag
def disable_zone_ui(zone, user):
    """Return True/False if the zone controls can be enabled in the UI"""
    if user.is_superuser and zone.status not in STATUS_FINISHED:
        return False
    elif not user.is_superuser and zone.status in STATUS_ALLOW_UPDATE:
        return False
    return True


@register.simple_tag
def get_zone_list_url(zone):
    """Return iRODS file list querying URL for landing zone"""
    irods_backend = get_backend_api('omics_irods')
    if not irods_backend:
        return None
    return irods_backend.get_url(
        view='list',
        project=zone.project,
        path=irods_backend.get_path(zone),
        md5=True,
        colls=True,
    )


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


# TODO: Move to SODAR Core (see bihealth/sodar-core#1662)
@register.simple_tag
def get_user_badge(user):
    """Return HTML badge for user"""
    if not user.is_active:
        icon = 'mdi:account-off'
        badge_class = 'secondary'
        user_class = 'inactive'
    elif user.is_superuser:
        icon = 'mdi:shield-account'
        badge_class = 'info'
        user_class = 'superuser'
    else:
        icon = 'mdi:account'
        badge_class = 'primary'
        user_class = 'active'
    email = True if user.is_active and user.email else False
    ret = (
        f'<span class="badge badge-{badge_class} sodar-user-badge '
        f'sodar-user-badge-{user_class}" '
        f'title="{user.get_full_name()}" data-toggle="tooltip">'
        f'<i class="iconify" data-icon="{icon}"></i> '
    )
    if email:
        ret += f'<a class="text-white" href="mailto:{user.email}">'
    ret += user.username
    if email:
        ret += '</a>'
    ret += '</span>'
    return ret
