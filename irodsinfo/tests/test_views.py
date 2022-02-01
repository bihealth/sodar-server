"""Tests for UI views in the irodsinfo app"""

import io
import json
import os
import zipfile

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from test_plus.test import TestCase
from unittest import skipIf

# Projectroles depedency
from projectroles.plugins import get_backend_api, change_plugin_status


# Local constants
CERT_PATH = os.path.dirname(__file__) + '/data/irods_server_crt.txt'
IRODS_ENV = {'test': 1}
IRODS_BACKEND_ENABLED = (
    True if 'omics_irods' in settings.ENABLED_BACKEND_PLUGINS else False
)
IRODS_BACKEND_SKIP_MSG = 'iRODS backend not enabled in settings'


class TestIrodsinfoViewBase(TestCase):
    """Base class for irodsinfo view tests"""

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()
        self.regular_user = self.make_user('regular_user')

        # No user
        self.anonymous = None


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsInfoView(TestIrodsinfoViewBase):
    """Tests for IrodsInfoView"""

    def test_render(self):
        """Test rendering irods info view with irodsbackend"""
        with self.login(self.regular_user):
            response = self.client.get(reverse('irodsinfo:info'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['irods_backend_enabled'])

    def test_render_no_backend(self):
        """Test rendering irods info view without irodsbackend"""
        if get_backend_api('omics_irods'):
            change_plugin_status(
                name='omics_irods', status=1, plugin_type='backend'
            )
        with self.login(self.regular_user):
            response = self.client.get(reverse('irodsinfo:info'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['irods_backend_enabled'])


@skipIf(not IRODS_BACKEND_ENABLED, IRODS_BACKEND_SKIP_MSG)
class TestIrodsConfigView(TestIrodsinfoViewBase):
    """Tests for IrodsConfigView"""

    def test_serve(self):
        """Test serving irods config"""
        with self.login(self.regular_user):
            response = self.client.get(reverse('irodsinfo:config'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/zip')
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename={}'.format('irods_config.zip'),
        )
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertEqual(len(zip_file.infolist()), 1)
        env_data = json.loads(
            zip_file.read(zip_file.infolist()[0]).decode('utf8')
        )
        self.assertEqual(('test', 1) in env_data.items(), False)

    @override_settings(IRODS_ENV_CLIENT=IRODS_ENV)
    def test_serve_env(self):
        """Test serving irods config with provided env"""
        with self.login(self.regular_user):
            response = self.client.get(reverse('irodsinfo:config'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/zip')
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename={}'.format('irods_config.zip'),
        )
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertEqual(len(zip_file.infolist()), 1)
        env_data = json.loads(
            zip_file.read(zip_file.infolist()[0]).decode('utf8')
        )
        self.assertEqual(('test', 1) in env_data.items(), True)

    @override_settings(IRODS_CERT_PATH=CERT_PATH)
    def test_serve_cert(self):
        """Test serving irods config with server cert"""
        with self.login(self.regular_user):
            response = self.client.get(reverse('irodsinfo:config'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/zip')
        self.assertEqual(
            response.get('Content-Disposition'),
            'attachment; filename={}'.format('irods_config.zip'),
        )
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertEqual(len(zip_file.infolist()), 2)
