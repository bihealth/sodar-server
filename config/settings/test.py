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

LOGGING = set_logging(DEBUG, level='CRITICAL')


# Local App Settings
# ------------------------------------------------------------------------------


# Plugin settings
ENABLED_BACKEND_PLUGINS = [
    'timeline_backend',
    'appalerts_backend',
    'sodar_cache',
    'ontologyaccess_backend',
    # 'taskflow',
    # 'omics_irods',
]

# Projectroles app settings
PROJECTROLES_SEND_EMAIL = True
PROJECTROLES_SEARCH_PAGINATION = 10  # Workaround for #360
PROJECTROLES_ALLOW_ANONYMOUS = False

# Samplesheets app settings
SHEETS_ENABLE_CACHE = False  # Temporarily disabled to fix CI, see issue #556

# iRODS settings shared by iRODS using apps
ENABLE_IRODS = False
IRODS_WEBDAV_ENABLED = True


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
