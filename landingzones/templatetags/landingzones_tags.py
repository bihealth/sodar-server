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
