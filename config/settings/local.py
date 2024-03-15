"""
Local settings

- Run in Debug mode

- Use console backend for emails

- Add Django Debug Toolbar
- Add django-extensions as app
"""

from .base import *  # noqa

import socket


# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool('DJANGO_DEBUG', True)
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# Note: This key only used for development and testing
SECRET_KEY = env(
    'DJANGO_SECRET_KEY',
    default='dlf%}b3:8+;o99yZ]2a11M2A.NC9e5fF6qs]S1,S:)iGJ;E>`c',
)

# Static Assets
# ------------------------------------------------------------------------------

# Add Samplesheets vue.js app assets
# STATICFILES_DIRS.append(str(ROOT_DIR('samplesheets/dist')))

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_PORT = 1025
EMAIL_HOST = 'localhost'
EMAIL_BACKEND = env(
    'DJANGO_EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)

# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': '',
    }
}

# django-debug-toolbar
# ------------------------------------------------------------------------------
ENABLE_DEBUG_TOOLBAR = env.bool('ENABLE_DEBUG_TOOLBAR', True)

if ENABLE_DEBUG_TOOLBAR:
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INSTALLED_APPS += ['debug_toolbar']

    INTERNAL_IPS = ['127.0.0.1', '10.0.2.2']

    # tricks to have debug toolbar when developing with docker
    if os.environ.get('USE_DOCKER') == 'yes':
        ip = socket.gethostbyname(socket.gethostname())
        INTERNAL_IPS += [ip[:-1] + '1']

    DEBUG_TOOLBAR_CONFIG = {
        'DISABLE_PANELS': ['debug_toolbar.panels.redirects.RedirectsPanel'],
        'SHOW_TEMPLATE_CONTEXT': True,
    }

# django-extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ['django_extensions']

GRAPH_MODELS = {'all_applications': False, 'group_models': True}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django.test.runner.DiscoverRunner'


# Local App Settings
# ------------------------------------------------------------------------------


# Plugin settings
ENABLED_BACKEND_PLUGINS = [
    'timeline_backend',
    'appalerts_backend',
    'ontologyaccess_backend',
    'taskflow',
    'omics_irods',
    'sodar_cache',
]
