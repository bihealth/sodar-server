"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""

from .base import *  # noqa


# DEBUG
# ------------------------------------------------------------------------------
# Turn debug off so tests run faster
DEBUG = False
TEMPLATES[0]['OPTIONS']['debug'] = True

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# Note: This key only used for development and testing.
SECRET_KEY = env('DJANGO_SECRET_KEY', default='CHANGEME!!!')

# MANAGER CONFIGURATION
# ------------------------------------------------------------------------------
ADMINS = [('Admin User', 'admin@example.com')]
MANAGERS = ADMINS

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025

# In-memory email backend stores messages in django.core.mail.outbox
# for unit testing purposes
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# CACHING
# ------------------------------------------------------------------------------
# Speed advantages of in-memory caching without having to run Memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': '',
    }
}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# PASSWORD HASHING
# ------------------------------------------------------------------------------
# Use fast password hasher so tests run faster
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# TEMPLATE LOADERS
# ------------------------------------------------------------------------------
# Keep templates in memory so tests run faster
TEMPLATES[0]['OPTIONS']['loaders'] = [
    [
        'django.template.loaders.cached.Loader',
        [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ],
    ]
]

# Logging
# ------------------------------------------------------------------------------

LOGGING_LEVEL = env.str('LOGGING_LEVEL', 'CRITICAL')
LOGGING = set_logging(LOGGING_LEVEL)
LOGGING_DISABLE_CMD_OUTPUT = True


# Celery settings
# ------------------------------------------------------------------------------

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


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

# Projectroles app settings
PROJECTROLES_ENABLE_MODIFY_API = True
PROJECTROLES_MODIFY_API_APPS = ['taskflow', 'samplesheets', 'landingzones']
PROJECTROLES_SEND_EMAIL = True
PROJECTROLES_SEARCH_PAGINATION = 10  # Workaround for #360
PROJECTROLES_ALLOW_ANONYMOUS = False
PROJECTROLES_ALLOW_LOCAL_USERS = True

# Samplesheets app settings
SHEETS_ENABLE_CACHE = False  # Temporarily disabled to fix CI, see issue #556
SHEETS_ENABLE_STUDY_TABLE_CACHE = True
SHEETS_EXTERNAL_LINK_PATH = os.path.join(
    ROOT_DIR, 'samplesheets/tests/config/ext_links.json'
)
SHEETS_IGV_OMIT_BAM = ['*dragen_evidence.bam']
SHEETS_IGV_OMIT_VCF = ['*cnv.vcf.gz', '*ploidy.vcf.gz', '*sv.vcf.gz']

# Landingzones app settings
LANDINGZONES_TRIGGER_ENABLE = True
LANDINGZONES_DISABLE_FOR_USERS = False

# iRODS settings shared by iRODS using apps
ENABLE_IRODS = True
IRODS_HOST = '127.0.0.1'
IRODS_PORT = 4488
IRODS_WEBDAV_ENABLED = True
IRODS_SODAR_AUTH = True

# Taskflow backend settings
TASKFLOW_TEST_MODE = True
TASKFLOW_TEST_PERMANENT_USERS = [
    'client_user',
    'rods',
    'rodsadmin',
    'public',
    'bih_proteomics_smb',
]

# UI test settings
PROJECTROLES_TEST_UI_CHROME_OPTIONS = [
    'headless',
    'no-sandbox',  # For Gitlab-CI compatibility
    'disable-dev-shm-usage',  # For testing stability
]
PROJECTROLES_TEST_UI_WINDOW_SIZE = (1400, 1000)
PROJECTROLES_TEST_UI_WAIT_TIME = 30
PROJECTROLES_TEST_UI_LEGACY_LOGIN = env.bool(
    'PROJECTROLES_TEST_UI_LEGACY_LOGIN', False
)
