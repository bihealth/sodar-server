"""
Django settings for the SODAR project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import os
import re

import environ

SITE_PACKAGE = 'sodar'
ROOT_DIR = environ.Path(__file__) - 3
APPS_DIR = ROOT_DIR.path(SITE_PACKAGE)

# Load operating system environment variables and then prepare to use them
env = environ.Env()

# .env file, should load only in development environment
READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', default=False)

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
    'rules.apps.AutodiscoverRulesConfig',  # Django rules engine
    'djangoplugins',  # Django plugins
    'pagedown',  # For markdown
    'markupfield',  # For markdown
    'db_file_storage',  # For storing files in database
    'rest_framework',  # For API views
    'knox',  # For token auth
    'docs',  # For the online user documentation/manual
    'dal',  # For user search combo box
    'dal_select2',
    'dj_iconify.apps.DjIconifyConfig',  # Iconify for SVG icons
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
    'taskflowbackend.apps.TaskflowbackendConfig',
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
    # General site apps
    'siteinfo.apps.SiteinfoConfig',
    'irodsinfo.apps.IrodsinfoConfig',
    'ontologyaccess.apps.OntologyaccessConfig',
    # Samplesheets study sub-apps
    'samplesheets.studyapps.germline.apps.GermlineConfig',
    'samplesheets.studyapps.cancer.apps.CancerConfig',
    # Samplesheets assay sub-apps
    'samplesheets.assayapps.dna_sequencing.apps.DnaSequencingConfig',
    'samplesheets.assayapps.meta_ms.apps.MetaMsConfig',
    'samplesheets.assayapps.microarray.apps.MicroarrayConfig',
    'samplesheets.assayapps.pep_ms.apps.PepMsConfig',
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
ADMINS = [("""Mikko Nieminen""", 'mikko.nieminen@bihealth.de')]

# See: https://docs.djangoproject.com/en/1.11/ref/settings/#managers
MANAGERS = ADMINS

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/1.11/ref/settings/#databases
# Uses django-environ to accept uri format
# See: https://django-environ.readthedocs.io/en/latest/#supported-types
DATABASES = {'default': env.db('DATABASE_URL', default='postgres:///sodar')}
DATABASES['default']['ATOMIC_REQUESTS'] = False

# Set default auto field (for Django 3.2+)
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Set django-db-file-storage as the default storage
DEFAULT_FILE_STORAGE = 'db_file_storage.storage.DatabaseFileStorage'

# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Berlin'

# See: https://docs.djangoproject.com/en/1.11/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/1.11/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/1.11/ref/settings/#use-i18n
USE_I18N = False

# See: https://docs.djangoproject.com/en/1.11/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/1.11/ref/settings/#use-tz
USE_TZ = True

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/1.11/ref/settings/#templates
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

# Location of root django.contrib.admin URL, use {% url 'admin:index' %}
ADMIN_URL = r'^admin/'


# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', 'redis://localhost:6379/0')
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


# Django REST framework default auth classes
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'knox.auth.TokenAuthentication',
    ),
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}


# LDAP configuration
# ------------------------------------------------------------------------------

# Enable LDAP if configured
ENABLE_LDAP = env.bool('ENABLE_LDAP', False)
ENABLE_LDAP_SECONDARY = env.bool('ENABLE_LDAP_SECONDARY', False)

if ENABLE_LDAP:
    import itertools
    import ldap
    from django_auth_ldap.config import LDAPSearch

    # Default values
    LDAP_DEFAULT_CONN_OPTIONS = {ldap.OPT_REFERRALS: 0}
    LDAP_DEFAULT_FILTERSTR = '(sAMAccountName=%(user)s)'
    LDAP_DEFAULT_ATTR_MAP = {
        'first_name': 'givenName',
        'last_name': 'sn',
        'email': 'mail',
    }

    # Primary LDAP server
    AUTH_LDAP_SERVER_URI = env.str('AUTH_LDAP_SERVER_URI', None)
    AUTH_LDAP_BIND_DN = env.str('AUTH_LDAP_BIND_DN', None)
    AUTH_LDAP_BIND_PASSWORD = env.str('AUTH_LDAP_BIND_PASSWORD', None)
    AUTH_LDAP_CONNECTION_OPTIONS = LDAP_DEFAULT_CONN_OPTIONS

    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        env.str('AUTH_LDAP_USER_SEARCH_BASE', None),
        ldap.SCOPE_SUBTREE,
        LDAP_DEFAULT_FILTERSTR,
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
        AUTH_LDAP2_CONNECTION_OPTIONS = LDAP_DEFAULT_CONN_OPTIONS

        AUTH_LDAP2_USER_SEARCH = LDAPSearch(
            env.str('AUTH_LDAP2_USER_SEARCH_BASE', None),
            ldap.SCOPE_SUBTREE,
            LDAP_DEFAULT_FILTERSTR,
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


# Logging
# ------------------------------------------------------------------------------


def set_logging(debug):
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            }
        },
        'loggers': {
            'irodsbackend': {
                'level': 'DEBUG' if debug else 'ERROR',
                'handlers': ['console'],
                'propagate': True,
            },
            'landingzones': {
                'level': 'DEBUG' if debug else 'ERROR',
                'handlers': ['console'],
                'propagate': True,
            },
            'ontologyaccess': {
                'level': 'DEBUG' if debug else 'ERROR',
                'handlers': ['console'],
                'propagate': True,
            },
            'projectroles': {
                'level': 'DEBUG' if debug else 'ERROR',
                'handlers': ['console'],
                'propagate': True,
            },
            'samplesheets': {
                'level': 'DEBUG' if debug else 'ERROR',
                'handlers': ['console'],
                'propagate': True,
            },
            'sodarcache': {
                'level': 'DEBUG' if debug else 'ERROR',
                'handlers': ['console'],
                'propagate': True,
            },
            'irodsadmin': {
                'level': 'ERROR',
                'handlers': ['console'],
                'propagate': True,
            },
        },
    }


LOGGING = set_logging(DEBUG)


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
    None,
    [
        'timeline_backend',
        'appalerts_backend',
        'sodar_cache',
        'ontologyaccess_backend',
        # 'taskflow',
        # 'omics_irods',
    ],
)


# General site settings
SITE_TITLE = 'SODAR'
SITE_SUBTITLE = env.str('SITE_SUBTITLE', 'Beta')
SITE_INSTANCE_TITLE = env.str('SITE_INSTANCE_TITLE', 'CUBI SODAR')


# General API settings
SODAR_API_DEFAULT_VERSION = '0.9.0'
SODAR_API_ALLOWED_VERSIONS = ['0.7.0', '0.7.1', '0.8.0', '0.9.0']
SODAR_API_MEDIA_TYPE = 'application/vnd.bihealth.sodar+json'
SODAR_API_DEFAULT_HOST = env.url(
    'SODAR_API_DEFAULT_HOST', 'http://127.0.0.1:8000'
)


# Projectroles app settings
PROJECTROLES_SITE_MODE = env.str('PROJECTROLES_SITE_MODE', 'SOURCE')
PROJECTROLES_SECRET_LENGTH = 32
PROJECTROLES_INVITE_EXPIRY_DAYS = env.int('PROJECTROLES_INVITE_EXPIRY_DAYS', 14)
PROJECTROLES_SEND_EMAIL = env.bool('PROJECTROLES_SEND_EMAIL', False)
PROJECTROLES_EMAIL_SENDER_REPLY = env.bool(
    'PROJECTROLES_EMAIL_SENDER_REPLY', False
)
PROJECTROLES_HELP_HIGHLIGHT_DAYS = 7
PROJECTROLES_ENABLE_SEARCH = True
PROJECTROLES_SEARCH_PAGINATION = 5
PROJECTROLES_DELEGATE_LIMIT = env.int('PROJECTROLES_DELEGATE_LIMIT', 1)
PROJECTROLES_DEFAULT_ADMIN = env.str('PROJECTROLES_DEFAULT_ADMIN', 'admin')
PROJECTROLES_ALLOW_LOCAL_USERS = env.bool(
    'PROJECTROLES_ALLOW_LOCAL_USERS', False
)
PROJECTROLES_DISABLE_CATEGORIES = env.bool(
    'PROJECTROLES_DISABLE_CATEGORIES', False
)

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


# Timeline app settings
TIMELINE_PAGINATION = 15


# Adminalerts app settings
ADMINALERTS_PAGINATION = 15


# SODAR site specific settings (not derived from SODAR Core)
SODAR_SUPPORT_EMAIL = env.str(
    'SODAR_SUPPORT_EMAIL', 'cubi-helpdesk@bihealth.de'
)
SODAR_SUPPORT_NAME = env.str('SODAR_SUPPORT_NAME', 'CUBI Helpdesk')


# iRODS settings shared by iRODS using apps
ENABLE_IRODS = env.bool('ENABLE_IRODS', True)
IRODS_HOST = env.str('IRODS_HOST', '127.0.0.1')
IRODS_PORT = env.int('IRODS_PORT', 4477)
IRODS_ZONE = env.str('IRODS_ZONE', 'omicsZone')
IRODS_ROOT_PATH = env.str('IRODS_ROOT_PATH', None)
IRODS_USER = env.str('IRODS_USER', 'rods')
IRODS_PASS = env.str('IRODS_PASS', 'rods')
IRODS_SAMPLE_COLL = 'sample_data'
IRODS_LANDING_ZONE_COLL = 'landing_zones'

# Optional iRODS env file
# (recommended: place in STATIC_ROOT + '/irods/irods_environment.json')
IRODS_ENV_PATH = env.str('IRODS_ENV_PATH', None)

# Optional iRODS certificate path
IRODS_CERT_PATH = env.str(
    'IRODS_CERT_PATH', STATIC_ROOT + '/irods/irods_server.crt'
)


# Taskflow backend settings
TASKFLOW_TARGETS = ['irods', 'sodar']
TASKFLOW_BACKEND_HOST = env.str('TASKFLOW_BACKEND_HOST', 'http://127.0.0.1')
TASKFLOW_BACKEND_PORT = env.int('TASKFLOW_BACKEND_PORT', 5005)
TASKFLOW_SODAR_SECRET = env.str('TASKFLOW_SODAR_SECRET', 'CHANGE ME!')
TASKFLOW_TEST_MODE = False  # Important to protect iRODS data


# Samplesheets and Landingzones link settings
IRODS_WEBDAV_ENABLED = env.bool('IRODS_WEBDAV_ENABLED', True)
IRODS_WEBDAV_URL = env.str('IRODS_WEBDAV_URL', 'https://127.0.0.1')
IRODS_WEBDAV_URL_ANON = env.str('IRODS_WEBDAV_URL_ANON', IRODS_WEBDAV_URL)
IRODS_WEBDAV_URL_ANON_TMPL = re.sub(
    r'^(https?://)(.*)$', r'\1{user}:{ticket}@\2{path}', IRODS_WEBDAV_URL_ANON
)
IRODS_WEBDAV_USER_ANON = env.str('IRODS_WEBDAV_USER_ANON', 'ticket')


# Irodsbackend settings
# Status query interval in seconds
IRODSBACKEND_STATUS_INTERVAL = env.int('IRODSBACKEND_STATUS_INTERVAL', 15)
# Set batch query size for improving sequential iRODS query performance (#432)
IRODS_QUERY_BATCH_SIZE = env.int('IRODS_QUERY_BATCH_SIZE', 24)


# Irodsinfo settings
# In the generated iRODS config, require SSL cert verification unless False
IRODSINFO_SSL_VERIFY = env.bool('IRODSINFO_SSL_VERIFY', True)
# Path to iRODS env file appended to client env file (default=IRODS_ENV_PATH)
IRODSINFO_ENV_PATH = env.str('IRODSINFO_ENV_PATH', IRODS_ENV_PATH)


# Samplesheets settings

# Allow critical altamISA warnings on import
SHEETS_ALLOW_CRITICAL = env.bool('SHEETS_ALLOW_CRITICAL', False)
SHEETS_ENABLE_CACHE = True  # Temporary, see issue #556
SHEETS_IRODS_LIMIT = env.int('SHEETS_IRODS_LIMIT', 50)  # iRODS file query limit
SHEETS_TABLE_HEIGHT = 400  # Study/assay table height
SHEETS_CONFIG_VERSION = '0.8.0'  # Minimum edit config version
SHEETS_MIN_COLUMN_WIDTH = 100  # Min default column width
SHEETS_MAX_COLUMN_WIDTH = 300  # Max default column width
SHEETS_VERSION_PAGINATION = env.int('SHEETS_VERSION_PAGINATION', 15)
SHEETS_IRODS_TICKET_PAGINATION = env.int('SHEETS_IRODS_TICKET_PAGINATION', 15)
SHEETS_IRODS_REQUEST_PAGINATION = env.int('SHEETS_IRODS_REQUEST_PAGINATION', 15)
SHEETS_ONTOLOGY_URL_TEMPLATE = (
    'https://bioportal.bioontology.org/ontologies/'
    '{ontology_name}/?p=classes&conceptid={accession}'
)
# Skip URL template modification if substring found in accession
SHEETS_ONTOLOGY_URL_SKIP = ['bioontology.org']

SHEETS_EXTERNAL_LINK_LABELS = {
    'x-bih-buch-genomics-wetlab-id': 'Wetlab-ID assigned by BIH genomics unit '
    'in Buch',
    'x-bih-cvk-genomics-wetlab-id': 'Wetlab-ID assigned by BIH genomics unit '
    'in CVK',
    'x-bih-tcell2015-id': 'ID assigned in "T-CELL 2015" project ran at BIH',
    'x-cegat-sequencing-id': 'CeGaT Sequencing ID',
    'x-charite-bcrt-genomics-wetlab-id': 'BCRT Genomics Wet-Lab ID',
    'x-charite-medgen-array-id': 'Charite Medical Genetics Array ID',
    'x-charite-medgen-blood-book-id': 'Charite Medical Genetics Blood Book ID',
    'x-dkfz-1touch-id': 'ID assigned through Heidelberg one-touch pipeline',
    'x-dkfz-ilse-id': 'ID assigned through DFKZ sequencing',
    'x-dkfz-mtk-id': 'ID assigned through DFKZ sequencing for the Molecular '
    'Tumor Conference project',
    'x-labor-berlin-blood-book-id': 'Labor Berlin Blood Book ID',
    'x-generic-remote': 'External ID',
}

# HACK: Supported cubi-tk templates, excluding ones which altamISA cannot parse
SHEETS_ENABLED_TEMPLATES = [
    'generic',
    'germline',
    'ms_meta_biocrates',
]


# Settings for sync sheets in minutes
SHEETS_SYNC_INTERVAL = env.int('SHEETS_SYNC_INTERVAL', 5)


# Landingzones app settings
# Status query interval in seconds
LANDINGZONES_STATUS_INTERVAL = env.int('LANDINGZONES_STATUS_INTERVAL', 3)
# Automatic move triggering check interval in seconds
LANDINGZONES_TRIGGER_MOVE_INVERVAL = env.int(
    'LANDINGZONES_TRIGGER_MOVE_INTERVAL', 30
)
LANDINGZONES_TRIGGER_FILE = env.str(
    'LANDINGZONES_TRIGGER_FILE', '.sodar_validate_and_move'
)

# Landingzones configapp plugin settings
LZ_BIH_PROTEOMICS_SMB_EXPIRY_DAYS = env.int(
    'LZ_BIH_PROTEOMICS_SMB_EXPIRY_DAYS', 14
)
LZ_BIH_PROTEOMICS_SMB_USER = env.str(
    'LZ_BIH_PROTEOMICS_SMB_USER', 'bih_proteomics_smb'
)
LZ_BIH_PROTEOMICS_SMB_PASS = env.str(
    'LZ_BIH_PROTEOMICS_SMB_PASS', 'eech1Iekvaivai6A'
)


# Ontologyaccess settings
ONTOLOGYACCESS_BULK_CREATE = env.int('ONTOLOGYACCESS_BULK_CREATE', 5000)
ONTOLOGYACCESS_QUERY_LIMIT = env.int('ONTOLOGYACCESS_QUERY_LIMIT', 250)


# Settings for HTTP AuthBasic
BASICAUTH_REALM = (
    'Login with user@CHARITE or user@MDC-BERLIN and your password.'
)
BASICAUTH_DISABLE = False
