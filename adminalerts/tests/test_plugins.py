"""Plugin tests for the adminalerts app"""

from django.urls import reverse
from test_plus.test import TestCase

# Projectroles dependency
from projectroles.plugins import SiteAppPluginPoint

from ..urls import urlpatterns
from .test_models import AdminAlertMixin


PLUGIN_NAME = 'adminalerts'
PLUGIN_TITLE = 'Alerts'
PLUGIN_URL_ID = 'adminalerts:list'


# NOTE: Setting up the plugin is done during migration


class TestPlugins(TestCase, AdminAlertMixin):
    """Test adminalerts plugin"""

    def setUp(self):
        # Create users
        self.superuser = self.make_user('superuser')
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()

        # Create alert
        self.alert = self._make_alert(
            message='alert',
            user=self.superuser,
            description='description',
            active=True)

    def test_plugin_retrieval(self):
        """Test retrieving the plugin from the database"""
        plugin = SiteAppPluginPoint.get_plugin(PLUGIN_NAME)
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.get_model().name, PLUGIN_NAME)
        self.assertEqual(plugin.name, PLUGIN_NAME)
        self.assertEqual(plugin.get_model().title, PLUGIN_TITLE)
        self.assertEqual(plugin.title, PLUGIN_TITLE)
        self.assertEqual(plugin.entry_point_url_id, PLUGIN_URL_ID)

    def test_plugin_urls(self):
        """Test plugin URLs to ensure they're the same as in the app config"""
        plugin = SiteAppPluginPoint.get_plugin(PLUGIN_NAME)
        self.assertEqual(plugin.urls, urlpatterns)

    def test_get_messages(self):
        """Test the get_messages() function"""
        plugin = SiteAppPluginPoint.get_plugin(PLUGIN_NAME)
        messages = plugin.get_messages()
        message = messages[0]

        self.assertEqual(len(messages), 1)
        self.assertIn(self.alert.message, message['content'])
        self.assertEqual(message['color'], 'info')
        self.assertEqual(message['dismissable'], False)
