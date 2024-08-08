"""Tests for ISATemplateAPI in the isatemplates app"""

from cubi_isa_templates import IsaTabTemplate, _TEMPLATES as CUBI_TEMPLATES

from django.test import override_settings

from test_plus.test import TestCase

# Projectroles dependency
from projectroles.plugins import get_backend_api

from isatemplates.api import ISATemplateAPI
from isatemplates.models import CookiecutterISATemplate
from isatemplates.tests.test_models import (
    CookiecutterISATemplateMixin,
    TEMPLATE_NAME,
    TEMPLATE_DESC,
)


# Local constants
CUBI_TEMPLATE_NAME = 'bulk_rnaseq'


class TestISATemplateAPI(CookiecutterISATemplateMixin, TestCase):
    """Tests for ISATemplateAPI"""

    @classmethod
    def _sort_list(cls, tpl_list):
        """Sort template list"""
        return sorted(tpl_list, key=lambda x: x['description'].lower())

    def setUp(self):
        self.user = self.make_user('superuser')
        self.user.is_superuser = True
        self.user.save()
        self.tpl_backend = get_backend_api('isatemplates_backend')

    def test_get_backend_api(self):
        """Test get_backend_api() with isatemplates backend"""
        self.assertIsInstance(
            get_backend_api('isatemplates_backend'), ISATemplateAPI
        )

    def test_get_list(self):
        """Test get_list() with default settings"""
        expected = [
            {
                'name': t.name,
                'description': t.description[0].upper() + t.description[1:],
            }
            for t in CUBI_TEMPLATES
        ]
        self.assertEqual(self.tpl_backend.get_list(), self._sort_list(expected))

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_get_list_disable_cubi(self):
        """Test get_list() with CUBI templates disabled"""
        self.assertEqual(self.tpl_backend.get_list(), [])

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_get_list_disable_cubi_with_custom(self):
        """Test get_list() with custom template only"""
        template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        expected = {'name': template.name, 'description': template.description}
        self.assertEqual(self.tpl_backend.get_list(), [expected])

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_get_list_disable_cubi_with_custom_inactive(self):
        """Test get_list() with custom template disabled"""
        self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=False,
            user=self.user,
        )
        self.assertEqual(self.tpl_backend.get_list(), [])

    def test_get_list_both_types(self):
        """Test get_list() with CUBI and custom templates"""
        template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        expected = [
            {
                'name': t.name,
                'description': t.description[0].upper() + t.description[1:],
            }
            for t in CUBI_TEMPLATES
        ]
        expected.append(
            {'name': template.name, 'description': template.description}
        )
        self.assertEqual(self.tpl_backend.get_list(), self._sort_list(expected))

    def test_get_template_cubi(self):
        """Test get_template() with CUBI template"""
        self.assertIsInstance(
            self.tpl_backend.get_template(CUBI_TEMPLATE_NAME), IsaTabTemplate
        )

    def test_get_template_custom(self):
        """Test get_template() with custom template"""
        template = self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        ret = self.tpl_backend.get_template(TEMPLATE_NAME)
        self.assertIsInstance(ret, CookiecutterISATemplate)
        self.assertEqual(template, ret)

    def test_get_template_non_existent(self):
        """Test get_template() with non-existent template"""
        with self.assertRaises(ValueError):
            self.tpl_backend.get_template(TEMPLATE_NAME)

    def test_is_template_cubi(self):
        """Test is_template() with CUBI template"""
        self.assertTrue(self.tpl_backend.is_template(CUBI_TEMPLATE_NAME))
        self.assertFalse(self.tpl_backend.is_template(TEMPLATE_NAME))

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_is_template_cubi_disable(self):
        """Test is_template() with CUBI templates disabled"""
        self.assertFalse(self.tpl_backend.is_template(CUBI_TEMPLATE_NAME))
        self.assertFalse(self.tpl_backend.is_template(TEMPLATE_NAME))

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_is_template_custom(self):
        """Test is_template() with custom template"""
        self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        self.assertFalse(self.tpl_backend.is_template(CUBI_TEMPLATE_NAME))
        self.assertTrue(self.tpl_backend.is_template(TEMPLATE_NAME))

    @override_settings(ISATEMPLATES_ENABLE_CUBI_TEMPLATES=False)
    def test_is_template_custom_inactive(self):
        """Test is_template() with inactive custom template"""
        self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=False,
            user=self.user,
        )
        self.assertFalse(self.tpl_backend.is_template(CUBI_TEMPLATE_NAME))
        self.assertFalse(self.tpl_backend.is_template(TEMPLATE_NAME))

    def test_is_template_both(self):
        """Test is_template() with both types"""
        self.make_isa_template(
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESC,
            configuration='{}',
            active=True,
            user=self.user,
        )
        self.assertTrue(self.tpl_backend.is_template(CUBI_TEMPLATE_NAME))
        self.assertTrue(self.tpl_backend.is_template(TEMPLATE_NAME))

    def test_get_model(self):
        """Test get_model()"""
        self.assertEqual(self.tpl_backend.get_model(), CookiecutterISATemplate)
