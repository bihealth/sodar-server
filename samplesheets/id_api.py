"""Class for Treuhandstelle proof-of-concept ID check"""

# TODO: Replace with a plugin structure allowing for adding more ID modules

import logging

from treuhandstelle import (
    AuthServer as THSAuthServer,
    ApiServer as THSApiServer,
    Treuhandstelle,
)


logger = logging.getLogger(__name__)


class IDServiceAPI:
    """ID service wrapper (will be used for a plugin structure)"""

    #: Actual THS API
    ths = None

    def __init__(self, config):
        """
        Initialize the wrapped API.

        :param config: ID service configuration (dict)
        """
        auth_server = THSAuthServer(
            verify_https=False, autorefresh=True, **config['auth']
        )
        api_server = THSApiServer(
            verify_https=False, proxies={}, **config['api']
        )
        self.ths = Treuhandstelle(auth_server, api_server)

    def check_id(self, name):
        """Check source ID in THS if enabled"""
        if not self.ths:
            raise Exception('THS not initialized')
        content, status_code, headers = self.ths.get_person_by_psn(name)
        logger.debug('THS result: {} ({})'.format(content, status_code))
        if status_code != 200:
            raise Exception(
                'Unable to verify source ID in Treuhandstelle: {} ({})'.format(
                    content, status_code
                )
            )
