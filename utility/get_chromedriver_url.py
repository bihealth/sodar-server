"""
Script to retrieve URL for the latest Chromedriver version from Google's
"Chrome for Testing" channel (new since Chrome v115).

See:
https://googlechromelabs.github.io/chrome-for-testing/
https://github.com/GoogleChromeLabs/chrome-for-testing#json-api-endpoints
"""

import json
import sys
import urllib.request


API_URL = (
    'https://googlechromelabs.github.io/chrome-for-testing/'
    'last-known-good-versions.json'
)
DL_URL = (
    'https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/'
    '{driver_version}/{platform}/chromedriver-linux64.zip'
)
PLATFORM = 'linux64'


def main():
    response = urllib.request.urlopen(API_URL).read()
    data = json.loads(response.decode('utf-8'))
    sys.stdout.write(
        DL_URL.format(
            driver_version=data['channels']['Stable']['version'],
            platform=PLATFORM,
        )
    )


if __name__ == "__main__":
    main()
