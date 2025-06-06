"""
Django settings for the SODAR project.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import itertools
import os
import re

import environ


SITE_PACKAGE = 'sodar'
ROOT_DIR = environ.Path(__file__) - 3
APPS_DIR = ROOT_DIR.path(SITE_PACKAGE)

# Load operating system environment variables and then prepare to use them
env = environ.Env()

# .env file, should load only in development environment
READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', False)

if READ_DOT_ENV_FILE:
    # Operating System Environment variables have precedence over variables
    # defined in the .env file, that is to say variables from the .env files
    # will only be used if not defined as environment variables.
    env_file = str(ROOT_DIR.path('.env'))
    env.read_env(env_file)

# SITE CONFIGURATION
# ------------------------------------------------------------------------------
# Hosts/domain names that are valid for this site
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['*'])
USE_X_FORWARDED_HOST = env.bool('DJANGO_USE_X_FORWARDED_HOST', False)

# APP CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    # Default Django apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Useful template tags
    # 'django.contrib.humanize',
    # Admin
    'django.contrib.admin',
]
THIRD_PARTY_APPS = [
    'crispy_forms',  # Form layouts
    'crispy_bootstrap4',  # Bootstrap4 theme for Crispy
    'rules.apps.AutodiscoverRulesConfig',  # Django rules engine
    'djangoplugins',  # Django plugins
    'pagedown',  # For markdown
    'markupfield',  # For markdown
    'rest_framework',  # For API views
    'knox',  # For token auth
    'social_django',  # For OIDC authentication
    'docs',  # For the online user documentation/manual
    'dal',  # For user search combo box
    'dal_select2',
    'dj_iconify.apps.DjIconifyConfig',  # Iconify for SVG icons
    'drf_spectacular',  # OpenAPI schema generation
    'webpack_loader',  # For accessing webpack bundles
    # SODAR Core apps
    # Project apps
    'projectroles.apps.ProjectrolesConfig',
    'timeline.apps.TimelineConfig',
    # Site apps
    'userprofile.apps.UserprofileConfig',
    'adminalerts.apps.AdminalertsConfig',
    'tokens.apps.TokensConfig',
    'appalerts.apps.AppalertsConfig',
    # Backend apps
    'sodarcache.apps.SodarcacheConfig',
]

# Project apps
LOCAL_APPS = [
    # Custom users app
    'sodar.users.apps.UsersConfig',
    # Project apps
    'samplesheets.apps.SamplesheetsConfig',
    'landingzones.apps.LandingzonesConfig',
    # Backend apps
    'irodsbackend.apps.IrodsbackendConfig',
    'taskflowbackend.apps.TaskflowbackendConfig',
    # General site apps
    'siteinfo.apps.SiteinfoConfig',
    'irodsinfo.apps.IrodsinfoConfig',
    'ontologyaccess.apps.OntologyaccessConfig',
    'isatemplates.apps.IsatemplatesConfig',
    # Samplesheets study sub-apps
    'samplesheets.studyapps.germline.apps.GermlineConfig',
    'samplesheets.studyapps.cancer.apps.CancerConfig',
    # Samplesheets assay sub-apps
    'samplesheets.assayapps.dna_sequencing.apps.DnaSequencingConfig',
    'samplesheets.assayapps.generic.apps.GenericConfig',
    'samplesheets.assayapps.generic_raw.apps.GenericRawConfig',
    'samplesheets.assayapps.meta_ms.apps.MetaMsConfig',
    'samplesheets.assayapps.microarray.apps.MicroarrayConfig',
    'samplesheets.assayapps.pep_ms.apps.PepMsConfig',
    'samplesheets.assayapps.cytof.apps.CytofConfig',
    # Landingzones config sub-apps
    'landingzones.configapps.bih_proteomics_smb.apps.BihProteomicsSmbConfig',
    # Admin apps
    'irodsadmin.apps.IrodsadminConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_cprofile_middleware.middleware.ProfilerMiddleware',
]

# MIGRATIONS CONFIGURATION
# ------------------------------------------------------------------------------
MIGRATION_MODULES = {'sites': 'sodar.contrib.sites.migrations'}

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool('DJANGO_DEBUG', False)

# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------
FIXTURE_DIRS = (str(APPS_DIR.path('fixtures')),)

# EMAIL CONFIGURATION
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env(
    'DJANGO_EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_SENDER = env('EMAIL_SENDER', default='noreply@example.com')
EMAIL_SUBJECT_PREFIX = env('EMAIL_SUBJECT_PREFIX', default='')

# MANAGER CONFIGURATION
# ------------------------------------------------------------------------------
# Provide ADMINS as: Name:email,Name:email
ADMINS = [x.split(':') for x in env.list('ADMINS', default=[])]
# See: https://docs.djangoproject.com/en/3.2/ref/settings/#managers
MANAGERS = ADMINS

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/3.2/ref/settings/#databases
# Uses django-environ to accept uri format
# See: https://django-environ.readthedocs.io/en/latest/#supported-types
DATABASES = {'default': env.db('DATABASE_URL', 'postgres:///sodar')}
DATABASES['default']['ATOMIC_REQUESTS'] = False

# Set default auto field (for Django 3.2+)
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Default Redis server URL
REDIS_URL = env.str('REDIS_URL', 'redis://127.0.0.1:6379/0')

# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Berlin'

# See: https://docs.djangoproject.com/en/3.2/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/3.2/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/3.2/ref/settings/#use-i18n
USE_I18N = False

# See: https://docs.djangoproject.com/en/3.2/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/3.2/ref/settings/#use-tz
USE_TZ = True

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/3.2/ref/settings/#templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(APPS_DIR.path('templates'))],
        'OPTIONS': {
            'debug': DEBUG,
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                # Site context processors
                'projectroles.context_processors.urls_processor',
                'projectroles.context_processors.site_app_processor',
                'projectroles.context_processors.app_alerts_processor',
                'projectroles.context_processors.sidebar_processor',
            ],
        },
    }
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------
STATIC_ROOT = str(ROOT_DIR('staticfiles'))
STATIC_URL = '/static/'

STATICFILES_DIRS = [str(APPS_DIR.path('static'))]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Iconify SVG icons
ICONIFY_JSON_ROOT = os.path.join(STATIC_ROOT, 'iconify')

WEBPACK_LOADER = {
    'SAMPLESHEETS': {
        # 'BUNDLE_DIR_NAME': 'samplesheets-vue/',
        'STATS_FILE': ROOT_DIR('samplesheets/vueapp/webpack-stats.json'),
    }
}

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
MEDIA_ROOT = str(APPS_DIR('media'))
MEDIA_URL = '/media/'

# URL Configuration
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
# Location of root django.contrib.admin URL, use {% url 'admin:index' %}
ADMIN_URL = 'admin/'

# PASSWORD STORAGE SETTINGS
# ------------------------------------------------------------------------------
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

# PASSWORD VALIDATION
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'UserAttributeSimilarityValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'MinimumLengthValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'NumericPasswordValidator'
    },
]

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    'rules.permissions.ObjectPermissionBackend',  # For rules
    'django.contrib.auth.backends.ModelBackend',
]

# Custom user app defaults
AUTH_USER_MODEL = 'users.User'
LOGIN_REDIRECT_URL = 'home'
LOGIN_URL = 'login'

# SLUGLIFIER
AUTOSLUG_SLUGIFY_FUNCTION = 'slugify.slugify'

# The age of session cookies in seconds
SESSION_COOKIE_AGE = env.int('DJANGO_SESSION_COOKIE_AGE', 1209600)
# Whether to expire the session when the user closes their browser
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool(
    'DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE', False
)

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', REDIS_URL)
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ['json']
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = 'json'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = 'json'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-time-limit
CELERYD_TASK_TIME_LIMIT = 5 * 60
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-soft-time-limit
CELERYD_TASK_SOFT_TIME_LIMIT = 60
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#broker-connection-retry-on-startup
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = False
CELERY_IMPORTS = [
    'landingzones.tasks_celery',
    'samplesheets.tasks_celery',
    'taskflowbackend.tasks_celery',
]


# API Settings
# ------------------------------------------------------------------------------

SODAR_API_DEFAULT_HOST = env.url(
    'SODAR_API_DEFAULT_HOST', 'http://127.0.0.1:8000'
)

SODAR_API_PAGE_SIZE = env.int('SODAR_API_PAGE_SIZE', 100)


# Django REST framework
# ------------------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'knox.auth.TokenAuthentication',
    ),
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_PAGINATION_CLASS': (
        'rest_framework.pagination.PageNumberPagination'
    ),
    'PAGE_SIZE': SODAR_API_PAGE_SIZE,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'PREPROCESSING_HOOKS': ['config.drf_spectacular.exclude_knox_hook']
}


# LDAP configuration
# ------------------------------------------------------------------------------

# Enable LDAP if configured
ENABLE_LDAP = env.bool('ENABLE_LDAP', False)
ENABLE_LDAP_SECONDARY = env.bool('ENABLE_LDAP_SECONDARY', False)
LDAP_DEBUG = env.bool('LDAP_DEBUG', False)
# Alternative domains for detecting LDAP access by email address
LDAP_ALT_DOMAINS = env.list('LDAP_ALT_DOMAINS', None, default=[])

if ENABLE_LDAP:
    import ldap
    from django_auth_ldap.config import LDAPSearch

    if LDAP_DEBUG:
        ldap.set_option(ldap.OPT_DEBUG_LEVEL, 255)
    # Default values
    LDAP_DEFAULT_CONN_OPTIONS = {ldap.OPT_REFERRALS: 0}
    LDAP_DEFAULT_ATTR_MAP = {
        'first_name': 'givenName',
        'last_name': 'sn',
        'email': 'mail',
    }

    # Primary LDAP server
    AUTH_LDAP_SERVER_URI = env.str('AUTH_LDAP_SERVER_URI', None)
    AUTH_LDAP_BIND_DN = env.str('AUTH_LDAP_BIND_DN', None)
    AUTH_LDAP_BIND_PASSWORD = env.str('AUTH_LDAP_BIND_PASSWORD', None)
    AUTH_LDAP_START_TLS = env.bool('AUTH_LDAP_START_TLS', False)
    AUTH_LDAP_CA_CERT_FILE = env.str('AUTH_LDAP_CA_CERT_FILE', None)
    AUTH_LDAP_CONNECTION_OPTIONS = {**LDAP_DEFAULT_CONN_OPTIONS}
    if AUTH_LDAP_CA_CERT_FILE:
        AUTH_LDAP_CONNECTION_OPTIONS[ldap.OPT_X_TLS_CACERTFILE] = (
            AUTH_LDAP_CA_CERT_FILE
        )
        AUTH_LDAP_CONNECTION_OPTIONS[ldap.OPT_X_TLS_NEWCTX] = 0
    AUTH_LDAP_USER_FILTER = env.str(
        'AUTH_LDAP_USER_FILTER', '(sAMAccountName=%(user)s)'
    )
    AUTH_LDAP_USER_SEARCH_BASE = env.str('AUTH_LDAP_USER_SEARCH_BASE', None)
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        AUTH_LDAP_USER_SEARCH_BASE,
        ldap.SCOPE_SUBTREE,
        AUTH_LDAP_USER_FILTER,
    )
    AUTH_LDAP_USER_ATTR_MAP = LDAP_DEFAULT_ATTR_MAP
    AUTH_LDAP_USERNAME_DOMAIN = env.str('AUTH_LDAP_USERNAME_DOMAIN', None)
    AUTH_LDAP_DOMAIN_PRINTABLE = env.str(
        'AUTH_LDAP_DOMAIN_PRINTABLE', AUTH_LDAP_USERNAME_DOMAIN
    )
    AUTHENTICATION_BACKENDS = tuple(
        itertools.chain(
            ('projectroles.auth_backends.PrimaryLDAPBackend',),
            AUTHENTICATION_BACKENDS,
        )
    )

    # Secondary LDAP server (optional)
    if ENABLE_LDAP_SECONDARY:
        AUTH_LDAP2_SERVER_URI = env.str('AUTH_LDAP2_SERVER_URI', None)
        AUTH_LDAP2_BIND_DN = env.str('AUTH_LDAP2_BIND_DN', None)
        AUTH_LDAP2_BIND_PASSWORD = env.str('AUTH_LDAP2_BIND_PASSWORD', None)
        AUTH_LDAP2_START_TLS = env.bool('AUTH_LDAP2_START_TLS', False)
        AUTH_LDAP2_CA_CERT_FILE = env.str('AUTH_LDAP2_CA_CERT_FILE', None)
        AUTH_LDAP2_CONNECTION_OPTIONS = {**LDAP_DEFAULT_CONN_OPTIONS}
        if AUTH_LDAP2_CA_CERT_FILE:
            AUTH_LDAP2_CONNECTION_OPTIONS[ldap.OPT_X_TLS_CACERTFILE] = (
                AUTH_LDAP2_CA_CERT_FILE
            )
            AUTH_LDAP2_CONNECTION_OPTIONS[ldap.OPT_X_TLS_NEWCTX] = 0
        AUTH_LDAP2_USER_FILTER = env.str(
            'AUTH_LDAP2_USER_FILTER', '(sAMAccountName=%(user)s)'
        )
        AUTH_LDAP2_USER_SEARCH_BASE = env.str(
            'AUTH_LDAP2_USER_SEARCH_BASE', None
        )
        AUTH_LDAP2_USER_SEARCH = LDAPSearch(
            AUTH_LDAP2_USER_SEARCH_BASE,
            ldap.SCOPE_SUBTREE,
            AUTH_LDAP2_USER_FILTER,
        )
        AUTH_LDAP2_USER_ATTR_MAP = LDAP_DEFAULT_ATTR_MAP
        AUTH_LDAP2_USERNAME_DOMAIN = env.str('AUTH_LDAP2_USERNAME_DOMAIN')
        AUTH_LDAP2_DOMAIN_PRINTABLE = env.str(
            'AUTH_LDAP2_DOMAIN_PRINTABLE', AUTH_LDAP2_USERNAME_DOMAIN
        )
        AUTHENTICATION_BACKENDS = tuple(
            itertools.chain(
                ('projectroles.auth_backends.SecondaryLDAPBackend',),
                AUTHENTICATION_BACKENDS,
            )
        )


# OpenID Connect (OIDC) configuration
# ------------------------------------------------------------------------------

ENABLE_OIDC = env.bool('ENABLE_OIDC', False)

if ENABLE_OIDC:
    AUTHENTICATION_BACKENDS = tuple(
        itertools.chain(
            ('social_core.backends.open_id_connect.OpenIdConnectAuth',),
            AUTHENTICATION_BACKENDS,
        )
    )
    TEMPLATES[0]['OPTIONS']['context_processors'] += [
        'social_django.context_processors.backends',
        'social_django.context_processors.login_redirect',
    ]
    SOCIAL_AUTH_JSONFIELD_ENABLED = True
    SOCIAL_AUTH_JSONFIELD_CUSTOM = 'django.db.models.JSONField'
    SOCIAL_AUTH_USER_MODEL = AUTH_USER_MODEL
    SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = [
        'username',
        'name',
        'first_name',
        'last_name',
        'email',
    ]
    SOCIAL_AUTH_OIDC_OIDC_ENDPOINT = env.str(
        'SOCIAL_AUTH_OIDC_OIDC_ENDPOINT', None
    )
    SOCIAL_AUTH_OIDC_KEY = env.str('SOCIAL_AUTH_OIDC_KEY', 'CHANGEME')
    SOCIAL_AUTH_OIDC_SECRET = env.str('SOCIAL_AUTH_OIDC_SECRET', 'CHANGEME')
    SOCIAL_AUTH_OIDC_USERNAME_KEY = env.str(
        'SOCIAL_AUTH_OIDC_USERNAME_KEY', 'username'
    )


# Logging
# ------------------------------------------------------------------------------

LOGGING_LEVEL = env.str('LOGGING_LEVEL', 'DEBUG' if DEBUG else 'ERROR')
LOGGING_APPS = env.list(
    'LOGGING_APPS',
    default=[
        'irodsadmin',
        'irodsbackend',
        'irodsinfo',
        'isatemplates',
        'landingzones',
        'ontologyaccess',
        'projectroles',
        'samplesheets',
        'siteinfo',
        'sodarcache',
        'taskflowbackend',
        'timeline',
    ],
)
LOGGING_FILE_PATH = env.str('LOGGING_FILE_PATH', None)


def set_logging(level=None):
    if not level:
        level = 'DEBUG' if DEBUG else 'ERROR'
    app_logger_config = {
        'level': level,
        'handlers': ['console', 'file'] if LOGGING_FILE_PATH else ['console'],
        'propagate': False,  # python-irodsclient>=1.1.9 fix
    }
    log_handlers = {
        'console': {
            'level': level,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    }
    if LOGGING_FILE_PATH:
        log_handlers['file'] = {
            'level': level,
            'class': 'logging.FileHandler',
            'filename': LOGGING_FILE_PATH,
            'formatter': 'simple',
        }
    return {
        'version': 1,
        'formatters': {
            'simple': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            }
        },
        'handlers': log_handlers,
        'loggers': {a: app_logger_config for a in LOGGING_APPS},
    }


LOGGING = set_logging(LOGGING_LEVEL)


# Sentry Client (Will be set up in production)
# ------------------------------------------------------------------------------

ENABLE_SENTRY = env.bool('ENABLE_SENTRY', False)


# Django-docs Settings
# ------------------------------------------------------------------------------

# Note: for serving to work, the docs have to be built after deployment.
DOCS_ROOT = ROOT_DIR.path('docs_manual/build/html/')
# DOCS_ACCESS = 'public'  # default

# Local App Settings
# ------------------------------------------------------------------------------


# Plugin settings
ENABLED_BACKEND_PLUGINS = env.list(
    'ENABLED_BACKEND_PLUGINS',
    default=[
        'timeline_backend',
        'appalerts_backend',
        'sodar_cache',
        'ontologyaccess_backend',
        'isatemplates_backend',
        # 'taskflow',
        # 'omics_irods',
    ],
)


# General site settings
SITE_TITLE = 'SODAR'
SITE_SUBTITLE = env.str('SITE_SUBTITLE', None)
SITE_INSTANCE_TITLE = env.str('SITE_INSTANCE_TITLE', 'CUBI SODAR')


# Projectroles app settings
PROJECTROLES_SITE_MODE = env.str('PROJECTROLES_SITE_MODE', 'SOURCE')
PROJECTROLES_TEMPLATE_INCLUDE_PATH = env.path(
    'PROJECTROLES_TEMPLATE_INCLUDE_PATH',
    os.path.join(APPS_DIR, 'templates', 'include'),
)
PROJECTROLES_SECRET_LENGTH = env.int('PROJECTROLES_SECRET_LENGTH', 32)
PROJECTROLES_INVITE_EXPIRY_DAYS = env.int('PROJECTROLES_INVITE_EXPIRY_DAYS', 14)
PROJECTROLES_SEND_EMAIL = env.bool('PROJECTROLES_SEND_EMAIL', False)
PROJECTROLES_EMAIL_SENDER_REPLY = env.bool(
    'PROJECTROLES_EMAIL_SENDER_REPLY', False
)
PROJECTROLES_EMAIL_HEADER = env.str('PROJECTROLES_EMAIL_HEADER', None)
PROJECTROLES_EMAIL_FOOTER = env.str('PROJECTROLES_EMAIL_FOOTER', None)
PROJECTROLES_HELP_HIGHLIGHT_DAYS = env.int(
    'PROJECTROLES_HELP_HIGHLIGHT_DAYS', 7
)
PROJECTROLES_ENABLE_SEARCH = env.bool('PROJECTROLES_ENABLE_SEARCH', True)
PROJECTROLES_SEARCH_PAGINATION = env.int('PROJECTROLES_SEARCH_PAGINATION', 5)
PROJECTROLES_DELEGATE_LIMIT = env.int('PROJECTROLES_DELEGATE_LIMIT', 1)
PROJECTROLES_DEFAULT_ADMIN = env.str('PROJECTROLES_DEFAULT_ADMIN', 'admin')
PROJECTROLES_ALLOW_LOCAL_USERS = env.bool(
    'PROJECTROLES_ALLOW_LOCAL_USERS', False
)
PROJECTROLES_ALLOW_ANONYMOUS = env.bool('PROJECTROLES_ALLOW_ANONYMOUS', False)
PROJECTROLES_ENABLE_MODIFY_API = True
PROJECTROLES_MODIFY_API_APPS = ['taskflow', 'samplesheets', 'landingzones']
PROJECTROLES_DISABLE_CATEGORIES = env.bool(
    'PROJECTROLES_DISABLE_CATEGORIES', False
)
PROJECTROLES_API_USER_DETAIL_RESTRICT = env.bool(
    'PROJECTROLES_API_USER_DETAIL_RESTRICT', False
)
PROJECTROLES_READ_ONLY_MSG = env.str(
    'PROJECTROLES_READ_ONLY_MSG',
    'This site is currently in read-only mode. Modifying data is not permitted.'
    'This includes landing zone operations.',
)
PROJECTROLES_SUPPORT_CONTACT = env.str('PROJECTROLES_SUPPORT_CONTACT', None)

# Warn about unsupported browsers (IE)
PROJECTROLES_BROWSER_WARNING = True
# Disable default CDN JS/CSS includes to replace with your local files
PROJECTROLES_DISABLE_CDN_INCLUDES = env.bool(
    'PROJECTROLES_DISABLE_CDN_INCLUDES', False
)
# Paths/URLs to optional global includes to supplement/replace default ones
PROJECTROLES_CUSTOM_JS_INCLUDES = env.list(
    'PROJECTROLES_CUSTOM_JS_INCLUDES', None, []
)
PROJECTROLES_CUSTOM_CSS_INCLUDES = env.list(
    'PROJECTROLES_CUSTOM_CSS_INCLUDES', None, []
)
# Inline HTML include to the head element of the base site template
PROJECTROLES_INLINE_HEAD_INCLUDE = env.str(
    'PROJECTROLES_INLINE_HEAD_INCLUDE', None
)
# Enable profiling for debugging/analysis
PROJECTROLES_ENABLE_PROFILING = env.bool('PROJECTROLES_ENABLE_PROFILING', False)
if PROJECTROLES_ENABLE_PROFILING:
    MIDDLEWARE += ['projectroles.middleware.ProfilerMiddleware']

# Adminalerts app settings
ADMINALERTS_PAGINATION = env.int('ADMINALERTS_PAGINATION', 15)

# Timeline app settings
TIMELINE_PAGINATION = env.int('TIMELINE_PAGINATION', 15)

# Tokens app settings
TOKENS_CREATE_PROJECT_USER_RESTRICT = env.bool(
    'TOKENS_CREATE_PROJECT_USER_RESTRICT', False
)


# iRODS settings shared by iRODS using apps
ENABLE_IRODS = env.bool('ENABLE_IRODS', True)
IRODS_HOST = env.str('IRODS_HOST', '127.0.0.1')
IRODS_HOST_FQDN = env.str('IRODS_HOST_FQDN', IRODS_HOST)
IRODS_PORT = env.int('IRODS_PORT', 4477)
IRODS_ZONE = env.str('IRODS_ZONE', 'sodarZone')
IRODS_ROOT_PATH = env.str('IRODS_ROOT_PATH', None)
IRODS_USER = env.str('IRODS_USER', 'rods')
IRODS_PASS = env.str('IRODS_PASS', 'rods')
# iRODS server checksum hash scheme (MD5 or SHA256)
IRODS_HASH_SCHEME = env.str('IRODS_HASH_SCHEME', 'MD5')
IRODS_SAMPLE_COLL = env.str('IRODS_SAMPLE_COLL', 'sample_data')
IRODS_LANDING_ZONE_COLL = env.str('IRODS_LANDING_ZONE_COLL', 'landing_zones')
# Enable entry point for custom local auth for iRODS users if no LDAP is in use
IRODS_SODAR_AUTH = env.bool('IRODS_SODAR_AUTH', False)
# Default iRODS environment for backend and client connections
# NOTE: irods_ssl_ca_certificate_file should be defined in IRODS_CERT_PATH
IRODS_ENV_DEFAULT = env.dict(
    'IRODS_ENV_DEFAULT',
    default={'irods_default_hash_scheme': IRODS_HASH_SCHEME},
)
# iRODS environment overrides for backend connections
IRODS_ENV_BACKEND = env.dict('IRODS_ENV_BACKEND', default={})
# iRODS environment overrides for client connections
IRODS_ENV_CLIENT = env.dict('IRODS_ENV_CLIENT', default={})
# Optional iRODS certificate path on server
IRODS_CERT_PATH = env.str('IRODS_CERT_PATH', None)

# Taskflow backend settings
# Connection timeout for taskflowbackend flows (other sessions not affected)
TASKFLOW_IRODS_CONN_TIMEOUT = env.int('TASKFLOW_IRODS_CONN_TIMEOUT', 3600)
TASKFLOW_LOCK_RETRY_COUNT = env.int('TASKFLOW_LOCK_RETRY_COUNT', 2)
TASKFLOW_LOCK_RETRY_INTERVAL = env.int('TASKFLOW_LOCK_RETRY_INTERVAL', 3)
# Interval in seconds for zone progress counters (0 for update on every file)
TASKFLOW_ZONE_PROGRESS_INTERVAL = env.int('TASKFLOW_ZONE_PROGRESS_INTERVAL', 10)
TASKFLOW_LOCK_ENABLED = True
TASKFLOW_TEST_MODE = False  # Important to protect iRODS data

# Samplesheets and Landingzones link settings
IRODS_WEBDAV_ENABLED = env.bool('IRODS_WEBDAV_ENABLED', True)
IRODS_WEBDAV_URL = env.str('IRODS_WEBDAV_URL', 'https://127.0.0.1')
IRODS_WEBDAV_URL_ANON = env.str('IRODS_WEBDAV_URL_ANON', IRODS_WEBDAV_URL)
IRODS_WEBDAV_URL_ANON_TMPL = re.sub(
    r'^(https?://)(.*)$', r'\1{user}:{ticket}@\2{path}', IRODS_WEBDAV_URL_ANON
)
IRODS_WEBDAV_USER_ANON = env.str('IRODS_WEBDAV_USER_ANON', 'ticket')
IRODS_WEBDAV_IGV_PROXY = env.bool('IRODS_WEBDAV_IGV_PROXY', True)


# Irodsbackend settings
# Status query interval in seconds
IRODSBACKEND_STATUS_INTERVAL = env.int('IRODSBACKEND_STATUS_INTERVAL', 15)
# Set batch query size for improving sequential iRODS query performance (#432)
IRODS_QUERY_BATCH_SIZE = env.int('IRODS_QUERY_BATCH_SIZE', 24)


# Samplesheets settings
# Allow critical altamISA warnings on import
SHEETS_ALLOW_CRITICAL = env.bool('SHEETS_ALLOW_CRITICAL', False)
# Temporary, see issue #556
SHEETS_ENABLE_CACHE = True
# Enable study table cache
SHEETS_ENABLE_STUDY_TABLE_CACHE = env.bool(
    'SHEETS_ENABLE_STUDY_TABLE_CACHE', True
)
# iRODS file query limit
SHEETS_IRODS_LIMIT = env.int('SHEETS_IRODS_LIMIT', 50)
# Minimum edit config version
SHEETS_CONFIG_VERSION = '0.8.0'
# Min default column width
SHEETS_MIN_COLUMN_WIDTH = env.int('SHEETS_MIN_COLUMN_WIDTH', 100)
# Max default column width
SHEETS_MAX_COLUMN_WIDTH = env.int('SHEETS_MAX_COLUMN_WIDTH', 300)
SHEETS_VERSION_PAGINATION = env.int('SHEETS_VERSION_PAGINATION', 15)
SHEETS_IRODS_TICKET_PAGINATION = env.int('SHEETS_IRODS_TICKET_PAGINATION', 15)
SHEETS_IRODS_REQUEST_PAGINATION = env.int('SHEETS_IRODS_REQUEST_PAGINATION', 15)
SHEETS_ONTOLOGY_URL_TEMPLATE = env.str(
    'SHEETS_ONTOLOGY_URL_TEMPLATE',
    (
        'https://bioportal.bioontology.org/ontologies/'
        '{ontology_name}/?p=classes&conceptid={accession}'
    ),
)
# Skip URL template modification if substring found in accession
SHEETS_ONTOLOGY_URL_SKIP = env.list(
    'SHEETS_ONTOLOGY_URL_SKIP', default=['bioontology.org', 'hpo.jax.org']
)
# Labels and URL patterns for external link columns
# Provide custom labels via a JSON file via SHEETS_EXTERNAL_LINK_PATH.
# Each entry should have a "label" and an optional "url".
# The URL should be a pattern containing "{id}" for the ID.
SHEETS_EXTERNAL_LINK_PATH = env.str(
    'SHEETS_EXTERNAL_LINK_PATH',
    os.path.join(ROOT_DIR, 'samplesheets/config/ext_links.json'),
)
# Remote sample sheet sync interval in minutes
SHEETS_SYNC_INTERVAL = env.int('SHEETS_SYNC_INTERVAL', 5)
# BAM/CRAM file path glob patterns to omit from study shortcuts and IGV sessions
SHEETS_IGV_OMIT_BAM = env.list(
    'SHEETS_IGV_OMIT_BAM', default=['*dragen_evidence.bam']
)
# VCF file path glob patterns to omit from study shortcuts and IGV sessions
SHEETS_IGV_OMIT_VCF = env.list(
    'SHEETS_IGV_OMIT_VCF',
    default=['*cnv.vcf.gz', '*ploidy.vcf.gz', '*sv.vcf.gz'],
)
# Default allowed hosts for iRODS access tickets.
# Can be overridden by project and ticket.
SHEETS_IRODS_TICKET_HOSTS = env.list('SHEETS_IRODS_TICKET_HOSTS', default=[])
# Restrict SampleDataFileExistsAPIView access to users with project roles
SHEETS_API_FILE_EXISTS_RESTRICT = env.bool(
    'SHEETS_API_FILE_EXISTS_RESTRICT', False
)
# Limit parser warnings to be saved in the database to N per investigation
SHEETS_PARSER_WARNING_SAVE_LIMIT = env.int(
    'SHEETS_PARSER_WARNING_SAVE_LIMIT', 100
)

# Landingzones app settings
# Status query interval in seconds
LANDINGZONES_STATUS_INTERVAL = env.int('LANDINGZONES_STATUS_INTERVAL', 3)
# Enable automated move triggering based on touched file
LANDINGZONES_TRIGGER_ENABLE = env.bool('LANDINGZONES_TRIGGER_ENABLE', True)
# Automatic move triggering check interval in seconds
LANDINGZONES_TRIGGER_MOVE_INTERVAL = env.int(
    'LANDINGZONES_TRIGGER_MOVE_INTERVAL', 30
)
# File name for automated move triggering
LANDINGZONES_TRIGGER_FILE = env.str(
    'LANDINGZONES_TRIGGER_FILE', '.sodar_validate_and_move'
)
# Disable non-superuser uploads via landing zones, useful for e.g. demo servers
LANDINGZONES_DISABLE_FOR_USERS = env.bool(
    'LANDINGZONES_DISABLE_FOR_USERS', False
)
# Limit creation of active landing zones per project (0 or None = no limit)
LANDINGZONES_ZONE_CREATE_LIMIT = env.int('LANDINGZONES_ZONE_CREATE_LIMIT', None)
# Limit concurrent landing zone validations per project (1 or more)
LANDINGZONES_ZONE_VALIDATE_LIMIT = env.int(
    'LANDINGZONES_ZONE_VALIDATE_LIMIT', 1
)
# Landing zone file list modal page size
LANDINGZONES_FILE_LIST_PAGINATION = env.int(
    'LANDINGZONES_FILE_LIST_PAGINATION', 15
)

# Landingzones configapp plugin settings
LZ_BIH_PROTEOMICS_SMB_EXPIRY_DAYS = env.int(
    'LZ_BIH_PROTEOMICS_SMB_EXPIRY_DAYS', 14
)
LZ_BIH_PROTEOMICS_SMB_USER = env.str(
    'LZ_BIH_PROTEOMICS_SMB_USER', 'bih_proteomics_smb'
)
LZ_BIH_PROTEOMICS_SMB_PASS = env.str('LZ_BIH_PROTEOMICS_SMB_PASS', 'CHANGE ME!')

# Ontologyaccess settings
ONTOLOGYACCESS_BULK_CREATE = env.int('ONTOLOGYACCESS_BULK_CREATE', 5000)
ONTOLOGYACCESS_QUERY_LIMIT = env.int('ONTOLOGYACCESS_QUERY_LIMIT', 250)

# Isatemplates settings
# Enable templates from cubi-isa-templates
ISATEMPLATES_ENABLE_CUBI_TEMPLATES = env.bool(
    'ISATEMPLATES_ENABLE_CUBI_TEMPLATES', True
)


# Settings for HTTP AuthBasic
BASICAUTH_REALM = env.str(
    'BASICAUTH_REALM', 'Log in with your SODAR user name and password.'
)
BASICAUTH_DISABLE = env.bool('BASICAUTH_DISABLE', False)
