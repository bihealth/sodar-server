"""API for accessing the Django Taskflow REST service"""

# TODO: Remove, not needed anymore

import requests

from django.conf import settings


TL_URL = 'timeline/taskflow/status/set'
ZONE_URL = 'zones/taskflow/status/set'


class SODARRequestException(Exception):
    """General django REST API submission exception"""


class SODARAPI:
    """API for accessing the Django Taskflow REST views"""

    def __init__(self, sodar_url):
        self.sodar_url = sodar_url

    def send_request(self, url, query_data):
        request_url = self.sodar_url + '/' + url
        query_data['sodar_secret'] = settings.TASKFLOW_SODAR_SECRET
        response = requests.post(request_url, data=query_data)

        if response.status_code != 200:
            raise SODARRequestException(
                '{}: {}'.format(
                    response.status_code, response.text or 'Unknown'
                )
            )

        return response

    def set_timeline_status(
        self, event_uuid, status_type, status_desc=None, extra_data=None
    ):
        set_data = {
            'event_uuid': event_uuid,
            'status_type': status_type,
            'status_desc': status_desc,
            'extra_data': extra_data,
            'sodar_secret': settings.TASKFLOW_SODAR_SECRET,
        }
        self.send_request(TL_URL, set_data)
