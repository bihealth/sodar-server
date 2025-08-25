"""Models for the isatemplates app"""

import json
import uuid

from cubi_isa_templates import _TEMPLATES as CUBI_TEMPLATES
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


# Local constants
ISA_FILE_PREFIXES = ['i_', 's_', 'a_']
INVALID_FILE_PREFIX_MSG = (
    'Invalid file name, must start with one of: {}'
).format(', '.join(ISA_FILE_PREFIXES))


class CookiecutterISATemplate(models.Model):
    """Cookiecutter ISA-Tab template model"""

    #: Template ID
    name = models.CharField(
        max_length=255,
        unique=True,
        blank=False,
        help_text='Internal unique template ID, leave blank to auto-generate',
    )

    #: Template description
    description = models.CharField(
        max_length=4096,
        unique=True,
        blank=False,
        help_text='Template description, used as display name in UI',
    )

    #: Configuration from cookiecutter.json file
    configuration = models.TextField(
        blank=False, help_text='Configuration from cookiecutter.json file'
    )

    #: Display template for users
    active = models.BooleanField(
        default=True, help_text='Display template for users in UI'
    )

    #: User who last edited the template
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='cookiecutter_templates',
        null=True,  # Keep null in case we need a management command for this
        help_text='User who last edited the template',
        on_delete=models.CASCADE,
    )

    #: DateTime of template creation
    date_created = models.DateTimeField(
        auto_now_add=True, help_text='DateTime of template creation'
    )

    #: DateTime of last template modification
    date_modified = models.DateTimeField(
        auto_now=True, help_text='DateTime of template modification'
    )

    #: SODAR UUID for the object
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='SODAR UUID for the object'
    )

    def __str__(self):
        return self.name

    def __repr__(self):
        values = [
            self.name,
            self.description,
            self.get_config_dict(),
            self.user.sodar_uuid if self.user else None,
            self.date_created,
            self.date_modified,
            self.sodar_uuid,
        ]
        return 'CookiecutterISATemplate({})'.format(
            ', '.join('\'{}\''.format(x) for x in values)
        )

    def _validate_cubi(self):
        """Validate uniqueness with CUBI templates"""
        if self.name in [t.name for t in CUBI_TEMPLATES]:
            raise ValidationError('Name found in CUBI templates')
        if self.description.lower() in [
            t.description.lower() for t in CUBI_TEMPLATES
        ]:
            raise ValidationError('Description found in CUBI templates')

    def save(self, **kwargs):
        if not self.name:  # Auto-generate name if not filled
            self.name = self.description[:255]
        # Force slugify on name
        self.name = slugify(self.name.lower()).replace('-', '_')
        # Validate against CUBI templates (NOTE: also if disabled)
        self._validate_cubi()
        super().save(**kwargs)

    # Custom row-level functions

    def get_config_dict(self):
        """
        Return configuration as ordered dictionary.

        :return: OrderedDict
        """
        return json.loads(self.configuration, object_pairs_hook=OrderedDict)


class CookiecutterISAFile(models.Model):
    """Cookiecutter ISA-Tab investigation/study/assay file model"""

    #: Template relation
    template = models.ForeignKey(
        CookiecutterISATemplate,
        related_name='files',
        null=False,
        help_text='Template to which this file belongs',
        on_delete=models.CASCADE,
    )

    #: Template file name
    file_name = models.CharField(
        max_length=4096,
        unique=False,
        blank=False,
        help_text='Template file name',
    )

    #: Template file content
    content = models.TextField(blank=False, help_text='Template file content')

    #: SODAR UUID for the object
    sodar_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text='SODAR UUID for the object'
    )

    def __str__(self):
        return f'{self.template.name}: {self.file_name}'

    def __repr__(self):
        values = [
            self.template.sodar_uuid,
            self.file_name,
            self.content,
            self.sodar_uuid,
        ]
        return 'CookiecutterISAFile({})'.format(
            ', '.join('\'{}\''.format(x) for x in values)
        )

    def _validate_file_name(self):
        if self.file_name[:2] not in ISA_FILE_PREFIXES:
            raise ValueError(INVALID_FILE_PREFIX_MSG)

    def save(self, **kwargs):
        self._validate_file_name()
        super().save(**kwargs)
