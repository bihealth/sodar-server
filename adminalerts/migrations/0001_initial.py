# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-03 09:54
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminAlert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(help_text='Alert message to be shown for users', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Full description of alert (optional, will be shown on a separate page)', null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, help_text='Alert creation timestamp')),
                ('date_expire', models.DateTimeField(help_text='Alert expiration timestamp')),
                ('active', models.BooleanField(default=True, help_text='Status of the invite (False if claimed or revoked)')),
                ('user', models.ForeignKey(help_text='Superuser who has set the alert', on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
