"""Utilities for the landingzones app"""

from datetime import datetime as dt

from django.utils.text import slugify


def get_zone_title(suffix):
    """Return the full title for a landing zone based on a suffix"""
    title = dt.now().strftime('%Y%m%d_%H%M%S')
    return title + '_' + slugify(suffix).replace('-', '_') if suffix else title
