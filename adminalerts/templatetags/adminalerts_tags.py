from django import template
from django.conf import settings
from django.utils import timezone

from ..models import AdminAlert


register = template.Library()


@register.simple_tag
def get_active_alerts():
    """Return active and non-expired admin alerts"""
    return AdminAlert.objects.filter(
        active=True, date_expire__gte=timezone.now()).order_by('-pk')
