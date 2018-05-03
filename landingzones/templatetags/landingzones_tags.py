from django import template
from django.conf import settings
from django.urls import reverse


from ..models import LandingZone


STATUS_STYLES = {
    'ACTIVE': 'bg-info',
    'PREPARING': 'bg-warning',
    'VALIDATING': 'bg-warning',
    'MOVING': 'bg-warning',
    'MOVED': 'bg-success',
    'FAILED': 'bg-danger'}


register = template.Library()


@register.simple_tag
def get_status_style(zone):
    return STATUS_STYLES[zone.status] \
        if zone.status in STATUS_STYLES else 'bg_faded'


@register.simple_tag
def get_zone_row_class(zone):
    return 'omics-lz-zone-tr-moved text-muted' if \
        zone.status == 'MOVED' else 'omics-lz-zone-tr-existing'


# TODO: Refactor/remove
@register.simple_tag
def get_irods_cmd(zone):
    """Return iRODS icommand for popover"""
    return '/omicsZone/projects/project{}/landing_zones/{}/{}'.format(
        zone.project.pk, zone.user, zone.title)


@register.simple_tag
def get_details_zones(project, user):
    """Return active user zones for the project details page"""
    return LandingZone.objects.filter(
        project=project, user=user).exclude(status='MOVED').order_by('-pk')


@register.simple_tag
def get_zone_dav_url(zone):
    return '{}{}'.format(
        settings.IRODS_WEBDAV_URL.rstrip('/'),
        zone.get_path())


@register.simple_tag
def get_zone_desc_html(zone):
    """Return zone description as HTML"""
    return '<div><strong>Description</strong><br />{}</div>'.format(
        zone.description)
