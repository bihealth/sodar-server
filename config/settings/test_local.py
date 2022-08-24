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
    'appalerts_backend',
    'sodar_cache',
    'ontologyaccess_backend',
    'taskflow',
    'omics_irods',
]


# Projectroles settings
PROJECTROLES_ENABLE_MODIFY_API = True
PROJECTROLES_MODIFY_API_APPS = ['taskflow', 'samplesheets', 'landingzones']


# iRODS settings shared by iRODS using apps
ENABLE_IRODS = True
IRODS_HOST = '127.0.0.1'  # Force test server
IRODS_PORT = 4488  # Force test server
IRODS_USER = 'rods'
IRODS_PASS = 'rods'
IRODS_ZONE = 'sodarZone'


# Taskflow backend settings
TASKFLOW_TEST_MODE = True
TASKFLOW_TEST_PERMANENT_USERS = [
    'client_user',
    'rods',
    'rodsadmin',
    'public',
    'bih_proteomics_smb',
]


# Samplesheets app settings
SHEETS_ENABLE_CACHE = True  # Temporary, see issue #556
