"""Utilities for User extensions"""

from django.contrib.auth.models import Group

SYSTEM_USER_GROUP = 'system'


def set_user_group(user):
    """Set user group based on user name"""

    if user.username.find('@') != -1:
        group_name = user.username.split('@')[1].lower()

    else:
        group_name = SYSTEM_USER_GROUP

    group, created = Group.objects.get_or_create(name=group_name)

    if group not in user.groups.all():
        group.user_set.add(user)
        print('Added user "{}" in group "{}"'.format(
            user.username, group_name))  # DEBUG
