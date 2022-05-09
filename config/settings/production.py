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
SECURE_REDIRECT_EXEMPT = env.list(
    'DJANGO_SECURE_REDIRECT_EXEMPT',
    default=['/taskflow/', r'^irodsbackend/api/auth$'],
)
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS += ['gunicorn']

# Static Assets
# ------------------------------------------------------------------------------
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Add Samplesheets vue.js app assets
STATICFILES_DIRS.append(str(ROOT_DIR('samplesheets/vueapp/dist')))

# Add optonal custom directory for static includes at deployment stage
STATICFILES_DIRS += env.list('CUSTOM_STATIC_DIR', default=[])

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

LOGGING_LEVEL = env.str('LOGGING_LEVEL', 'ERROR')
LOGGING_APPS = env.list(
    'LOGGING_APPS',
    default=[
        'django',
        'django.requests',
        'irodsadmin',
        'irodsbackend',
        'irodsinfo',
        'landingzones',
        'ontologyaccess',
        'projectroles',
        'samplesheets',
        'siteinfo',
        'sodarcache',
        'taskflowbackend',
    ],
)
LOGGING = set_logging(LOGGING_LEVEL)


# Sentry Client
# ------------------------------------------------------------------------------

if ENABLE_SENTRY:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    SENTRY_DSN = '%s?verify_ssl=0' % env.str('SENTRY_DSN')
    sentry_sdk.init(SENTRY_DSN, integrations=[DjangoIntegration()])


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
ENABLED_BACKEND_PLUGINS = env.list(
    'ENABLED_BACKEND_PLUGINS',
    None,
    [
        'timeline_backend',
        'appalerts_backend',
        'ontologyaccess_backend',
        'sodar_cache',
        'taskflow',
        'omics_irods',
    ],
)


# iRODS settings shared by iRODS using apps
# NOTE: irods_ssl_ca_certificate_file should be defined in IRODS_CERT_PATH
IRODS_ENV_DEFAULT = env.dict(
    'IRODS_ENV_DEFAULT',
    default={
        'irods_client_server_negotiation': 'request_server_negotiation',
        'irods_client_server_policy': 'CS_NEG_REQUIRE',
        'irods_default_hash_scheme': 'MD5',
        'irods_encryption_algorithm': 'AES-256-CBC',
        'irods_encryption_key_size': 32,
        'irods_encryption_num_hash_rounds': 16,
        'irods_encryption_salt_size': 8,
        'irods_ssl_verify_server': 'cert',
    },
)
