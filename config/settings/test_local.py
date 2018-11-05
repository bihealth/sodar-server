"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""


from .test import *  # noqa


# Local App Settings
# ------------------------------------------------------------------------------


# Taskflow backend settings
TASKFLOW_TEST_MODE = True     # Important! Make taskflow use a test iRODS server


# Plugin settings
ENABLED_BACKEND_PLUGINS = [
    'timeline_backend',
    'taskflow',
    'omics_irods',
]
