"""
Production Configurations

- Use WhiteNoise for serving static files
- Use Redis for cache
"""

import logging

from .base import *  # noqa


# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# Raises ImproperlyConfigured exception if DJANGO_SECRET_KEY not in os.environ
SECRET_KEY = env('DJANGO_SECRET_KEY')

# This ensures that Django will be able to detect a secure connection
# properly on Heroku.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Use Whitenoise to serve static files
# See: https://whitenoise.readthedocs.io/
WHITENOISE_MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware']
MIDDLEWARE = WHITENOISE_MIDDLEWARE + MIDDLEWARE

# SECURITY CONFIGURATION
# ------------------------------------------------------------------------------
# set this to 60 seconds and then to 518400 when you can prove it works
SECURE_HSTS_SECONDS = 60

SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True
)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    'DJANGO_SECURE_CONTENT_TYPE_NOSNIFF', default=True
)
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = env.bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
SECURE_REDIRECT_EXEMPT = ['/taskflow/']
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS += ['gunicorn']

# Static Assets
# ------------------------------------------------------------------------------
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Add Samplesheets vue.js app assets
STATICFILES_DIRS.append(str(ROOT_DIR('samplesheets/dist')))

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
TEMPLATES[0]['OPTIONS']['loaders'] = [
    (
        'django.template.loaders.cached.Loader',
        [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ],
    )
]

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# Use the Heroku-style specification
# Raises ImproperlyConfigured exception if DATABASE_URL not in os.environ
DATABASES['default'] = env.db('DATABASE_URL')

# CACHING
# ------------------------------------------------------------------------------
REDIS_LOCATION = '{0}/{1}'.format(
    env('REDIS_URL', default='redis://127.0.0.1:6379'), 0
)

# Heroku URL does not pass the DB number, so we parse it in
# http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_LOCATION,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,  # mimics memcache behavior
        },
    }
}

# Logging
# ------------------------------------------------------------------------------

LOGGING = set_logging(DEBUG)

LOGGING['loggers']['django.db.backends'] = {
    'level': 'ERROR',
    'handlers': ['console'],
    'propagate': False,
}

LOGGING['loggers']['django.security.DisallowedHost'] = {
    'level': 'ERROR',
    'handlers': ['console'],
    'propagate': False,
}


# Custom Admin URL, use {% url 'admin:index' %}
ADMIN_URL = env('DJANGO_ADMIN_URL', default='admin')


# EMAIL CONFIGURATION
# ------------------------------------------------------------------------------
EMAIL_URL = env.email_url('EMAIL_URL', 'smtp://0.0.0.0')

EMAIL_HOST = EMAIL_URL['EMAIL_HOST']
EMAIL_PORT = EMAIL_URL['EMAIL_PORT']
EMAIL_BACKEND = EMAIL_URL['EMAIL_BACKEND']
EMAIL_HOST_USER = EMAIL_URL['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = EMAIL_URL['EMAIL_HOST_PASSWORD']


# Local App Settings
# ------------------------------------------------------------------------------


# Plugin settings
ENABLED_BACKEND_PLUGINS = [
    'timeline_backend',
    'sodar_cache',
    'taskflow',
    'omics_irods',
]
