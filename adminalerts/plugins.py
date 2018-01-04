from django.urls import reverse
from django.utils import timezone

# Projectroles dependency
from projectroles.plugins import SiteAppPluginPoint


from .models import AdminAlert
from .urls import urlpatterns


class SiteAppPlugin(SiteAppPluginPoint):
    """Projectroles plugin for registering the app"""

    #: Name (slug-safe, used in URLs)
    name = 'adminalerts'

    #: Title (used in templates)
    title = 'Alerts'

    #: App URLs (will be included in settings by djangoplugins)
    urls = urlpatterns

    #: FontAwesome icon ID string
    icon = 'exclamation-triangle'

    #: Description string
    description = 'Administrator alerts to be shown for users'

    #: Entry point URL ID
    entry_point_url_id = 'alert_list'

    #: Required permission for displaying the app
    app_permission = 'adminalerts.add_alert'

    def get_messages(self):
        """
        Return a list of messages to be shown to users.
        :return: List of dicts or and empty list if no messages
        """
        messages = []
        alerts = AdminAlert.objects.filter(
            active=True, date_expire__gte=timezone.now()).order_by('-pk')

        for a in alerts:
            content = '<i class="fa fa-exclamation-triangle"></i> ' + a.message

            if a.description:
                content += \
                    '<span class="pull-right"><a href="{}" class="text-info">' \
                    '<i class="fa fa-arrow-circle-right"></i> ' \
                    'Details</a>'.format(
                        reverse('alert_detail', kwargs={'pk': a.pk}))

            messages.append({
                'content': content,
                'color': 'info',
                'dismissable': False})

        return messages
