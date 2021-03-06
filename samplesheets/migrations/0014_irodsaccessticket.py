# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-11-19 12:23
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projectroles', '0015_fix_appsetting_constraint'),
        ('samplesheets', '0013_isatab'),
    ]

    operations = [
        migrations.CreateModel(
            name='IrodsAccessTicket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sodar_uuid', models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True)),
                ('ticket', models.CharField(help_text='Ticket token', max_length=255)),
                ('path', models.CharField(help_text='Path to iRODS collection', max_length=255)),
                ('label', models.CharField(blank=True, help_text='Ticket label (optional)', max_length=255, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, help_text='DateTime of ticket creation')),
                ('date_expires', models.DateTimeField(blank=True, help_text='DateTime of ticket expiration (leave unset to never expire; click x on righthand-side of field to unset)', null=True)),
                ('assay', models.ForeignKey(blank=True, help_text='Assay the ticket belongs to (optional)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='irods_access_ticket', to='samplesheets.Assay')),
                ('project', models.ForeignKey(help_text='Project the ticket belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='irods_access_ticket', to='projectroles.Project')),
                ('study', models.ForeignKey(help_text='Study the ticket belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='irods_access_ticket', to='samplesheets.Study')),
                ('user', models.ForeignKey(help_text='User that created the ticket', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='irods_access_ticket', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date_created'],
            },
        ),
    ]
