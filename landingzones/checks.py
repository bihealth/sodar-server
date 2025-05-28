"""Django checks for the landingzones app"""

from django.conf import settings
from django.core.checks import Warning, register


W001_MSG = (
    'LANDINGZONES_ZONE_VALIDATE_LIMIT is set to 0. This value is not allowed '
    'and it is considered as 1.'
)
W001 = Warning(W001_MSG, obj=settings, id='landingzones.W001')


@register()
def check_validate_limit(app_configs, **kwargs):
    """Check if LANDINGZONES_ZONE_VALIDATE_LIMIT is correctly set"""
    ret = []
    if settings.LANDINGZONES_ZONE_VALIDATE_LIMIT == 0:
        ret.append(W001)
    return ret
