# Generated by Django 3.2.25 on 2024-07-31 08:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CookiecutterISATemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Internal unique template ID, leave blank to auto-generate', max_length=255, unique=True)),
                ('description', models.CharField(help_text='Template description, used as display name in UI', max_length=4096, unique=True)),
                ('configuration', models.TextField(help_text='Configuration from cookiecutter.json file')),
                ('active', models.BooleanField(default=True, help_text='Display template for users in UI')),
                ('date_created', models.DateTimeField(auto_now_add=True, help_text='DateTime of template creation')),
                ('date_modified', models.DateTimeField(auto_now=True, help_text='DateTime of template modification')),
                ('sodar_uuid', models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True)),
                ('user', models.ForeignKey(help_text='User who last edited the template', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cookiecutter_templates', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CookiecutterISAFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(help_text='Template file name', max_length=4096)),
                ('content', models.TextField(help_text='Template file content')),
                ('sodar_uuid', models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True)),
                ('template', models.ForeignKey(help_text='Template to which this file belongs', on_delete=django.db.models.deletion.CASCADE, related_name='files', to='isatemplates.cookiecutterisatemplate')),
            ],
        ),
    ]
