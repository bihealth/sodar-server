"""Utilities for the landingzones app"""

import re

from datetime import datetime as dt

from django.conf import settings
from django.utils.text import slugify

from landingzones.constants import (
    STATUS_FINISHED,
    ZONE_STATUS_PREPARING,
    ZONE_STATUS_VALIDATING,
)
from landingzones.models import LandingZone


# Local constants
SUFFIX_CLEAN_RE = re.compile(r'\A\W+|\W+\Z')


def get_zone_title(suffix):
    """Return the full title for a landing zone based on a suffix"""
    title = dt.now().strftime('%Y%m%d_%H%M%S')
    return title + '_' + slugify(suffix).replace('-', '_') if suffix else title


def get_zone_create_limit(project):
    """Return True if zone creation limit has been reached"""
    limit = settings.LANDINGZONES_ZONE_CREATE_LIMIT
    if (
        limit
        and 0
        < limit
        <= LandingZone.objects.filter(project=project)
        .exclude(status__in=STATUS_FINISHED)
        .count()
    ):
        return True
    return False


def get_zone_validate_limit(project):
    """Return True if zone validation limit has been reached"""
    limit = settings.LANDINGZONES_ZONE_VALIDATE_LIMIT
    if (
        limit
        and 0
        < limit
        <= LandingZone.objects.filter(
            project=project,
            status__in=[ZONE_STATUS_PREPARING, ZONE_STATUS_VALIDATING],
        ).count()
    ):
        return True
    return False


def cleanup_file_prohibit(prohibit_val):
    """
    Return cleaned up file_name_prohibit setting value.

    :param prohibit_val: String
    :return: List of strings
    """
    ret = prohibit_val.split(',')
    return [
        x
        for x in [
            re.sub(SUFFIX_CLEAN_RE, '', s.lower().strip())
            for s in ret
            if not any([s.lower().endswith(x) for x in ['.md5', '.sha256']])
        ]
        if x
    ]
