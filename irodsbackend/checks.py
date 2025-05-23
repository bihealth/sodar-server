"""Django checks for the irodsbackend app"""

from django.conf import settings
from django.core.checks import Error, Warning, register


# Projectroles dependency
from projectroles.plugins import get_app_plugin


W001_MSG = (
    'iRODS and OIDC authentication are enabled, but SODAR_IRODS_AUTH is '
    'disabled. You need to enable SODAR_IRODS_AUTH for OIDC users to access '
    'iRODS.'
)
W001 = Warning(W001_MSG, obj=settings, id='irodsbackend.W001')

W002_MSG = (
    'iRODS is enabled with only local user authentication, but '
    'SODAR_IRODS_AUTH is disabled. You need to enable SODAR_IRODS_AUTH for '
    'local users to access iRODS.'
)
W002 = Warning(W002_MSG, obj=settings, id='irodsbackend.W002')

W003_MSG = (
    'iRODS and OIDC authentication are enabled, but the tokens site app is not '
    'enabled. Enable the tokens app to provide SODAR API tokens for OIDC '
    'users to access iRODS.'
)
W003 = Warning(W003_MSG, obj=settings, id='irodsbackend.W003')

E001_MSG = (
    'Invalid value for IRODS_HASH_SCHEME. Accepted values are "MD5" and '
    '"SHA256".'
)
E001 = Error(E001_MSG, obj=settings, id='irodsbackend.E001')


@register()
def check_sodar_auth_oidc(app_configs, **kwargs):
    """Check if SODAR auth for iRODS is enabled for OIDC users"""
    ret = []
    if (
        settings.ENABLE_IRODS
        and not settings.IRODS_SODAR_AUTH
        and settings.ENABLE_OIDC
    ):
        ret.append(W001)
    return ret


@register()
def check_sodar_auth_local(app_configs, **kwargs):
    """Check if SODAR auth for iRODS is enabled for local users"""
    ret = []
    if (
        settings.ENABLE_IRODS
        and not settings.IRODS_SODAR_AUTH
        and not settings.ENABLE_OIDC
        and not settings.ENABLE_LDAP
    ):
        ret.append(W002)
    return ret


@register()
def check_token_app_oidc(app_configs, **kwargs):
    """Check if tokens app is enabled for OIDC users"""
    ret = []
    if (
        settings.ENABLE_IRODS
        and settings.ENABLE_OIDC
        and not get_app_plugin('tokens')
    ):
        ret.append(W003)
    return ret


@register()
def check_irods_hash_scheme(app_configs, **kwargs):
    """Check for IRODS_HASH_SCHEME validity"""
    ret = []
    if settings.IRODS_HASH_SCHEME not in ['MD5', 'SHA256']:
        ret.append(E001)
    return ret
