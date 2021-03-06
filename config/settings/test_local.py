"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""

from .test import *  # noqa


# Local App Settings
# ------------------------------------------------------------------------------


# Taskflow backend settings
TASKFLOW_TEST_MODE = True  # Important! Make taskflow use a test iRODS server
IRODS_HOST = '127.0.0.1'
IRODS_PORT = 4488
IRODS_USER = 'rods'
IRODS_PASS = 'rods'
IRODS_ZONE = 'sodarZone'


# Plugin settings
ENABLED_BACKEND_PLUGINS = [
    'timeline_backend',
    'appalerts_backend',
    'sodar_cache',
    'ontologyaccess_backend',
    'taskflow',
    'omics_irods',
]


# Samplesheets app settings
SHEETS_ENABLE_CACHE = True  # Temporary, see issue #556

# iRODS settings shared by iRODS using apps
ENABLE_IRODS = True

# Override this if host is e.g. the host of a Docker Compose network
TASKFLOW_TEST_SODAR_HOST = env.str(
    'TASKFLOW_TEST_SODAR_HOST', 'http://127.0.0.1'
)
