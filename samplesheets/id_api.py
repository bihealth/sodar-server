"""Class for Treuhandstelle proof-of-concept ID check"""

# TODO: Replace with a plugin structure allowing for adding more ID modules

import logging
import requests
import time

from keycloak import KeycloakOpenID


logger = logging.getLogger(__name__)


CHECK_URL = 'participant/get-by-psn'


class IDServiceAPI:
    """ID service wrapper (will be used for a plugin structure)"""

    auth_config = None
    api_config = None

    def __init__(self, config):
        """
        Initialize the wrapped API.

        :param config: ID service configuration (dict)
        """
        # TODO: Validate config
        self.auth_config = config['auth']
        self.api_config = config['api']

    def check_id(self, name):
        """Check source ID in THS if enabled"""
        open_id = KeycloakOpenID(
            server_url=self.auth_config['server_url'],
            client_id=self.auth_config['client_id'],
            realm_name=self.auth_config['realm_name'],
            client_secret_key=self.auth_config['client_secret_key'],
            verify=False,
        )
        token = open_id.token(
            self.auth_config['username'], self.auth_config['password']
        )
        url = '{}api/v{}/{}'.format(
            self.api_config['base_url'], self.api_config['version'], CHECK_URL
        )
        params = {'psn': name}
        headers = {
            'content-type': 'application/json',
            'user-agent': 'Treuhandstellen Python SDK',
            'connection': 'keep-alive',
            'nonce': str(time.time()),
            'authorization': 'Bearer {}'.format(token['access_token']),
        }
        response = requests.get(
            url, params=params, headers=headers, verify=False
        )
        content = response.json()
        status_code = response.status_code
        logger.debug('Response: {} ({})'.format(content, status_code))
        open_id.logout(token['refresh_token'])  # TODO: Is logout needed?
        if status_code != 200:
            raise Exception(
                'Unable to verify source ID in Treuhandstelle: {} ({})'.format(
                    content, status_code
                )
            )
