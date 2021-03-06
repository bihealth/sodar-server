# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-23 10:53
from __future__ import unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samplesheets', '0005_rename_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assay',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='investigation',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='process',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='study',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
    ]
