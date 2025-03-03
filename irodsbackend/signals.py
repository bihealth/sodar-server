"""Signals for the irodsbackend app"""

import logging

from irods.exception import UserDoesNotExist

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.urls import reverse

# Projectroles dependency
from projectroles.models import AUTH_TYPE_OIDC
from projectroles.plugins import get_backend_api


logger = logging.getLogger(__name__)


APP_NAME = 'omics_irods'
REGULAR_USER_PW_MSG = 'You can log in with the same password you use for SODAR.'
OIDC_USER_PW_MSG = (
    'You need to create an API token to use as your iRODS password.'
)


def create_irods_user(sender, user, **kwargs):
    """Signal for creating iRODS user for LDAP user or SODAR auth"""
    try:
        irods_backend = get_backend_api('omics_irods')
    except Exception as ex:
        logger.error('Exception initializing irodsbackend: {}'.format(ex))
        return
    if not irods_backend or (
        not hasattr(user, 'ldap_username') and not settings.IRODS_SODAR_AUTH
    ):
        logger.debug(
            'Skipping iRODS user creation for user "{}"'.format(user.username)
        )
        return  # Skip for local users without SODAR auth, or if no iRODS conn

    # Set username
    # TODO: Use a common method for this (see sodar-core#1056)
    if hasattr(user, 'ldap_username') and user.username.find('@') != -1:
        u_split = user.username.split('@')
        user_name = u_split[0] + '@' + u_split[1].upper()
    else:
        user_name = user.username

    try:
        with irods_backend.get_session() as irods:
            try:
                irods.users.get(user_name)
                logger.debug(
                    'Skipping iRODS user creation, user "{}" already '
                    'exists'.format(user_name)
                )
            except UserDoesNotExist:
                logger.info('Creating user "{}" in iRODS..'.format(user_name))
                # Create user
                try:
                    irods.users.create(
                        user_name=user_name,
                        user_type='rodsuser',
                        user_zone=settings.IRODS_ZONE,
                    )
                except Exception as ex:
                    logger.error(
                        'Exception creating user in iRODS: {}'.format(ex)
                    )
                    return
                # Add user alert
                app_alerts = get_backend_api('appalerts_backend')
                if app_alerts:
                    if user.get_auth_type() == AUTH_TYPE_OIDC:
                        pw_msg = OIDC_USER_PW_MSG
                        alert_url = reverse('tokens:list')
                    else:
                        pw_msg = REGULAR_USER_PW_MSG
                        alert_url = reverse('irodsinfo:info')
                    app_alerts.add_alert(
                        app_name=APP_NAME,
                        alert_name='irods_user_create',
                        user=user,
                        message='User account "{}" created in iRODS. {}'.format(
                            user_name, pw_msg
                        ),
                        url=alert_url,
                    )
                logger.info('User creation OK')
    except Exception as ex:
        # NOTE: Logging warning because this does not actually prevent login
        logger.warning(
            'Unable to update user in iRODS, exception in opening session: '
            '{}'.format(ex)
        )


# Connect signal
user_logged_in.connect(create_irods_user)
