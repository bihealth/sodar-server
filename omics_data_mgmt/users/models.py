from django.contrib.auth.models import AbstractUser
from django.contrib.auth.signals import user_logged_in
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = models.CharField(_('Name of User'), blank=True, max_length=255)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:user_detail', kwargs={'username': self.username})


def handle_ldap_login(sender, user, **kwargs):
    """Handle LDAP logins here as needed"""

    if hasattr(user, 'ldap_username'):

        # Make domain in username uppercase
        if (user.username.find('@') != -1 and
                user.username.split('@')[1].islower()):
            u_split = user.username.split('@')
            user.username = u_split[0] + '@' + u_split[1].upper()
            user.save()

        # Save user name from first_name and last_name into name
        if user.name in ['', None]:
            if user.first_name != '':
                user.name = user.first_name + (
                    ' ' + user.last_name if user.last_name != '' else '')

                user.save()

user_logged_in.connect(handle_ldap_login)
