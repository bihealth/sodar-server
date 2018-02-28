# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-28 09:25
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('samplesheets', '0008_auto_20180227_1818'),
    ]

    operations = [
        migrations.AddField(
            model_name='arc',
            name='api_id',
            field=models.CharField(blank=True, help_text='ISA API object id', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='arc',
            name='omics_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='Internal UUID for the object', unique=True),
        ),
        migrations.AddField(
            model_name='arc',
            name='retraction_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Consent retraction data'),
        ),
        migrations.AddField(
            model_name='arc',
            name='sharing_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Data sharing rules'),
        ),
    ]
