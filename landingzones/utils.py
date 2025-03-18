"""Utilities for the landingzones app"""

import re

from datetime import datetime as dt

from django.utils.text import slugify


# Local constants
SUFFIX_CLEAN_RE = re.compile(r'\A\W+|\W+\Z')


def get_zone_title(suffix):
    """Return the full title for a landing zone based on a suffix"""
    title = dt.now().strftime('%Y%m%d_%H%M%S')
    return title + '_' + slugify(suffix).replace('-', '_') if suffix else title


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
            if not s.lower().endswith('md5')
        ]
        if x
    ]
