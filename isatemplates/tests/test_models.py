"""Tests for models in the isatemplates app"""

import json
import os
import random
import string

from cubi_isa_templates import _TEMPLATES as CUBI_TEMPLATES
from collections import OrderedDict
from typing import Optional

from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.utils.text import slugify

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.models import SODARUser

from isatemplates.models import CookiecutterISAFile, CookiecutterISATemplate


# Local constants
TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), 'templates', 'test_generic'
)
TEMPLATE_JSON_PATH = os.path.join(TEMPLATE_PATH, 'cookiecutter.json')
TEMPLATE_NAME = 'custom_generic'
TEMPLATE_NAME_AUTO_GEN = 'custom_generic_rna_sequencing_isa_tab_template'
TEMPLATE_DESC = 'Custom generic RNA sequencing ISA-tab template'
ISA_FILE_DIR = '{{cookiecutter.__output_dir}}'
INV_FILE_NAME = 'i_Investigation.txt'
INV_PATH = os.path.join(TEMPLATE_PATH, ISA_FILE_DIR, INV_FILE_NAME)


class CookiecutterISATemplateMixin:
    """Helpers for CookiecutterISATemplate model testing"""

    @classmethod
    def make_isa_template(
        cls,
        name: Optional[str],
        description: str,
        configuration: str,
        active: bool = True,
        user: Optional[SODARUser] = None,
    ) -> CookiecutterISATemplate:
        """
        Create and save a CookiecutterISATemplate object.

        :param name: String or None
        :param description: String
        :param configuration: String
        :param active: Boolean
        :param user: User object or None
        :return: CookiecutterISATemplate object
        """
        return CookiecutterISATemplate.objects.create(
            name=name,
            description=description,
            configuration=configuration,
            active=active,
            user=user,
        )


class CookiecutterISAFileMixin:
    """Helpers for CookiecutterISAFile model testing"""

    @classmethod
    def make_isa_file(
        cls, template: CookiecutterISATemplate, file_name: str, content: str
    ) -> CookiecutterISAFile:
        """
        Create and save a CookiecutterISAFile object.

        :param template: CookiecutterISATemplate object
        :param file_name: String
        :param content: String
        :return: CookiecutterISAFile object
        """
        return CookiecutterISAFile.objects.create(
            template=template, file_name=file_name, content=content
        )


class CookiecutterISAModelTestBase(TestCase):
    """Base class for Cookiecutter ISA-Tab template model tests"""

    def setUp(self):
        self.user = self.make_user('superuser')
        self.user.is_superuser = True
        self.user.save()


class TestCookiecutterISATemplate(
    CookiecutterISATemplateMixin, CookiecutterISAModelTestBase
):
    """Tests for CookiecutterISATemplate"""

    def setUp(self):
        super().setUp()
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            self.configuration = f.read().decode('utf-8')
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration=self.configuration,
            active=True,
            user=self.user,
        )

    def test_initialization(self):
        """Test CookiecutterISATemplate initialization"""
        expected = {
            'id': self.template.pk,
            'name': TEMPLATE_NAME,
            'description': TEMPLATE_DESC,
            'configuration': self.configuration,
            'active': True,
            'user': self.user.pk,
            'sodar_uuid': self.template.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.template), expected)

    def test_save_empty_name(self):
        """Test save() with empty name"""
        self.template.name = None
        self.template.save()
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, TEMPLATE_NAME_AUTO_GEN)

    def test_save_non_slugified_name(self):
        """Test save with non-slugified name"""
        name = 'Non-slugified name'
        self.template.name = name
        self.template.save()
        self.template.refresh_from_db()
        self.assertEqual(
            self.template.name, slugify(name.lower()).replace('-', '_')
        )

    def test_save_empty_name_long_desc(self):
        """Test save() with empty name and long description"""
        desc = ''.join(random.choice(string.ascii_letters) for _ in range(2048))
        self.template.name = None
        self.template.description = desc
        self.template.save()
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, desc.lower()[:255])
        self.assertEqual(self.template.description, desc)

    def test_save_duplicate_cubi_name(self):
        """Test save() with name found in CUBI templates"""
        self.template.name = CUBI_TEMPLATES[0].name
        with self.assertRaises(ValidationError):
            self.template.save()

    def test_save_duplicate_cubi_description(self):
        """Test save() with description found in CUBI templates"""
        # NOTE: Test with different case to ensure this still gets caught
        self.template.name = CUBI_TEMPLATES[0].name.upper()
        with self.assertRaises(ValidationError):
            self.template.save()

    def test_str(self):
        """Test CookiecutterISATemplate.__str__()"""
        self.assertEqual(self.template.__str__(), self.template.name)

    def test_repr(self):
        """Test CookiecutterISATemplate.__repr__()"""
        values = [
            self.template.name,
            self.template.description,
            self.template.get_config_dict(),
            self.user.sodar_uuid,
            self.template.date_created,
            self.template.date_modified,
            self.template.sodar_uuid,
        ]
        expected = 'CookiecutterISATemplate({})'.format(
            ', '.join('\'{}\''.format(x) for x in values)
        )
        self.assertEqual(self.template.__repr__(), expected)

    def test_get_config_dict(self):
        """Test get_config_dict()"""
        ret = self.template.get_config_dict()
        self.assertIsInstance(ret, OrderedDict)
        self.assertEqual(
            ret, json.loads(self.configuration, object_pairs_hook=OrderedDict)
        )


class TestCookiecutterISAFile(
    CookiecutterISATemplateMixin,
    CookiecutterISAFileMixin,
    CookiecutterISAModelTestBase,
):
    """Tests for CookiecutterISAFile"""

    def setUp(self):
        super().setUp()
        with open(TEMPLATE_JSON_PATH, 'rb') as f:
            self.configuration = f.read().decode('utf-8')
        self.template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration=self.configuration,
            active=True,
            user=self.user,
        )
        with open(INV_PATH, 'r', encoding='utf-8') as f:
            self.file_content = f.read()
        self.file = self.make_isa_file(
            template=self.template,
            file_name=INV_FILE_NAME,
            content=self.file_content,
        )

    def test_initialization(self):
        """Test CookiecutterISAFile initialization"""
        expected = {
            'id': self.file.pk,
            'template': self.template.pk,
            'file_name': INV_FILE_NAME,
            'content': self.file_content,
            'sodar_uuid': self.file.sodar_uuid,
        }
        self.assertEqual(model_to_dict(self.file), expected)

    def test_save_invalid_name_prefix(self):
        """Test save() with invalid name prefix"""
        self.file.file_name = 'x_Investigation.txt'
        with self.assertRaises(ValueError):
            self.file.save()

    def test_str(self):
        """Test CookiecutterISAFile.__str__()"""
        expected = f'{self.template.name}: {self.file.file_name}'
        self.assertEqual(self.file.__str__(), expected)

    def test_repr(self):
        """Test CookiecutterISAFile.__repr__()"""
        values = [
            self.template.sodar_uuid,
            self.file.file_name,
            self.file_content,
            self.file.sodar_uuid,
        ]
        expected = 'CookiecutterISAFile({})'.format(
            ', '.join('\'{}\''.format(x) for x in values)
        )
        self.assertEqual(self.file.__repr__(), expected)
