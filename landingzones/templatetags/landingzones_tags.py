from django import template
from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.plugins import get_backend_api

from ..models import LandingZone, STATUS_STYLES

DISABLED_STATES = [
    'NOT CREATED',
    'MOVED',
    'DELETED']

irods_backend = get_backend_api('omics_irods')

register = template.Library()


@register.simple_tag
def get_status_style(zone):
    return STATUS_STYLES[zone.status] \
        if zone.status in STATUS_STYLES else 'bg_faded'


@register.simple_tag
def get_zone_row_class(zone):
    return 'omics-lz-zone-tr-moved text-muted' if \
        zone.status in DISABLED_STATES else 'omics-lz-zone-tr-existing'


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
        kwargs={'study': zone.assay.study.omics_uuid}) + \
        '#' + str(zone.assay.omics_uuid)


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
    return reverse(
        'landingzones:irods_list',
        kwargs={
            'landingzone': zone.omics_uuid})
