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

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
# NOTE: Hardcoding this due to issue #2288
AUTHENTICATION_BACKENDS = [
    'rules.permissions.ObjectPermissionBackend',  # For rules
    'django.contrib.auth.backends.ModelBackend',
]

# LDAP configuration
# ------------------------------------------------------------------------------

ENABLE_LDAP = False
ENABLE_LDAP_SECONDARY = False
LDAP_DEBUG = False
LDAP_ALT_DOMAINS = []


# OpenID Connect (OIDC) configuration
# ------------------------------------------------------------------------------

ENABLE_OIDC = False


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
    'isatemplates_backend',
    'taskflow',
    'omics_irods',
]

# Projectroles app settings
PROJECTROLES_SITE_MODE = 'SOURCE'
PROJECTROLES_SECRET_LENGTH = 32
PROJECTROLES_INVITE_EXPIRY_DAYS = 14
PROJECTROLES_SEND_EMAIL = True
PROJECTROLES_EMAIL_SENDER_REPLY = False
PROJECTROLES_EMAIL_HEADER = None
PROJECTROLES_EMAIL_FOOTER = None
PROJECTROLES_HELP_HIGHLIGHT_DAYS = 7
PROJECTROLES_ENABLE_SEARCH = True
PROJECTROLES_SEARCH_PAGINATION = 10  # Workaround for #360
PROJECTROLES_ROLE_PAGINATION = 15
PROJECTROLES_DELEGATE_LIMIT = 1
PROJECTROLES_DEFAULT_ADMIN = 'admin'
PROJECTROLES_ALLOW_LOCAL_USERS = True
PROJECTROLES_ALLOW_ANONYMOUS = False
PROJECTROLES_ENABLE_MODIFY_API = True
PROJECTROLES_MODIFY_API_APPS = ['taskflow', 'samplesheets', 'landingzones']
PROJECTROLES_DISABLE_CATEGORIES = False
PROJECTROLES_API_USER_DETAIL_RESTRICT = False
PROJECTROLES_SUPPORT_CONTACT = None
PROJECTROLES_BROWSER_WARNING = True
PROJECTROLES_DISABLE_CDN_INCLUDES = False
PROJECTROLES_CUSTOM_JS_INCLUDES = []
PROJECTROLES_CUSTOM_CSS_INCLUDES = []
PROJECTROLES_INLINE_HEAD_INCLUDE = None
PROJECTROLES_ENABLE_PROFILING = False

# Adminalerts app settings
ADMINALERTS_PAGINATION = 15

# Timeline app settings
TIMELINE_PAGINATION = 15

# Tokens app settings
TOKENS_CREATE_PROJECT_USER_RESTRICT = False

# iRODS settings shared by iRODS using apps
IRODS_HOST = '127.0.0.1'
IRODS_HOST_FQDN = IRODS_HOST
IRODS_PORT = 4488
IRODS_ZONE = 'sodarZone'
IRODS_ROOT_PATH = None
IRODS_USER = 'rods'
IRODS_PASS = 'rods'
IRODS_HASH_SCHEME = 'MD5'
IRODS_SAMPLE_COLL = 'sample_data'
IRODS_LANDING_ZONE_COLL = 'landing_zones'
IRODS_SODAR_AUTH = True
IRODS_WEBDAV_ENABLED = True
IRODS_ENV_DEFAULT = {'irods_default_hash_scheme': IRODS_HASH_SCHEME}
IRODS_ENV_BACKEND = {}
IRODS_ENV_CLIENT = {}
IRODS_CERT_PATH = None
IRODS_WEBDAV_ENABLED = True
IRODS_WEBDAV_URL = 'https://127.0.0.1'
IRODS_WEBDAV_URL_ANON = IRODS_WEBDAV_URL
IRODS_WEBDAV_USER_ANON = 'ticket'
IRODS_WEBDAV_IGV_PROXY = False

# Irodsbackend settings
IRODSBACKEND_STATUS_INTERVAL = 15
IRODS_QUERY_BATCH_SIZE = 24

# Isatemplates settings
ISATEMPLATES_ENABLE_CUBI_TEMPLATES = True

# Samplesheets app settings
SHEETS_ALLOW_CRITICAL = False
SHEETS_ENABLE_CACHE = False  # Temporarily disabled to fix CI, see issue #556
SHEETS_ENABLE_STUDY_TABLE_CACHE = True
SHEETS_IRODS_LIMIT = 50
SHEETS_MIN_COLUMN_WIDTH = 100
SHEETS_MAX_COLUMN_WIDTH = 300
SHEETS_VERSION_PAGINATION = 15
SHEETS_IRODS_TICKET_PAGINATION = 15
SHEETS_IRODS_REQUEST_PAGINATION = 15
SHEETS_ONTOLOGY_URL_TEMPLATE = (
    'https://bioportal.bioontology.org/ontologies/'
    '{ontology_name}/?p=classes&conceptid={accession}'
)
SHEETS_ONTOLOGY_URL_SKIP = ['bioontology.org', 'hpo.jax.org']
SHEETS_EXTERNAL_LINK_PATH = os.path.join(
    ROOT_DIR, 'samplesheets/tests/config/ext_links.json'
)
SHEETS_SYNC_ENABLE = True
SHEETS_SYNC_INTERVAL = 5
SHEETS_IGV_OMIT_BAM = ['*dragen_evidence.bam']
SHEETS_IGV_OMIT_VCF = ['*cnv.vcf.gz', '*ploidy.vcf.gz', '*sv.vcf.gz']
SHEETS_IRODS_TICKET_HOSTS = []
SHEETS_API_FILE_EXISTS_RESTRICT = False
SHEETS_PARSER_WARNING_SAVE_LIMIT = 100

# Landingzones app settings
LANDINGZONES_STATUS_INTERVAL = 3
LANDINGZONES_TRIGGER_ENABLE = True
LANDINGZONES_TRIGGER_MOVE_INTERVAL = 30
LANDINGZONES_TRIGGER_FILE = '.sodar_validate_and_move'
LANDINGZONES_DISABLE_FOR_USERS = False
LANDINGZONES_ZONE_CREATE_LIMIT = None
LANDINGZONES_ZONE_VALIDATE_LIMIT = 4
LANDINGZONES_FILE_LIST_PAGINATION = 25
LANDINGZONES_ZONE_MOVE_VERIFY = False
LZ_BIH_PROTEOMICS_SMB_EXPIRY_DAYS = 14
LZ_BIH_PROTEOMICS_SMB_USER = 'bih_proteomics_smb'
LZ_BIH_PROTEOMICS_SMB_PASS = 'CHANGE ME!'

# Ontologyaccess settings
ONTOLOGYACCESS_BULK_CREATE = 5000
ONTOLOGYACCESS_QUERY_LIMIT = 250

# Taskflowbackend settings
TASKFLOW_IRODS_CONN_TIMEOUT = 3600
TASKFLOW_LOCK_RETRY_COUNT = 2
TASKFLOW_LOCK_RETRY_INTERVAL = 3
TASKFLOW_ZONE_PROGRESS_INTERVAL = 60  # Set this high to ease testing
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
    'headless=new',
    'no-sandbox',  # For CI compatibility
    'disable-dev-shm-usage',  # For testing stability
]
PROJECTROLES_TEST_UI_WINDOW_SIZE = (1400, 1000)
PROJECTROLES_TEST_UI_WAIT_TIME = 30
PROJECTROLES_TEST_UI_LEGACY_LOGIN = env.bool(
    'PROJECTROLES_TEST_UI_LEGACY_LOGIN', False
)
