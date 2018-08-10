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
    entry_point_url_id = 'adminalerts:list'

    #: Required permission for displaying the app
    app_permission = 'adminalerts.create_alert'

    def get_messages(self, user=None):
        """
        Return a list of messages to be shown to users.
        :param user: User object (optional)
        :return: List of dicts or and empty list if no messages
        """
        messages = []
        alerts = AdminAlert.objects.filter(
            active=True, date_expire__gte=timezone.now()).order_by('-pk')

        for a in alerts:
            content = '<i class="fa fa-exclamation-triangle"></i> ' + a.message

            if a.description.raw:
                content += \
                    '<span class="pull-right"><a href="{}" class="text-info">' \
                    '<i class="fa fa-arrow-circle-right"></i> ' \
                    'Details</a>'.format(
                        reverse(
                            'adminalerts:detail',
                            kwargs={'uuid': a.omics_uuid}))

            messages.append({
                'content': content,
                'color': 'info',
                'dismissable': False})

        return messages
