# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-06-12 12:34
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('samplesheets', '0008_genericmaterial_extract_label_json'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genericmaterial',
            name='extract_label',
        ),
    ]
