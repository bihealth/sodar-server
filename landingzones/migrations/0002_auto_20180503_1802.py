# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-05-03 16:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landingzones', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='landingzone',
            name='status',
            field=models.CharField(default='CREATING', help_text='Status of landing zone', max_length=64),
        ),
        migrations.AlterField(
            model_name='landingzone',
            name='status_info',
            field=models.CharField(blank=True, default='Creating landing zone in iRODS', help_text='Additional status information', max_length=1024, null=True),
        ),
    ]
