# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-27 10:16
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samplesheets', '0011_remove_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='genericmaterial',
            name='extra_material_type',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='Extra material type (from "material_type")', null=True),
        ),
        migrations.AddField(
            model_name='investigation',
            name='archive_name',
            field=models.CharField(blank=True, help_text='File name of the original archive if imported', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='investigation',
            name='contacts',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Investigation contacts'),
        ),
        migrations.AddField(
            model_name='investigation',
            name='public_release_date',
            field=models.DateField(help_text='Public release date', null=True),
        ),
        migrations.AddField(
            model_name='investigation',
            name='publications',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Investigation publications'),
        ),
        migrations.AddField(
            model_name='investigation',
            name='submission_date',
            field=models.DateField(help_text='Submission date', null=True),
        ),
        migrations.AddField(
            model_name='study',
            name='contacts',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Study contacts'),
        ),
        migrations.AddField(
            model_name='study',
            name='public_release_date',
            field=models.DateField(help_text='Public release date', null=True),
        ),
        migrations.AddField(
            model_name='study',
            name='publications',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Study publications'),
        ),
        migrations.AddField(
            model_name='study',
            name='submission_date',
            field=models.DateField(help_text='Submission date', null=True),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='item_type',
            field=models.CharField(choices=[('SOURCE', 'Source'), ('MATERIAL', 'Material'), ('SAMPLE', 'Sample'), ('DATA', 'Data File')], default='MATERIAL', help_text='Type of item (SOURCE, MATERIAL, SAMPLE, DATA)', max_length=255),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='material_type',
            field=models.CharField(blank=True, help_text='Material type (from "type")', max_length=255, null=True),
        ),
    ]
