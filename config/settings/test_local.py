"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""

from .test import *  # noqa


# Local App Settings
# ------------------------------------------------------------------------------


# Plugin settings
ENABLED_BACKEND_PLUGINS = [
    'timeline_backend',
    # 'taskflow',
    # 'omics_irods',
]
