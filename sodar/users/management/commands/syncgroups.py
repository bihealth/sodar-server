from django.contrib import auth
from django.core.management.base import BaseCommand
from django.db import transaction

from sodar.users.utils import set_user_group


User = auth.get_user_model()


class Command(BaseCommand):
    help = 'Synchronizes user groups based on user name'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        print('Synchronizing user groups')

        with transaction.atomic():
            for user in User.objects.all():
                user.groups.clear()
                user.save()
                group_name = set_user_group(user)

                if group_name:
                    print('{} -> {}'.format(user.username, group_name))

        print(
            'Synchronized groups for {} users'.format(
                User.objects.all().count()
            )
        )
