"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""


from .test import *  # noqa


# Local App Settings
# ------------------------------------------------------------------------------


# Taskflow backend settings
TASKFLOW_TEST_MODE = True  # Important! Make taskflow use a test iRODS server
IRODS_HOST = '0.0.0.0'
IRODS_PORT = 4488
IRODS_USER = 'rods'
IRODS_PASS = 'rods'
IRODS_ZONE = 'omicsZone'


# Plugin settings
ENABLED_BACKEND_PLUGINS = [
    'sodar_cache',
    'timeline_backend',
    'taskflow',
    'omics_irods',
]


# Samplesheets app settings
SHEETS_ENABLE_CACHE = True  # Temporary, see issue #556
